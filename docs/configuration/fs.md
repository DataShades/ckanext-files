# Filesystem storage configuration

Private filesystem storage

```ini
## Storage adapter used by the storage
ckanext.files.storage.NAME.type = files:fs
## Path to the folder where uploaded data will be stored.
ckanext.files.storage.NAME.path =
## Create storage folder if it does not exist.
ckanext.files.storage.NAME.initialize = false
```


Public filesystem storage

```ini
## Storage adapter used by the storage
ckanext.files.storage.NAME.type = files:public_fs
## Path to the folder where uploaded data will be stored.
ckanext.files.storage.NAME.path =
## Create storage folder if it does not exist.
ckanext.files.storage.NAME.initialize = false
## URL of the storage folder. `public_prefix + location` must produce a public URL
ckanext.files.storage.NAME.public_prefix =
```
