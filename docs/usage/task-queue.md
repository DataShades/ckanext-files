# Task queue

/// admonition | Warning
    type: warning

This feature is experimental and may change in future. Keep track of changelog
if you are using tasks or validators that schedule tasks, like
`files_transfer_ownership`.

///

One of the challenges introduced by independently managed files is related to
file ownership. As long as you can call `files_transfer_ownership` manually,
things are transparent. But as soon as you add custom file field to dataset,
you probably want to automatically transfer ownership of the file refered by
this custom field.

Imagine, that you have PDF file owned by you. One day you specify ID of this
file in the `attachment_id` field of the dataset and now download link for this
file is shown on the dataset page. But if file owned by you, nobody else can
download the the file. So you decide to transfer file ownership to dataset,
allowing anyone who sees dataset, see the file as well.

You prefer to avoid two independent API calls: update dataset and transfer
ownership after it, because there will be a time window between these two
actions, when data is not valid. Or even worse, after updating dataset you'll
lose internet connection and won't be able to finish the transfer.

Neither you can transfer ownership first and then update the
dataset. `attachment_id` may have additional validators and you don't know in
advance, whether you'll be able to successfully update dataset after the
transfer.

This problem can be solved via queuing additional *tasks* inside the
action. For example, validator that checks whether certain file ID can be used
as an `attachment_id`, also can schedule the ownership transfer. If dataset
update completed without errors, queued task is executed automatically and
dataset becomes the owner of the file.

Task is queued via `ckanext.files.shared.add_task` function, which accepts
callables that represent the task. Task callable has signature `(result: Any,
idx: int, prev: Any) -> Any`. It receives the result of action which
caused task execution, task's position in queue and the result of previous
task.

/// admonition | Example
    type: example

One of `attachment_id` validators can queue the following tak via
`add_task(transfer_attachment_to_dataset_task)` if `attachment_id` field of the
dataset contains the ID of the file that requires transfer after successful
dataset modification:

```python
def transfer_attachment_to_dataset_task(dataset: dict[str, Any], idx: int, prev: Any) -> Any:
    return tk.get_action("files_transfer_ownership")(
        {"ignore_auth": True},
        {
            "id": dataset["attachment_id"],
            "owner_type": "package",
            "owner_id": dataset["id"],
            "pin": True,
        },
    )
```

///

As the first argument, the task receives the result of action which was
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
of the ID field. As in most cases it's `id`, you can omit it and rely on the
default value:

* organization: `files_transfer_ownership("organization")`
* dataset: `files_transfer_ownership("package")`
* user: `files_transfer_ownership("user")`


/// admonition | Alternative
    type: tip

Instead of using tasks, you can use [CKAN
Signals](https://docs.ckan.org/en/2.11/extensions/signals.html). Create a
listener for the
[`action_succeeded`](https://docs.ckan.org/en/2.11/extensions/signals.html#ckan.lib.signals.action_succeeded)
signal and transfer ownership inside the listener.

This approach resembles logic of [the activity
extension](https://github.com/ckan/ckan/blob/ckan-2.11.2/ckanext/activity/subscriptions.py#L24-L26)
that creates activity records after API action finishes its execution.

///
