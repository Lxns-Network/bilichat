import typing as T
import json
import time
import io

from .entities import User, Group
from .event.models import BotMessage
from .network import fetch

class BiliChat_Protocol:
    async def _sendMessage(self, receiver_id: int, receiver_type: int, message_type: int, content, at_uid: int = 0):
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False)
        data = {
            'msg[sender_uid]': self.cookies['DedeUserID'],
            'msg[receiver_id]': receiver_id,
            'msg[receiver_type]': receiver_type,
            'msg[msg_type]': message_type,
            'msg[msg_status]': 0,
            'msg[content]': content,
            'msg[timestamp]': int(time.time()),
            'msg[new_face_version]': 0,
            'msg[dev_id]': "3201E4DA-BAC0-4308-816B-294DAF70A608",
            'from_firework': 0,
            'build': 0,
            'mobi_app': 'web',
            'csrf_token': self.cookies['bili_jct'],
            'csrf': self.cookies['bili_jct']
        }
        if at_uid != 0:
            data['msg[at_uids][0]'] = at_uid
        
        result = await fetch.http_post(f"{self.baseurl}/web_im/v1/web_im/send_msg", data_map=data, cookies=self.cookies)
        return result["data"]

    async def sendPrivateMessage(self, receiver_id: int, message: str, at_uid: int = 0):
        return BotMessage.parse_obj(
            await self._sendMessage(receiver_id, 1, 1, {
                'content': message
            }, at_uid)
        )

    async def sendGroupMessage(self, receiver_id: int, message: str, at_uid: int = 0):
        return BotMessage.parse_obj(
            await self._sendMessage(receiver_id, 2, 1, {
                'content': message
            }, at_uid)
        )

    async def uploadPrivateImage(self, receiver_id: int, path: str, at_uid: int = 0):
        image = open(path, "rb").read()
        result = await fetch.upload("https://api.bilibili.com/x/dynamic/feed/draw/upload_bfs", image, {
            "biz": "im",
            "csrf": self.cookies['bili_jct'],
            "build": "0",
            "mobi_app": "web"
        }, cookies=self.cookies)
        return BotMessage.parse_obj(
            await self._sendMessage(receiver_id, 1, 2, {
                "url": result["data"]["image_url"],
                "height": result["data"]["image_height"],
                "width": result["data"]["image_width"],
                "imageType": "jpeg",
                "original": 1,
                "size": int(len(io.BytesIO(image).read()) / 1e3)
            }, at_uid)
        )

    async def uploadGroupImage(self, receiver_id: int, path: str, at_uid: int = 0):
        image = open(path, "rb").read()
        result = await fetch.upload("https://api.bilibili.com/x/dynamic/feed/draw/upload_bfs", image, {
            "biz": "im",
            "csrf": self.cookies['bili_jct'],
            "build": "0",
            "mobi_app": "web"
        }, cookies=self.cookies)
        return BotMessage.parse_obj(
            await self._sendMessage(receiver_id, 2, 2, {
                "url": result["data"]["image_url"],
                "height": result["data"]["image_height"],
                "width": result["data"]["image_width"],
                "imageType": "jpeg",
                "original": 1,
                "size": int(len(io.BytesIO(image).read()) / 1e3)
            }, at_uid)
        )
    
    async def recallPrivateMessage(self, receiver_id: int, message_key: int, at_uid: int = 0):
        return BotMessage.parse_obj(
            await self._sendMessage(receiver_id, 1, 5, message_key, at_uid)
        )
    
    async def recallGroupMessage(self, receiver_id: int, message_key: int, at_uid: int = 0):
        return BotMessage.parse_obj(
            await self._sendMessage(receiver_id, 2, 5, message_key, at_uid)
        )

    async def getUserDetail(self, user_id: int):
        result = await fetch.http_get(f"{self.baseurl}/account/v1/user/infos", params={
            "uids": user_id,
            "build": 0,
            "mobi_app": "web"
        }, cookies=self.cookies)
        if result['code'] != 0:
            print(result)
        return User.parse_obj(result["data"][0])

    async def getGroupDetail(self, group_id: int):
        result = await fetch.http_get(f"{self.baseurl}/link_group/v1/group/detail", params={
            "group_id": group_id,
        }, cookies=self.cookies)
        if result['code'] != 0:
            print(result)
        return Group.parse_obj(result["data"])
