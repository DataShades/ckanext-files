import glob
import os

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan import model
from ckan.lib import uploader

from ckanext.files.model import File
from ckanext.files.storage import fs

from ckanext.files import types, interfaces, shared  # isort: skip # noqa: F401


class FilesUploaderPlugin(p.SingletonPlugin):
    p.implements(p.IUploader)
    p.implements(interfaces.IFiles)

    def files_get_storage_adapters(self):
        # type: () -> dict[str, types.Any]

        return {
            "files_uploader:resource": ResourceStorage,
            "files_uploader:image": ImageStorage,
        }

    # IUploader
    def get_uploader(self, upload_to, old_filename):
        # type: (str, str | None) -> types.PUploader | None
        return Uploader(upload_to, old_filename)

    def get_resource_uploader(self, resource):
        # type: (dict[str, types.Any]) -> types.PResourceUploader | None
        return ResourceUploader(resource)


class Uploader(uploader.Upload):
    def __init__(self, object_type, old_filename=None):
        # type: (str, str | None) -> None
        self.storage = shared.get_storage(image_storage_name())
        super(Uploader, self).__init__(object_type, old_filename)

    def upload(self, max_size=2):
        # type: (int) -> None
        if hasattr(self, "verify_type"):
            self.verify_type()

        if self.filename:
            tk.get_action("files_file_create")(
                {"ignore_auth": True},
                {
                    "name": self.filename,
                    "upload": self.upload_file,
                    "storage": self.storage.settings["name"],
                    "object_type": self.object_type,
                },
            )
            self.clear = True

        if (
            self.clear
            and self.old_filename
            and not self.old_filename.startswith("http")
            and self.old_filepath
        ):
            existing = model.Session.execute(
                File.by_location(self.old_filename, self.storage.settings["name"]),
            ).scalar()
            if not existing:
                return
            tk.get_action("files_file_delete")(
                {"ignore_auth": True},
                {"id": existing.id},
            )


class ResourceUploader(uploader.ResourceUpload):
    # mimetype: Optional[str]
    # filesize: int

    def __init__(self, resource):
        # type: (dict[str, types.Any]) -> None
        self.storage = shared.get_storage(resource_storage_name())
        super(ResourceUploader, self).__init__(resource)

    def get_path(self, id):
        # type: (str) -> str
        return os.path.join(
            self.storage.settings["path"],
            self._file_location(id),
        )

    def _file_location(self, id):
        # type: (str) -> str
        return self.storage.compute_name(id, {"resource_id": id}, None)

    def upload(self, id, max_size=10):
        # type: (str, int) -> None
        # If a filename has been provided (a file is being uploaded)
        # we write it to the filepath (and overwrite it if it already
        # exists). This way the uploaded file will always be stored
        # in the same location
        if self.filename and self.upload_file:
            tk.get_action("files_file_create")(
                {"ignore_auth": True},
                {
                    "name": self.filename,
                    "upload": self.upload_file,
                    "storage": self.storage.settings["name"],
                    "resource_id": id,
                },
            )

        # The resource form only sets self.clear (via the input clear_upload)
        # to True when an uploaded file is not replaced by another uploaded
        # file, only if it is replaced by a link to file.
        # If the uploaded file is replaced by a link, we should remove the
        # previously uploaded file to clean up the file system.
        if self.clear:
            existing = model.Session.execute(
                File.by_location(
                    self._file_location(id),
                    self.storage.settings["name"],
                ),
            ).scalar()
            if not existing:
                return
            tk.get_action("files_file_delete")(
                {"ignore_auth": True},
                {"id": existing.id},
            )


class ImageStorage(fs.FileSystemStorage):
    def compute_name(self, name, extras, upload=None):
        # type: (str, dict[str, types.Any], types.Upload|None) -> str
        return os.path.join("storage", "uploads", extras["object_type"], name)

    def make_manager(self):
        return ImageManager(self)


class ImageManager(fs.FileSystemManager):
    capabilities = shared.combine_capabilities(
        fs.FileSystemManager.capabilities,
        shared.Capability.SCAN,
    )

    def scan(self):
        # type: () -> types.Iterable[str]
        path = self.storage.settings["path"]
        for name in glob.iglob(os.path.join(path, "uploads", "*", "*")):
            yield os.path.relpath(name, path)


class ResourceStorage(fs.FileSystemStorage):
    def compute_name(self, name, extras, upload=None):
        # type: (str, dict[str, types.Any], types.Upload|None) -> str
        res_id = extras["resource_id"]
        return os.path.join("resources", res_id[0:3], res_id[3:6], res_id[6:])

    def make_manager(self):
        return ResourceManager(self)


class ResourceManager(fs.FileSystemManager):
    capabilities = shared.combine_capabilities(
        fs.FileSystemManager.capabilities,
        shared.Capability.SCAN,
    )

    def scan(self):
        # type: () -> types.Iterable[str]
        path = self.storage.settings["path"]
        for name in glob.iglob(os.path.join(path, "resources", "???", "???", "*")):
            yield os.path.relpath(name, path)


def resource_storage_name():
    # type: () -> str
    return tk.config.get("ckanext.files_uploader.resource_storage", "resource")


def image_storage_name():
    # type: () -> str
    return tk.config.get("ckanext.files_uploader.image_storage", "image")
