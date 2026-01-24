# File Upload Widget

## Capabilities
The File Upload Widget enables users to:

- Upload files from a local device.
- Import files via external URLs.
- Select previously uploaded files from a Media Gallery.
- Drag and drop files into the upload zone.
- Manage multiple file uploads with progress tracking.

## Usage

Enable the `file_upload_widget` plugin in your CKAN config:

```ini
ckan.plugins = ... files file_upload_widget
```

Then reference the snippet in your scheming schema:

```yaml
form_snippet: files_upload_widget.html
```

!!! warning
    You need to implement the API actions `uploadAction` and `uploadLinkAction` to make the widget work properly. By default, it uses the `default` and `link` storages and does not include proper auth checks.

    Read about why separate API actions are required in the [permissions](./permissions.md) section.


## Options
The widget supports the following configuration options within the schema field definition.

### accept
Defines the file types the file input should accept. This maps to the HTML5 `accept` attribute.

**Example:**
```yaml
- field_name: image
  label: Image
  form_snippet: files_upload_widget.html
  accept: image/*
```

## JavaScript Options (file-upload-widget.js)
You can configure the JavaScript behavior by passing options via `form_attrs` in the schema. These are converted to `data-module-*` attributes.

| Option | Attribute | Default | Description |
| :--- | :--- | :--- | :--- |
| **maxFiles** | `data-module-max-files` | `0` | Maximum number of files allowed. Set to `0` for unlimited. |
| **disableUrl** | `data-module-disable-url` | `false` | If `true`, hides the URL import button and window. |
| **disableMedia** | `data-module-disable-media` | `false` | If `true`, hides the Media Gallery button and window. |
| **uploadAction** | `data-module-upload-action` | `file_widget_file_create` | API action used for uploading local files. |
| **uploadLinkAction** | `data-module-upload-link-action` | `file_widget_link_create` | API action used for importing files via URL. |

**Configuration Example:**
```yaml
- field_name: resources
  form_snippet: files_upload_widget.html
  form_attrs:
    data-module-max-files: 5
    data-module-disable-media: true
    data-module-upload-action: my_custom_upload_action
```
