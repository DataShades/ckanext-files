# Task queue

One of the challenges introduced by independently managed files is related to
file ownership. As long as you can call `files_transfer_ownership` manually,
things are transparent. But as soon as you add custom file field to dataset,
you probably want to automatically transfer ownership of the file refered by
this custom field.

Imagine, that you have PDF file owned by you. And you specify ID of this file
in the `attachment_id` field of the dataset. You want to show download link for
this file on the dataset page. But if file owned by you, nobody will be able to
download the file. So you decide to transfer file ownership to dataset, so that
anyone who sees dataset, can see the file as well.

You cannot update dataset and transfer ownership after it, because there will
be a time window between these two actions, when data is not valid. Or even
worse, after updating dataset you'll lose internet connection and won't be able
to finish the transfer.

Neither you can transfer ownership first and then update the
dataset. `attachment_id` may have additional validators and you don't know in
advance, whether you'll be able to successfully update dataset after the
transfer.

This problem can be solved via queuing additional *tasks* inside the
action. For example, validator that checks if certain file ID can be used as
`attachment_id` can queue ownership transfer. If dataset update completed
without errors, queued task is executed automatically and dataset becomes the
owner of the file.

Task is queued via `ckanext.files.shared.add_task` function, which accepts
objects inherited from `ckanext.files.shared.Task`. `Task` class requires
implementing abstract method `run(result: Any, idx: int, prev: Any)`, which is
called when task is executed. This method receives the result of action which
caused task execution, task's position in queue and the result of previous
task.

!!! example

    One of `attachment_id` validators can queue the following `MyTask`
    via `add_task(MyTask(file_id))` to transfer `file_id` ownership to the
    updated dataset:

    ```python
    from ckanext.files.shared import Task

    class MyTask(Task):
        def __init__(self, file_id):
            self.file_id = file_id

        def run(self, dataset, idx, prev):
            return tk.get_action("files_transfer_ownership")(
                {"ignore_auth": True},
                {
                    "id": self.file_id,
                    "owner_type": "package",
                    "owner_id": dataset["id"],
                    "pin": True,
                },
            )
    ```

As the first argument, `Task.run` receives the result of action which was
called. Right now only following actions support tasks:

* `package_create`
* `packaage_update`
* `resource_create`
* `resource_update`
* `group_create`
* `group_update`
* `organization_create`
* `organization_update`
* `user_create`
* `user_update`

If you want to enable tasks support for your custom action, decorate it with
`ckanext.files.shared.with_task_queue` decorator:

```python
from ckanext.files.shared import with_task_queue

@with_task_queue
def my_action(context, data_dict)
    # you can call `add_task` inside this action's stack frame.
    ...
```

Good example of validator using tasks is `files_transfer_ownership` validator
factory. It can be added to metadata schema as
`files_transfer_ownership(owner_type, name_of_id_field)`. For example, if you
are adding this validator to resource, call it as
`files_transfer_ownership("resource", "id")`. The second argument is the name
of the ID field. As in most cases it's `id`, you can omit the second argument:

* organization: `files_transfer_ownership("organization")`
* dataset: `files_transfer_ownership("package")`
* user: `files_transfer_ownership("user")`
