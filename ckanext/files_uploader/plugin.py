import glob
import os

import ckan.plugins as p

from ckanext.files.storage import fs

from ckanext.files import types, interfaces, shared  # isort: skip # noqa: F401


class FilesUploaderPlugin(p.SingletonPlugin):
    p.implements(p.IUploader)
    p.implements(interfaces.IFiles)

    def files_get_storage_adapters(self):
        # type: () -> dict[str, types.Any]

        return {
            "files_uploader:resource": ResourceStorage,
            # "files_uploader:group": ...,
            # "files_uploader:user": ...,
        }

    # IUploader
    def get_uploader(self, upload_to, old_filename):
        # type: (str, str | None) -> types.PUploader | None
        return Uploader(upload_to, old_filename)

    def get_resource_uploader(self, resource):
        # type: (dict[str, types.Any]) -> types.PResourceUploader | None
        return ResourceUploader(resource)


class Uploader(object):
    def __init__(self, object_type, old_filename=None):
        # type: (str, str | None) -> None
        ...

    def upload(self, max_size=2):
        # type: (int) -> None
        ...

    def update_data_dict(self, data_dict, url_field, file_field, clear_field):
        # type: (dict[str, types.Any], str, str, str) -> None
        ...


class ResourceUploader(object):
    # mimetype: Optional[str]
    # filesize: int

    def __init__(self, resource):
        # type: (dict[str, types.Any]) -> None
        self.mimetype = types.cast("str|None", None)
        self.filesize = 0
        self.resource = resource
        self.storage = shared.get_storage("resource")

    def get_path(self, id: str) -> str:
        # type: (str) -> str
        return os.path.join(
            self.storage.settings["path"],
            self.storage.compute_name(id, {}, None),
        )

    def upload(self, id, max_size=10):
        # type: (str, int) -> None
        ...


class ResourceStorage(fs.FileSystemStorage):
    def compute_name(self, name, extras, upload=None):
        # type: (str, dict[str, types.Any], types.Upload|None) -> str
        return os.path.join("resources", name[0:3], name[3:6], name[6:])

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
