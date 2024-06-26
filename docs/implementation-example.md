# Example implementation of custom storage adapter

Storage consist of the storage object that dispatches operation requests and 3
services that do the actual job: Reader, Uploader and Manager. To define a
custom storage, you need to extend the main storage class, describe storage
logic and register storage via `IFiles.files_get_storage_adapters`.

Let's implement DB storage. It will store files in SQL table using
SQLAlchemy. There will be just one requirement for the table: it must have
column for storing unique identifier of the file and another column for storing
content of the file as bytes.

For the sake of simplicity, our storage will work only with existing
tables. Create the table manually before we begin.

First of all, we create an adapter that does nothing and register it in our
plugin.

```python
from __future__ import annotations

from typing import Any
import sqlalchemy as sa

import ckan.plugins as p
from ckan.model.types import make_uuid
from ckanext.files import shared


class ExamplePlugin(p.SingletonPlugin):
    p.implements(shared.IFiles)
    def files_get_storage_adapters(self) -> dict[str, Any]:
        return {"example:db": DbStorage}


class DbStorage(shared.Storage):
    ...

```

After installing and enabling your custom plugin, you can configure storage
with this adapter by adding a single new line to config file:

```ini
ckanext.files.storage.db.type = files:db
```

But if you check storage via `ckan files storages -v`, you'll see that it can't
do anything.

```sh
ckan files storages -v

... db: example:db
...        Supports: Capability.NONE
...        Does not support: Capability.REMOVE|STREAM|CREATE|...

```


Before we start uploading files, let's make sure that storage has proper
configuration. As files will be stored in the DB table, we need the *name of
the table* and *DB connection string*. Let's assume that table already exists,
but we don't know which columns to use for files. So we need name of column for
content and for file's unique identifier. ckanext-files uses term `location`
instead of identifier, so we'll do the same in our implementation.

There are 4 required options in total:
* `db_url`: DB connection string
* `table`: name of the table
* `location_column`: name of column for file's unique identifier
* `content_column`: name of column for file's content

It's not mandatory, but is highly recommended that you declare config options
for the adapter. It can be done via `Storage.declare_config_options` class
method, which accepts `declaration` object and `key` namespace for storage
options.

```python
class DbStorage(shared.Storage):

    @classmethod
    def declare_config_options(cls, declaration, key) -> None:
        declaration.declare(key.db_url).required()
        declaration.declare(key.table).required()
        declaration.declare(key.location_column).required()
        declaration.declare(key.content_column).required()

```

And we probably want to initialize DB connection when storage is
initialized. For this we'll extend constructor, which must be defined as method
accepting keyword-only arguments:

```python
class DbStorage(shared.Storage):
    ...

    def __init__(self, **settings: Any) -> None:
        db_url = self.ensure_option(settings, "db_url")

        self.engine = sa.create_engine(db_url)
        self.location_column = sa.column(
            self.ensure_option(settings, "location_column")
        )
        self.content_column = sa.column(self.ensure_option(settings, "content_column"))
        self.table = sa.table(
            self.ensure_option(settings, "table"),
            self.location_column,
            self.content_column,
        )
        super().__init__(**settings)

```

You can notice that we are using `Storage.ensure_option` quite often. This
method returns the value of specified option from settings or raises an
exception.

The table definition and columns are saved as storage attributes, to simplify
building SQL queries in future.

Now we are going to define classes for all 3 storage services and tell storage,
how to initialize these services.

There are 3 services: Reader, Uploader and Manager. Each of them initialized
via corresponding storage method: `make_reader`, `make_uploader` and
`make_manager`. And each of them accepts a single argument during creation, the
storage itself.

```python
class DbStorage(shared.Storage):
    def make_reader(self):
        return DbReader(self)

    def make_uploader(self):
        return DbUploader(self)

    def make_manager(self):
        return DbManager(self)


class DbReader(shared.Reader):
    ...


class DbUploader(shared.Uploader):
    ...


class DbManager(shared.Manager):
    ...
```

Our first target is Uploader service. It's responsible for file creation. For
the minimal implementation it needs `upload` method and `capabilities`
attribute which tells the storage, what exactly the Uploader can do.

```python
class DbUploader(shared.Uploader):
    capabilities = shared.Capability.CREATE

    def upload(self, location: str, upload: shared.Upload, extras: dict[str, Any]) -> shared.FileData:
        ...
```

`upload` receives the `location`(name) of the uploaded file; `upload` object
with file's content; and `extras` dictionary that contains any additional
arguments that can be passed to uploader. We are going to ignore `location` and
generate a unique UUID for every uploaded file instead of using user-defined
filename.

The goal is to write the file into DB and return `shared.FileData` that
contains location of the file in DB(value of `location_column`), size of the
file in bytes, MIMEtype of the file and hash of file content.

For location we'll just use `ckan.model.types.make_uuid` function. Size and
MIMEtype are already available as `upload.size` and `upload.content_type`.

The only problem is hash of the content. You can compute it in any way you
like, but there is a simple option if you have no preferences. `upload` has
`hashing_reader` method, which returns an iterable for file content. When you
read file through it, content hash is automatically computed and you can get it
using `get_hash` method of the reader.

Just make sure to read the whole file before checking the hash, because hash
computed using consumed content. I.e, if you just create the hashing reader,
but do not read a single byte from it, you'll receive the hash of empty
string. If you read just 1 byte, you'll receive the hash of this single byte,
etc.

The easiest option for you is to call `reader.read()` method to consume the
whole file and then call `reader.get_hash()` to receive the hash.

Here's the final implementation of DbUploader:

```python
class DbUploader(shared.Uploader):
    capabilities = shared.Capability.CREATE

    def upload(self, location: str, upload: shared.Upload, extras: dict[str, Any]) -> shared.FileData:
        uuid = make_uuid()
        reader = upload.hashing_reader()

        values = {
            self.storage.location_column: uuid,
            self.storage.content_column: reader.read(),
        }
        stmt = sa.insert(self.storage.table, values)

        result = self.storage.engine.execute(stmt)

        return shared.FileData(
            uuid,
            upload.size,
            upload.content_type,
            reader.get_hash()
        )
```

Now you can upload file into your new `db` storage:

```sh
ckanapi action files_file_create storage=db name=hello.txt upload@<(echo -n 'hello world')

...{
...  "atime": null,
...  "content_type": "text/plain",
...  "ctime": "2024-06-17T13:48:52.121755+00:00",
...  "hash": "5eb63bbbe01eeed093cb22bb8f5acdc3",
...  "id": "bdfc0268-d36d-4f1b-8a03-2f2aaa21de24",
...  "location": "5a4472b3-cf38-4c58-81a6-4d4acb7b170e",
...  "mtime": null,
...  "name": "hello.txt",
...  "owner_id": "59ea0f6c-5c2f-438d-9d2e-e045be9a2beb",
...  "owner_type": "user",
...  "pinned": false,
...  "size": 11,
...  "storage": "db",
...  "storage_data": {}
...}

```

File is created, but you cannot read it just yet. Try running `ckan files
stream` CLI command with file ID:

```sh
ckan files stream bdfc0268-d36d-4f1b-8a03-2f2aaa21de24

... Operation stream is not supported by db storage
... Aborted!

```

As expected, you have to write extra code.

Streaming, reading and generating links is a responsibility of Reader
service. We only need `stream` method for minimal implementation. This method
receives `shared.FileData` object(the same object as the one returned from
`Uploader.upload`) and `extras` containing all additional arguments passed by
the caller. The result is any iterable producing bytes.

We'll use `location` property of `shared.FileData` as a value for
`location_column` inside the table.

And don't forget to add `STREAM` capability to `Reader.capabilities`.

```python
class DbReader(shared.Reader):
    capabilities = shared.Capability.STREAM

    def stream(self, data: shared.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        stmt = (
            sa.select(self.storage.content_column)
            .select_from(self.storage.table)
            .where(self.storage.location_column == data.location)
        )
        row = self.storage.engine.execute(stmt).fetchone()

        return row

```

The result may be confusing: we returning Row object from the stream
method. But our goal is to return *any* iterable that produces bytes. Row is
iterable(tuple-like). And it contains only one item - value of column with file
content, i.e, bytes. So it satisfy the requirements.

Now you can check content via CLI once again.

```sh
ckan files stream bdfc0268-d36d-4f1b-8a03-2f2aaa21de24

... hello world
```

Finally, we need to add file removal for the minimal implementation. And it
also nice to to have `SCAN` capability, as it shows all files currently
available in storage, so we add it as bonus. These operations handled by
Manager. We need `remove` and `scan` methods. Arguments are already familiar to
you. As for results:

* `remove`: return `True` if file was successfully removed. Should return
  `False` if file does not exist, but it's allowed to return `True` as long as
  you are not checking the result.
* `scan`: return iterable with all file locations

```python
class DbManager(shared.Manager):
    storage: DbStorage
    capabilities = shared.Capability.SCAN | shared.Capability.REMOVE

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        stmt = sa.select(self.storage.location_column).select_from(self.storage.table)
        for row in self.storage.engine.execute(stmt):
            yield row[0]

    def remove(
        self,
        data: shared.FileData | shared.MultipartData,
        extras: dict[str, Any],
    ) -> bool:
        stmt = sa.delete(self.storage.table).where(
            self.storage.location_column == data.location,
        )
        self.storage.engine.execute(stmt)
        return True
```

Now you can list the all the files in storage:
```sh
ckan files scan -s db
```

And remove file using ckanaapi and file ID

```sh
ckanapi action files_file_delete id=bdfc0268-d36d-4f1b-8a03-2f2aaa21de24
```

That's all you need for the basic storage. But check definition of base storage
and services to find details about other methods. And also check implementation
of other storages for additional ideas.
<
