All public utilites are collected inside     `ckanext.files.shared` module. Avoid using anything that     is not listed there. Do not import anything from modules other than     `shared`.
## get_storage

Signature: `(name: str | None = None) -> Storage`

Return existing storage instance.

Storages are initialized when plugin is loaded. As result, this function
always returns the same storage object for the given name.

If no name specified, default storage is returned.

!!! example
	```python
	default_storage = get_storage()
	storage = get_storage("storage name")
	```


## make_storage

Signature: `(name: str, settings: dict[str, Any]) -> Storage`

Initialize storage instance with specified settings.

Storage adapter is defined by `type` key of the settings. All other
settings depend on the specific adapter.

!!! example
	```python
	storage = make_storage("memo", {"type": "files:redis"})
	```


## make_upload

Signature: `(value: types.Uploadable | Upload) -> Upload`

Convert value into Upload object

Use this function for simple and reliable initialization of Upload
object. Avoid creating Upload manually, unless you are 100% sure you can
provide correct MIMEtype, size and stream.

!!! example
	```python
	storage.upload("file.txt", make_upload(b"hello world"))
	```


## Upload

Signature: `(stream: types.PUploadStream, filename: str, size: int, content_type: str) -> None`

Standard upload details.

!!! example
	```python
	Upload(
	    BytesIO(b"hello world"),
	    "file.txt",
	    11,
	    "text/plain",
	)
	```


## HashingReader

Signature: `(stream: types.PUploadStream, chunk_size: int = 16384, algorithm: str = md5) -> None`

IO stream wrapper that computes content hash while stream is consumed.

!!! example

	```python
	reader = HashingReader(readable_stream)
	for chunk in reader:
	    ...
	print(f"Hash: {reader.get_hash()}")
	```


## Capability

Enumeration of operations supported by the storage.

!!! example
	```python
	read_and_write = Capability.STREAM | Capability.CREATE
	if storage.supports(read_and_write)
	    ...
	```


## File

Signature: `(**kwargs)`

Model with file details.

!!! example
	```python
	file = File(
	    name="file.txt",
	    location="relative/path/safe-name.txt",
	    content_type="text/plain",
	    size=100,
	    hash="abc123",
	    storage="default",
	)
	```


## Multipart

Signature: `(**kwargs)`

Model with details of incomplete upload.

!!! example
	```python
	upload = Multipart(
	    name="file.txt",
	    location="relative/path/safe-name.txt",
	    content_type="text/plain",
	    size=100,
	    hash="abc123",
	    storage="default",
	)
	```


## Owner

Signature: `(**kwargs)`

Model with details about current owner of an item.

!!! example
	```python
	owner = Owner(
	    item_id=file.id,
	    item_type="file",
	    owner_id=user.id,
	    owner_type="user,
	)
	```


## TransferHistory

Signature: `(**kwargs)`

Model for tracking ownership history of the file.

!!! example
	```python
	record = TransferHistory(
	    item_id=file.id,
	    item_type="file",
	    owner_id=prev_owner.owner_id,
	    owner_type=prev_owner.owner_type,
	)
	```


## FileData

Signature: `(location: str, size: int = 0, content_type: str = application/octet-stream, hash: str = "", storage_data: dict[str, Any] = <factory>) -> None`

Information required by storage to operate the file.

!!! example
	```python
	FileData(
	    "local/path.txt",
	    123,
	    "text/plain",
	    md5_of_content,
	)
	```


## MultipartData

Signature: `(location: str = "", size: int = 0, content_type: str = "", hash: str = "", storage_data: dict[str, Any] = <factory>) -> None`

Information required by storage to operate the incomplete upload.

!!! example
	```python
	FileData(
	    "local/path.txt",
	    expected_size,
	    expected_content_type,
	    expected_hash,
	)
	```


## IFiles

Extension point for ckanext-files.

This interface is not stabilized. Implement it with `inherit=True`.

!!! example
	```python
	class MyPlugin(p.SingletonPlugin):
	    p.implements(interfaces.IFiles, inherit=True)
	```


## Storage

Signature: `(**settings: Any)`

Base class for storage implementation.

!!! example
	```python
	class MyStorage(Storage):
	    def make_uploader(self):
	        return MyUploader(self)

	    def make_reader(self):
	        return MyReader(self)

	    def make_manager(self):
	        return MyManager(self)
	```


## Uploader

Signature: `(storage: Storage)`

Service responsible for writing data into a storage.

!!! example
	```python
	class MyUploader(Uploader):
	    def upload(
	        self, location: str, upload: Upload, extras: dict[str, Any]
	    ) -> FileData:
	        reader = upload.hashing_reader()

	        with open(location, "wb") as dest:
	            dest.write(reader.read())

	        return FileData(
	            location, upload.size,
	            upload.content_type,
	            reader.get_hash()
	        )
	```


## Reader

Signature: `(storage: Storage)`

Service responsible for reading data from the storage.

!!! example
	```python
	class MyReader(Reader):
	    def stream(
	        self, data: FileData, extras: dict[str, Any]
	    ) -> Iterable[bytes]:
	        return open(data.location, "rb")
	```


## Manager

Signature: `(storage: Storage)`

Service responsible for maintenance file operations.

!!! example
	```python
	class MyManager(Manager):
	    def remove(
	        self, data: FileData|MultipartData, extras: dict[str, Any]
	    ) -> bool:
	        os.remove(data.location)
	        return True
	```


## add_task

Signature: `(task: types.PTask)`

Add task to the current task queue.

This function can be called only inside task queue context. Such context
initialized automatically inside functions decorated with
`with_task_queue`:
```python
@with_task_queue
def taks_producer():
    add_task(...)

task_producer()
```

Task queue context can be initialized manually using TaskQueue and
`with` statement:
```python
queue = TaskQueue()
with queue:
    add_task(...)

queue.process(execution_data)
```


## with_task_queue

Signature: `(func: Any, name: str | None = None)`

Decorator for functions that schedule tasks.

Decorated function automatically initializes separate task queue which is
processed when function is finished. All tasks receive function's result as
execution data(first argument of `Task.run`).

Without this decorator, you have to manually create task queue context
before queuing tasks.

!!! example
	```python
	@with_task_queue
	def my_action(context, data_dict):
	    ...
	```


## Task

Base task for TaskQueue.

The only requirement for subclasses is implementing Task.run.


## TaskQueue

Thread-safe context for managing tasks.

!!! example
	```python
	queue = TaskQueue()
	with queue:
	    function_that_adds_tasks_to_queue()
	data_passed_into_tasks = ...
	queue.process(data_passed_into_tasks)
	```


## types (ckanext.files.types module)

Types for the extension.


## config (ckanext.files.config module)

Configuration readers of the extension.

This module contains functions that simplify accessing configuration option
from the CKAN config file.

It's recommended to use these functions istead of accessing config options by
name, if you want your code to be more compatible with different versions of
the extension.


## exc (ckanext.files.exceptions module)

Exception definitions for the extension.

Hierarchy:

* Exception
    * FilesError
        * QueueError
            * OutOfQueueError
        * StorageError
            * UnknownAdapterError
            * UnknownStorageError
            * UnsupportedOperationError
            * PermissionError
            * MissingFileError
            * ExistingFileError
            * ExtrasError
                * MissingExtrasError
            * InvalidStorageConfigurationError
                * MissingStorageConfigurationError
            * UploadError
                * WrongUploadTypeError
                * NameStrategyError
                * LargeUploadError
                    * UploadOutOfBoundError
                * UploadMismatchError
                    * UploadTypeMismatchError
                    * UploadHashMismatchError
                    * UploadSizeMismatchError
