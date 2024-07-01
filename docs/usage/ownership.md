# File ownership

Every file *can* have an owner and there can be only one owner of the
file. It's possible to create file without an owner, but usually application
will only benefit from keeping every file with its owner. Owner is described
with two fields: ID and type.

When file is created, by default the current user from API action's context is
assigned as an owner of the file. From now on, the owner can perform other
operations, such as renaming/displaying/removing with the file.

Apart from chaining auth function, to modify access rules for the file, plugin
can implement `IFiles.files_file_allows` and `IFiles.files_owner_allows`
methods.

```python
def files_file_allows(
    self,
    context: Context,
    file: File | Multipart,
    operation: types.FileOperation,
) -> bool | None:
    ...

def files_owner_allows(
    self,
    context: Context,
    owner_type: str, owner_id: str,
    operation: types.OwnerOperation,
) -> bool | None:
    ...

```

These methods receive current action context, the tested object details, and
the name of operation(`show`, `update`, `delete`,
`file_transfer`). `files_file_allows` checks permission for accessed file. It's
usually called when user interacts with file directly. `files_owner_allows`
works with owner described by type and ID. It's usually called when user
transfer file ownership, perform bulk file operation for owner files, or just
trying to get the list of files that belongs to owner.

If method returns true/false, operation is allowed/denied. If method returns
`None`, default logic used to check access.

As already mentoined, by default, user who owns the file, can access it. But
what about different owners? What if file owned by other entity, like resource
or dataset?

Out of the box, nobody can access such files. But there are three config
options that modify this restriction.

`ckanext.files.owner.cascade_access = ENTITY_TYPE ANOTHER_TYPE` gives access to
file owned by entity if user already has access to entity itself. Use words
like `package`, `resource`, `group` instead of `ENTITY_TYPE`.

For example: file is owned by *resource*. If cascade access is enabled, whoever
has access to `resource_show` of the *resource*, can also see the file owned by
this resource. If user passes `resource_update` for *resource*, he can also
modify the file owned by this resource, etc.

!!! danger
    Be careful and do not add `user` to
    `ckanext.files.owner.cascade_access`. User's own files are considered
    private and most likely you don't really need anyone else to be able to see
    or modify these files.

The second option is `ckanext.files.owner.transfer_as_update`.  When
transfer-as-update enabled, any user who has `<OWNER_TYPE>_update` permission,
can transfer own files to this `OWNER_TYPE`. Intead of using this option, you
can define `<OWNER_TYPE>_file_transfer`.

And the third option is `ckanext.files.owner.scan_as_update`.  Just as with
ownership transfer, it gives user permission to list all files of the owner if
user can `<OWNER_TYPE>_update` it. Intead of using this option, you
can define `<OWNER_TYPE>_file_scan`.
