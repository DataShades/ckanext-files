# Filesystem storage configuration

Private filesystem storage

```ini
## Storage adapter used by the storage
ckanext.files.storage.NAME.type = files:fs
## Path to the folder where uploaded data will be stored.
ckanext.files.storage.NAME.path =
## Create storage folder if it does not exist.
ckanext.files.storage.NAME.create_path = false
## Use this flag if files can be stored inside subfolders
## of the main storage path.
ckanext.files.storage.NAME.recursive = false
```


Public filesystem storage

```ini
## Storage adapter used by the storage
ckanext.files.storage.NAME.type = files:public_fs
## Path to the folder where uploaded data will be stored.
ckanext.files.storage.NAME.path =
## Create storage folder if it does not exist.
ckanext.files.storage.NAME.create_path = false
## Use this flag if files can be stored inside subfolders
## of the main storage path.
ckanext.files.storage.NAME.recursive = false
## URL of the storage folder. `public_prefix + location` must produce a public URL
ckanext.files.storage.NAME.public_prefix =
```
