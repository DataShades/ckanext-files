ckan.module("files--uploader", function () {
  return {
    options: {
      triggerEvent: "change",
      progressTplSelector: null,
      triggerSelector: null,
      fileSelector: null,
      storage: "default",
      uploaderType: "multipart",
      showNotifications: false,
    },

    initialize() {
      $.proxyAll(this, /_on/);

      this.uploader = this.sandbox.files.makeUploader(
        this.options.uploaderType,
        {
          storage: this.options.storage,
        },
      );

      this.uploader.addEventListener("start", this._onStart);
      this.uploader.addEventListener("progress", this._onProgress);
      this.uploader.addEventListener("finish", this._onFinish);
      this.uploader.addEventListener("fail", this._onFail);
      this.uploader.addEventListener("error", this._onError);

      this.fileField = this.options.fileSelector
        ? $(this.options.fileSelector)
        : this.el;

      const triggerEl = this.options.triggerSelector
        ? $(this.options.triggerSelector)
        : this.el;

      triggerEl.on(this.options.triggerEvent, () => this.processFiles());

      this.progressBars = new WeakMap();
      this.progressTpl = $(this.options.progressTplSelector);
    },

    processFiles() {
      const files = Array.from(this.fileField[0].files);
      return files.map((file) =>
        this.sandbox.files.upload(file, this.uploader),
      );
    },

    _onStart({ detail: { file } }) {
      if (this.progressTpl.length) {
        const bar = this.progressTpl
          .clone(true)
          .prop("hidden", false)
          .insertAfter(this.progressTpl)
          .show();
        bar.find("label").text(file.name);
        this.progressBars.set(file, bar);
      }
    },

    _onProgress({ detail: { file, loaded, total } }) {
      const bar = this.progressBars.get(file);
      if (bar) {
        const completion = ((loaded * 100) / total).toFixed(0);
        bar
          .find(".progress-bar")
          .removeClass("bg-primary bg-secondary bg-danger bg-success")
          .addClass("bg-primary")
          .text(completion + "%")
          .css("width", completion + "%");
      }
    },

    _onFinish({ detail: { file } }) {
      if (this.options.showNotifications) {
        this.sandbox.notify(file.name, "upload completed", "success");
      }

      const bar = this.progressBars.get(file);
      if (bar) {
        bar
          .find(".progress-bar")
          .removeClass("bg-primary bg-secondary bg-danger bg-success")
          .addClass("bg-success");
      }
    },

    _onFail({ detail: { file, reasons } }) {
      if (this.options.showNotifications) {
        this.sandbox.notify(
          file.name,
          this._formatValidationErrors(reasons),
          "error",
        );
      }

      const bar = this.progressBars.get(file);
      if (bar) {
        bar
          .find(".progress-bar")
          .removeClass("bg-primary bg-secondary bg-danger bg-success")
          .addClass("bg-danger");
      }
    },
    _onError({ detail: { file, message } }) {
      if (this.options.showNotifications) {
        this.sandbox.notify(file.name, message, "error");
      }

      const bar = this.progressBars.get(file);
      if (bar) {
        bar
          .find(".progress-bar")
          .removeClass("bg-primary bg-secondary bg-danger bg-success")
          .addClass("bg-danger");
      }
    },

    _formatValidationErrors(errors) {
      return Object.entries(errors)
        .filter(([k, v]) => k[0] !== "_" && Array.isArray(v))
        .map(([k, v]) => k + " - " + v)
        .join(";");
    },
  };
});
