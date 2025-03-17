# Storage configuration

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
## Name of the Redis hash that contains all uploads
ckanext.files.storage.xxx.path = ckanext:files:default:file_content
```

Sometimes you will see a validation error if storage has required config
options. Let's try using `files:fs` storage instead of the redis:

```ini
ckanext.files.storage.xxx.type = files:fs
```

Now any attempt to run `ckan config declaration files -d` will show an error,
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
## If file already exists, replace it with new content.
ckanext.files.storage.NAME.override_existing = false
## Descriptive name of the storage used for debugging. When empty, name from
## the config option is used, i.e: `ckanext.files.storage.DEFAULT_NAME...`
ckanext.files.storage.NAME.name = NAME
```
