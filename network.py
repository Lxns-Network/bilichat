import json
import mimetypes
import typing as T
from pathlib import Path
from .logger import Network

import aiohttp

class fetch:
    @staticmethod
    async def http_post(url, data_map, **_):
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data_map, **_) as response:
                data = await response.text(encoding="utf-8")
                Network.debug(f"requested url={url}, by data_map={data_map}, and status={response.status}, data={data}")
                response.raise_for_status()
        try:
            return json.loads(data)
        except json.decoder.JSONDecodeError:
            Network.error(f"requested {url} with {data_map}, responsed {data}, decode failed...")

    @staticmethod
    async def http_get(url, params=None, **_): 
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, **_) as response:
                response.raise_for_status()
                data = await response.text(encoding="utf-8")
                Network.debug(f"requested url={url}, by params={params}, and status={response.status}, data={data}")
        try:
            return json.loads(data)
        except json.decoder.JSONDecodeError:
            Network.error(f"requested {url} with {params}, responsed {data}, decode failed...")

    @staticmethod
    async def upload(url, filedata: bytes, addon_dict: dict, **_):
        upload_data = aiohttp.FormData()
        upload_data.add_field("file_up", filedata)
        for item in addon_dict.items():
            upload_data.add_fields(item)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=upload_data, **_) as response:
                response.raise_for_status()
                Network.debug(f"requested url={url}, and status={response.status}, addon_dict={addon_dict}")
                return await response.json()