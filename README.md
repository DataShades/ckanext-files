[![Tests](https://github.com/DataShades/ckanext-files/actions/workflows/test.yml/badge.svg?branch=storage)](https://github.com/DataShades/ckanext-files/actions/workflows/test.yml)

# ckanext-files

Files as first-class citizens of CKAN. Upload, manage, remove files directly
and attach them to datasets, resources, etc.

## Content

* [Requirements](#requirements)
* [Installation](#installation)
* [Usage](#usage)
  * [Configure the storage](#configure-the-storage)
  * [Usage in code](#usage-in-code)
  * [Usage in browser](#usage-in-browser)
  * [Multi-storage](#multi-storage)
* [Configuration](#configuration)


## Requirements

Compatibility with core CKAN versions:

| CKAN version | Compatible? |
|--------------|-------------|
| 2.9          | no          |
| 2.10         | yes         |
| 2.11         | yes         |
| master       | yes         |


It's recommended to install the extension via pip. If you are using GitHub
version of this extension, stick to the vX.Y.Z tags to avoid breaking
changes. Check the changelog before upgrading the extension.

## Installation

To install ckanext-files:

1. Install the extension
   ```sh
   # minimal installation
   pip install ckanext-files

   # with Google Cloud Storage support
   pip install 'ckanext-files[gcs]'
   ```

1. Add `files` to the `ckan.plugins` setting in your CKAN
   config file.

1. Run DB migrations
   ```sh
   ckan db upgrade -p files
   ```

## Usage

### Configure the storage

Before uploading files, you have to configure a **storage**. Storage defines
the *adapter* used for uploads(i.e, where and how data will be stored:
filesystem, cloud, DB, etc.), add, depending on the adapter, a few specific
options. For example, filesystem adapter likely requires a path to the folder
where uploads are stored. DB adapter may need DB connection parameters. Cloud
adapter most likely will not work without an API key. These additional options
are specific to adapter and you have to check its documentation to find out
what are the possible options.

Let's start from the Redis adapter, because it has minimal requirements in terms
of configuration.

Add the following line to the CKAN config file:

```ini
ckanext.files.storage.default.type = files:redis
```

The name of adapter is `files:redis`. It follows recommended naming convention
for adapters:`<EXTENSION>:<TYPE>`. You can tell from the name above that we are
using adapter defined in the `files` extension with `redis` type. But this
naming convention is not enforced and its only purpose is avoiding name
conflicts. Technically, adapter name can use any character, including spaces,
newlines and emoji.


If you accidentally make a typo in the driver's name, because of config
validation, any CKAN CLI command will produce an error message with the list of
available drivers:

```sh
Invalid configuration values provided:
ckanext.files.storage.default.type: Value must be one of ['files:fs', 'files:public_fs', 'files:redis']
Aborted!
```

Storage is configured, so we can actually upload the file. Let's use
[ckanapi](https://github.com/ckan/ckanapi) for this task. Files are created via
    `files_file_create` API action and this time we have to pass 2 parameters into
it:

* `name`: the name of uploaded file
* `upload`: content of the file

The final command is here:

```sh
ckanapi action files_file_create name=hello.txt upload='hello world'
```

And that's what you see as result:

```json
{
  "atime": null,
  "content_type": "text/plain",
  "ctime": "2024-06-02T15:02:14.819117+00:00",
  "hash": "5eb63bbbe01eeed093cb22bb8f5acdc3",
  "id": "e21162ab-abfb-476c-b8c5-5fe7cb89eca0",
  "location": "24d27fb9-a5f0-42f6-aaa3-7dcb599a0d46",
  "mtime": null,
  "name": "hello.txt",
  "size": 11,
  "storage": "default",
  "storage_data": {}
}
```

Content of the file can be checked via CKAN CLI. Use `id` from the last API
call's output in the command `ckan files stream ID`:

```sh
ckan files stream e21162ab-abfb-476c-b8c5-5fe7cb89eca0
```

Alternatively, we can use Redis CLI and to get the content of the file. Note,
you cannot get the content via CKAN API, because it's JSON-based and streaming
files doesn't suit its principles.

By default, Redis driver puts the content under the key
`<PREFIX><LOCATION>`. Pay attention to `LOCATION`. It's the value available as
`location` in the API response(i.e, `24d27fb9-a5f0-42f6-aaa3-7dcb599a0d46` in
our case). It's different from the `id`(ID used by DB to uniquely identify file
record) and `name`(human readable name of the file). In our scenario,
`location` location looks like UUID because of the internal details of Redis
adapter implementation. But different adapters may use more path-like value,
i.e. something similar to `path/to/folder/hello.txt`.

`PREFIX` can be configured, but we skipped this step and got the default value:
`ckanext:files:default:file_content:`. So the final Redis key of our file is
`ckanext:files:default:file_content:24d27fb9-a5f0-42f6-aaa3-7dcb599a0d46`

```redis
redis-cli

127.0.0.1:6379> GET ckanext:files:default:file_content:24d27fb9-a5f0-42f6-aaa3-7dcb599a0d46
"hello world"
```

And before we moved further, let's remove the file, using its `id`:

```sh
ckanapi action files_file_delete id=e21162ab-abfb-476c-b8c5-5fe7cb89eca0
```

### Usage in code

If you are writing the code and you want to interact with the storage directly,
without the API layer, you can do it via a number of public functions of the
extension.

Let's configure filesystem storage first. Filesystem driver has a mandatory
option `path` that controls filesystem location, where files are stored. If
path does not exist, storage will raise an exception by default. But it can
also create missing path if you enable `create_path` option. Here's our final
version of settings:

```ini
ckanext.files.storage.default.type = files:fs
ckanext.files.storage.default.path = /tmp/example
ckanext.files.storage.default.create_path = true
```

Now we are going to connect to CKAN shell via `ckan shell` CLI command and
create an instance of the storage:

```python
from ckanext.files.shared import get_storage
storage = get_storage()
```

Because you have all configuration in place, the rest is fairly
straightforward. We will upload the file, read it's content and remove it from
the CKAN shell.

To create the file, `storage.upload` method must be called with 3 parameters:

* the human readable name of the file
* special steam-like object with content of the file
* dictionary with extra parameters that are consumed by the storage adapter

You can use any string as the first parameter. The last parameter is not used
by `files:fs` adapter, so we'll use an empty dictionary. And the only
problematic parameter is the "special stream-like object". To make things
simpler, ckanext-files has `ckanext.files.shared.make_upload` function, that
accepts a number of different types(`str`, `bytes`,
`werkzeug.datastructures.FileStorage`) and converts them into expected format.


```python
from ckanext.files.shared import make_upload

upload = make_upload("hello world")
result = storage.upload('file.txt', upload, {})

print(result)

... FileData(
...     location='60b385e7-8137-496c-bb1d-6ae4d7963ab3',
...     size=11,
...     content_type='text/plain',
...     hash='5eb63bbbe01eeed093cb22bb8f5acdc3',
...     storage_data={}
... )
```

`result` is an instance of `ckanext.files.shared.FileData` dataclass. It
contains all the information that is required by storage to manage the file.

`result` object has `location` attribute that shows the name of the file
*relative* to the `path` option specified in the storage configuration. If you
visit `/tmp/example` directory, which was specified as a `path` for the storage,
you'll see there a file with the name matching `location` from result. And its
content matches the content of our upload, which is quite an expected outcome.

```sh
cat /tmp/example/60b385e7-8137-496c-bb1d-6ae4d7963ab3

... hello world
```

But let's go back to the shell and try reading file from the python's
code. We'll pass `result` to the storage's `stream` method, which produces a
readable buffer based on our result. This buffer has `read` method so we can
work with the buffer just as we usually do with IO streams:

```python
buffer = storage.stream(result)
content = buffer.read()
print(content)

... b'hello world'
```

In most cases, storage only needs a location of the file object to read it. So,
if you don't have `result` generated during the upload, you still can read the
file as long as you have its location. But remember, that some storage adapters
may require additional information, and the following example must be adapted
depending on the adapter:

```python
from ckanext.files.shared import FileData

location = "60b385e7-8137-496c-bb1d-6ae4d7963ab3"
data = FileData(location)

buffer = storage.stream(data)
content = buffer.read()
print(content)

... b'hello world'
```

And finally we need to remove the file

```python
storage.remove(result)
```

### Usage in browser

You can upload files using JavaScript CKAN modules. The extension extends
CKAN's Sandbox object(available as `this.sandbox` inside the JS CKAN module),
so we can use shortcut and upload file directly from the DevTools. Open any
CKAN page, switch to JS console and create the sandbox instance. Inside it we
have `files` object, which in turn contains `upload` method. This method
accepts `File` object for upload(the same object you can get from the
`input[type=file]`).

```js
sandbox = ckan.sandbox()
await sandbox.files.upload(
  new File(["content"], "file.txt", {type: "text/plain"})
)

... {
...     "id": "18cdaa65-5eed-4078-89a8-469b137627ce",
...     "name": "file.txt",
...     "location": "b53907c3-8434-4dee-9a9e-6c4d3055d200",
...     "content_type": "text/plain",
...     "size": 7,
...     "hash": "9a0364b9e99bb480dd25e1f0284c8555",
...     "storage": "default",
...     "ctime": "2024-06-02T16:12:27.902055+00:00",
...     "mtime": null,
...     "atime": null,
...     "storage_data": {}
... }
```

If you are still using FS storage configured in previous section, switch to
`/tmp/example` folder and check it's content:

```sh
ls /tmp/example
... b53907c3-8434-4dee-9a9e-6c4d3055d200

cat b53907c3-8434-4dee-9a9e-6c4d3055d200
... content
```

And, as usually, let's remove file using the ID from the `upload` promise:

```js
sandbox.client.call("POST", "files_file_delete", {
  id: "18cdaa65-5eed-4078-89a8-469b137627ce"
})
```

### Multi-storage

It's possible to use multiple storages at the same time and specify which one
you want to use when uploading a file. Up until now we used the following storage options:

* `ckanext.files.storage.default.type`
* `ckanext.files.storage.default.path`
* `ckanext.files.storage.default.create_path`

All of them have a common prefix `ckanext.files.storage.default.` and it's a
key for using multiple storages simultaneously.

Every option of the storage follows the pattern:
`ckanext.files.storage.<STORAGE_NAME>.<OPTION>`. As all the options above
contain `default` on position of `<STORAGE_NAME>`, they are related to the
`default` storage.

If you want to configure a storage with the name `custom` change the
configuration of storage:

```ini
ckanext.files.storage.custom.type = files:fs
ckanext.files.storage.custom.path = /tmp/example
ckanext.files.storage.custom.create_path = true
```

And, if you want to use Redis-based storage named `memory` and filesystem-based
storage named `default`, use the following configuration:

```ini
ckanext.files.storage.memory.type = files:redis

ckanext.files.storage.default.type = files:fs
ckanext.files.storage.default.path = /tmp/example
ckanext.files.storage.default.create_path = true
```

The `default` storage is special. ckanext-files use it by default, as name
suggests. If you remove configuration for the `default` storage and try to
create a file, you'll see the following error:

```sh
ckanapi action files_file_create name=hello.txt upload='hello world'

... ckan.logic.ValidationError: None - {'storage': ['Storage default is not configured']}
```

Storage **default** is not configured. That's why we need `default`
configuration. But if you want to use a different storage or you don't want to
add the `default` storage, you can always specify the name of the storage you
are going to use.

When using API actions, add `storage` parameter to the call:

```sh
ckanapi action files_file_create name=hello.txt upload='hello world' storage=memory
```

When writing python code, pass storage name to `get_storage` function:
```python
storage = get_storage("memory")
```

When writing JS code, make a `Standard` uploader with the custom storage name
and pass this uploader to `upload` function:

```js
const sandbox = ckan.sandbox()
const file = new File(["content"], "file.txt", {type: "text/plain"})
const uploader = sandbox.files.makeUploader('Standard', {storage: "memory"})

await sandbox.files.upload(
  file,
  uploader,
)
```


## Configuration

There are two types of config options for ckanext-files:

* Global: affects the behavior of the extension and every available storage
  adapter.
* Storage configuration: changes behavior of the specific storage and never
  affects anything outside of the storage.

Depending on the type of the storage, available options are quite
different. For example, `files:fs` storage type requires `path` option that
controls filesystem path where uploads are stored. `files:redis` storage type
accepts `prefix` option that defines Redis' key prefix of files stored in
Redis. All storage specific options always have form
`ckanext.files.storage.<STORAGE>.<OPTION>`:

```ini
ckanext.files.storage.memory.prefix = xxx:
# or
ckanext.files.storage.my_drive.path = /tmp/hello
```

Below is the list of non-storage specific options. Details of the specific
storage type can be found in the dedicated section of the storage type.

```ini

# Default storage used for upload when no explicit storage specified
# (optional, default: default)
ckanext.files.default_storage = default

# Configuration of the named storage.
# (optional, default: )
ckanext.files.storage.<NAME>.<OPTION> =

```

Starting from CKAN v2.10 you can check all available options for the storage
type via config declarations CLI. First, add the storage type to the config
file:

```ini
ckanext.files.storage.xxx.type = files:redis
```

Now run the command that shows all available config option of the
plugin.

```sh
ckan config declaration files -d
```

Because redis storage adapter is enabled, you'll see all the options
regsitered by redis driver alongside with the global options:


```ini
## ckanext-files ###############################################################
## ...
## Storage adapter used by the storage
ckanext.files.storage.xxx.type = files:redis
## The maximum size of a single upload.
## Supports size suffixes: 42B, 2M, 24KiB, 1GB. `0` means no restrictions.
ckanext.files.storage.xxx.max_size = 0
## Descriptive name of the storage used for debugging.
ckanext.files.storage.xxx.name = xxx
## Static prefix of the Redis key generated for every upload.
ckanext.files.storage.xxx.prefix = ckanext:files:default:file_content:
```

Sometimes you will see a validation error if storage has required config
options. Let's try using `files:fs` storage instead of the redis:

```ini
ckanext.files.storage.xxx.type = files:fs
```

Now attempt to run `ckan config declaration files -d` will show an error,
because required `path` option is missing:

```sh
Invalid configuration values provided:
ckanext.files.storage.xxx.path: Missing value
Aborted!
```

Add the required option to satisfy the application

```ini
ckanext.files.storage.xxx.type = files:fs
ckanext.files.storage.xxx.path = /tmp
```

And run CLI command once again. This time you'll see the list of allowed
options:

```ini
## ckanext-files ###############################################################
## ...
## Storage adapter used by the storage
ckanext.files.storage.xxx.type = files:fs
## The maximum size of a single upload.
## Supports size suffixes: 42B, 2M, 24KiB, 1GB. `0` means no restrictions.
ckanext.files.storage.xxx.max_size = 0
## Descriptive name of the storage used for debugging.
ckanext.files.storage.xxx.name = xxx
## Path to the folder where uploaded data will be stored.
ckanext.files.storage.xxx.path =
## Create storage folder if it does not exist.
ckanext.files.storage.xxx.create_path = false
```
