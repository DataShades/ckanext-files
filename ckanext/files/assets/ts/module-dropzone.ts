import {topics} from "./shared"

/**
 * Add file/directories to upload queue via drag'n'drop.
 *
 */
window.ckan.module("files--dropzone", function ($) {
    return {
        options: {
            immediate: false,
        },

        initialize() {
            // @ts-ignore
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
        _onDragEnter() {},
        _onDragLeave() {},

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

        scanEntry(entry: FileSystemEntry | null, cb: (file: File) => void) {
            if (!entry) return;

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
            this.sandbox.publish(topics.addFileToQueue, file, {
                immediate: this.options.immediate,
            });
        },
    };
})
