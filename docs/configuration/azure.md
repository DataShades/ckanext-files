# Azure Blob storage configuration

To use this storage install extension with `azure` extras.

```sh
pip install 'ckanext-files[azure]'
```


```ini
## Storage adapter used by the storage
ckanext.files.storage.NAME.type = files:azure_blob
## Name of the account.
ckanext.files.storage.NAME.account_name =
## Key for the account.
ckanext.files.storage.NAME.account_key =
## Custom resource URL.
ckanext.files.storage.NAME.account_url = https://{account_name}.blob.core.windows.net
## Name of the storage container.
ckanext.files.storage.NAME.container_name =
```
