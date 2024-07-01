# Apache libcloud storage configuration

To use this storage install extension with `libcloud` extras.

```sh
pip install 'ckanext-files[libcloud]'
```

The actual storage backend is controlled by `provider` option of the
storage. List of all providers is available
[here](https://libcloud.readthedocs.io/en/stable/storage/supported_providers.html#provider-matrix)

```ini
## Storage adapter used by the storage
ckanext.files.storage.NAME.type = files:libcloud
## apache-libcloud storage provider. List of providers available at https://libcloud.readthedocs.io/en/stable/storage/supported_providers.html#provider-matrix . Use upper-cased value from Provider Constant column
ckanext.files.storage.NAME.provider =
## API key or username
ckanext.files.storage.NAME.key =
## Secret password
ckanext.files.storage.NAME.secret =
## JSON object with additional parameters passed directly to storage constructor.
ckanext.files.storage.NAME.params =
## Name of the container(bucket)
ckanext.files.storage.NAME.container =
```
