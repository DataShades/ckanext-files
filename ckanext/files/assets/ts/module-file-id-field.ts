window.ckan.module("files--file-id-field", function ($) {
    return {
        options: {
            idField: `[name="file_id"]`,
            packageId: null,
            resourceId: null,
            progressBar: "#resource-upload-progressbar",
        },

        uploadKey: "ckanextFiles.incompleteUpload",

        idField: null as unknown as JQuery,
        bar: null as unknown as JQuery,
        uploadButton: null as unknown as JQuery,
        uploadField: null as unknown as JQuery<HTMLInputElement>,
        uploader: null as unknown as CkanextFiles.Adapter,

        initialize() {
            this.idField = $(this.options.idField);
            this.bar = $(this.options.progressBar);
            this.uploadButton = $("#resource-upload-button");

            this.$(".btn-remove-url").on("click", () => {
                this.$("#field-clear-upload").prop("checked", true);
                this.$("#field-resource-upload").focus();
            });
            this.uploadField = this.$("#field-resource-upload");

            this.uploadField.on("change", (event) => {
                // this module exects a single file in field. All files but first will
                // be ignored
                const file = event.target.files![0];
                this._processFile(file);
            });

            this.uploader = this.sandbox.files.makeUploader("Multipart", {
                uploadAction: "files_resource_upload",
            });

            this._setupUploadListeners();
            this._enableUploadControls();

            const incomplete = this._getIncompleteUpload();
            if (incomplete) {
                const contentNode = document.createElement("div");
                const nameNode = document.createElement("strong");
                nameNode.append(incomplete.name);
                const sizeNode = document.createElement("em");
                sizeNode.append(this.formatFileSize(incomplete.size));

                contentNode.append(
                    "Previous upload is not completed. To resume, select a file with the same name and size: ",
                    nameNode,
                    " (",
                    sizeNode,
                    ")",
                    ". Selecting a different file will discard the incomplete upload and start a new one.",
                );

                this.sandbox.ui
                    .notification(contentNode, {
                        title: "Incomplete upload detected",
                        dismissible: true,
                        style: "warning",
                    })
                    .show();

                this._setProgress(incomplete.uploaded, incomplete.size);
            }
        },

        _enableUploadControls() {
            this.uploadField.prop("disabled", false);
            this.uploadButton.prop("disabled", false);
        },

        formatFileSize(bytes: number) {
            const units = ["B", "KiB", "MiB", "GiB", "TiB"];
            let unitIndex = 0;

            while (bytes >= 1024 && unitIndex < units.length - 1) {
                bytes /= 1024;
                unitIndex++;
            }

            return `${bytes.toFixed(2)} ${units[unitIndex]}`;
        },

        _setProgress(uploaded: number, size: number) {
            this.bar.css("width", `${((uploaded / size) * 100).toFixed(0)}%`);
        },

        _setupUploadListeners() {
            this.uploader.addEventListener("multipartid", (({
                detail: { file, id },
            }: CustomEvent) => {
                this._commitUpload({
                    created: new Date(),
                    size: file.size,
                    name: file.name,
                    id,
                    uploaded: 0,
                });
                this._switchSubmit(false);

                this.bar.css("width", "0%");
            }) as EventListener);

            this.uploader.addEventListener("progress", (({
                detail: { loaded, total },
            }: CustomEvent) => {
                this._commitUpload({ uploaded: loaded });
                this._setProgress(loaded, total);
            }) as EventListener);

            this.uploader.addEventListener("finish", (({
                detail: { result },
            }: CustomEvent) => {
                this._resetUpload();
                this._switchSubmit(true);
                this.idField.val(result.id);
            }) as EventListener);

            this.uploader.addEventListener("fail", (({
                detail: { reasons },
            }: CustomEvent) => {
                this.sandbox.ui
                    .notification(Object.values(reasons), {
                        title: "Upload error",
                        dismissible: true,
                        style: "danger",
                    })
                    .show();
                this._resetUpload();
            }) as EventListener);

            this.uploader.addEventListener("error", (({
                detail: { message },
            }: CustomEvent) => {
                this.sandbox.ui
                    .notification(message, {
                        title: "Upload error",
                        dismissible: true,
                        style: "danger",
                    })
                    .show();
            }) as EventListener);
        },

        /**
         * Process the uploaded file.
         */
        _processFile(file: File) {
            if (!file) {
                this.idField.val("");
                return;
            }

            const incomplete = this._getIncompleteUpload();
            if (
                incomplete &&
                incomplete.size === file.size &&
                incomplete.name === file.name
            ) {
                this.uploader.resume(file, incomplete.id);
            } else {
                this.uploader.upload(file, {
                    resource_id: this.options.resourceId,
                    package_id: this.options.packageId,
                    multipart: true,
                });
            }
        },

        _getIncompleteUpload() {
            const value = localStorage.getItem(this.uploadKey);
            if (value) {
                const data = JSON.parse(value);
                const age = Number(new Date()) - Number(new Date(data.created));
                // S3 multipart uploads are expired in 7 days. To be sure that upload
                // will not expire in the middle of request, ignore uploads older than 6
                // days.
                if (age / 1000 / 3600 / 24 < 6) {
                    return data;
                }
            }
        },

        _commitUpload(data: object) {
            const value = this._getIncompleteUpload() || {};
            Object.assign(value, data);
            localStorage.setItem(this.uploadKey, JSON.stringify(value));
        },

        _resetUpload() {
            localStorage.removeItem(this.uploadKey);
        },

        _switchSubmit(enabled: boolean) {
            this.el
                .closest("form")
                .find(`[type="submit"]`)
                .prop("disabled", !enabled);
        },
    };
});
