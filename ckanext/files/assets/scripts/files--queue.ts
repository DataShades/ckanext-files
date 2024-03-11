ckan.module("files--scheduler", function ($) {
  return {
    initialize() {
      const scheduler = this.$("[data-queue-scheduler]");
      scheduler.on("change", (event: Event) =>
        this.push(...(event.target as HTMLInputElement).files!),
      );
    },

    push(...files: File[]) {
      files.forEach((file) =>
        this.sandbox.publish(ckan.CKANEXT_FILES.topics.addFileToQueue, file),
      );
    },
  } as any;
});

ckan.module("files--restorer", function ($) {
  return {
    options: {
      name: "",
      size: 0,
      uploaded: 0,
      id: "",
    },

    initialize() {
      $.proxyAll(this, /_on/);
      this.el.on("change", this._onChange);
    },

    _onChange(event: Event) {
      const file = (event.target as HTMLInputElement).files?.[0];

      if (!file) {
        return;
      }

      if (this.options.name && file.name !== this.options.name) {
        this.sandbox.notify(
          "Name mismatch.",
          `Expected name: ${this.options.name}`,
        );
        return;
      }

      if (this.options.size && file.size !== this.options.size) {
        this.sandbox.notify(
          "Size mismatch.",
          `Expected size: ${this.options.size.toLocaleString()} bytes`,
        );
        return;
      }

      this.sandbox.publish(ckan.CKANEXT_FILES.topics.restoreFileInQueue, file, {
        id: this.options.id,
        uploaded: this.options.uploaded,
      });
    },
  };
});
ckan.module("files--queue", function ($) {
  return {
    options: {
      storage: "default",
      uploader: "Standard",
    },

    initialize() {
      $.proxyAll(this, /_on/);
      ckan.pubsub.subscribe(
        ckan.CKANEXT_FILES.topics.addFileToQueue,
        this._onFile,
      );
      ckan.pubsub.subscribe(
        ckan.CKANEXT_FILES.topics.restoreFileInQueue,
        this._onFile,
      );

      this.tpl = this.$("[data-upload-template]")
        .remove()
        .removeAttr("data-upload-template hidden");

      this.widgets = new WeakMap();
    },

    teardown() {
      ckan.pubsub.unsubscribe(
        ckan.CKANEXT_FILES.topics.addFileToQueue,
        this._onFile,
      );
      ckan.pubsub.unsubscribe(
        ckan.CKANEXT_FILES.topics.restoreFileInQueue,
        this._onFile,
      );
    },

    _onFile(
      file: File,
      options = { id: "", uploaded: 0, uploader: null, storage: null },
    ) {
      const widget = this.tpl.clone(true).appendTo(this.el);
      const info = {
        file,
        id: options.id,
        uploaded: options.uploaded || 0,
        uploader: this.sandbox.files.makeUploader(
          options.uploader || this.options.uploader,
          { storage: options.storage || this.options.storage },
        ),
      };

      this.widgets.set(widget[0], info);

      widget.on("click", "[data-upload-resume]", this._onWidgetResume);
      widget.on("click", "[data-upload-pause]", this._onWidgetPause);

      info.uploader.addEventListener(
        "commit",
        (event: CustomEvent) => (info.id = event.detail.id),
      );
      info.uploader.addEventListener(
        "progress",
        ({ detail: { loaded, total } }: CustomEvent) =>
          this.setWidgetCompletion(widget, loaded, total),
      );
      info.uploader.addEventListener(
        "finish",
        ({ detail: { file, result } }: CustomEvent) => {
          this.toggleAnimation(widget, false);
          widget
            .find("[data-upload-progress]")
            .removeClass("bg-primary bg-secondary")
            .addClass("bg-success");
          this.sandbox.publish(
            ckan.CKANEXT_FILES.topics.queueItemUploaded,
            file,
            result,
          );
        },
      );

      this.setWidgetName(widget, info.file.name);
      this.setWidgetCompletion(widget, info.uploaded, info.file.size);
    },

    setWidgetName(widget: JQuery, name: string) {
      widget.find("[data-item-name]").text(name);
    },

    setWidgetCompletion(widget: JQuery, uploaded: number, total: number) {
      const value = (uploaded * 100) / total;
      const info = this.widgets.get(widget[0]);
      info.uploaded = uploaded;

      const completion = value.toFixed(0) + "%";
      widget
        .find("[data-upload-progress]")
        .text(completion)
        .css("width", completion);
    },

    toggleAnimation(widget: JQuery, state: boolean) {
      widget
        .find("[data-upload-progress]")
        .toggleClass("progress-bar-animated", state);
    },

    _onWidgetResume(event: JQuery.TriggeredEvent) {
      const info = this.widgets.get(event.delegateTarget);
      if (info.uploaded >= info.total) return;

      const widget = $(event.delegateTarget);
      widget
        .find("[data-upload-progress]")
        .removeClass("bg-secondary")
        .addClass("bg-primary");

      if (info.id) {
        info.uploader.resume(info.file, info.id);
      } else {
        info.uploader.upload(info.file);
      }

      this.toggleAnimation(widget, true);
    },

    _onWidgetPause(event: JQuery.TriggeredEvent) {
      const info = this.widgets.get(event.delegateTarget);
      if (info.uploaded >= info.total) return;

      const widget = $(event.delegateTarget);
      widget
        .find("[data-upload-progress]")
        .removeClass("bg-primary")
        .addClass("bg-secondary");

      info.uploader.pause(info.file);
      this.toggleAnimation(widget, false);
    },
  };
});
