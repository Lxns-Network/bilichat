import logbook
from logbook import Logger, StreamHandler
from logbook import (
    INFO,
    DEBUG
)
import os
import sys

logbook.set_datetime_format('local')
stream_handler = StreamHandler(sys.stdout, level=INFO if not os.environ.get("BILICHAT_DEBUG") else DEBUG)
stream_handler.format_string = '[{record.time:%Y-%m-%d %H:%M:%S}][BiliChat][{record.channel}] {record.message}'
stream_handler.push_application()

Event = Logger('Event', level=INFO)
Network = Logger("Network", level=DEBUG)
Session = Logger("Session", level=INFO)
Protocol = Logger("Protocol", level=INFO)