# User avatars

!!! info

    This workflow is similar to group/organization migration. It contains the
    sequence of actions, but explanations are removed, because you already know
    details from the group migration. Only steps that are different will contain
    detailed explanation of the process.


Configure local filesystem storage with support of public
links(`files:public_fs`) for user images.

??? info "Storage name"

    This extension expects that the name of user images storage will be
    `user_images`. This name will be used in all other commands of this migration
    workflow. If you want to use different name for user images storage, override
    `ckanext.files.user_images_storage` config option which has default value
    `user_images` and don't forget to adapt commands if you use a different name
    for the storage.

??? info "Location"

    `ckanext.files.storage.user_images.path` resembles this option for
    group/organization images storage. But user images are kept inside `user`
    folder by default. As result, value of this option should match value of
    `ckan.storage_path` option plus `storage/uploads/user`. In example below we
    assume that value of `ckan.storage_path` is `/var/storage/ckan`.

??? info "Public URL"

    `ckanext.files.storage.user_images.public_root` resebles this option for
    group/organization images storage. But user images are available at CKAN URL
    plus `uploads/user`.

```ini
ckanext.files.storage.user_images.type = files:public_fs
ckanext.files.storage.user_images.max_size = 10MiB
ckanext.files.storage.user_images.supported_types = image
ckanext.files.storage.user_images.path = /var/storage/ckan/storage/uploads/user
ckanext.files.storage.user_images.public_root = %(ckan.site_url)s/uploads/user
```

Check the list of untracked files available inside newly configured storage:

```sh
ckan files scan -s user_images -u
```

Track all these files:

```sh
ckan files scan -s user_images -t
```

Re-check that now you see no untracked files:

```ini
ckan files scan -s user_images -u
```

Transfer image ownership to corresponding users:

```sh
ckan files migrate users user_images
```

Update user template. Required field is defined in `user/new_user_form.html`
and `user/edit_user_form.html`. It's a bit different from the filed used by
group/organization, but you again need to add
`field_upload="files_image_upload"` parameter to the macro `image_upload` and
replace `h.uploads_enabled()` with `h.files_user_images_storage_is_configured()`.

User has no dedicated interface for validation schema modification and here
comes the biggest difference from group migration. You need to chain
`user_create` and `user_update` action and modify schema from `context`:


```python
def _patch_schema(schema):
    schema["files_image_upload"] = [
        tk.get_validator("ignore_empty"),
        tk.get_validator("files_into_upload"),
        tk.get_validator("files_validate_with_storage")("user_images"),
        tk.get_validator("files_upload_as")(
            "user_images",
            "user",
            "id",
            "public_url",
            "user_patch",
            "image_url",
        ),
    ]


@tk.chained_action
def user_update(next_action, context, data_dict):
    schema = context.setdefault('schema', ckan.logic.schema.default_update_user_schema())
    _patch_schema(schema)
    return next_action(context, data_dict)



@tk.chained_action
def user_create(next_action, context, data_dict):
    schema = context.setdefault('schema', ckan.logic.schema.default_user_schema())
    _patch_schema(schema)
    return next_action(context, data_dict)
```

Validators are all the same, but now we are using `user` instead of
`group`/`organization` in parameters.


That's all. Just as with groups, you can update an avatar and verify that all
new filenames resemble UUIDs.
