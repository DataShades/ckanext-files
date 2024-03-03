import six
import uuid
import os
from werkzeug.datastructures import FileStorage

from google.cloud.storage import Client
from google.oauth2.service_account import Credentials
from .base import Storage, Uploader, Manager, Capability
from ckanext.files import utils

if six.PY3:
    from typing import Any


class GoogleCloudUploader(Uploader):
    storage = None  # type: GoogleCloudStorage # pyright: ignore

    required_options = ["bucket"]
    capabilities = utils.combine_capabilities(Capability.CREATE)

    def upload(self, name, upload, extras):  # pragma: no cover
        # type: (str, FileStorage, dict[str, Any]) -> dict[str, Any]
        filename = str(uuid.uuid4())
        filepath = os.path.join(self.storage.settings["path"], filename)

        client = self.storage.client
        blob = client.bucket(self.storage.settings["bucket"]).blob(filepath)
        blob.upload_from_file(upload.stream)
        return {"filename": filename, "content_type": upload.content_type}


class GoogleCloudManager(Manager):
    storage = None  # type: GoogleCloudStorage # pyright: ignore
    required_options = ["bucket"]
    capabilities = utils.combine_capabilities(Capability.REMOVE)

    def remove(self, data):
        # type: (dict[str, Any]) -> bool
        filepath = os.path.join(self.storage.settings["path"], data["filename"])
        client = self.storage.client  # type: Client
        blob = client.bucket(self.storage.settings["bucket"]).blob(filepath)
        blob.delete()
        return True


class GoogleCloudStorage(Storage):
    def __init__(self, **settings):
        # type: (**Any) -> None
        settings["path"] = settings.setdefault("path", "").lstrip("/")

        super(GoogleCloudStorage, self).__init__(**settings)

        credentials = None
        credentials_file = settings.get("credentials_file", None)
        if credentials_file:
            credentials = Credentials.from_service_account_file(credentials_file)

        self.client = Client(credentials=credentials)

    def make_uploader(self):
        return GoogleCloudUploader(self)

    def make_manager(self):
        return GoogleCloudManager(self)
