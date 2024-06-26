# Validators


| Validator                                                    | Effect                                                                                                                                                               |
|--------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| files_into_upload                                            | Transform value of field(usually file uploaded via `<input type="file">`) into upload object using `ckanext.files.shared.make_upload`                                |
| files_parse_filesize                                         | Convert human-readable filesize(1B, 10MiB, 20GB) into an integer                                                                                                     |
| files_ensure_name(name_field)                                | If `name_field` is empty, copy into it filename from current field. Current field must be processed with `files_into_upload` first                                   |
| files_file_id_exists                                         | Verify that file ID exists                                                                                                                                           |
| files_accept_file_with_type(*type)                           | Verify that file ID refers to file with one of specified types. As a type can be used full MIMEtype(`image/png`), or just its main(`image`) or secondary(`png`) part |
| files_accept_file_with_storage(*storage_name)                | Verify that file ID refers to file stored inside one of specified storages                                                                                           |
| files_transfer_ownership(owner_type, name_of_owner_id_field) | Transfer ownership for file ID to specified entity when current API action is successfully finished                                                                  |
