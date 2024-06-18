## files_file_create

Create a new file.

This action passes uploaded file to the storage without strict
validation. File is converted into standard upload object and everything
else is controlled by storage. The same file may be uploaded to one storage
and rejected by other, depending on configuration.

This action is way too powerful to use it directly. The recommended
approach is to register a different action for handling specific type of
uploads and call current action internally.

When uploading a real file(or using `werkqeug.datastructures.FileStorage`),
name parameter can be omited. In this case, the name of uploaded file is used.

```python
ckanapi action files_file_create upload@path/to/file.txt
```

When uploading a raw content of the file using string or bytes object, name
is mandatory.

```python
ckanapi action files_file_create upload="hello world" name=file.txt
```

Requires storage with `CREATE` capability.

Params:

* `name`: human-readable name of the file. Default: guess using upload field
* `storage`: name of the storage that will handle the upload. Default: `default`
* `upload`: content of the file as string, bytes, file descriptor or uploaded file

Returns:

dictionary with file details.


## files_file_delete

Remove file from storage.

Unlike packages, file has no `state` field. Removal usually means that file
details removed from DB and file itself removed from the storage.

Some storage can implement revisions of the file and keep archived versions
or backups. Check storage documentation if you need to know whether there
are chances that file is not completely removed with this operation.

Requires storage with `REMOVE` capability.

Params:

* `id`: ID of the file. `name` and `location` cannot be used here.
* `completed`: use `False` to remove incomplete uploads. Default: `True`

Returns:

dictionary with details of the removed file.


## files_file_pin




## files_file_rename




## files_file_search

Search files.

This action is not stabilized yet and will change in future.

Provides an ability to search files using exact filter by name,
content_type, size, owner, etc. Results are paginated and returned in
package_search manner, as dict with `count` and `results` items.

All columns of File model can be used as filters. Before the search, type
of column and type of filter value are compared. If they are the same,
original values are used in search. If type different, column value and
filter value are casted to string.

This request produces `size = 10` SQL expression:
```sh
ckanapi action files_file_search size:10
```

This request produces `size::text = '10'` SQL expression:
```sh
ckanapi action files_file_search size=10
```

Even though results are usually not changed, using correct types leads to
more efficient search.

Apart from File columns, the following Owner properties can be used for
searching: `owner_id`, `owner_type`, `pinned`.

`storage_data` and `plugin_data` are dictionaries. Filter's value for these
fields used as a mask. For example, `storage_data={"a": {"b": 1}}` matches
any File with `storage_data` *containing* item `a` with value that contains
`b=1`. This works only with data represented by nested dictionaries,
without other structures, like list or sets.

Experimental feature: File columns can be passed as a pair of operator and
value. This feature will be replaced by strictly defined query language at
some point:

```sh
ckanapi action files_file_search size:'["<", 100]' content_type:'["like", "text/%"]'
```
Fillowing operators are accepted: `=`, `<`, `>`, `!=`, `like`

Params:

* `start`: index of first row in result/number of rows to skip. Default: `0`
* `rows`: number of rows to return. Default: `10`
* `sort`: name of File column used for sorting. Default: `name`
* `reverse`: sort results in descending order. Default: `False`
* `storage_data`: mask for `storage_data` column. Default: `{}`
* `plugin_data`: mask for `plugin_data` column. Default: `{}`
* `owner_type: str`: show only specific owner id if present. Default: `None`
* `owner_type`: show only specific owner type if present. Default: `None`
* `pinned`: show only pinned/unpinned items if present. Default: `None`
* `completed`: use `False` to search incomplete uploads. Default: `True`

Returns:

* `count`: total number of files mathing filters
* `results`: array of dictionaries with file details.


## files_file_search_by_user

Internal action. Do not use it.


## files_file_show




## files_file_unpin




## files_multipart_complete




## files_multipart_refresh




## files_multipart_start




## files_multipart_update




## files_resource_upload




## files_transfer_ownership
