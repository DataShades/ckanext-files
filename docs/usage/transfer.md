# Ownership transfer

File ownership can be transfered. As there can be only one owner of the file,
as soon as you transfer ownership over file, you yourself do not own this file.

To transfer ownership, use `files_transfer_ownership` action and specify `id`
of the file, `owner_id` and `owner_type` of the new owner.

You can't just transfer ownership to anyone. You either must pass
`IFiles.files_owner_allows` check for `file_transfer` operation, or pass a
cascade access check for the future owner of the file when cascade access and
transfer-as-update is enabled.

For example, if you have the following options in config file:

```ini
ckanext.files.owner.cascade_access = organization
ckanext.files.owner.transfer_as_update = true
```
you must pass `organization_update` auth function if you want to transfer file
ownership to organization.

In addition, file can be *pinned*. In this way we mark important files. Imagine
the resource and its uploaded file. The link to this file is used by resource
and we don't want this file to be accidentally transfered to someone else. We
pin the file and now nobody can transfer the file without explicit confirmation
of his intention.

There are two ways to move pinned file:

* you can call `files_file_unpin` first and then transfer the ownership via
  separate API call
* you can pass `force` parameter to `files_transfer_ownership`
