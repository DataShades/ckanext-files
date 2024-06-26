# CLI

ckanext-files register `files` entrypoint under `ckan` command. Commands below
must be executed as `ckan -c $CKAN_INI files <COMMAND>`.

`adapters [-v]`

List all available storage adapters. With `-v/--verbose` flag docstring from
adapter classes are printed as well.


`storages [-v]`

List all configured storages. With `-v/--verbose` flag all supported
capabilities are shown.

`stream FILE_ID [-o OUTPUT] [--start START] [--end END]`

Stream content of the file to STDOUT. For non-textual files use output
redirection `stream ID > file.ext`. Alternatively, output destination can be
specified via `-o/--output` option. If it contains path to directory, inside
this directory will be created file with the same name as streamed
item. Otherwise, `OUTPUT` is used as filename.

`--start` and `--end` can be used to receive a fragment of the file. Only
positive values are guaranteed to work with any storage that supports
STREAM. Some storages support negative values for these options and count them
from the end of file. I.e `--start -10` reads last 10 bytes of file. `--end -1`
reads till the last byte, but the last byte is not included into output.

`scan [-s default] [-u] [-t [-a OWNER_ID]]`

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
