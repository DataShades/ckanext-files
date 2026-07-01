import {topics} from './shared'

window.ckan.module("files--queue", function ($) {
    return {
        options: {
            storage: "default",
            uploader: "Standard",
        },
        tpl: null as unknown as JQuery,
        widgets: null as unknown as WeakMap<HTMLElement, any>,

        initialize() {
            // @ts-ignore
            $.proxyAll(this, /_on/);
            window.ckan.pubsub.subscribe(topics.addFileToQueue, this._onFile);
            window.ckan.pubsub.subscribe(
                topics.restoreFileInQueue,
                this._onFile,
            );

            this.tpl = this.$("[data-upload-template]")
                .remove()
                .removeAttr("data-upload-template hidden");

            this.widgets = new WeakMap();
        },

        teardown() {
            window.ckan.pubsub.unsubscribe(topics.addFileToQueue, this._onFile);
            window.ckan.pubsub.unsubscribe(
                topics.restoreFileInQueue,
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
                    this.sandbox.files.makeUploader(options.uploader || this.options.uploader, {
                        storage: options.storage || this.options.storage,
                    }),
            };

            this.widgets.set(widget[0], info);

            widget.on("click", "[data-upload-resume]", this._onWidgetResume);
            widget.on("click", "[data-upload-pause]", this._onWidgetPause);

            info.uploader.addEventListener("fail", (({
                detail: { reasons, file },
            }: CustomEvent<{
                reasons: { [key: string]: string[] };
                file: File;
            }>) => {
                this.sandbox.notify(
                    file.name,
                    Object.entries(reasons)
                        .filter(([k]) => k[0] !== "_")
                        .map(([, v]) => (Array.isArray(v) ? v.join("; ") : v))
                        .join("; "),
                );
                this.sandbox.notify.el[0].scrollIntoView();

                this.toggleAnimation(widget, false);

                widget
                    .find("[data-upload-progress]")
                    .removeClass("bg-primary bg-secondary")
                    .addClass("bg-danger progress-bar-danger");
            }) as EventListener);
            info.uploader.addEventListener("error", (({
                detail: { message, file },
            }: CustomEvent<{ message: string; file: File }>) => {
                this.sandbox.notify(file.name, message);
                this.sandbox.notify.el[0].scrollIntoView();

                this.toggleAnimation(widget, false);
                widget
                    .find("[data-upload-progress]")
                    .removeClass("bg-primary bg-secondary")
                    .addClass("bg-danger progress-bar-danger");
            }) as EventListener);

            info.uploader.addEventListener("progress", (({
                detail: { loaded, total },
            }: CustomEvent) =>
                this.setWidgetCompletion(
                    widget,
                    loaded,
                    total,
                )) as EventListener);
            info.uploader.addEventListener("finish", (({
                detail: { file, result },
            }: CustomEvent) => {
                this.toggleAnimation(widget, false);
                widget
                    .find("[data-upload-progress]")
                    .removeClass("bg-primary bg-secondary")
                    .addClass("bg-success progress-bar-success");
                this.sandbox.publish(topics.queueItemUploaded, file, result);
            }) as EventListener);

            this.setWidgetName(widget, info.file.name);
            this.setWidgetCompletion(widget, info.uploaded, info.file.size);

            if (options.immediate) {
                widget.find("[data-upload-resume]").trigger("click");
            }
        },

        setWidgetName(widget: any, name: string) {
            widget.find("[data-item-name]").text(name);
        },

        setWidgetCompletion(widget: any, uploaded: number, total: number) {
            const value = (uploaded * 100) / total;
            const info = this.widgets.get(widget[0]);
            info.uploaded = uploaded;

            const completion = value.toFixed(0) + "%";
            widget
                .find("[data-upload-progress]")
                .text(completion)
                .css("width", completion);
        },

        toggleAnimation(widget: any, state: boolean) {
            widget
                .find("[data-upload-progress]")
                .toggleClass("progress-bar-animated active", state);
        },

        _onWidgetResume(event: any) {
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

        _onWidgetPause(event: any) {
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
})
