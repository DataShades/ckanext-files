# ckanext-files

Files as first-class citizens of CKAN. Upload, manage, remove files directly
and attach them to datasets, resources, etc.

## Requirements

Compatibility with core CKAN versions:

| CKAN version | Compatible? |
|--------------|-------------|
| 2.8          | yes         |
| 2.9          | yes         |
| 2.10         | yes         |
| master       | yes         |

CKAN v2.8 and v2.9 are supported by ckanext-files v0.2. Starting from v1.0 this
extension switches to CKAN support policy of two latest CKAN releases. I.e,
ckanext-files v1.0 supports only CKAN v2.10 and v2.11.

v0.2 will not receive any new features, only bug-fixes.

It's recommended to install the extension via pip, so you probably have all the
requirements pinned already. If you are using GitHub version of this extension,
stick to the vX.Y.Z tags to avoid breaking changes. Check the changelog before
upgrading the extension.

## Installation

To install ckanext-files:

1. Install the extension
   ```sh
   # minimal installation
   pip install ckanext-files

  # Google Cloud Storage support
   pip install 'ckanext-files[gcstorage]'
   ```

1. Add `files` to the `ckan.plugins` setting in your CKAN
   config file.

1. Run DB migrations
   ```sh
   # CKAN >= v2.9 with alembic
   ckan db upgrade -p files

   # CKAN == v2.8
   paster  --plugin=ckanext-files  files -c ckan.ini initdb
   ```

## Usage



## Configuration

There are two types of config options for ckanext-files:
* Global configuration affects the common behavior of the extension
* Storage configuration changes behavior of the specific storage and never
  affects anything outside of the storage

Depending on the type of the storage, available options for storage change. For
example, `files:fs` storage type requires `path` option that controls
filesystem path where uploads are stored. `files:redis` storage type accepts
`prefix` option that defines Redis' key prefix of files stored in Redis. All
storage specific options always have form
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
