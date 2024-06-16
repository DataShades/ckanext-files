[![Tests](https://github.com/DataShades/ckanext-files/actions/workflows/test.yml/badge.svg)](https://github.com/DataShades/ckanext-files/actions/workflows/test.yml)

# ckanext-files

Files as first-class citizens of CKAN. Upload, manage, remove files directly
and attach them to datasets, resources, etc.

## Requirements

Compatibility with core CKAN versions:

| CKAN version | Compatible? |
|--------------|-------------|
| 2.9          | no          |
| 2.10         | yes         |
| 2.11         | yes         |
| master       | yes         |


It's recommended to install the extension via pip. If you are using GitHub
version of the extension, stick to the vX.Y.Z tags to avoid breaking
changes. Check the [changelog](CHANGELOG.md) before upgrading the extension.

## Installation

To install ckanext-files:

1. Install the extension
   ```sh
   # minimal installation
   pip install ckanext-files
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
the **adapter** used for uploads(i.e, where and how data will be stored:
filesystem, cloud, DB, etc.), and, depending on the adapter, a few specific
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


If you make a typo in the adapter's name, any CKAN CLI command will produce an
error message with the list of available adapters:

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

Alternatively, we can use Redis CLI to get the content of the file. Note, you
cannot get the content via CKAN API, because it's JSON-based and streaming
files doesn't suit its principles.

By default, Redis adapter puts the content under the key
`<PREFIX><LOCATION>`. Pay attention to `LOCATION`. It's the value available as
`location` in the API response(i.e, `24d27fb9-a5f0-42f6-aaa3-7dcb599a0d46` in
our case). It's different from the `id`(ID used by DB to uniquely identify file
record) and `name`(human readable name of the file). In our scenario,
`location` looks like UUID because of the internal details of Redis adapter
implementation. But different adapters may use more path-like value,
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

Let's configure filesystem storage first. Filesystem adapter has a mandatory
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
by `files:fs` adapter, so we'll pass an empty dictionary. And the only
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
contains all the information required by storage to manage the file.

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

It's possible to configure multiple storages at once and specify which one you
want to use for the individual file upload. Up until now we used the following
storage options:

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
configuration. But if you want to upload a file into a different storage or you
don't want to add the `default` storage at all, you can always specify
explicitly the name of the storage you are going to use.

When using API actions, add `storage` parameter to the call:

```sh
ckanapi action files_file_create name=hello.txt upload='hello world' storage=memory
```

When writing python code, pass storage name to `get_storage` function:
```python
storage = get_storage("memory")
```

When writing JS code, pass object `{uploaderParams: [{storage: "memory"}]}` to
`upload` function:

```js
const sandbox = ckan.sandbox()
const file = new File(["content"], "file.txt", {type: "text/plain"})
const options = {uploaderParams: [{storage: "memory"}]};

await sandbox.files.upload(file, options)
```

### Tracked and untracked files

There is a difference between creating files via action:

```python
tk.get_action("files_file_create")(
    {"ignore_auth": True},
    {"upload": "hello", "name": "hello.txt"}
)
```

and via direct call to `Storage.upload`:

```python
from ckanext.files.shared import get_storage, make_upload

storage = get_storage()
storage.upload("hello.txt", make_upload("hello"), {})
```

The former snippet creates a *tracked* file: file uploaded to the storage and
its details are saved to database.

The latter snippet creates an *untracked* file: file uploaded to the storage,
but its details are not saved anywhere.

Untracked files can be used to achieve specific goals. For example, imagine a
storage adapter that writes files to the specified ZIP archive. You can create
an interface, that initializes such storage for *an existing ZIP resource* and
uploads files into it. You don't need a separate record in DB for every
uploaded file, because all of them go into the resource, that is already stored
in DB.

But such use-cases are pretty specific, so prefer to use API if you are not
sure, what you need. The main reason to use tracked files is their
discoverability: you can use `files_file_search` API action to list all the
tracked files and optionally filter them by storage, location, content_type,
etc:

```sh
ckanapi action files_file_search

... {
...   "count": 123,
...   "results": [
...     {
...       "atime": null,
...       "content_type": "text/plain",
...       "ctime": "2024-06-02T14:53:12.345358+00:00",
...       "hash": "5eb63bbbe01eeed093cb22bb8f5acdc3",
...       "id": "67a0dc8f-be91-48cd-bc8a-9934e12a48d0",
...       "location": "25c01077-c2cf-484b-a417-f231bb6b448b",
...       "mtime": null,
...       "name": "hello.txt",
...       "size": 11,
...       "storage": "default",
...       "storage_data": {}
...     },
...     ...
...   ]
... }

ckanapi action files_file_search size:5 rows=1

... {
...   "count": 2,
...   "results": [
...     {
...       "atime": null,
...       "content_type": "text/plain",
...       "ctime": "2024-06-02T14:53:12.345358+00:00",
...       "hash": "5eb63bbbe01eeed093cb22bb8f5acdc3",
...       "id": "67a0dc8f-be91-48cd-bc8a-9934e12a48d0",
...       "location": "25c01077-c2cf-484b-a417-f231bb6b448b",
...       "mtime": null,
...       "name": "hello.txt",
...       "size": 5,
...       "storage": "default",
...       "storage_data": {}
...     }
...   ]
... }

ckanapi action files_file_search content_type=application/pdf

... {
...   "count": 0,
...   "results": []
... }
```

As for untracked files, their discoverability depends on the storage
adapters. Some of them, `files:fs` for example, can scan the storage and locate
all uploaded files, both thacked and untracked. If you have `files:fs` storage
configured as `default`, use the following command to scan its content:

```sh
ckan files scan
```

If you want to scan a different storage, specify its name via
`-s/--storage-name` option. Remember, that some storage adapters do not support
scanning.

```sh
ckan files scan -s memory
```

If you want to see untracked files only, add `-u/--untracked-only` flag.

```sh
ckan files scan -u
```

If you want to track any untracked files, by creating a DB record for every
such file, add `-t/--track` flag. After that you'll be able to discover
previously untracked files via `files_file_search` API action. Most usable this
option will be during the migration, when you are configuring a new storage,
that points to an existing location with files.

```sh
ckan files scan -t
```

## File upload strategies

TBD

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


### Global configuration

```ini
# Default storage used for upload when no explicit storage specified
# (optional, default: default)
ckanext.files.default_storage = default

# Any authenticated user can upload files.
# (optional, default: false)
ckanext.files.authenticated_uploads.allow = false

# Names of storages that can by used by non-sysadmin users when authenticated
# uploads enabled
# (optional, default: default)
ckanext.files.authenticated_uploads.storages = default

# List of owner types that grant access on owned file to anyone who has
# access to the owner of file. For example, if this option has value
# `resource package`, anyone who passes `resource_show` auth, can see all
# files owned by resource; anyone who passes `package_show`, can see all
# files owned by package; anyone who passes
# `package_update`/`resource_update` can modify files owned by
# package/resource; anyone who passes `package_delete`/`resource_delete` can
# delete files owned by package/resoure. IMPORTANT: Do not add `user` to
# this list. Files may be temporarily owned by user during resource creation.
# Using cascade access rules with `user` exposes such temporal files to
# anyone who can read user's profile.
# (optional, default: package resource group organization)
ckanext.files.owner.cascade_access = package resource group organization

# Use `*_update` auth function to check cascade access for ownership
# transfer. Works with `ckanext.files.owner.cascade_access`, which by itself
# will check `*_file_transfer` auth function, but switch to `*_update` when
# this flag is enabled.
# (optional, default: true)
ckanext.files.owner.transfer_as_update = true
```

### Storage configuration

All available options for the storage type can be checked via config
declarations CLI. First, add the storage type to the config file:

```ini
ckanext.files.storage.xxx.type = files:redis
```

Now run the command that shows all available config option of the
plugin.

```sh
ckan config declaration files -d
```

Because Redis storage adapter is enabled, you'll see all the options
regsitered by Redis adapter alongside with the global options:

```ini
## ckanext-files ###############################################################
## ...
## Storage adapter used by the storage
ckanext.files.storage.xxx.type = files:redis
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
## Path to the folder where uploaded data will be stored.
ckanext.files.storage.xxx.path =
## Create storage folder if it does not exist.
ckanext.files.storage.xxx.create_path = false
```

There is a number of options that are supported by every storage. You can set
them and expect that every storage, regardless of type, will use these options
in the same way:

```ini
## Storage adapter used by the storage
ckanext.files.storage.NAME.type = ADAPTER
## The maximum size of a single upload.
## Supports size suffixes: 42B, 2M, 24KiB, 1GB. `0` means no restrictions.
ckanext.files.storage.NAME.max_size = 0
## Space-separated list of MIME types or just type or subtype part.
## Example: text/csv pdf application video jpeg
ckanext.files.storage.NAME.supported_types =
## Descriptive name of the storage used for debugging. When empty, name from
## the config option is used, i.e: `ckanext.files.storage.DEFAULT_NAME...`
ckanext.files.storage.NAME.name = NAME
```

#### Redis storage configuration

```ini
## Storage adapter used by the storage
ckanext.files.storage.NAME.type = files:redis
## Static prefix of the Redis key generated for every upload.
ckanext.files.storage.NAME.prefix = ckanext:files:default:file_content:
```

#### Filesystem storage configuration

Private filesystem storage

```ini
## Storage adapter used by the storage
ckanext.files.storage.NAME.type = files:fs
## Path to the folder where uploaded data will be stored.
ckanext.files.storage.NAME.path =
## Create storage folder if it does not exist.
ckanext.files.storage.NAME.create_path = false
```


Public filesystem storage

```ini
## Storage adapter used by the storage
ckanext.files.storage.NAME.type = files:public_fs
## Path to the folder where uploaded data will be stored.
ckanext.files.storage.NAME.path =
## Create storage folder if it does not exist.
ckanext.files.storage.NAME.create_path = false
## URL of the storage folder. `public_root + location` must produce a public URL
ckanext.files.storage.NAME.public_root =
```

## Migration from native CKAN storage system

Important: ckanext-files itself is an independent file-management system. You
don't have to migrate existing files from groups, users and resources to
it. You can just start using ckanext-files for **new fields** defined in
metadata schema or for uploading arbitrary files. And continue using native
CKAN uploads for group/user images and resource files. Migration workflows
described here merely exist as a PoC of using ckanext-files for everything in
CKAN. Don't migrate your production instances yet, because concepts and rules
may change in future and migration process will change as well. Try migration
only as an experiment, that gives you an idea of what else you want to see in
ckanext-file, and share this idea with us.

Note: every migration workflow described below requires installed
ckanext-files. Complete [installation](#installation) section before going
further.

CKAN has following types of files:

* group/organization images
* user avatars
* resource files
* site logo
* files uploaded via custom logic from extensions

At the moment, there is no migration strategy for the last two types. Replacing
site logo manually is a trivial task, so there will be no dedicated command for
it. As for extensions, every of them is unique, so feel free to create an issue
in the current repository: we'll consider creation of migration script for your
scenario or, at least, explain how you can perform migration by yourself.

Migration process for group/organization/user images and resource uploads
described below. Keep in mind, that this process only describes migration from
native CKAN storage system, that keeps files inside local filesystem. If you
are using storage extensions, like
[ckanext-s3filestore](https://github.com/okfn/ckanext-s3filestore) or
[ckanext-cloudstorage](https://github.com/TkTech/ckanext-cloudstorage), create
an issue in the current repository with a request of migration command. As
there are a lot of different forks of such extension, creating reliable
migration script may be challenging, so we need some details about your
environment to help with migration.

Migration workflows bellow require certain changes to metadata schemas, UI
widgets for file uploads and styles of your portal(depending on the
customization).

### Migration for group/organization images

Note: internally, groups and organizations are the same entity, so this
workflow describes both of them.

First of all, you need a configured storage that supports public links. As all
group/organization images are stored inside local filesystem, you can use
`files:public_fs` storage adapter.

This extension expects that the name of group images storage will be
`group_images`. This name will be used in all other commands of this migration
workflow. If you want to use different name for group images storage, override
`ckanext.files.group_images_storage` config option which has default value
`group_images` and don't forget to adapt commands if you use a different name
for the storage.

This configuration example sets 10MiB restriction on upload size via
`ckanext.files.storage.group_images.max_size` option. Feel free to change it or
remove completely to allow any upload size. This restriction is applied to
future uploads only. Any existing file that exceeds limit is kept.

Uploads restricted to `image/*` MIMEtype via
`ckanext.files.storage.group_images.supported_types` option. You can make this
option more or less restrictive. This restriction is applied to future uploads
only. Any existing file with wrong MIMEtype is kept.

`ckanext.files.storage.group_images.path` controls location of the upload
folder in filesystem. It should match value of `ckan.storage_path` option plus
`storage/uploads/group`. In example below we assume that value of
`ckan.storage_path` is `/var/storage/ckan`.

`ckanext.files.storage.group_images.public_root` option specifies base URL from
which every group image can be accessed. In most cases it's CKAN URL plus
`uploads/group`. If you are serving CKAN application from the `ckan.site_url`,
leave this option unchanged. If you are using `ckan.root_path`, like `/data/`,
insert this root path into the value of the option. Example below uses
`%(ckan.site_url)s` wildcard, which will be automatically replaced with the
value of `ckan.site_url` config option. You can specify site URL explicitely if
you don't like this wildcard syntax.

```ini
ckanext.files.storage.group_images.type = files:public_fs
ckanext.files.storage.group_images.max_size = 10MiB
ckanext.files.storage.group_images.supported_types = image
ckanext.files.storage.group_images.path = /var/storage/ckan/storage/uploads/group
ckanext.files.storage.group_images.public_root = %(ckan.site_url)s/uploads/group
```

Now let's run a command that show us the list of files available under newly
configured storage:

```sh
ckan files scan -s group_images
```

All these files are not tracked by files extension yet, i.e they don't have
corresponding record in DB with base details, like size, MIMEtype, filehash,
etc. Let's create these details via the command below. It's safe to run this
command multiple times: it will gather and store information about files not
registered in system and ignore any previously registered file.

```sh
ckan files scan -s group_images -t
```

Finally, let's run the command, that shows only untracked files. Ideally,
you'll see nothing upon executing it, because you just registered every file in
the system.

```ini
ckan files scan -s group_images -u
```

Note, all the file are still available inside storage directory. If previous
command shows nothing, it only means that CKAN already knows details about each
file from the storage directory. If you want to see the list of the files
again, omit `-u` flag(which stands for "untracked") and you'll see again all
the files in the command output:

```ini
ckan files scan -s group_images
```

Now, when all images are tracked by the system, we can give the ownership over
these files to groups/organizations that are using them. Run the command below
to connect files with their owners. It will search for groups/organizations
first and report, how many connections were identified. There will be
suggestion to show identified relationship and the list of files that have no
owner(if there are such files). Presence of files without owner usually means
that you removed group/organization from database, but did not remove its
image.

Finally, you'll be asked if you want to transfer ownership over files. This
operation does not change existing data and if you disable ckanext-files after
ownership transfer, you won't see any difference. The whole ownership transfer
is managed inside custom DB tables generated by ckanext-files, so it's safe
operation.

```sh
ckan files migrate groups group_images
```

Here's an example of output that you can see when running the command:

```sh
Found 3 files. Searching file owners...
[####################################] 100% Located owners for 2 files out of 3.

Show group IDs and corresponding file? [y/N]: y
d7186937-3080-429f-a434-22b74b9a8d39: file-1.png
87e2a1aa-7905-4a28-a087-90433f8e169e: file-2.png

Show files that do not belong to any group? [y/N]: y
file-3.png

Transfer file ownership to group identified in previous steps? [y/N]: y
Transfering file-2.png  [####################################]  100%
```

Now comes the most complex part. You need to change metadata schema and UI in
order to:

* make sure that all new files are uploaded and managed by ckanext-files
  instead of native CKAN's uploader
* generate image URLs using ckanext-files functionality. Right now, while files
  stored in the original storage folder it makes no difference. But if you
  change upload directory in future or even decide to move files from local
  filesystem into different storage backend, it will guarantee that files are
  remain visible.


Original CKAN workflow for uploading files was:

* just save image URL provided by user or
* upload a file
* put it into directory that is publicly served by application
* replace uploaded file in the HTML form/group metadata with the public URL of
  the uploaded file

This approach is different from strategy recommended by ckanext-files. But in
order to make the migration as simple as possible, we'll stay close to original
workflow.

Note: suggestet approach resembles existing process of file uploads in
CKAN. But ckanext-files was designed as a system, that gives you a
choice. Check [file upload strategies](#file-upload-strategies) to learn more
about alternative implementations of upload and their pros/cons.

First, we need to replace **Upload/Link** widget on group/organization form. If
you are using native group templates, create `group/snippets/group_form.html`
and `organization/snippets/organization_form.html`. Inside both files, extend
original template and override block `basic_fields`. You only need to replace last field

```jinja2
{{ form.image_upload(
    data, errors, is_upload_enabled=h.uploads_enabled(),
    is_url=is_url, is_upload=is_upload) }}
```

with

```jinja2
{{ form.image_upload(
    data, errors, is_upload_enabled=h.files_group_images_storage_is_configured(),
    is_url=is_url, is_upload=is_upload,
    field_upload="files_image_upload") }}
```

There are two differences with the original. First, we use
`h.files_group_images_storage_is_configured()` instead of
`h.uploads_enabled()`. As we are using different storage for different upload
types, now upload widgets can be enabled independently. And second, we pass
`field_upload="files_image_upload"` argument into macro. It will send uploaded
file to CKAN inside `files_image_upload` instead of original `image_upload`
field. This must be done because CKAN unconditionally strips `image_upload`
field from submission payload, making processing of the file too unreliable. We
changed the name of upload field and CKAN keeps this new field, so that we can
process it as we wish.

Note: if you are using ckanext-scheming, you only need to replace
`form_snippet` of the `image_url` field, instead of rewriting the whole
template.

Now, let's define validation rules for this new upload field. We need to create
plugins that modify validation schema for group and organization. Due to CKAN
implementation details, you need separate plugin for group and organization.

Note: if you are using ckanext-scheming, you can add `files_image_upload`
validators to schemas of organization and group. Check the list of validators
that must be applied to this new field below.

Here's an example of plugins that modify validation schemas of group and
organization. As you can see, they are mostly the same:

```python
from ckan.lib.plugins import DefaultGroupForm, DefaultOrganizationForm
from ckan.logic.schema import default_create_group_schema, default_update_group_schema


def _modify_schema(schema, type):
    schema["files_image_upload"] = [
        tk.get_validator("ignore_empty"),
        tk.get_validator("files_into_upload"),
        tk.get_validator("files_validate_with_storage")("group_images"),
        tk.get_validator("files_upload_as")(
            "group_images",
            type,
            "id",
            "public_url",
            type + "_patch",
            "image_url",
        ),
    ]


class FilesGroupPlugin(p.SingletonPlugin, DefaultGroupForm):
    p.implements(p.IGroupForm, inherit=True)
    is_organization = False

    def group_types(self):
        return ["group"]

    def create_group_schema(self):
        return _modify_schema(default_create_group_schema(), "group")

    def update_group_schema(self):
        return _modify_schema(default_update_group_schema(), "group")


class FilesOrganizationPlugin(p.SingletonPlugin, DefaultOrganizationForm):
    p.implements(p.IGroupForm, inherit=True)
    is_organization = True

    def group_types(self):
        return ["organization"]

    def create_group_schema(self):
        return _modify_schema(default_create_group_schema(), "organization")

    def update_group_schema(self):
        return _modify_schema(default_update_group_schema(), "organization")
```

There are 4 validators that must be applied to the new upload field:

* `ignore_empty`: to skip validation, when image URL set manually and no upload
  selected.
* `files_into_upload`: to convert value of upload field into normalized format,
  which is expected by ckanext-files
* `files_validate_with_storage(STORAGE_NAME)`: this validator requires an
  argument: the name of the storage we are using for image uploads. The
  validator will use storage settings to verify size and MIMEtype of the
  appload.
* `files_upload_as(STORAGE_NAME, GROUP_TYPE, NAME_OF_ID_FIELD, "public_url",
  NAME_OF_PATCH_ACTION, NAME_OF_URL_FIELF)`: this validator is the most
  challenging. It accepts 6 arguments:
  * the name of storage used for image uploads
  * `group` or `organization` depending on processed entity
  * name of the ID field of processed entity. It's `id` in your case.
  * `public_url` - use this exact value. It tells which property of file you
    want to use as link to the file.
  * `group_patch` or `organization_patch` depending on processed entity
  * `image_url` - name of the field that contains URL of the
    image. ckanext-files will put the public link of uploaded file into this
    field when form is processed.

That's all. Now every image upload for group/organization is handled by
ckanext-files. To verify it, do the following. First, check list of files
currently stored in `group_images` storage via command that we used in the
beginning of the migration:

```sh
ckan files scan -s group_images
```

You'll see a list of existing files. Their names follow format
`<ISO_8691_DATETIME><FILENAME>`, e.g `2024-06-14-133840.539670photo.jpg`.

Now upload an image into existing group, or create a new group with any
image. When you check list of files again, you'll see one new record. But this
time this record resembles UUID: `da046887-e76c-4a68-97cf-7477665710ff`.

### Migration for user avatars

This workflow is similar to group/organization migration. It contains the
sequence of actions, but explanations are removed, because you already know
details from the group migration. Only steps that are different will contain
detailed explanation of the process.


Configure local filesystem storage with support of public
links(`files:public_fs`) for user images.

This extension expects that the name of user images storage will be
`user_images`. This name will be used in all other commands of this migration
workflow. If you want to use different name for user images storage, override
`ckanext.files.user_images_storage` config option which has default value
`user_images` and don't forget to adapt commands if you use a different name
for the storage.

`ckanext.files.storage.user_images.path` resembles this option for
group/organization images storage. But user images are kept inside `user`
folder by default. As result, value of this option should match value of
`ckan.storage_path` option plus `storage/uploads/user`. In example below we
assume that value of `ckan.storage_path` is `/var/storage/ckan`.

`ckanext.files.storage.user_images.public_root` resebles this option for
group/organization images storage. But user images are available at CKAN URL
plus `uploads/user`.

```ini
ckanext.files.storage.user_images.type = files:public_fs
ckanext.files.storage.user_images.max_size = 10MiB
ckanext.files.storage.user_images.supported_types = image
ckanext.files.storage.user_images.path = /var/storage/ckan/storage/uploads/user
ckanext.files.storage.user_images.public_root = %(ckan.site_url)s/uploads/user
```

Check the list of untracked files available inside newly configured storage:

```sh
ckan files scan -s user_images -u
```

Track all these files:

```sh
ckan files scan -s user_images -t
```

Re-check that now you see no untracked files:

```ini
ckan files scan -s user_images -u
```

Transfer image ownership to corresponding users:

```sh
ckan files migrate users user_images
```

Update user template. Required field is defined in `user/new_user_form.html`
and `user/edit_user_form.html`. It's a bit different from the filed used by
group/organization, but you again need to add
`field_upload="files_image_upload"` parameter to the macro `image_upload` and
replace `h.uploads_enabled()` with `h.files_user_images_storage_is_configured()`.

User has no dedicated interface for validation schema modification and here
comes the biggest difference from group migration. You need to chain
`user_create` and `user_update` action and modify schema from `context`:


```python
def _patch_schema(schema):
    schema["files_image_upload"] = [
        tk.get_validator("ignore_empty"),
        tk.get_validator("files_into_upload"),
        tk.get_validator("files_validate_with_storage")("user_images"),
        tk.get_validator("files_upload_as")(
            "user_images",
            "user",
            "id",
            "public_url",
            "user_patch",
            "image_url",
        ),
    ]


@tk.chained_action
def user_update(next_action, context, data_dict):
    schema = context.setdefault('schema', ckan.logic.schema.default_update_user_schema())
    _patch_schema(schema)
    return next_action(context, data_dict)



@tk.chained_action
def user_create(next_action, context, data_dict):
    schema = context.setdefault('schema', ckan.logic.schema.default_user_schema())
    _patch_schema(schema)
    return next_action(context, data_dict)
```

Validators are all the same, but now we are using `user` instead of
`group`/`organization` in parameters.


That's all. Just as with groups, you can update an avatar and verify that all
new filenames resemble UUIDs.

### Migration for resource uploads

Configure named storage for resources. Use `files:ckan_resource_fs` storage
adapter.

This extension expects that the name of resources storage will be
`resources`. This name will be used in all other commands of this migration
workflow. If you want to use different name for resources storage, override
`ckanext.files.resources_storage` config option which has default value
`resources` and don't forget to adapt commands if you use a different name for
the storage.

`ckanext.files.storage.resources.path` must match value of `ckan.storage_path`
option, followed by `resources` directory. In example below we assume that
value of `ckan.storage_path` is `/var/storage/ckan`.

Example below sets 10MiB limit on resource size. Modify it if you are using
different limit set by `ckan.max_resource_size`.

Unlike group and user images, this storage does not need upload type
restriction and `public_root`.

```ini
ckanext.files.storage.resources.type = files:ckan_resource_fs
ckanext.files.storage.resources.max_size = 10MiB
ckanext.files.storage.resources.path = /var/storage/ckan/resources
```

Check the list of untracked files available inside newly configured storage:

```sh
ckan files scan -s resources -u
```

Track all these files:

```sh
ckan files scan -s resources -t
```

Re-check that now you see no untracked files:

```ini
ckan files scan -s resources -u
```

Transfer file ownership to corresponding resources. In addition to simple
ownership transfer, this command will ask you, whether you want to modify
resource's `url_type` and `url` fields. It's required to move file management
to files extension completely and enable possibility of migration to different
storage type.

If you accept resource modifications, for every file owner `url_type` will be
changed to `file` and `url` will be changed to file ID. Then all modified
packages will be reindexed.

Changing `url_type` means that some pages will change. For example, instead of
**Download** button CKAN will show you **Go to resource** button on the
resource page, because **Download** label is specific to `url_type=upload`. And
some views may stop working as well. But this is safer option for migration,
than leaving `url_type` unchanged: ckanext-files manages files in its own way
and some assumptions about files will not work anymore, so using different
`url_type` is the fastest way to tell everyone that something changed.

Broken views can be easily fixed. Every view implemented as a separate
plugin. You always can inherit from this plugin and override methods that
relied on different behavior. And a lot of views work with file URL directly,
so they won't even see the difference.

```sh
ckan files migrate local-resources resources
```

And the next goal is correct metadata schema. If you are using ckanext-schemin,
you need to modify validators of `url` and `format` fields.

If you are working with native schemas, you have to modify dataset schema via
implementing IDatasetForm. Here's an example:


```python
from ckan.lib.plugins import DefaultDatasetForm
from ckan.logic import schema

class FilesDatasetPlugin(p.SingletonPlugin, DefaultDatasetForm):
    p.implements(p.IDatasetForm, inherit=True)

    def is_fallback(self):
        return True

    def package_types(self):
        return ["dataset"]

    def _modify_schema(self, schema):
        schema["resources"]["url"].extend([
            tk.get_validator("files_verify_url_type_and_value"),
            tk.get_validator("files_file_id_exists"),
            tk.get_validator("files_transfer_ownership")("resource","id"),
        ])
        schema["resources"]["format"].insert(0, tk.get_validator("files_content_type_from_file")("url"))

    def create_package_schema(self):
        sch = schema.default_create_package_schema()
        self._modify_schema(sch)
        return sch

    def update_package_schema(self):
        sch = schema.default_update_package_schema()
        self._modify_schema(sch)
        return sch

    def show_package_schema(self):
        sch = schema.default_show_package_schema()
        sch["resources"]["url"].extend([
            tk.get_validator("files_verify_url_type_and_value"),
            tk.get_validator("files_id_into_resource_download_url"),
        ])
        return sch

```

Both create and update schemas are updated in the same way. We add a new
validator to format field, to correctly identify file format. And wi add a
number of validators to `url`:

* `files_verify_url_type_and_value`: skip validation if we are not working with
  resource that contains file.
* `files_file_id_exists`: verify existence of file ID
* `files_transfer_ownership("resource","id")`: move file ownership to resource
  after successful validation

At top of this, we also have two validators applied to
`show_package_schema`(use `output_validators` in ckanext-scheming):

* `files_verify_url_type_and_value`: skip validation if we are not working with
  resource that contains file.
* `files_id_into_resource_download_url`: replace file ID with download URL in
  API output


And the next part is the trickiest. You need to create a number of templates
and JS modules. But because ckanext-files is actively developed, most likely,
your custom files will be outdated pretty soon.

Instead, we recommend enabling patch for resource form that shipped with
ckanext-files. It's a bit hacky, but because the extension itself is stil in
alpha-stage, it should be acceptable. Check [file upload
strategies](#file-upload-strategies) for examples of implementation that you
can add to your portal instead of the default patch.

To enable patch for templates, add following line to the config file:

```ini
ckanext.files.enable_resource_migration_template_patch = true
```

This option adds **Add file** button to resource form

![button on resource form](./screenshots/resource-form-btn.png)

Upon clicking, this button is replaced by widget that supports uploading new
files of selecting previously uploaded files that are not used by any resource
yet

![expanded widget on resource form](./screenshots/resource-form-file.png)
