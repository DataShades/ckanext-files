import {topics} from './shared'
/**
 * Add to queue a file, that has associated incomplete upload.
 *
 * Supports a number of properties to verify that the new file matches
 * previously uploaded file.
 *
 *
 */
window.ckan.module("files--restorer", function ($) {
    return {
        options: {
            name: "",
            size: 0,
            uploaded: 0,
            id: "",
            immediate: false,
        },

        initialize() {
            // @ts-ignore
            $.proxyAll(this, /_on/);
            this.el.on("change", this._onChange);
        },

        _onChange(event: JQuery.ChangeEvent) {
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

            this.sandbox.publish(topics.restoreFileInQueue, file, {
                id: this.options.id,
                uploaded: this.options.uploaded,
                immediate: this.options.immediate,
            });
        },
    };
});
