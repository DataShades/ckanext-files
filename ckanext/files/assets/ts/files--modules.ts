/**
 * Add selected file to upload queue whenever `[data-queue-scheduler]`
 * dispatches `change` event.
 *
 */
ckan.module("files--image-upload", function ($) {
    type TStart = { detail: { file: File } };
    type TFinish = { detail: { file: File; result: { [key: string]: any } } };
    type TFail = {
        detail: { file: File; reasons: { [key: string]: string[] } };
    };
    type TError = { detail: { file: File; message: string } };

    return {
        options: {
            spinner: null,
            action: null,
            field: null,
        },
        queue: null,

        initialize() {
            for (let param of ["field", "action"]) {
                if (!this.options[param]) {
                    console.error(
                        `files--image-upload cannot be initialized without '${param}' option`,
                    );
                    return;
                }
            }

            if (!this.options.action) {
                console.error(
                    "files--image-upload cannot be initialized without `action` option",
                );
                return;
            }
            $.proxyAll(this, /_on/);

            this.queue = new Set();

            this.el.on("change", (event: Event) =>
                this.upload(...(event.target as HTMLInputElement).files!),
            );
            this.spinner = $(this.options.spinner);
            this.field = $(this.options.field);
            this.submits = this.el
                .closest("form")
                .find("input[type=submit],button[type=submit]");
        },

        upload(...files: File[]) {
            files.forEach(async (file) => {
                const uploader = this.sandbox.files.makeUploader("Standard");

                try {
                    this.queue.add(file);
                    this.refreshFormState();

                    const options: ckan.CKANEXT_FILES.UploadOptions = {
                        uploaderParams: [{ uploadAction: this.options.action }],
                    };
                    const {
                        details: { result },
                    } = await this.sandbox.files.upload(file, options);
                    this.field.val(result.id);
                } catch (err) {
                    if (typeof err === "string") {
                        this.reportError("Error", err);
                    } else {
                        for (let [field, problems] of Object.entries(
                            err as { [key: string]: string[] },
                        )) {
                            if (field.startsWith("__")) continue;
                            this.reportError(field, problems.join(","));
                        }
                    }
                }
                this.queue.delete(file);
                this.refreshFormState();
            });
        },

        reportError(label: string, message: string) {
            const box = this.sandbox.notify.initialize(
                this.sandbox.notify.create(label, message),
            );
            this.field.parent().append(box);
        },

        refreshFormState() {
            this.spinner.prop("hidden", !this.queue.size);
            this.submits.prop("disabled", !!this.queue.size);
        },
    };
});

/**
 * Add selected file to upload queue whenever `[data-queue-scheduler]`
 * dispatches `change` event.
 *
 */
ckan.module("files--scheduler", function ($) {
    return {
        options: {
            immediate: false,
        },
        initialize() {
            const scheduler = this.$("[data-queue-scheduler]");
            scheduler.on("drop", (event: Event) => event.preventDefault());
            scheduler.on("change", (event: Event) =>
                this.push(...(event.target as HTMLInputElement).files!),
            );
        },

        push(...files: File[]) {
            files.forEach((file) =>
                this.sandbox.publish(
                    ckan.CKANEXT_FILES.topics.addFileToQueue,
                    file,
                    { immediate: this.options.immediate },
                ),
            );
        },
    };
});

/**
 * Add file/directories to upload queue via drag'n'drop.
 *
 */
ckan.module("files--dropzone", function ($) {
    return {
        options: {
            immediate: false,
        },

        initialize() {
            $.proxyAll(this, /_on/);
            const element = this.el[0];

            element.addEventListener("dragover", this._onDragOver);
            element.addEventListener("dragenter", this._onDragEnter);
            element.addEventListener("dragleave", this._onDragLeave);
            element.addEventListener("drop", this._onDrop);
        },

        _onDragOver(event: DragEvent) {
            event.preventDefault();
        },
        _onDragEnter(event: DragEvent) {},
        _onDragLeave(event: DragEvent) {},

        _onDrop(event: DragEvent) {
            event.preventDefault();
            if (!event.dataTransfer) {
                return;
            }

            for (let entry of event.dataTransfer.items) {
                this.scanEntry(entry.webkitGetAsEntry(), (file: File) =>
                    this.push(file),
                );
            }
        },

        scanEntry(
            entry: FileSystemFileEntry | FileSystemDirectoryEntry,
            cb: (file: File) => void,
        ) {
            if (entry.isFile) {
                (entry as FileSystemFileEntry).file(cb);
            } else {
                (entry as FileSystemDirectoryEntry)
                    .createReader()
                    .readEntries((entries) =>
                        entries.forEach((e) => this.scanEntry(e, cb)),
                    );
            }
        },

        push(file: File) {
            this.sandbox.publish(
                ckan.CKANEXT_FILES.topics.addFileToQueue,
                file,
                { immediate: this.options.immediate },
            );
        },
    };
});

/**
 * Add to queue a file, that has associated incomplete upload.
 *
 * Supports a number of properties to verify that the new file matches
 * previously uploaded file.
 *
 *
 */
ckan.module("files--restorer", function ($) {
    return {
        options: {
            name: "",
            size: 0,
            uploaded: 0,
            id: "",
            immediate: false,
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
                this.sandbox.notify.el[0].scrollIntoView();
                return;
            }

            if (this.options.size && file.size !== this.options.size) {
                this.sandbox.notify(
                    "Size mismatch.",
                    `Expected size: ${this.options.size.toLocaleString()} bytes`,
                );
                this.sandbox.notify.el[0].scrollIntoView();
                return;
            }

            this.sandbox.publish(
                ckan.CKANEXT_FILES.topics.restoreFileInQueue,
                file,
                {
                    id: this.options.id,
                    uploaded: this.options.uploaded,
                    immediate: this.options.immediate,
                },
            );
        },
    };
});

ckan.module("files--shared-queue", function ($) {
    return {
        initialize() {
            $.proxyAll(this, /_on/);

            this.worker = new SharedWorker(
                this.sandbox.url(
                    "ckanext-files/scripts/files--shared-uploader.js",
                ),
            );

            this.worker.port.onmessage = console.debug;
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
            options = {
                immediate: false,
                id: "",
                uploaded: 0,
                uploaderInstance: null,
                uploader: null,
                storage: null,
            },
        ) {
            const widget = this.tpl.clone(true).appendTo(this.el);
            const info = {
                file,
                id: options.id,
                uploaded: options.uploaded || 0,
                uploader:
                    options.uploaderInstance ||
                    this.sandbox.files.makeUploader(
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
                "fail",
                ({
                    detail: { reasons, file },
                }: CustomEvent<{
                    reasons: { [key: string]: string[] };
                    file: File;
                }>) => {
                    this.sandbox.notify(
                        file.name,
                        Object.entries(reasons)
                            .filter(([k, v]) => k[0] !== "_")
                            .map(([k, v]) =>
                                Array.isArray(v) ? v.join("; ") : v,
                            )
                            .join("; "),
                    );
                    this.sandbox.notify.el[0].scrollIntoView();

                    this.toggleAnimation(widget, false);

                    widget
                        .find("[data-upload-progress]")
                        .removeClass("bg-primary bg-secondary")
                        .addClass("bg-danger progress-bar-danger");
                },
            );
            info.uploader.addEventListener(
                "error",
                ({
                    detail: { message, file },
                }: CustomEvent<{ message: string; file: File }>) => {
                    this.sandbox.notify(file.name, message);
                    this.sandbox.notify.el[0].scrollIntoView();

                    this.toggleAnimation(widget, false);
                    widget
                        .find("[data-upload-progress]")
                        .removeClass("bg-primary bg-secondary")
                        .addClass("bg-danger progress-bar-danger");
                },
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
                        .addClass("bg-success progress-bar-success");
                    this.sandbox.publish(
                        ckan.CKANEXT_FILES.topics.queueItemUploaded,
                        file,
                        result,
                    );
                },
            );

            this.setWidgetName(widget, info.file.name);
            this.setWidgetCompletion(widget, info.uploaded, info.file.size);

            if (options.immediate) {
                widget.find("[data-upload-resume]").trigger("click");
            }
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
                .toggleClass("progress-bar-animated active", state);
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
