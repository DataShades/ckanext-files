# Capabilities

To understand in advance whether specific storage can perform certain actions,
ckanext-files uses `ckanext.files.shared.Capability`. It's an enumeration of
operations that can be supported by storage:

| Capability     | Action performed by storage                                            |
|----------------|------------------------------------------------------------------------|
| CREATE         | create a file as an atomic object                                      |
| STREAM         | return file content as stream of bytes                                 |
| COPY           | make a copy of the file inside the same storage                        |
| REMOVE         | remove file from the storage                                           |
| MULTIPART      | create file in 3 stages: start, upload(repeatable), complete           |
| MOVE           | move file to a different location inside the same storage              |
| EXISTS         | check if file exists                                                   |
| SCAN           | iterate over all files in the storage                                  |
| APPEND         | add content to the existing file                                       |
| COMPOSE        | combine multiple files into a new one in the same storage              |
| RANGE          | return specific range of bytes from the file                           |
| ANALYZE        | return file details from the storage, as if file was uploaded just now |
| LINK_PERMANENT | make permanent download link                                           |
| LINK_TEMPORAL  | make expiring download link                                            |
| LINK_ONE_TIME  | make one-time download link                                            |

These capabilities are defined when storage is created and are automatically
checked by actions that work with storage. For manual checks use
`Storage.supports` method with the specific capability. If you want to check
presence of multiple capabilities at once, you can combine them via bitwise-or
operator.

```python
from ckanext.files.shared import Capability, get_storage

storage = get_storage()

can_read = storage.supports(Capability.STREAM)

read_and_write = Capability.CREATE | Capability.STREAM
can_read_and_write = storage.supports(read_and_write)

```

`ckan files storages -v` CLI command lists all configured storages with their
capabilities.
