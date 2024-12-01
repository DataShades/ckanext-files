import contextlib

from .db import DbStorage
from .filebin import FilebinStorage
from .fs import CkanResourceFsStorage, FsStorage, PublicFsStorage
from .link import LinkStorage
from .redis import RedisStorage

with contextlib.suppress(ImportError):
    from .s3 import S3Storage

with contextlib.suppress(ImportError):
    from .google_cloud import GoogleCloudStorage

with contextlib.suppress(ImportError):
    from .opendal import OpenDalStorage

with contextlib.suppress(ImportError):
    from .libcloud import LibCloudStorage


__all__ = [
    "FsStorage",
    "PublicFsStorage",
    "CkanResourceFsStorage",
    "RedisStorage",
    "S3Storage",
    "GoogleCloudStorage",
    "FilebinStorage",
    "OpenDalStorage",
    "LibCloudStorage",
    "DbStorage",
    "LinkStorage",
]
