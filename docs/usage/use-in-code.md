# Usage in code

If you are writing the code and you want to interact with the storage directly,
without the API layer, you can do it via a number of public functions of the
extension available in `ckanext.files.shared`.

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

To create the file, `storage.upload` method must be called with 2 parameters:

* the human readable name of the file
* special steam-like object with content of the file

You can use any string as the first parameter. As for the "special stream-like
object", ckanext-files has `ckanext.files.shared.make_upload` function, that
accepts a number of different types(`bytes`,
`werkzeug.datastructures.FileStorage`, `BytesIO`, file descriptor) and converts
them into expected format.

=== "bytes"

    ```python
    from ckanext.files.shared import make_upload

    upload = make_upload(b"hello world")
    result = storage.upload('file.txt', upload)

    print(result)

    ... FileData(
    ...     location='60b385e7-8137-496c-bb1d-6ae4d7963ab3',
    ...     size=11,
    ...     content_type='text/plain',
    ...     hash='5eb63bbbe01eeed093cb22bb8f5acdc3',
    ...     storage_data={}
    ... )
    ```

=== "BytesIO"

    ```python
    from io import BytesIO
    from ckanext.files.shared import make_upload

    upload = make_upload(BytesIO(b"hello world"))
    result = storage.upload('file.txt', upload)

    print(result)

    ... FileData(
    ...     location='60b385e7-8137-496c-bb1d-6ae4d7963ab3',
    ...     size=11,
    ...     content_type='text/plain',
    ...     hash='5eb63bbbe01eeed093cb22bb8f5acdc3',
    ...     storage_data={}
    ... )
    ```

=== "SpooledTemporaryFile"

    ```python
    from tempfile import SpooledTemporaryFile
    from ckanext.files.shared import make_upload

    file = SpooledTemporaryFile()
    file.write(b"hello world")
    file.seek(0)
    upload = make_upload(file)
    result = storage.upload('file.txt', upload)

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

`result` object has `location` attribute that contains the name of the file
*relative* to the `path` option specified in the storage configuration. If you
visit `/tmp/example` directory, which was set as a `path` for the storage,
you'll see there a file with the name matching `location` from result. And its
content matches the content of our upload, which is quite an expected outcome.

```sh
cat /tmp/example/60b385e7-8137-496c-bb1d-6ae4d7963ab3

... hello world
```

But let's go back to the shell and try reading file from the python's
code. We'll pass `result` to the storage's `stream` method, which produces an
iterable of bytes based on our result:

```python
buffer = storage.stream(result)
content = b"".join(buffer)

... b'hello world'
```

In most cases, storage only needs a location of the file object to read it. So,
if you don't have `result` generated during the upload, you still can read the
file as long as you have its location. But remember, that some storage adapters
may require additional information, and the following example must be modified
depending on the adapter:

```python
from ckanext.files.shared import FileData

location = "60b385e7-8137-496c-bb1d-6ae4d7963ab3"
data = FileData(location)

buffer = storage.stream(data)
content = b"".join(buffer)
print(content)

... b'hello world'
```

And finally we can to remove the file

```python
storage.remove(result)
```
