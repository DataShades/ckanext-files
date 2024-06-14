from __future__ import annotations

from ckanext.files import shared


class BashifyIoStorage(shared.Storage):
    hidden = True

    def make_uploader(self):
        return BashifyIoUploader(self)

    def make_reader(self):
        return BashifyIoReader(self)

    def make_manager(self):
        return BashifyIoManager(self)


class BashifyIoUploader(shared.Uploader):
    pass


class BashifyIoReader(shared.Reader):
    pass


class BashifyIoManager(shared.Manager):
    pass
