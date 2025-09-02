"""Base abstract functionality of the extentsion.

All classes required for specific storage implementations are defined
here. Some utilities, like `make_storage` are also added to this module instead
of `utils` to avoid import cycles.

This module relies only on types, exceptions and utils to prevent import
cycles.

"""

from __future__ import annotations

import dataclasses
from time import time
from typing import Any, ClassVar, cast

import file_keeper as fk
import flask
from typing_extensions import TypeAlias, override

import ckan.plugins.toolkit as tk
from ckan import types
from ckan.config.declaration import Declaration, Key

from . import config, utils

adapters = fk.adapters
storages = fk.Registry["fk.Storage"]()

FileData: TypeAlias = fk.FileData

make_storage = fk.make_storage


def get_storage(name: str | None = None) -> fk.Storage:
    """Return existing storage instance.

    Storages are initialized when plugin is loaded. As result, this function
    always returns the same storage object for the given name.

    If no name specified, default storage is returned.

    Args:
        name: name of the configured storage

    Returns:
        storage instance

    Raises:
        UnknownStorageError: storage with the given name is not configured

    Example:
        ```
        default_storage = get_storage()
        storage = get_storage("storage name")
        ```

    """
    if name is None:
        name = config.default_storage()

    storage = storages.get(name)

    if not storage:
        raise fk.exc.UnknownStorageError(name)

    return storage


@dataclasses.dataclass()
class Settings(fk.Settings):
    supported_types: list[str] = cast("list[str]", dataclasses.field(default_factory=list))
    max_size: int = 0


class Uploader(fk.Uploader):
    pass


class Manager(fk.Manager):
    pass


class Reader(fk.Reader):
    """Service responsible for reading data from the storage.

    :py:class:`Storage` internally calls methods of this service. For example,
    ``Storage.stream(data, **kwargs)`` results in ``Reader.stream(data,
    kwargs)``.

    >>> class MyReader(Reader):
    >>>     def stream(
    >>>         self, data: FileData, extras: dict[str, Any]
    >>>     ) -> Iterable[bytes]:
    >>>         return open(data.location, "rb")

    """

    def response(self, data: FileData, extras: dict[str, Any]) -> types.Response:
        if not self.storage.supports(fk.Capability.STREAM):
            raise fk.exc.UnsupportedOperationError("stream", self)

        return flask.Response(
            self.stream(data, extras),
            mimetype=data.content_type or None,
            headers={"Content-length": str(data.size)},
        )


class Storage(fk.Storage):
    """Base class for storage implementation."""

    settings: Settings
    reader: Reader
    uploader: Uploader
    manager: Manager

    SettingsFactory: ClassVar[type[Settings]] = Settings  # pyright: ignore[reportIncompatibleVariableOverride]
    UploaderFactory: ClassVar[type[Uploader]] = Uploader  # pyright: ignore[reportIncompatibleVariableOverride]
    ReaderFactory: ClassVar[type[Reader]] = Reader  # pyright: ignore[reportIncompatibleVariableOverride]
    ManagerFactory: ClassVar[type[Manager]] = Manager  # pyright: ignore[reportIncompatibleVariableOverride]

    def validate_size(self, size: int):
        max_size = self.settings.max_size
        if max_size and size > max_size:
            raise fk.exc.LargeUploadError(size, max_size)

    def validate_content_type(self, content_type: str):
        supported_types = self.settings.supported_types
        if supported_types and not utils.is_supported_type(
            content_type,
            supported_types,
        ):
            raise fk.exc.WrongUploadTypeError(content_type)

    @override
    def upload(self, location: fk.Location, upload: fk.Upload, /, **kwargs: Any) -> FileData:
        self.validate_size(upload.size)
        self.validate_content_type(upload.content_type)

        return super().upload(location, upload, **kwargs)

    @override
    def multipart_start(self, location: fk.Location, size: int, /, **kwargs: Any) -> FileData:
        self.validate_size(size)
        self.validate_content_type(kwargs.get("content_type", ""))

        return super().multipart_start(location, size, **kwargs)

    @override
    def temporal_link(self, data: FileData, duration: int, /, **kwargs: Any) -> str:
        try:
            link = super().temporal_link(data, duration, **kwargs)
        except fk.exc.UnsupportedOperationError:
            link = None

        if not link:
            token = utils.encode_token(
                {
                    "topic": "download_file",
                    "exp": str(int(time()) + duration),
                    "storage": self.settings.name,
                    "location": data.location,
                },
            )
            link = tk.url_for("files.temporal_download", token=token, _external=True)
        return link

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        declaration.declare(key.max_size, 0).append_validators(
            "files_parse_filesize",
        ).set_description(
            "The maximum size of a single upload."
            + "\nSupports size suffixes: 42B, 2M, 24KiB, 1GB."
            + " `0` means no restrictions.",
        )

        declaration.declare_list(key.supported_types, None).set_description(
            "Space-separated list of MIME types or just type or subtype part."
            + "\nExample: text/csv pdf application video jpeg",
        )

        declaration.declare_bool(key.override_existing).set_description(
            "If file already exists, replace it with new content.",
        )

        declaration.declare_bool(key.initialize).set_description(
            "Prepare storage backend for uploads(create path, bucket, DB). This op",
        )

        declaration.declare(key.path, "").set_description(
            "Prefix for the file's location. The actual meaning of this option"
            + " depends on the adapter. FS adapter uses the path as a root folder for uploads."
            + " Cloud adapters, usually, use path as a prefix for the name of uploaded objects.",
        )

        declaration.declare(key.name, key[-1]).set_description(
            "Descriptive name of the storage used for debugging. When empty,"
            + " name from the config option is used,"
            + " i.e: `ckanext.files.storage.DEFAULT_NAME...`",
        )

        declaration.declare_list(key.location_transformers, None).set_description(
            "List of transformations applied to the file location."
            " Depending on the storage type, sanitizing the path or removing"
            " special characters can be sensible. Empty value leaves location"
            " unchanged, `uuid` transforms location into UUID, `uuid_with_extension`"
            " transforms filename into UUID and appends original file's extension"
            " to it.",
        )

        declaration.declare_list(key.disabled_capabilities, None).set_description(
            "Capabilities that are not supported even if implemented."
            " Can be used to transform fully-featured storage into a"
            " read-only/write-only storage."
        )

    def as_response(
        self,
        data: FileData,
        filename: str | None = None,
        /,
        send_inline: bool = False,
        **kwargs: Any,
    ) -> types.Response:
        """Make Flask response with file attachment.

        By default, files are served as attachments and are downloaded as
        result.

        If rendering is safe and preferable enable ``send_inline`` flag.

        Args:
            data: file details
            filename: expected name of the file used instead of the real name

        Keyword Args:
            send_inline: do not force download and try rendering file in browser
            **kwargs: ...

        Returns:
            Flask response with file's content
        """
        resp = self.reader.response(data, kwargs)

        inline_types = config.inline_types()
        disposition = (
            "inline" if send_inline or utils.is_supported_type(data.content_type, inline_types) else "attachment"
        )

        resp.headers.set(
            "content-disposition",
            disposition,
            filename=filename or data.location,
        )

        return resp
