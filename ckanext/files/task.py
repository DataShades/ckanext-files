"""Task queue logic.

It's a high-level module that relies on base and utils.

"""

from __future__ import annotations

import contextvars
import abc
import dataclasses
import functools
from typing import Any, Literal
from ckan.types import FlattenKey

from ckanext.files import exceptions, base, utils
import ckan.plugins.toolkit as tk

_task_queue: contextvars.ContextVar[list[Task] | None] = contextvars.ContextVar(
    "transfer_queue",
    default=None,
)


class TaskQueue:
    queue: list[Any]
    token: contextvars.Token[Any] | None

    def __len__(self):
        return len(self.queue)

    def __init__(self):
        self.queue = []
        self.token = None

    def __enter__(self):
        self.token = _task_queue.set(self.queue)
        return self.queue

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        if self.token:
            _task_queue.reset(self.token)

    @classmethod
    def add_task(cls, task: Task):
        queue = _task_queue.get()
        if queue is None:
            raise exceptions.OutOfQueueError
        queue.append(task)

    def process(self, result: dict[str, Any]):
        while self.queue:
            task = self.queue.pop(0)
            task.run(result)


class Task(abc.ABC):
    @staticmethod
    def extract(source: dict[str, Any], path: FlattenKey):
        for step in path:
            source = source[step]

        return source

    @abc.abstractmethod
    def run(self, result: dict[str, Any]):
        ...


@dataclasses.dataclass
class OwnershipTransferTask(Task):
    file_id: str
    owner_type: str
    id_path: FlattenKey

    def run(self, result: dict[str, Any]):
        tk.get_action("files_transfer_ownership")(
            {"ignore_auth": True},
            {
                "id": self.file_id,
                "owner_type": self.owner_type,
                "owner_id": self.extract(result, self.id_path),
                "force": True,
                "pin": True,
            },
        )


@dataclasses.dataclass
class UploadAndAttachTask(Task):
    storage: str
    upload: utils.Upload
    owner_type: str
    id_path: FlattenKey

    attach_as: Literal["id", "public_url"] | None
    action: str | None = None
    destination_field: str | None = None

    def run(self, result: dict[str, Any]):
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
                "force": True,
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


def action_with_task_queue(action: Any, name: str | None = None):
    @functools.wraps(action)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        queue = TaskQueue()
        with queue:
            result = action(*args, *kwargs)
            queue.process(result)

        return result

    if name:
        wrapper.__name__ = name
    return wrapper
