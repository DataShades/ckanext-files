# Tracked and untracked files

There is a difference between creating files via action:

```python
tk.get_action("files_file_create")(
    {"ignore_auth": True},
    {"upload": b"hello", "name": "hello.txt"}
)
```

and via direct call to `Storage.upload`:

```python
from ckanext.files.shared import get_storage, make_upload

storage = get_storage()
storage.upload("hello.txt", make_upload(b"hello"))
```

The former snippet creates a *tracked* file: file uploaded to the storage and
its details are saved to the database.

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

=== "Show all files"

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
    ...       "location": "hello.txt",
    ...       "mtime": null,
    ...       "name": "hello.txt",
    ...       "size": 11,
    ...       "storage": "default",
    ...       "storage_data": {}
    ...     },
    ...     ...
    ...   ]
    ... }
    ```

=== "Get first file with size 5 bytes"
    ```sh
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
    ...       "location": "hello.txt",
    ...       "mtime": null,
    ...       "name": "hello.txt",
    ...       "size": 5,
    ...       "storage": "default",
    ...       "storage_data": {}
    ...     }
    ...   ]
    ... }

    ```

=== "Show all PDF files"
    ```sh

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
