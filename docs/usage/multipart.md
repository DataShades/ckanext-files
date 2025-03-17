# Multipart, resumable and signed uploads

This feature has many names, but it basically divides a single upload into
multiple stages. It can be used in following situations:

* a really big file must be uploaded to cloud. It cannot fit into server's
  temporal storage, so you split the file into smaller part and upload them
  separately. Every part is uploaded to server and next part must wait till the
  previous moved from server to cloud. This is a _multipart_ upload.
* client has unstable or slow connection. Any upload takes ages and quite often
  connection is interrupted so user has to spend extra time re-uploading
  files. To improve user experience, you want to track the upload progress and
  keep incomplete file on server. If connection is interrupted, user can
  continue upload from the point he stopped the last time, appending content to
  existing incomplete file. This is a _resumable_ upload.
* files are kept on cloud and uploads are quite intense on the portal. You
  don't want to spend server resources on transferring content from client to
  cloud. Instead you generate a URL that allows user to upload a single file
  directly into specific location on cloud. User sends data to this URL and
  only notifies the application, when upload is finished, so that the
  application can make file visible. This is a _signed_ upload.

All these situations are united inside 4 API actions, which are available if
storage has `MULTIPART` capability. Whether only one strategy is used all the
time, or you can choose which flavor of multipart upload you'll use, it all
depends on the storage adapter. Adapters available out of the box in
ckanext-files usually implement only one strategy.

The following API actions are used in multipart workflow:

* `files_multipart_start`: initialize multipart upload and set expected final
  size and MIMEtype. Basic _multipart_ upload usually just returns upload ID
  from this action. _Resumable_ upload creates empty file in the storage to
  accumulate content inside it. _Signed_ upload produces a URL for direct
  upload.
* `files_multipart_update`: upload the fragment of the file of modify the
  upload in some other way. Most often this action accepts ID of the upload and
  `upload` field with fragment of the uploaded file.
* `files_multipart_refresh`: this action synchronizes and returns current
  upload progress. It can be used if upload was paused and client does not know
  how many bytes were uploaded and from which byte the next upload fragment
  starts.
* `files_multipart_complete`: finalize the upload and convert it into normal
  file, available to other parts of the application. _Multipart_ upload usually
  combines all uploaded parts into single file here. _Resumable_ upload
  verifies that the result has expected MIMEtype and size. _Signed_ upload just
  registers completed file in the system.

Implementation of multipart upload depends on the used adapter, so make sure
you checked its documentation before using any multipart actions. There are
some common steps in multipart upload workflow that are *usually* the same
among all adapters:

* `files_multipart_start` requires `content_type` and `size` parameters. These
  values will be used to validate completed upload.
* `files_multipart_start` allows `hash` parameter. This value will be used to
  validate completed upload. Unlike `content_type` and `size`, `hash` is
  usually optional, because it may be difficult for client to compute it.
* `files_multipart_update` accepts upload ID as `id` and fragment of the file
  as `upload`. Sequence of calls to `files_multipart_update` with
  non-overlapping fragments can be used to upload the file. Even if adapter
  implements signed uploads and client is supposed to send file to the signed
  URL instead of using `files_multipart_update`.
* `files_multipart_complete` compares `content_type`, `size` and `hash`(if
  present) specified during initialization of upload with actual values. If
  they are different, upload is not converted into normal file. Depending on
  implementation, storage may just ignore incorrect initial expectations an
  assign a real values to the file as long as they are allowed by storage
  configuration. But it's recommended to reject such uploads, so it safer to
  assume, that incorrect expectations are not accepted.


Incomplete files support most of normal file actions, but you need to pass
`completed=False` to action when working with incomplete files. I.e, if you
want to remove incomplete upload, use its ID and `completed=False`:

```sh
ckanapi action files_file_delete id=bdfc0268-d36d-4f1b-8a03-2f2aaa21de24 completed=False
```

Incompleted files do not support streaming and downloading via public interface
of the extension. But storage adapter can expose such features via custom
methods if it's technically possible.

Example of basic multipart upload is shown above. `files:fs` adapter can be
used for running this example, as it implements `MULTIPART`.

First, create text file and check its size:

```sh
echo 'hello world!' > /tmp/file.txt
wc -c /tmp/file.txt

... 13 /tmp/file.txt
```

The size is `13` bytes and content type is `text/plain`. These values must be
used for upload initialization.

```sh
ckanapi action files_multipart_start name=file.txt size=13 content_type=text/plain

... {
...   "content_type": "text/plain",
...   "ctime": "2024-06-22T14:47:01.313016+00:00",
...   "hash": "",
...   "id": "90ebd047-96a0-4f32-a810-ffc962cbc380",
...   "location": "file.txt",
...   "name": "file.txt",
...   "owner_id": "59ea0f6c-5c2f-438d-9d2e-e045be9a2beb",
...   "owner_type": "user",
...   "pinned": false,
...   "size": 13,
...   "storage": "default",
...   "storage_data": {
...     "uploaded": 0
...   }
... }
```

Here `storage_data` contains `{"uploaded": 0}`. It may be different for other
adapters, especially if they implement non-consecutive uploads, but generally
it's the recommended way to keep upload progress.

Now we'll upload first 5 bytes of file.

```sh
ckanapi action files_multipart_update id=90ebd047-96a0-4f32-a810-ffc962cbc380 \
    upload@<(dd if=/tmp/file.txt bs=1 count=5)

... {
...   "content_type": "text/plain",
...   "ctime": "2024-06-22T14:47:01.313016+00:00",
...   "hash": "",
...   "id": "90ebd047-96a0-4f32-a810-ffc962cbc380",
...   "location": "file.txt",
...   "name": "file.txt",
...   "owner_id": "59ea0f6c-5c2f-438d-9d2e-e045be9a2beb",
...   "owner_type": "user",
...   "pinned": false,
...   "size": 13,
...   "storage": "default",
...   "storage_data": {
...     "uploaded": 5
...   }
... }

```

If you try finalizing upload right now, you'll get an error.

```sh
ckanapi action files_multipart_complete id=90ebd047-96a0-4f32-a810-ffc962cbc380

... ckan.logic.ValidationError: None - {'upload': ['Actual value of upload size(5) does not match expected value(13)']}

```

Let's upload the rest of bytes and complete the upload.

```sh
ckanapi action files_multipart_update id=90ebd047-96a0-4f32-a810-ffc962cbc380 \
    upload@<(dd if=/tmp/file.txt bs=1 skip=5)

ckanapi action files_multipart_complete id=90ebd047-96a0-4f32-a810-ffc962cbc380

... {
...   "atime": null,
...   "content_type": "text/plain",
...   "ctime": "2024-06-22T14:57:18.483716+00:00",
...   "hash": "c897d1410af8f2c74fba11b1db511e9e",
...   "id": "a740692f-e3d5-492f-82eb-f04e47c13848",
...   "location": "file.txt",
...   "mtime": null,
...   "name": "file.txt",
...   "owner_id": null,
...   "owner_type": null,
...   "pinned": false,
...   "size": 13,
...   "storage": "default",
...   "storage_data": {}
... }
```

Now file can be used normally. You can transfer file ownership to someone,
stream or modify it. Pay attention to ID: completed file has its own unique ID,
which is different from the ID of the incomplete upload.
