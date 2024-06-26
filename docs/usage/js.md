# JavaScript utilities

Note: ckanext-files does not provide stable CKAN JS modules at the moment. Try
creating your own widgets and share with us your examples or
requirements. We'll consider creating and including widgets into ckanext-files
if they are generic enough for majority of the users.

ckanext-files registers few utilities inside CKAN JS namespace to help with
building UI components.

First group of utilities registered inside CKAN Sandbox. Inside CKAN JS modules
it's accessible as `this.sandbox`. If you are writing code outside of JS
modules, Sandbox can be initialized via call to `ckan.sandbox()`

```js
const sandbox = ckan.sandbox()
```

When `files` plugin loaded, sandbox contains `files` attribute with two
members:

* `upload`: high-level helper for uploding files.
* `makeUploader`: factory for uploader-objects that gives more control over
  upload process.

The simplest way to upload the file is using `upload` helper.

```js
await sandbox.files.upload(
    new File(["file content"], "name.txt", {type: "text/plain"}),
)
```

This function uploads file to `default` storage via `files_file_create`
action. Extra parameters for API call can be passed using second argument of
`upload` helper. Use an object with `requestParams` key. Value of this key will
be added to standard API request parameters. For example, if you want to use
`storage` with name `memory` and `field` with value `custom`:

```js
await sandbox.files.upload(
    new File(["file content"], "name.txt", {type: "text/plain"}),
    {requestParams: {storage: "memory", field: "custom"}}
)
```

If you need more control over upload, you can create an **uploader** and
interact with it directly, instead of using `upload` helper.

*Uploader* is an object that uploads file to server. It extends base uploader,
which defines standard interface for this object. Uploader perfroms all the API
calls internally and returns uploaded file details. Out of the box you can use
`Standard` and `Multipart` uploaders. `Standard` uses `files_file_create` API
action and specializes on normal uploads. `Multipart` relies on
`files_multipart_*` actions and can be used to pause and continue upload.

To create uploader instance, pass its name as a string to `makeUploader`. And
then you can call `upload` method of the uploader to perform the actual
upload. This method requires two arguments:

* the file object
* object with additional parameters of API request, the same as `requestParams`
  from example above. If you want to use default parameters, pass an empty
  object. If you want to use `memory` storage, pass `{storage: "memory"}`, etc.

```js
const uploader = sandbox.files.makeUploader("Standard")
await uploader.upload(new File(["file content"], "name.txt", {type: "text/plain"}), {})
```

One of the reasons to use manually created uploader is progress
tracking. Uploader supports event subscriptions via
`uploader.addEventListener(event, callback)` and here's the list of possible
upload events:

* `start`: file upload started. Event has `detail` property with object that
  contains uploaded file as `file`.
* `multipartid`: multipart upload initialized. Event has `detail` property with
  object that contains uploaded file as `file` and ID of multipart upload as
  `id`.
* `progress`: another chunk of file was transferred to server. Event has
  `detail` property with object that contains uploaded file as `file`, number
  of loaded bytes as `loaded` and total number of bytes that must be
  transferred as `total`.
* `finish`: file upload successfully finished. Event has `detail` property with
  object that contains uploaded file as `file` and file details from API
  response as `result`.
* `fail`: file upload failed. Event has `detail` property with object that
  contains uploaded file as `file` and object with CKAN validation errors as
  `reasons`.
* `error`: error unrelated to validation happened during upload, like call to
  non-existing action. Event has `detail` property with object that contains
  uploaded file as `file` and error as `message`.


If you want to use `upload` helper with customized uploader, there are two ways
to do it.

* pass `adapter` property with uploader name inside second argument of `upload`
  helper:
  ```js
  await sandbox.files.upload(new File(...), {adapter: "Multipart"})
  ```
* pass `uploader` property with uploader instance inside second argument of `upload`
  helper:
  ```js
  const uploader = sandbox.files.makeUploader("Multipart")
  await sandbox.files.upload(new File(...), {uploader})
  ```

The second group of ckanext-files utilities is available as
`ckan.CKANEXT_FILES` object. This object mainly serves as extension and
configuration point for `sandbox.files`.

`ckan.CKANEXT_FILES.adapters` is a collection of all classes that can be used
to initialize uploader. It contains `Standard`, `Multipart` and `Base`
classes. `Standard` and `Multipart` can be used as is, while `Base` must be
extended by your custom uploader class. Add your custom uploader classes to
`adapters`, to make them available application-wide:

```js

class MyUploader extends Base { ... }

ckan.CKANEXT_FILES.adapters["My"] = MyUploader;

await sandbox.files.upload(new File(...), {adapter: "My"})
```

`ckan.CKANEXT_FILES.defaultSettings` contain the object with default settings
available as `this.settings` inside any uploader. You can change the name of
the storage used by all uploaders using this object. Note, changes will apply
only to uploaders initialized after modification.

```js
ckan.CKANEXT_FILES.defaultSettings.storage = "memory"
```
