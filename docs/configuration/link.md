# Storage storage configuration


```ini
## Storage adapter used by the storage
ckanext.files.storage.NAME.type = files:link
## Request timeout used when link details fetched during upload.
ckanext.files.storage.NAME.type = 5
## List of allowed protocols for link uploads. Empty list means all protocols are allowed.
ckanext.files.storage.NAME.protocols =
## List of allowed hostnames for link uploads. Empty list means all domains are allowed.
ckanext.files.storage.NAME.domains =
```
