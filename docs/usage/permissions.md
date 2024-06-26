# Permissions

File creation is not allowed by default. Only sysadmin can use
`files_file_create` and `files_multipart_start` actions. This is done
deliberately: uncontrolled uploads can turn your portal into user's personal
cloud-storage.

There are three ways to grant upload permission to normal users.

The BAD option is simple. Enable `ckanext.files.authenticated_uploads.allow`
config option and every registered user will be allowed to upload files. But
only into `default` storage. If you want to change the list of storages
available to common user, specify storage names as
`ckanext.files.authenticated_uploads.storages` option.

The GOOD option is relatively simple. Define chained auth function with name
`files_file_create`. It's called whenever user initiates an upload. Now you can
decide whether user is allowed to upload files with specified parameters.

The BEST option is to leave this restriction unchanged. Do not allow any user
to call `files_file_create`. Instead, create a new action for your
goal. ckanext-files isn't a solution - it's a tool that helps you in building
the solution.

If you need to add *documents* field to dataset that contains uploaded PDF
files, create a separate action `dataset_document_attach`. Specify access rules
and validation for it. Or even hardcode the storage that will be used for
uploads. And then, from this new action, call `files_file_create` with
`ignore_auth: True`.

In this way you control every side of uploading documents into dataset and do
not accidentally break other functionality, because every other feature will
define its own action.
