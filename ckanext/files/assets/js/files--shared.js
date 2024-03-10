(function (ckan, $) {
  function upload(file, uploader = new StandardUploader()) {
    return uploader.upload(file);
  }

  function makeUploader(adapter, ...options) {
    const factory = ckan.CKANEXT_FILES.adapters[adapter];
    if (!factory) {
      throw new Error(`Uploader ${adapter} is not registered`);
    }
    return new factory(...options);
  }

  ckan.sandbox.extend({
    files: {
      upload,
      makeUploader,
    },
  });

  class BaseUploader extends EventTarget {
    constructor(settings) {
      super();
      this.settings = { ...ckan.CKANEXT_FILES.default_settings, ...settings };
      this.sandbox = ckan.sandbox();

      const csrfField =
        document.querySelector("meta[name=csrf_field_name]")?.content ??
        "_csrf_token";
      this.csrfToken = document.querySelector(
        `meta[name=${csrfField}]`,
      )?.content;

      this;
    }

    upload(file) {
      throw new Error("BaseUploader.upload is not implemented");
    }

    dispatchStart(file) {
      this.dispatchEvent(new CustomEvent("start", { detail: { file } }));
    }
    dispatchProgress(file, loaded, total) {
      this.dispatchEvent(
        new CustomEvent("progress", { detail: { file, loaded, total } }),
      );
    }
    dispatchFinish(file, result) {
      this.dispatchEvent(
        new CustomEvent("finish", { detail: { file, result } }),
      );
    }
    dispatchFail(file, reasons) {
      this.dispatchEvent(
        new CustomEvent("fail", { detail: { file, reasons } }),
      );
    }
    dispatchError(file, error) {
      this.dispatchEvent(
        new CustomEvent("error", { detail: { file, message } }),
      );
    }
  }

  class StandardUploader extends BaseUploader {
    upload(file) {
      const request = new XMLHttpRequest();
      this._prepareRequest(request, file);
      this._sendRequest(request, file);
      return request;
    }

    _addListeners(request, file) {
      request.upload.addEventListener("loadstart", (event) =>
        this.dispatchStart(file),
      );

      request.upload.addEventListener("progress", (event) =>
        this.dispatchProgress(file, event.loaded, event.total),
      );

      request.addEventListener("load", (event) => {
        const result = JSON.parse(request.responseText);
        if (result.success) {
          this.dispatchFinish(file, result.result);
        } else {
          this.dispatchFail(file, result.error);
        }
      });

      request.addEventListener("error", (event) =>
        this.dispatchError(file, request.responseText),
      );
    }

    _prepareRequest(request, file) {
      this._addListeners(request, file);

      request.open(
        "POST",
        this.sandbox.client.url("/api/action/files_file_create"),
      );

      if (this.csrfToken) {
        request.setRequestHeader("X-CSRFToken", this.csrfToken);
      }
    }

    _sendRequest(request, file) {
      const data = new FormData();
      data.append("upload", file);

      data.append("storage", this.settings.storage);
      request.send(data);
    }
  }

  class MultipartUploader extends BaseUploader {
    async upload(file) {
      let info = await this._initializeUpload(file);
      //   this.dispatchError(file, );
      //   this.dispatchFail(file, );

      this.dispatchStart(file);

      let start = info.storage_data.uploaded || 0;

      while (start < file.size) {
        info = await this._uploadChunk(
          info.id,
          file.slice(start, start + this.settings.chunkSize),
          start,
        );

        const uploaded = info.storage_data.uploaded;
        if (uploaded <= start) {
          throw new Error();
        }

        this.dispatchProgress(file, start, file.size);
        start = uploaded;
      }

      this.dispatchProgress(file, file.size, file.size);
      info = await this._completeUpload(info);
      this.dispatchFinish(file, info);
    }

    _initializeUpload(file) {
      return new Promise((done, fail) =>
        this.sandbox.client.call(
          "POST",
          "files_upload_initialize",
          {
            storage: this.settings.storage,
            name: file.name,
            size: file.size,
          },
          (data) => {
            done(data.result);
          },
          (resp) => {
            fail(
              typeof resp.responseJSON === "string"
                ? resp.responseText
                : resp.responseJSON.error,
            );
          },
        ),
      );
    }

    _uploadChunk(id, part, start) {
      if (!part.size) {
        throw new Error("0-length chunks are not allowed");
      }
      const request = new XMLHttpRequest();

      const result = new Promise((done, fail) => {
        request.addEventListener("load", (event) => {
          const result = JSON.parse(request.responseText);
          if (result.success) {
            done(result.result);
          } else {
            fail(result.error);
          }
        });

        request.addEventListener("error", (event) =>
          fail(request.responseText),
        );
      });

      request.open(
        "POST",
        this.sandbox.client.url("/api/action/files_upload_update"),
      );

      if (this.csrfToken) {
        request.setRequestHeader("X-CSRFToken", this.csrfToken);
      }

      this._sendRequest(request, part, start, id);

      return result;
    }

    _sendRequest(request, part, position, id) {
      const form = new FormData();
      form.append("upload", part);
      form.append("position", position);
      form.append("id", id);
      request.send(form);
    }

    _completeUpload(data) {
      return new Promise((done, fail) =>
        this.sandbox.client.call(
          "POST",
          "files_upload_complete",
          {
            id: data.id,
          },
          (data) => {
            done(data.result);
          },
          (resp) => {
            fail(
              typeof resp.responseJSON === "string"
                ? resp.responseText
                : resp.responseJSON.error,
            );
          },
        ),
      );
    }
  }

  ckan.CKANEXT_FILES = {
    adapters: {
      base: BaseUploader,
      standard: StandardUploader,
      multipart: MultipartUploader,
    },
    default_settings: {
      storage: "default",
      chunkSize: 100,
    },
  };
})(ckan, $);
