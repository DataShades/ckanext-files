# Configure the storage

Before uploading files, you have to configure a **storage**: place where all
uploaded files are stored. Storage relies on **adapter** that describes where
and how data is be stored: filesystem, cloud, DB, etc. And, depending on the
adapter, storage may have a couple of addition specific options. For example,
filesystem adapter likely requires a path to the folder where uploads are
stored. DB adapter may need DB connection parameters. Cloud adapter most likely
will not work without an API key. These additional options are specific to
adapter and you have to check its documentation to find out what are the
possible options.

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


??? question "See an error?"

    If you make a typo in the adapter's name, any CKAN CLI command will produce an
    error message with the list of available adapters:

    ```sh
    Invalid configuration values provided:
    ckanext.files.storage.default.type: Value must be one of ['files:fs', 'files:redis']
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
echo -n 'hello world' > /tmp/myfile.txt
ckanapi action files_file_create name=hello.txt upload@/tmp/myfile.txt
```

And that's what you see as result:

```json
{
  "atime": null,
  "content_type": "text/plain",
  "ctime": "2024-06-02T15:02:14.819117+00:00",
  "hash": "5eb63bbbe01eeed093cb22bb8f5acdc3",
  "id": "e21162ab-abfb-476c-b8c5-5fe7cb89eca0",
  "location": "hello.txt",
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

Alternatively, we can use Redis CLI to get the content of the file.

/// admonition | Note
File cannot be streamed via CKAN API, because it's JSON-based and streaming
files doesn't suit its principles.
///

By default, Redis adapter puts the content into hash
`ckanext:files:default:file_content`. Inside it, file stored under the key that
matches `location` in the API response(i.e, `hello.txt` in our case). It's
different from the `id`(used to connect a file from the storage to its metadata
stored in CKAN DB) and `name`(human readable name of the file). In our
scenario, `location` matches filename because of the internal details of Redis
adapter implementation. But different adapters can use more path-like
value(`path/to/folder/hello.txt`), or even
UUID(`24d27fb9-a5f0-42f6-aaa3-7dcb599a0d46`)

The name of the Redis hash(`ckanext:files:default:file_content`) is
configurable, but we skipped this step and got the default value:
`ckanext:files:default:file_content`.

```sh
$ redis-cli

127.0.0.1:6379> HGET ckanext:files:default:file_content hello.txt
"hello world"
```

/// admonition | Don't forget to remove the file
    type: tip
```sh
ckanapi action files_file_delete id=e21162ab-abfb-476c-b8c5-5fe7cb89eca0
```
///
