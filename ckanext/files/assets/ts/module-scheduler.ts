import {topics} from "./shared"

/**
 * Add selected file to upload queue whenever `[data-queue-scheduler]`
 * dispatches `change` event.
 *
 */
window.ckan.module("files--scheduler", function () {
    return {
        options: {
            immediate: false,
        },
        initialize() {
            const scheduler = this.$("[data-queue-scheduler]");
            scheduler.on("drop", (event) => event.preventDefault());
            scheduler.on("change", (event) =>
                this.push(...(event.target as HTMLInputElement).files!),
            );
        },

        push(...files: File[]) {
            files.forEach((file) =>
                this.sandbox.publish(topics.addFileToQueue, file, {
                    immediate: this.options.immediate,
                }),
            );
        },
    };
});
