import uuid
import logging
import six
import os
from werkzeug.datastructures import FileStorage
from ckanext.files import utils
from .base import Storage, Uploader, Capability, Manager

if six.PY3:
    from typing import Any

log = logging.getLogger(__name__)


class FileSystemUploader(Uploader):
    required_options = ["path"]
    capabilities = utils.combine_capabilities(Capability.CREATE)

    def upload(self, name, upload, extras):  # pragma: no cover
        # type: (str, FileStorage, dict[str, Any]) -> dict[str, Any]
        filename = str(uuid.uuid4())
        filepath = os.path.join(self.storage.settings["path"], filename)

        upload.save(filepath)

        return {"filename": filename, "content_type": upload.content_type}


class FileSystemManager(Manager):
    required_options = ["path"]
    capabilities = utils.combine_capabilities(Capability.REMOVE)

    def remove(self, data):
        # type: (dict[str, Any]) -> bool
        filepath = os.path.join(self.storage.settings["path"], data["filename"])
        if not os.path.exists(filepath):
            return False

        os.remove(filepath)
        return True


class FileSystemStorage(Storage):
    capabilities = utils.combine_capabilities(
        Capability.CREATE, Capability.STREAM, Capability.REMOVE
    )

    def make_uploader(self):
        return FileSystemUploader(self)

    def make_manager(self):
        return FileSystemManager(self)

    def __init__(self, **settings):
        # type: (**Any) -> None
        path = self.ensure_option(settings, "path")
        if not os.path.exists(path):
            os.makedirs(path)

        super(FileSystemStorage, self).__init__(**settings)


class PublicFileSystemStorage(FileSystemStorage):
    capabilities = utils.combine_capabilities(
        FileSystemStorage.capabilities, Capability.DOWNLOAD
    )

    def __init__(self, **settings):
        # type: (**Any) -> None
        self.ensure_option(settings, "public_root")
        super(PublicFileSystemStorage, self).__init__(**settings)
