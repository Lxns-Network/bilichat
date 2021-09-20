from collections import namedtuple
from pydantic import BaseModel

InternalEvent = namedtuple("Event", ("name", "body"))