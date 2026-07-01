window.ckan.module("files--resource-select", ($) => {
    return {
        options: {
            successEvent: "files-file-created",
            errorEvent: "files-file-failed",
            select: null as string | null,
            initialValue: null as string | null,
        },
        url: null as HTMLElement | null,
        select: null as JQuery | null,

        initialize() {
            if (!this.options.select) {
                console.error(
                    "files--resource-select cannot be initialized without `select` option",
                );
                return;
            }

            // @ts-ignore
            $.proxyAll(this, /_on/);

            this.el.on({
                [this.options.successEvent]: this._onSuccess,
                [this.options.errorEvent]: this._onError,
            });

            this.url = document.getElementById("field-resource-url");
            this.select = $(this.options.select);
            if (this.options.initialValue) {
                // @ts-ignore
                this.select.select2("data", this.options.initialValue);
            }
        },
        _onSuccess({ detail }: { detail: any }) {
            // @ts-ignore
            this.select.select2("data", {
                id: detail.id,
                text: detail.name,
            });
        },
        _onError({
            detail: err,
        }: {
            detail: string | { [key: string]: string[] };
        }) {
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
        },
        reportError(label: string, message: string) {
            const box = this.sandbox.notify.initialize(
                this.sandbox.notify.create(label, message),
            );
            this.el.closest("label").parent().after(box);
        },
    };
});
