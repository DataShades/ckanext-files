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

/// note

This functionality is not stable. Check `multipart_*`, `resumable_*` and
`signed` methods of the storage for current examples of implementations.

///
