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
ckanapi action files_file_create upload@<(echo -n "hello world") name=file.txt
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

```sh
ckanapi action files_file_delete id=226056e2-6f83-47c5-8bd2-102e2b82ab9a
```

Params:

* `id`: ID of the file
* `completed`: use `False` to remove incomplete uploads. Default: `True`

Returns:

dictionary with details of the removed file.


## files_file_pin

Pin file to the current owner.

Pinned file cannot be transfered to a different owner. Use it to guarantee
that file referred by entity is not accidentally transferred to a different
owner.

Params:

* `id`: ID of the file
* `completed`: use `False` to pin incomplete uploads. Default: `True`

Returns:

dictionary with details of updated file


## files_file_rename

Rename the file.

This action changes human-readable name of the file, which is stored in
DB. Real location of the file in the storage is not modified.

```sh
ckanapi action files_file_show \
    id=226056e2-6f83-47c5-8bd2-102e2b82ab9a \
    name=new-name.txt
```

Params:

* `id`: ID of the file
* `name`: new name of the file
* `completed`: use `False` to rename incomplete uploads. Default: `True`

Returns:

dictionary with file details


## files_file_scan

List files of the owner

This action internally calls files_file_search, but with static values of
owner filters. If owner is not specified, files filtered by current
user. If owner is specified, user must pass authorization check to see
files.

Params:

* `owner_id`: ID of the owner
* `owner_type`: type of the owner

The all other parameters are passed as-is to `files_file_search`.

Returns:

* `count`: total number of files matching filters
* `results`: array of dictionaries with file details.


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

* `count`: total number of files matching filters
* `results`: array of dictionaries with file details.


## files_file_show

Show file details.

This action only displays information from DB record. There is no way to
get the content of the file using this action(or any other API action).

```sh
ckanapi action files_file_show id=226056e2-6f83-47c5-8bd2-102e2b82ab9a
```

Params:

* `id`: ID of the file
* `completed`: use `False` to show incomplete uploads. Default: `True`

Returns:

dictionary with file details


## files_file_unpin

Pin file to the current owner.

Pinned file cannot be transfered to a different owner. Use it to guarantee
that file referred by entity is not accidentally transferred to a different
owner.

Params:

* `id`: ID of the file
* `completed`: use `False` to unpin incomplete uploads. Default: `True`

Returns:

dictionary with details of updated file


## files_multipart_complete

Finalize multipart upload and transform it into completed file.

Depending on storage this action may require additional parameters. But
usually it just takes ID and verify that content type, size and hash
provided when upload was initialized, much the actual value.

If data is valid and file is completed inside the storage, new File entry
with file details created in DB and file can be used just as any normal
file.

Requires storage with `MULTIPART` capability.

Params:

* `id`: ID of the incomplete upload

Returns:

dictionary with details of the created file


## files_multipart_refresh

Refresh details of incomplete upload.

Can be used if upload process was interrupted and client does not how many
bytes were already uploaded.

Requires storage with `MULTIPART` capability.

Params:

* `id`: ID of the incomplete upload

Returns:

dictionary with details of the updated upload


## files_multipart_start

Initialize multipart(resumable,continuous,signed,etc) upload.

Apart from standard parameters, different storages can require additional
data, so always check documentation of the storage before initiating
multipart upload.

When upload initialized, storage usually returns details required for
further upload. It may be a presigned URL for direct upload, or just an ID
of upload which must be used with `files_multipart_update`.

Requires storage with `MULTIPART` capability.

Params:

* `storage`: name of the storage that will handle the upload. Default: `default`
* `name`: name of the uploaded file.
* `content_type`: MIMEtype of the uploaded file. Used for validation
* `size`: Expected size of upload. Used for validation
* `hash`: Expected content hash. If present, used for validation.

Returns:

dictionary with details of initiated upload. Depends on used storage


## files_multipart_update

Update incomplete upload.

Depending on storage this action may require additional parameters. Most
likely, `upload` with the fragment of uploaded file.

Requires storage with `MULTIPART` capability.

Params:

* `id`: ID of the incomplete upload

Returns:

dictionary with details of the updated upload


## files_resource_upload

Create a new file inside resource storage.

This action internally calls `files_file_create` with `ignore_auth=True`
and always uses resources storage.

New file is not attached to resource. You need to call
`files_transfer_ownership` manually, when resource created.

Params:

* `name`: human-readable name of the file. Default: guess using upload field
* `upload`: content of the file as string, bytes, file descriptor or uploaded file

Returns:

dictionary with file details.


## files_transfer_ownership

Transfer file ownership.

Params:

* `id`: ID of the file upload
* `completed`: use `False` to transfer incomplete uploads. Default: `True`
* `owner_id`: ID of the new owner
* `owner_type`: type of the new owner
* `force`: move file even if it's pinned. Default: `False`
* `pin`: pin file after transfer to stop future transfers. Default: `False`

Returns:

dictionary with details of updated file
