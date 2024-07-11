"""Task queue logic.

Create a context for scheduling tasks upon exiting the context.

Initially was designed for `with_task_queue` decorator. It creates task queue
upon entering the API action and keeps track of ownership transfer tasks
produced by validators. If all validators succesfully passed and decorated
action finished, tasks are executed, moving file ownership to the
created/updated entity.

It's a high-level module that relies on base and utils.

"""

from __future__ import annotations

import abc
import contextvars
import dataclasses
import functools
from collections import deque
from typing import Any, Literal

import ckan.plugins.toolkit as tk
from ckan.types import FlattenKey

from ckanext.files import base, exceptions, types, utils

_task_queue: contextvars.ContextVar[deque[types.PTask] | None] = contextvars.ContextVar(
    "transfer_queue",
    default=None,
)


class TaskQueue:
    """Thread-safe context for managing tasks.

    Example:
        ```python
        queue = TaskQueue()
        with queue:
            function_that_adds_tasks_to_queue()
        data_passed_into_tasks = ...
        queue.process(data_passed_into_tasks)
        ```
    """

    # container for tasks
    queue: deque[types.PTask]

    # refresh token that restores previous state of queue
    token: contextvars.Token[Any] | None

    def __len__(self):
        return len(self.queue)

    def __init__(self):
        self.queue = deque()
        self.token = None

    def __enter__(self):
        # save token to restore previous queue. Required for nested queues
        self.token = _task_queue.set(self.queue)
        return self.queue

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        # restore previous queue state. Required for nested queues
        if self.token:
            _task_queue.reset(self.token)

    def process(self, data: dict[str, Any]):
        """Execute queued tasks in FIFO order.

        `data` is passed to every task as a first argument. In addition, task
        receives its position in execution queue and results of the previous
        task. The first task receives Task.NO_PREVIOUS_TASK as third argument,
        because there are no results from previous task yet.
        """
        prev = Task.NO_PREVIOUS_TASK
        idx = 0
        while self.queue:
            task = self.queue.popleft()
            prev = task(data, idx, prev)
            idx += 1


class Task(abc.ABC):
    """Base task for TaskQueue.

    The only requirement for subclasses is implementing Task.run.
    """

    NO_PREVIOUS_TASK = object()

    @staticmethod
    def extract(source: dict[str, Any], path: FlattenKey):
        """Extract value from dictionary using FlattenKey from validators.

        Args:
            source: dictionary with data
            path: path to the extracted member from source

        Example:
            ```python
            data = {"a": {"b": {"c": 42}}}
            assert Task.extract(data, ("a", "b", "c")) == 42
            ```
        """
        for step in path:
            source = source[step]

        return source

    def __call__(self, result: Any, idx: int, prev: Any):
        return self.run(result, idx, prev)

    @abc.abstractmethod
    def run(self, result: Any, idx: int, prev: Any):
        """Execute task.

        `result` is an arbitrary data passed into every task in the
        queue. `idx` reflects current task's position in queue. `prev` contains
        result of previous task or Task.NO_PREVIOUS_TASK if current task is the
        first in the queue.
        """
        ...


@dataclasses.dataclass
class OwnershipTransferTask(Task):
    """Taks for transfering ownership to not-yet-existing entity.

    Designed for scheduling from validators:

    Example:
        ```python
        def validator(key, data, errors, context):
            file_id = data[key]
            owner_id_path = key[:-1] + ("id",)
            task = OwnershipTransferTask(file_id, "resource", owner_id_path)
            add_task(task)
        ```

    This task requires the ID of the file to trasfer, type of the future owner
    and flattened path to ID field of the owner.

    Example:
        ```python
        task = OwnershipTransferTask('xxx', 'resource', ("resources", 0, "id"))
        dataset = {"name": "test", "resources": [{"id": "123"}]}
        task.run(dataset, 0, Task.NO_PREVIOUS_TASK)
        ```
    """

    # ID of the transfered file
    file_id: str
    # type of the future owner
    owner_type: str
    # flattened path to ID of future owner in execution data
    id_path: FlattenKey

    def run(self, result: dict[str, Any], idx: int, prev: Any):
        """Transfer file ownership.

        Ownerhip transfered to an entity whose ID is stored in `result` under
        `self.id_path` path.
        """
        return tk.get_action("files_transfer_ownership")(
            {"ignore_auth": True},
            {
                "id": self.file_id,
                "owner_type": self.owner_type,
                "owner_id": self.extract(result, self.id_path),
                # "force": True,
                "pin": True,
            },
        )


@dataclasses.dataclass
class UploadAndAttachTask(Task):
    """Taks for creating file and transfering it to specified owner.

    Optionally, task can update owner using specified API action.

    Designed for scheduling from validators:
    >>> def validator(key, data, errors, context):
    >>>     upload = data[key]
    >>>     owner_id_path = key[:-1] + ("id",)
    >>>     task = UploadAndAttachTask("default, upload, "resource", owner_id_path)
    >>>     add_task(task)

    This task requires the name of the storage for uploaded file, upload
    object, type of the future owner and flattened path to ID field of the
    owner.

    Optionally, it accepts action name for patching owner entity, name of the
    file's property that will be copied into owner entity and field of owner
    entity to copy file's property into it.

    Example:
    >>> task = UploadAndAttachTask(
    >>>     "default",
    >>>     make_upload(b"file.txt", "hello world),
    >>>     "resource",
    >>>     ("resources", 0, "id"),
    >>>     "id",
    >>>     "resource_patch",
    >>>     "attachment_id",
    >>> )
    >>> dataset = {"name": "test", "resources": [{"id": "123", "attachment_id": None}]}
    >>> task.run(dataset, 0, Task.NO_PREVIOUS_TASK)

    """

    # storage for file upload
    storage: str
    # upload object with file's content
    upload: utils.Upload
    # type of future owner
    owner_type: str
    # flattened path to owner's ID field
    id_path: FlattenKey

    # property of the file that will be added to owner data. Currently
    # supported only id and public_url.
    attach_as: Literal["id", "public_url"] | None
    # action to use for patching owner's data
    action: str | None = None
    # field in owner's data that will hold property of the current file
    destination_field: str | None = None

    def run(self, result: dict[str, Any], idx: int, prev: Any):
        """Upload file, transfer ownership and, optionally, patch the owner."""
        info = tk.get_action("files_file_create")(
            {"ignore_auth": True},
            {"upload": self.upload, "storage": self.storage},
        )

        info = tk.get_action("files_transfer_ownership")(
            {"ignore_auth": True},
            {
                "id": info["id"],
                "owner_type": self.owner_type,
                "owner_id": self.extract(result, self.id_path),
                # "force": True,
                "pin": True,
            },
        )

        if self.attach_as and self.action and self.destination_field:
            if self.attach_as:
                storage = base.get_storage(self.storage)
                value = storage.public_link(base.FileData.from_dict(info))
            else:
                value = info["id"]

            user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
            tk.get_action(self.action)(
                {"ignore_auth": True, "user": user["name"]},
                {"id": info["owner_id"], self.destination_field: value},
            )

        return info


def with_task_queue(func: Any, name: str | None = None):
    """Decorator for functions that schedule tasks.

    Decorated function automatically initializes separate task queue which is
    processed when function is finished. All tasks receive function's result as
    execution data(first argument of `Task.run`).

    Without this decorator, you have to manually create task queue context
    before queuing tasks.

    Example:
        ```python
        @with_task_queue
        def my_action(context, data_dict):
            ...
        ```
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        queue = TaskQueue()
        with queue:
            result = func(*args, *kwargs)
            queue.process(result)

        return result

    if name:
        wrapper.__name__ = name
    return wrapper


def add_task(task: types.PTask):
    """Add task to the current task queue.

    This function can be called only inside task queue context. Such context
    initialized automatically inside functions decorated with
    `with_task_queue`:

    Example:
        ```python
        @with_task_queue
        def taks_producer():
            add_task(...)

        task_producer()
        ```

    Task queue context can be initialized manually using TaskQueue and
    `with` statement:

    Example:
        ```python
        queue = TaskQueue()
        with queue:
            add_task(...)

        queue.process(execution_data)
        ```
    """
    queue = _task_queue.get()
    if queue is None:
        raise exceptions.OutOfQueueError
    queue.append(task)
