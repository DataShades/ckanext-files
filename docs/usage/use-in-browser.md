# Usage in browser

You can upload files using JavaScript CKAN modules. ckanext-files extends
CKAN's Sandbox object(available as `this.sandbox` inside the JS CKAN module),
so we can use shortcut and upload file directly from the DevTools. Open any
CKAN page, switch to JS console and create the sandbox instance. Inside it we
have `files` object, which in turn contains `upload` method. This method
accepts `File` object for upload(the same object you can get from the
`input[type=file]`).

```js
sandbox = ckan.sandbox()
await sandbox.files.upload(
    new File(["content"], "browser.txt")
)

... {
...     "id": "18cdaa65-5eed-4078-89a8-469b137627ce",
...     "name": "browser.txt",
...     "location": "browser.txt",
...     "content_type": "text/plain",
...     "size": 7,
...     "hash": "9a0364b9e99bb480dd25e1f0284c8555",
...     "storage": "default",
...     "ctime": "2024-06-02T16:12:27.902055+00:00",
...     "mtime": null,
...     "atime": null,
...     "storage_data": {}
... }
```

If you are still using FS storage configured in previous section, switch to
`/tmp/example` folder and check it's content:

```sh
$ ls /tmp/example
browser.txt

$ cat browser.txt
content
```

And, as usually, let's remove file using the ID from the `upload` promise:

```js
sandbox.client.call("POST", "files_file_delete", {
    id: "18cdaa65-5eed-4078-89a8-469b137627ce"
})
```
