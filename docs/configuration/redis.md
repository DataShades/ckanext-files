# Redis storage configuration

```ini
## Storage adapter used by the storage
ckanext.files.storage.NAME.type = files:redis
## Static prefix of the Redis key generated for every upload.
ckanext.files.storage.NAME.prefix = ckanext:files:default:file_content:
```
