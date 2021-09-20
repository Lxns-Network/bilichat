from pydantic import BaseModel

class Group(BaseModel):
    group_id: int
    group_cover: str
    group_name: str
    group_notice: str
    owner_uid: int
    fans_medal_name: str