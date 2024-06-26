# Global configuration

```ini
# Default storage used for upload when no explicit storage specified
# (optional, default: default)
ckanext.files.default_storage = default

# MIMEtypes that can be served without content-disposition:attachment header.
# (optional, default: application/pdf image video)
ckanext.files.inline_content_types = application/pdf image video

# Storage used for user image uploads. When empty, user image uploads are not
# allowed.
# (optional, default: user_images)
ckanext.files.user_images_storage = user_images

# Storage used for group image uploads. When empty, group image uploads are
# not allowed.
# (optional, default: group_images)
ckanext.files.group_images_storage = group_images

# Storage used for resource uploads. When empty, resource uploads are not
# allowed.
# (optional, default: resources)
ckanext.files.resources_storage = resources

# Enable HTML templates and JS modules required for unsafe default
# implementation of resource uploads via files. IMPORTANT: this option exists
# to simplify migration and experiments with the extension. These templates
# may change a lot or even get removed in the public release of the
# extension.
# (optional, default: false)
ckanext.files.enable_resource_migration_template_patch = false

# Any authenticated user can upload files.
# (optional, default: false)
ckanext.files.authenticated_uploads.allow = false

# Names of storages that can by used by non-sysadmin users when authenticated
# uploads enabled
# (optional, default: default)
ckanext.files.authenticated_uploads.storages = default

# List of owner types that grant access on owned file to anyone who has
# access to the owner of file. For example, if this option has value
# `resource package`, anyone who passes `resource_show` auth, can see all
# files owned by resource; anyone who passes `package_show`, can see all
# files owned by package; anyone who passes
# `package_update`/`resource_update` can modify files owned by
# package/resource; anyone who passes `package_delete`/`resource_delete` can
# delete files owned by package/resoure. IMPORTANT: Do not add `user` to this
# list. Files may be temporarily owned by user during resource creation.
# Using cascade access rules with `user` exposes such temporal files to
# anyone who can read user's profile.
# (optional, default: package resource group organization)
ckanext.files.owner.cascade_access = package resource group organization

# Use `<OWNER_TYPE>_update` auth function to check access for ownership
# transfer. When this flag is disabled `<OWNER_TYPE>_file_transfer` auth
# function is used.
# (optional, default: true)
ckanext.files.owner.transfer_as_update = true

# Use `<OWNER_TYPE>_update` auth function to check access when listing all
# files of the owner. When this flag is disabled `<OWNER_TYPE>_file_scan`
# auth function is used.
# (optional, default: true)
ckanext.files.owner.scan_as_update = true
```
