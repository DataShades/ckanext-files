# File upload strategies

There is no "right" way to add file to entity via ckanext-files. Everything
depends on your use-case and here you can find a few different ways to combine
file and arbitrary entity.

## Attach existing file and then transfer ownership via API

The simplest option is just saving file ID inside a field of the entity. It's
recommended to transfer file ownership to the entity and pin the file.

```sh
ckanapi action package_patch id=PACKAGE_ID attachment_id=FILE_ID

ckanapi action files_transfer_ownership id=FILE_ID \
    owner_type=package owner_id=PACKAGE_ID pin=true
```

Pros:

* simple and transparent

Cons:

* it's easy to forget about ownership transfer and leave the entity with the
  inaccessible file
* after entity got reference to file and before ownership is transfered data
  may be considered invalid.

## Automatically transfer ownership using validator

Add `files_transfer_ownership(owner_type)` to the validation schema of entity
and put the ID of the file into it. When it validated, ownership transfer task
is queued and file automatically transfered to the entity after the update.

Pros:

* minimal amount of changes if metadata schema already modified
* relationships between owner and file are up-to-date after any modification

Cons:

* works only with files uploaded in advance and cannot handle native
  implementation of resource form

## Upload file and assign owner via queued task

Add a field that accepts uploaded file. The action itself does not process the
upload. Instead create a validator for the upload field, that will schedule a
task for file upload and ownership transfer.

In this way, if action is failed, no upload happens and you don't need to do
anything with the file, as it never left server's temporal directory. If action
finished without an error, the task is executed and file uploaded/attached to
action result.

Basically, it's an extension of the previous option, that allows you to use
`input[type=file]` for upload instead of `input[type=text]` for existing file
ID.

Pros:

* can be used together with native group/user/resource form after small
  modification of CKAN core.
* handles upload inside other action as an atomic operation

Cons:

* you have to validate file before upload happens to prevent situation when
  action finished successfully but then upload failed because of file's content
  type or size.
* tasks themselves are experimental and it's not recommended to put a lot of
  logic into them
* there are just too many things that can go wrong

## Add a new action that combines uploads, modifications and ownership transfer

If you want to add attachment to dataset, create a separate action that accepts
dataset ID and uploaded file. Internally it will upload the file by calling
`files_file_create`, then update dataset via `packaage_patch` and finally
transfer ownership via `files_transfer_ownership`.

Even better, you can just create a file and transfer ownership to dataset. No
need to put file's ID into dataset field, as they are already connected via
ownership entity. As long as you don't need to expose file details inside
dataset's API representation, you can use `files_file_scan` or
`files_file_search` to list all the dataset's files.

Pros:

* no magic. Everything is described in the new action
* can be extracted into shared extension and used across multiple portals

Cons:

* if you need to upload multiple files and update multipe fields, action
  quickly becomes too compicated.
* integration with existing workflows, like dataset/resource creation is
  hard. You have to override existing views or create a brand new ones.
