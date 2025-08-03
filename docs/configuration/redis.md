# Redis storage configuration

```ini
## Storage adapter used by the storage
ckanext.files.storage.NAME.type = files:redis
## Name of the Redis HASH that contains all uploads
ckanext.files.storage.NAME.bucket = ckanext:files:default:file_content
```
