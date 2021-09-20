import typing as T
from enum import Enum
from pydantic import BaseModel
import json

class MessageItemType(Enum):
    BotMessage = "BotMessage"
    Message = "Message"
    MessageRecall = "MessageRecall"

class BotMessage(BaseModel):
    type: MessageItemType = "BotMessage"
    msg_content: T.Optional[str]
    msg_key: int

    def __init__(self, msg_content: str = "", **_):
        if msg_content != "":
            super().__init__(msg_content=json.loads(msg_content)["content"], **_)

class Message(BaseModel):
    type: MessageItemType = "Message"
    at_uids: list
    content: T.Union[str, dict]
    msg_key: int
    msg_seqno: int
    msg_status: int
    msg_type: int
    new_face_version: T.Optional[int]
    notify_code: str
    receiver_id: int
    receiver_type: int
    sender_uid: int
    timestamp: int

    def __init__(self, content: str, **_):
        super().__init__(content=json.loads(content), **_)

class MessageRecall(BaseModel):
    type: MessageItemType = "MessageRecall"
    at_uids: list
    content: str
    msg_key: int
    msg_seqno: int
    msg_status: int
    msg_type: int
    new_face_version: int
    notify_code: str
    receiver_id: int
    receiver_type: int
    sender_uid: int
    timestamp: int

class Emoji(BaseModel):
    gif_url: T.Optional[str]
    size: int
    text: str
    url: str