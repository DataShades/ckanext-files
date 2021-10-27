# ckanext-files

Upload and use standalone files. No resources, no datasets, just files.


## Requirements


Compatibility with core CKAN versions:

| CKAN version | Compatible? |
|--------------|-------------|
| 2.9          | yes         |
| master       | yes         |

## Installation

To install ckanext-files:

1. Install the extension

		pip install ckanext-files

1. Add `files` to the `ckan.plugins` setting in your CKAN
   config file.

1. Updgrade DB

		ckan db upgrade -p files

## API

Each API action has corresponding auth-function with the same name. By default
only sysadmin can pass auth check(unless different behavior explicitly
mentioned in action description). Whenever you are using this extension feel
free to redefine these auth-functions using `tk.chained_auth_function`.

Some of API actions has `kind` parameter. It defines which folder will store
the file, which config options will be applied, etc. Default value is
`ckanext_files_file`

* `files_file_create`

  Create new `file` entity.

  Parameters:
  * `name` Name for the uploaded file.
  * `upload` File itself
  * `kind` Type of uploaded file.
  * `extras` Dictionary with any details that can be used for your needs.

  Returns:
  * `id: str` Unique ID of the new `file`.
  * `name: str` Name for the `file`.
  * `url: str` File itself
  * `kind: str` Type of uploaded file.
  * `uploaded_at: datetime.datetime` File creation date
  * `extras: Optional[dict[str, Any]]` Dictionary with any details that can be used for your needs.

* `files_file_show`

  Show `file` detiles.

  Parameters:
  * `id: str`: ID or name of file entity

  Returns: same as `files_file_create`

* `files_file_update`

  Update `file` entity.

  Parameters:
  * `id: str`
  * `name: Optional[str]` Name for the `file` file.
  * `upload: Optional[werkzeug.datastructures.FileStorage]` File itself
  * `kind: Optional[str]` Type of uploaded file.
  * `extras: Optional[dict[str, Any]]` Dictionary with any details that can be used for your needs.

  Returns: same as `files_file_create`

* `files_file_delete`

  Remove `file` entity.

  Parameters:
  * `id: str`: ID of file entity

  Returns: `True`

## Config settings

	# Allowed size for uploaded file in MB.
	# (optional, default: 2).
	ckanext.files.<KIND>.max_size = 2
