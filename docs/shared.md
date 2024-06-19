## `get_storage(name: 'str | None' = None) -> 'Storage'`

Return existing storage instance.

Storages are initialized when plugin is loaded. As result, this function
always returns the same storage object for the given name.

If no name specified, default storage is returned.

Example:
```python
default_storage = get_storage()
storage = get_storage("storage name")
```


## `make_storage(name: 'str', settings: 'dict[str, Any]') -> 'Storage'`

Initialize storage instance with specified settings.

Storage adapter is defined by `type` key of the settings. All other
settings depend on the specific adapter.

Example:
```python
storage = make_storage("memo", {"type": "files:redis"})
```


## `make_upload(value: 'FileStorage | Upload | tempfile.SpooledTemporaryFile[Any] | TextIOWrapper | bytes | bytearray | BinaryIO') -> 'Upload'`

Convert value into Upload object

Use this function for simple and reliable initialization of Upload
object. Avoid creating Upload manually, unless you are 100% sure you can
provide correct MIMEtype, size and stream.

Example:
```python
storage.upload("file.txt", make_upload(b"hello world"))
```


## `with_task_queue(func: 'Any', name: 'str | None' = None)`

Decorator for functions that schedule tasks.

Decorated function automatically initializes separate task queue that is
processed when function is finished. All tasks receive function's result as
execution data(first argument to Task.run).

Without this decorator, you have to manually create task queue context
before queuing tasks.

Example:
```python
@with_task_queue
def my_action(context, data_dict):
    ...
```


## `add_task(task: 'Task')`

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

If task queue context can be initialized manually using TaskQueue and
`with` statement:
```python
queue = TaskQueue()
with queue:
    add_task(...)

queue.process(execution_data)
```
