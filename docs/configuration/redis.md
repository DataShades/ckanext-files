# Redis storage configuration

```ini
## Storage adapter used by the storage
ckanext.files.storage.NAME.type = files:redis
## Name of the Redis hash that contains all uploads
ckanext.files.storage.NAME.path = ckanext:files:default:file_content
```
