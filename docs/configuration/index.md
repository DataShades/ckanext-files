# Configuration

There are two types of config options for ckanext-files:

* Global: affects the behavior of the extension and every available storage
  adapter.
* Storage configuration: changes behavior of the specific storage and never
  affects anything outside of the storage.

Depending on the type of the storage, available options are quite
different. For example, `files:fs` storage type requires `path` option that
controls filesystem path where uploads are stored and allows `recursive` flag
that enables sub-directories. `files:redis` storage type accepts optional
`path` option that defines the name of the Redis' hash where files are stored
and has nothing similar to `recursive`. All storage specific options always
have form `ckanext.files.storage.<STORAGE>.<OPTION>`:

```ini
ckanext.files.storage.memory.path = xxx
# or
ckanext.files.storage.my_drive.path = /tmp/hello
```
