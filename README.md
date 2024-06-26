[![Tests](https://github.com/DataShades/ckanext-files/actions/workflows/test.yml/badge.svg)](https://github.com/DataShades/ckanext-files/actions/workflows/test.yml)

# ckanext-files

Files as first-class citizens of CKAN. Upload, manage, remove files directly
and attach them to datasets, resources, etc.

Read the [documentation](https://datashades.github.io/ckanext-files/) for a full user guide.


## Quickstart

1. Install the extension
   ```sh
   pip install ckanext-files
   ```

1. Add `files` to the `ckan.plugins` setting in your CKAN
   config file.

1. Run DB migrations
   ```sh
   ckan db upgrade -p files
   ```

1. Configure storage

    ```ini
    ckanext.files.storage.default.type = files:fs
    ckanext.files.storage.default.path = /tmp/example
    ckanext.files.storage.default.create_path = true
    ```

1. Upload your first file

    ```sh
    ckanapi action files_file_create upload@~/Downloads/file.txt`
    ```


## Development

Install `dev` extras and nodeJS dependencies:

```sh
pip install -e '.[dev]'
npm ci
```

Run unittests:
```sh
pytest
```

Run frontend tests:
```sh
# start test server in separate terminal
make test-server

# run tests
npx cypress run
```

Run typecheck:
```sh
npx pyright
```


## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)
