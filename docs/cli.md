# CLI

ckanext-files register `files` entrypoint under `ckan` command. Commands below
must be executed as `ckan -c $CKAN_INI files <COMMAND>`.

## adapters

!!! example

    ```sh
    ckan files adapters
    ```

List all available storage adapters.

| Option           | Effect                      |
|------------------|-----------------------------|
| `-v`/`--verbose` | Include adapter's docstring |



## storages

!!! example

    ```sh
    ckan files storages
    ```

List all configured storages.


| Option           | Effect                         |
|------------------|--------------------------------|
| `-v`/`--verbose` | Include storage's capabilities |


## stream FILE_ID

!!! example

    ```sh
    ckan files stream b9483985-2681-4647-9b0f-f4acb4fd0fd3 -o /tmp
    ```

Stream content of the file to STDOUT. For non-textual files use output
redirection `stream ID > file.ext`. Alternatively, output destination can be
specified via `-o` option. If it contains path to directory, inside this
directory will be created file with the same name as streamed item. Otherwise,
`OUTPUT` is used as filename.

`--start` and `--end` can be used to receive a fragment of the file. Only
positive values are guaranteed to work with any storage that supports
STREAM. Some storages support negative values for these options and count them
from the end of file. I.e `--start -10` reads last 10 bytes of file. `--end -1`
reads till the last byte, but the last byte is not included into output.

| Option          | Effect                                  |
|-----------------|-----------------------------------------|
| `-o`/`--output` | Stream into specified file or directory |
| `--start`       | Start streaming from specified position |
| `--end`         | End streaming at position               |



## scan

!!! example

    ```sh
    ckan files scan
    ```

List all files that exist in storage. Works only if storage supports `SCAN`. By
default shows content of `default` storage. `-s/--storage-name` option changes
target storage.

`-u/--untracked-only` flag shows only untracked files, that has no
corresponding record in DB. Can be used to identify leftovers after removing
data from portal.

`-t/--track` flag registers any untracked file by creating DB record for
it. Can be used only when `ANALYZE` is supported. Files are created without an
owner. Use `-a/--adopt-by` option with user ID to give ownership over new files
to the specified user. Can be used when configuring a new storage connected to
existing location with files.


| Option                  | Effect                                                      |
|-------------------------|-------------------------------------------------------------|
| `-s`/`--storage-name`   | Name of the target storage                                  |
| `-u`/`--untracked-only` | Show only untracked files                                   |
| `-t`/`--track`          | Track every untracked file                                  |
| `-a`/`--adopt-by`       | Transfer every file affected by `-t` flag to specified user |


## stats

Group of commands for computing storage statistics.

### overview

!!! example

    ```sh
    ckan files stats overview
    ```

General information about storage usage.


| Option                | Effect                     |
|-----------------------|----------------------------|
| `-s`/`--storage-name` | Name of the target storage |


### owner

!!! example

    ```sh
    ckan files stats owner
    ```

Files distribution by owner.


| Option                | Effect                     |
|-----------------------|----------------------------|
| `-s`/`--storage-name` | Name of the target storage |

### types

!!! example

    ```sh
    ckan files stats types
    ```

Files distribution by MIMEtype.

| Option                | Effect                                                 |
|-----------------------|--------------------------------------------------------|
| `-s`/`--storage-name` | Name of the target storage                             |
| `-v`/`--verbose`      | Do not group records by owner ID instead of owner type |


## maintain

Group of commands for storage maintenance.

### empty-owner

!!! example

    ```sh
    ckan files maintain empty-owner --remove
    ```

Manage files that have no owner.

In normal workflow every file has an owner. Usually, unowned files appear after
performing `scan` with `--track` flag. Prefer transfering such files to an
owner or removing them.

| Option                | Effect                     |
|-----------------------|----------------------------|
| `-s`/`--storage-name` | Name of the target storage |
| `--remove`            | Remove all located files   |

### invalid-owner

!!! example

    ```sh
    ckan files maintain invalid-owner --remove
    ```

Manage files that have owner details, but owner itself cannot be located.

There are no restrictions for owner type and ID values. It's possible to assign
absolutely any value to these attributes. But usually owner type refers to the
name of CKAN model, and owner ID refers to model's ID. ckanext-files can locate
owners that are specified in such way.

Extensions can use different logic, but in this case, they need to extend owner
location logic and explain, how custom owners can be found.

As result, if owner of file is specified but cannot be found, it means that
owner was removed from DB. Prefer transfering such files to a different owner
or removing them.


| Option                | Effect                     |
|-----------------------|----------------------------|
| `-s`/`--storage-name` | Name of the target storage |
| `--remove`            | Remove all located files   |


### missing-files

!!! example

    ```sh
    ckan files maintain missing-files --remove
    ```

Manage files that do not exist in storage.

Such items appear when real file is removed from the storage manually. For
example, by running `rm -f /path/to/file` in case of `files:fs` storage.

These files must be removed from DB as well. Usually, there is no sense in
storing metadata of content that is no longer available.



| Option                | Effect                     |
|-----------------------|----------------------------|
| `-s`/`--storage-name` | Name of the target storage |
| `--remove`            | Remove all located files   |


## migrate

Group of commands for migration from different storage implementations.

!!! info

    This is experimental command and migration process can change in the
    stable release of ckanext-files.

### groups STORAGE_NAME

!!! example

    ```sh
    ckan files migrate groups group_images
    ```

Migrate group images to specified storage.

### users STORAGE_NAME

!!! example

    ```sh
    ckan files migrate users user_images
    ```

Migrate user avatars to specified storage.

### local-resources STORAGE_NAME

!!! example

    ```sh
    ckan files migrate local-resources resources
    ```

Migrate resources uploaded via original ResourceUploader.
