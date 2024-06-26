# OpenDAL storage configuration

To use this storage install extension with `opendal` extras.

```sh
pip install 'ckanext-files[opendal]'
```

The actual storage backend is controlled by `scheme` option of the
storage. List of all schemes is available
[here](https://docs.rs/opendal/latest/opendal/services/index.html)

```ini
## Storage adapter used by the storage
ckanext.files.storage.NAME.type = files:opendal
## OpenDAL service type. Check available services at  https://docs.rs/opendal/latest/opendal/services/index.html
ckanext.files.storage.NAME.scheme =
## JSON object with parameters passed directly to OpenDAL operator.
ckanext.files.storage.NAME.params =
```
