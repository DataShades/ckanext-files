ckan.module("file-upload-widget", function ($, _) {
    "use strict";

    return {
        options: {
            fileInput: '.file-upload-widget input[type="file"]',
            fileInputButton: '.file-upload-widget .file-input-button',
        },
        initialize: function () {
            $.proxyAll(this, /_/);

            console.log('file-upload-widget initialized');

            this.initBtn = this.el.find(".fuw-init-btn");

            // Bind events
            this.initBtn.on('click', this._onTriggerModal);
        },
        _onTriggerModal: function (e) {
            console.log('trigger modal');
        }
    };
});
