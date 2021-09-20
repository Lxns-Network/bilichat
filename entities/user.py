from pydantic import BaseModel

class UserLevel(BaseModel):
    current_exp: int
    current_level: int
    current_min: int
    next_exp: int

class UserNameplate(BaseModel):
    condition: str
    image: str
    image_small: str
    level: str
    name: str
    nid: int

class UserOfficialVerify(BaseModel):
    desc: str
    type: int

class UserPendant(BaseModel):
    expire: int
    image: str
    image_enhance: str
    image_enhance_frame: str
    name: str
    pid: int

class UserVipLabel(BaseModel):
    path: str

class UserVip(BaseModel):
    accessStatus: int
    dueRemark: str
    label: UserVipLabel
    themeType: int
    vipDueDate: int
    vipStatus: int
    vipStatusWarn: str
    vipType: int

class User(BaseModel):
    DisplayRank: int
    face: str
    level_info: UserLevel
    mid: str
    nameplate: UserNameplate
    official_verify: UserOfficialVerify
    pendant: UserPendant
    rank: int
    sex: int
    sign: str
    uid: int
    uname: str
    vip: UserVip