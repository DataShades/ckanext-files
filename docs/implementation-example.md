# Example implementation of custom storage adapter

Storage consist of the storage object that dispatches operation requests and 3
services that do the actual job: Reader, Uploader and Manager. To define a
custom storage, you need to extend the main storage class, describe storage
logic and register storage via `IFiles.files_get_storage_adapters`.

/// admonition | Info
    type: info

ckanext-files uses [file-keeper](https://pypi.org/project/file-keeper/) that
has approximately the same workflow of registering new adapters. Main
difference is that ckanext-files creates wrappers around file-keeper's base
classes to provide better CKAN integration. For example
`declare_config_options` method exists only in ckanext-files and helps in
understanding how storage can be configured, while file-keeper requires
checking the source code or documentation to find out the list of possible
configuration options.

///

Let's implement DB storage. It will store files in SQL table using
SQLAlchemy. There will be just one requirement for the table: it must have
column for storing unique identifier of the file and another column for storing
content of the file as bytes.

!!! info

    For the sake of simplicity, our storage will work only with existing
    tables. Create the table manually before we begin.

## Storage

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
ckanext.files.storage.db.type = example:db
```

But if you check storage via `ckan files storages -v`, you'll see that it can't
do anything.

```sh
ckan files storages -v

... db: example:db
...        Supports: Capability.NONE
...        Does not support: Capability.REMOVE|STREAM|CREATE|...

```


## Settings

Before we start uploading files, let's make sure that storage has proper
configuration. As files will be stored in the DB table, we need the *name of
the table* and *DB connection string*. Let's assume that table already exists,
but we don't know which columns to use for files. So we need name of column for
content and for file's unique identifier. ckanext-files uses term `location`
instead of identifier, and we'll do the same in our implementation.

There are 4 required options in total:

* `db_url`: DB connection string
* `table`: name of the table
* `location_column`: name of column for file's unique identifier
* `content_column`: name of column for file's content

/// admonition
    type: tip

It's not mandatory, but is highly recommended that you declare config options
for the adapter. It can be done via `Storage.declare_config_options` class
method, which accepts `declaration` object and `key` namespace for storage
options.

Declarations can be used to config introspection and validation.

```python
class DbStorage(shared.Storage):

    @classmethod
    def declare_config_options(cls, declaration, key):
        declaration.declare(key.db_url).required()
        declaration.declare(key.table).required()
        declaration.declare(key.location_column).required()
        declaration.declare(key.content_column).required()

```

///

And we probably want to initialize DB connection when storage is
initialized.

The first step here is to extend `shared.Settings` dataclass and define:

* custom options
* initialization of custom properties(DB connection)

Options are defined as dataclass' fields, while initialization happens inside
its `__post_init__` method.

```python
import dataclasses

@dataclasses.dataclass()
class Settings(fk.Settings):
    db_url: str = ""
    table_name: str = ""
    location_column: str = ""
    content_column: str = ""

    engine: sa.Engine = None  # type: ignore
    table: Any = None
    location: Any = None
    content: Any = None


    def __post_init__(self, **kwargs: Any):
        super().__post_init__(**kwargs)

        self.engine = sa.create_engine(self.db_url)
        self.location = sa.column(self.location_column)
        self.content = sa.column(self.content_column)
        self.table = sa.table(self.table_name, self.location, self.content)
```

The table definition and columns are saved as settings attributes as well, to simplify
building SQL queries in future.

Now we need to specify this new dataclass as a `SettingsFactory` for the custom storage:

```py
class DbStorage(shared.Storage):
    ...

    SettingsFactory = Settings
```

In this way, whenever `DbStorage` is initialized, it creates `Settings`
instance with configuration options from the config file and saves this
`Settings` instance as `self.settings`. In the end, if you have
`ckanext.files.storage.db.db_url = hello://world`, it can be accessed as:

```py

storage = get_storage("db")
print(storage.settings.db_url)
```

## Services

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

/// admonition
    type: tip

It's also possible to specify service factories using settings-like style:

```py
class DbStorage(shared.Storage):
    ...
    UploaderFactory = DbUploader
    ManagerFactory = DbManager
    ReaderFactory = DbReader
```

Using `*Factory` attributes may be simpler, but `make_*` methods have higher
flexibility.

///

### Uploader

Our first target is Uploader service. It's responsible for file creation. For
the minimal implementation it needs `upload` method and `capabilities`
attribute which tells the storage, what exactly the Uploader can do.

```python

class DbUploader(shared.Uploader):
    capabilities = shared.Capability.CREATE

    def upload(
        self,
        location: shared.Location,
        upload: shared.Upload,
        extras: dict[str, Any]
    ) -> shared.FileData:
        ...
```

`upload` receives the `location`(name) of the uploaded file; `upload` object
with file's content; and `extras` dictionary that contains any additional
arguments that can be passed to uploader.

`Location` type is an alias for `str` that helps identify potentially unsecure
invocations of the `Uploader.upload` method.  We are going to ignore `location`
and generate a unique UUID for every uploaded file instead of using
user-defined filename. Because of it, it doesn't matter whether you pass
`str(uuid_location)` or `shared.Location(uuid_location)` to the `upload` method
in the end.

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

    def upload(
        self,
        location: shared.Location,
        upload: shared.Upload,
        extras: dict[str, Any]
    ) -> shared.FileData:
        uuid = make_uuid()
        reader = upload.hashing_reader()

        cfg = self.storage.settings

        values = {
            cfg.location: uuid,
            cfg.content: reader.read(),
        }
        stmt = sa.insert(cfg.table, values)

        result = cfg.engine.execute(stmt)

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

### Reader

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
        cfg = self.storage.settings

        stmt = (
            sa.select(cfg.content)
            .select_from(cfg.table)
            .where(cfg.location == data.location)
        )
        row = cfg.engine.execute(stmt).fetchone()

        return row

```

/// admonition
    type: info

The result may be confusing: we returning Row object from the stream
method. But our goal is to return *any* iterable that produces bytes. Row is
iterable(tuple-like). And it contains only one item - value of column with file
content, i.e, bytes. So it satisfies the requirements.

///

Now you can check content via CLI once again.

```sh
ckan files stream bdfc0268-d36d-4f1b-8a03-2f2aaa21de24

... hello world
```

### Manager

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
        cfg = self.storage.settings

        stmt = sa.select(cfg.location).select_from(cfg.table)
        for row in cfg.engine.execute(stmt):
            yield row[0]

    def remove(
        self,
        data: shared.FileData,
        extras: dict[str, Any],
    ) -> bool:
        cfg = self.storage.settings

        stmt = sa.delete(cfg.table).where(
            cfg.location == data.location,
        )
        cfg.engine.execute(stmt)
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

/// admonition | Registering file-keeper's adapters
    type: tip

Adapters registered in file-keeper using its entry-points are not available in
CKAN. But it can be easily changed, by creating wrapper class and registering
it using `IFiles`:


```py

from file_keeper_extension.adapters import CustomStorage
from ckanext.files import shared

# make sure you used `shared.Storage` as a leftmost ancestor
class WrappedCustomStorage(shared.Storage, CustomStorage)

    # describe settings, mainly to validate them in advance
    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)

        # declare CustomStorage's configuration here
        ...

# in plugin.py
class MyPlugin(p.SingletonPlugin):
    p.implements(interfaces.IFiles, inherit=True)

    def files_get_storage_adapters(self):
        return {
            "my:custom": WrappedCustomStorage,
        }

```

///
