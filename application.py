import aiohttp
import asyncio
import inspect
import copy
import time

from contextlib import AsyncExitStack
from typing import Callable, NamedTuple, Awaitable, Any, List, Dict
from async_lru import alru_cache

from .event import InternalEvent
from .event.builtins import ExecutorProtocol, Depend
from .event.models import (
    Message, MessageRecall, MessageItemType
)
from .misc import argument_signature, raiser, TRACEBACKED
from .protocol import BiliChat_Protocol
from .logger import Event, Protocol
from .logger import Session as SessionLogger

class BiliChat(BiliChat_Protocol):
    event: Dict[
        str, List[Callable[[Any], Awaitable]]
    ] = {}
    lifecycle: Dict[str, List[Callable]] = {
        "start": [],
        "end": [],
        "around": []
    }
    global_dependencies: List[Depend]
    global_middlewares: List

    def __init__(self,
                 cookies,
                 global_dependencies: List[Depend] = None,
                 global_middlewares: List = None):
        self.global_dependencies = global_dependencies or []
        self.global_middlewares = global_middlewares or []
        self.cookies = dict([l.split("=", 1) for l in cookies.split("; ")])
        self.baseurl = "https://api.vc.bilibili.com"
        self.session_ts = int(round(time.time() * 1000000))

        self.message_list = []
        self.user_list = {}
        self.group_list = {}

    async def http_event(self):
        async with aiohttp.ClientSession() as session:
            max_ack_list = {}
            async with session.get(f"{self.baseurl}/session_svr/v1/session_svr/get_sessions", params={
                "session_type": 4, # 1: 私聊, 2: 通知, 3: 应援团, 4: 全部
                "group_fold": 1,
                "unfollow_fold": 0,
                "sort_rule": 2,
                "build": 0,
                "mobi_app": "web"
            }, cookies=self.cookies) as res: # 获取最新最热最潮 seqno
                received_data = await res.json()
                for _session in received_data["data"]["session_list"]:
                    max_ack_list[_session["talker_id"]] = _session["max_seqno"]
            Protocol.info(f"Connected to uid: {self.cookies['DedeUserID']}")
            while True: # 开始轮询
                session_list = []
                async with session.get(f"{self.baseurl}/session_svr/v1/session_svr/new_sessions", params={
                    "begin_ts": self.session_ts,
                    "build": 0,
                    "mobi_app": "web"
                }, cookies=self.cookies) as res: # 获取有新消息的会话（该接口只有一条最新消息）
                    try:
                        received_data = await res.json()
                    except TypeError:
                        continue
                    if received_data:
                        if received_data['data']['session_list'] is not None:
                            self.session_ts = int(round(time.time() * 1000000))
                            session_list = received_data['data']['session_list']
                
                for _session in session_list: # 获取新消息会话的多条消息
                    talker_id = _session["talker_id"]
                    ack_seqno = max_ack_list.get(talker_id) # 无视机器人开启前的消息
                    if ack_seqno is None: # 新会话
                        ack_seqno = _session["max_seqno"]
                    max_ack_list[talker_id] = _session["max_seqno"]
                    async with session.post(f"{self.baseurl}/svr_sync/v1/svr_sync/update_ack", params={
                        "talker_id": talker_id,
                        "session_type": _session["session_type"],
                        "ack_seqno": ack_seqno,
                        "build": 0,
                        "mobi_app": "web",
                        'csrf_token': self.cookies['bili_jct'],
                        'csrf': self.cookies['bili_jct']
                    }, cookies=self.cookies) as res: # 已读
                        try:
                            received_data = await res.json()
                        except TypeError:
                            continue
                    async with session.get(f"{self.baseurl}/svr_sync/v1/svr_sync/fetch_session_msgs", params={
                        "sender_device_id": 1,
                        "talker_id": talker_id,
                        "session_type": _session["session_type"],
                        "size": 5,
                        "begin_seqno": ack_seqno,
                        "build": 0,
                        "mobi_app": "web"
                    }, cookies=self.cookies) as res:
                        try:
                            received_data = await res.json()
                        except TypeError:
                            continue
                        if received_data:
                            if received_data['data']['messages'] is not None:
                                for _message in received_data['data']['messages']:
                                    message_type_list = {
                                        1: Message, # 文本
                                        2: Message, # 图片
                                        5: MessageRecall # 撤回
                                    }
                                    message = message_type_list[_message["msg_type"]].parse_obj(_message)

                                    user_id = message.sender_uid
                                    if message.receiver_type == 2: # 应援团
                                        group_id = message.receiver_id
                                        if group_id not in self.group_list:
                                            self.group_list[group_id] = await self.getGroupDetail(group_id)
                                    if user_id not in self.user_list:
                                        self.user_list[user_id] = await self.getUserDetail(user_id)
                                    self.message_list.append(message)
                                    await self.queue.put(InternalEvent(
                                        name=self.getEventCurrentName(type(message)),
                                        body=message
                                    ))
                await asyncio.sleep(2) # 每 2 秒轮询一次

    async def event_runner(self):
        while True:
            try:
                event_context: NamedTuple[InternalEvent] = await asyncio.wait_for(self.queue.get(), 3)
            except asyncio.TimeoutError:
                continue
            
            if event_context.name in self.registeredEventNames:
                for event_body in list(self.event.values()) \
                        [self.registeredEventNames.index(event_context.name)]:
                    if event_body:
                        if event_context.name == "Message":
                            msg_type = event_context.body.msg_type
                            member = self.user_list[event_context.body.sender_uid]
                            if msg_type == 1:
                                content = event_context.body.content['content']
                            elif msg_type == 2:
                                content = "[图片]"
                            if event_context.body.receiver_type == 1:
                                Event.info(f"{member.uname} -> {content}")
                            elif event_context.body.receiver_type == 2:
                                group = self.group_list[event_context.body.receiver_id]
                                Event.info(f"{group.group_name} - {member.uname} -> {content}")
                        running_loop = asyncio.get_running_loop()
                        running_loop.create_task(self.executor(event_body, event_context))

    @property
    def registeredEventNames(self):
        return [self.getEventCurrentName(i) for i in self.event.keys()]

    async def executor(self,
                       executor_protocol: ExecutorProtocol,
                       event_context,
                       extra_parameter={},
                       lru_cache_sets=None
                       ):
        lru_cache_sets = lru_cache_sets or {}
        executor_protocol: ExecutorProtocol
        for depend in executor_protocol.dependencies:
            if not inspect.isclass(depend.func):
                depend_func = depend.func
            elif hasattr(depend.func, "__call__"):
                depend_func = depend.func.__call__
            else:
                raise TypeError("must be callable.")

            if depend_func in lru_cache_sets and depend.cache:
                depend_func = lru_cache_sets[depend_func]
            else:
                if depend.cache:
                    original = depend_func
                    if inspect.iscoroutinefunction(depend_func):
                        depend_func = alru_cache(depend_func)
                    else:
                        depend_func = lru_cache(depend_func)
                    lru_cache_sets[original] = depend_func

            result = await self.executor_with_middlewares(
                depend_func, depend.middlewares, event_context, lru_cache_sets
            )
            if result is TRACEBACKED:
                return TRACEBACKED

        ParamSignatures = argument_signature(executor_protocol.callable)
        PlaceAnnotation = self.get_annotations_mapping()
        CallParams = {}
        for name, annotation, default in ParamSignatures:
            if default:
                if isinstance(default, Depend):
                    if not inspect.isclass(default.func):
                        depend_func = default.func
                    elif hasattr(default.func, "__call__"):
                        depend_func = default.func.__call__
                    else:
                        raise TypeError("must be callable.")

                    if depend_func in lru_cache_sets and default.cache:
                        depend_func = lru_cache_sets[depend_func]
                    else:
                        if default.cache:
                            original = depend_func
                            if inspect.iscoroutinefunction(depend_func):
                                depend_func = alru_cache(depend_func)
                            else:
                                depend_func = lru_cache(depend_func)
                            lru_cache_sets[original] = depend_func

                    CallParams[name] = await self.executor_with_middlewares(
                        depend_func, default.middlewares, event_context, lru_cache_sets
                    )
                    continue
                else:
                    raise RuntimeError("checked a unexpected default value.")
            else:
                if annotation in PlaceAnnotation:
                    CallParams[name] = PlaceAnnotation[annotation](event_context)
                    continue
                else:
                    if name not in extra_parameter:
                        raise RuntimeError(f"checked a unexpected annotation: {annotation}")

        async with AsyncExitStack() as stack:
            sorted_middlewares = self.sort_middlewares(executor_protocol.middlewares)
            for async_middleware in sorted_middlewares['async']:
                await stack.enter_async_context(async_middleware)
            for normal_middleware in sorted_middlewares['normal']:
                stack.enter_context(normal_middleware)

            return await self.run_func(executor_protocol.callable, **CallParams, **extra_parameter)
    
    def run(self):
        loop = asyncio.get_event_loop()
        self.queue = asyncio.Queue(loop=loop)
        loop.create_task(self.http_event())
        loop.create_task(self.event_runner())
        try:
            for start_callable in self.lifecycle['start']:
                loop.run_until_complete(self.run_func(start_callable, self))

            for around_callable in self.lifecycle['around']:
                loop.run_until_complete(self.run_func(around_callable, self))

            loop.run_forever()
        except KeyboardInterrupt:
            SessionLogger.info("catched Ctrl-C, exiting..")
        except Exception as e:
            traceback.print_exc()
        finally:
            for around_callable in self.lifecycle['around']:
                loop.run_until_complete(self.run_func(around_callable, self))

            for end_callable in self.lifecycle['end']:
                loop.run_until_complete(self.run_func(end_callable, self))

    def receiver(self,
                 event_name,
                 dependencies: List[Depend] = None,
                 use_middlewares: List[Callable] = None):
        def receiver_warpper(func: Callable):
            if not inspect.iscoroutinefunction(func):
                raise TypeError("event body must be a coroutine function.")
            
            self.event.setdefault(event_name, [])
            self.event[event_name].append(ExecutorProtocol(
                callable=func,
                dependencies=(dependencies or []) + self.global_dependencies,
                middlewares=(use_middlewares or []) + self.global_middlewares
            ))
            return func

        return receiver_warpper

    def getEventCurrentName(self, event_value):
        class_list = (
            Message,
            MessageRecall
        )
        if isinstance(event_value, class_list):  # normal class
            return event_value.__class__.__name__
        elif event_value in class_list:  # message
            return event_value.__name__
        elif isinstance(event_value, (  # enum
            MessageItemType
        )):
            return event_value.name
        else:
            return event_value

    def get_annotations_mapping(self):
        return {
            BiliChat: lambda k: self,
            Message: lambda k: k.body \
                if self.getEventCurrentName(k.body) == "Message" else \
                raiser(ValueError("you cannot setting a unbind argument.")),
            MessageRecall: lambda k: k.body \
                if self.getEventCurrentName(k.body) == "MessageRecall" else \
                raiser(ValueError("you cannot setting a unbind argument.")),
            "Sender": lambda k: k.body.sender \
                if self.getEventCurrentName(k.body) in MessageTypes else \
                raiser(ValueError("Sender is not enable in this type of event.")),
            "Type": lambda k: self.getEventCurrentName(k.body)
        }

    @staticmethod
    def sort_middlewares(iterator):
        return {
            "async": [
                i for i in iterator if all([
                    hasattr(i, "__aenter__"),
                    hasattr(i, "__aexit__")
                ])
            ],
            "normal": [
                i for i in iterator if all([
                    hasattr(i, "__enter__"),
                    hasattr(i, "__exit__")
                ])
            ]
        }

    @staticmethod
    async def run_func(func, *args, **kwargs):
        if inspect.iscoroutinefunction(func):
            await func(*args, **kwargs)
        else:
            func(*args, **kwargs)
