/**
 * Upload file and trigger event with file data on specified element.
 *
 */
window.ckan.module("files--auto-upload", function ($) {
    return {
        options: {
            adapter: "Standard",
            spinner: "",
            action: null,
            selector: null,
            successEvent: "files-file-created",
            errorEvent: "files-file-failed",
            eventTarget: null,
            copyIdInto: "",
            requestParams: {},
            field: null,
        },
        queue: null as unknown as Set<any>,
        spinner: null as unknown as JQuery,
        field: null as null | JQuery,
        submits: null as unknown as JQuery,
        idTarget: null as unknown as JQuery,
        uploader: null as unknown as CkanextFiles.Adapter,

        initialize() {
            if (!this.options.action) {
                console.error(
                    "files--auto-upload cannot be initialized without `action` option",
                );
                return;
            }
            // @ts-ignore
            $.proxyAll(this, /_on/);

            this.queue = new Set();

            let field: any = this.el;
            if (this.options.selector) {
                field = field.find(this.options.selector);
            }

            field.on("change", (event: Event) =>
                this.upload(...(event.target as HTMLInputElement).files!),
            );
            this.spinner = $(this.options.spinner);

            if (this.options.field) this.field = $(this.options.field);

            this.submits = field
                .closest("form")
                .find("input[type=submit],button[type=submit]");
            this.idTarget = $(this.options.copyIdInto);

            this.uploader = this.sandbox.files.makeUploader(this.options.adapter, {
                uploadAction: this.options.action,
            });
        },

        upload(...files: File[]) {
            files.forEach(async (file) => {
                this.queue.add(file);
                this.refreshFormState();
                const options: CkanextFiles.UploadOptions = {
                    uploader: this.uploader,
                    requestParams: {
                        ...this.options.requestParams,
                        multipart: this.uploader instanceof this.sandbox.files.adapters.Multipart,
                    },
                };
                this.sandbox.files
                    .upload(file, options)
                    .then(
                        (result: any) => {
                            this.idTarget.val(result.id);
                            this.dispatchResult(
                                this.options.successEvent,
                                result,
                            );
                        },
                        (err: any) =>
                            this.dispatchResult(this.options.errorEvent, err),
                    )
                    .then(() => {
                        this.queue.delete(file);
                        this.refreshFormState();
                    });
            });
        },

        dispatchResult(event: string, detail: any) {
            const target = this.options.eventTarget
                ? $(this.options.eventTarget)
                : this.el;
            target[0].dispatchEvent(new CustomEvent(event, { detail }));
        },

        refreshFormState() {
            this.spinner.prop("hidden", !this.queue.size);
            this.submits.prop("disabled", !!this.queue.size);
        },
    };
});
