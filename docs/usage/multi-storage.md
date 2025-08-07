# Multi-storage

It's possible to configure multiple storages at once and specify which one you
want to use for the individual file upload. Up until now we used the following
storage options:

* `ckanext.files.storage.default.type`
* `ckanext.files.storage.default.path`
* `ckanext.files.storage.default.initialize`

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
ckanext.files.storage.custom.initialize = true
```

And, if you want to use Redis-based storage named `memory` and filesystem-based
storage named `default`, use the following configuration:

```ini
ckanext.files.storage.memory.type = files:redis

ckanext.files.storage.default.type = files:fs
ckanext.files.storage.default.path = /tmp/example
ckanext.files.storage.default.initialize = true
```

The `default` storage is special. ckanext-files uses it _by default_, as name
suggests. If you remove configuration for the `default` storage and try to
create a file, you'll see the following error:

```sh
echo 'hello world' > /tmp/myfile.txt
ckanapi action files_file_create name=hello.txt upload@/tmp/myfile.txt

... ckan.logic.ValidationError: None - {'storage': ['Storage default is not configured']}
```

"Storage **default** is not configured" - that's why we need `default`
configuration. But if you want to upload a file into a different storage or you
don't want to add the `default` storage at all, you can specify explicitly the
name of the storage you are going to use.

=== "API"

    When using API actions, add `storage` parameter to the call:

    ```sh
    echo 'hello world' > /tmp/myfile.txt
    ckanapi action files_file_create name=hello.txt \
        upload@/tmp/myfile.txt \
        storage=memory
    ```

=== "Python"

    When writing python code, pass storage name to `get_storage` function:
    ```python
    storage = get_storage("memory")
    ```

=== "JS"

    When writing JS code, pass object `{requestParams: {storage: "memory"}}` to
    `upload` function:

    ```js
    const sandbox = ckan.sandbox()
    const file = new File(["content"], "file.txt")
    const options = {requestParams: {storage: "memory"}};

    await sandbox.files.upload(file, options)
    ```
