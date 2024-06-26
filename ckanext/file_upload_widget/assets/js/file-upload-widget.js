ckan.module("file-upload-widget", function ($, _) {
    "use strict";

    return {
        const: {
            fileInputButton: '.btn-file-input',
            urlInputButton: '.btn-url-input',
            mediaInputButton: '.btn-media-input',
            //
            mainWindowBlock: '.fuw-main-window',
            urlInputBlock: '.fuw-url-input',
            mediaInputBlock: '.fuw-media-input',
            cancelBtn: '.fuw-cancel-btn',
        },
        initialize: function () {
            $.proxyAll(this, /_/);

            console.log('file-upload-widget initialized');

            this.initBtn = this.el.find(".fuw-init-btn");
            this.fileInputBtn = this.el.find(this.const.fileInputButton);
            this.urlInputBtn = this.el.find(this.const.urlInputButton);
            this.mediaInputBtn = this.el.find(this.const.mediaInputButton);

            this.mainWindow = this.el.find(this.const.mainWindowBlock);
            this.urlWindow = this.el.find(this.const.urlInputBlock);
            this.mediaWindow = this.el.find(this.const.mediaInputBlock);

            this.cancelBtn = this.el.find(this.const.cancelBtn);

            // Bind events
            this.initBtn.on('click', this._onTriggerModal);
            this.fileInputBtn.on('click', this._onFileInputTriggered);
            this.urlInputBtn.on('click', this._onUrlInputTriggered);
            this.mediaInputBtn.on('click', this._onMediaInputTriggered);
            this.cancelBtn.on('click', this._onCancelAction);
        },
        _onTriggerModal: function (e) {
            console.log('trigger modal');
        },
        _onFileInputTriggered: function (e) {
            console.log('file input triggered');
        },
        _onUrlInputTriggered: function (e) {
            console.log('url input triggered');

            this.urlWindow.toggle();
            this.mainWindow.toggle();
            this.cancelBtn.toggle();
        },
        _onMediaInputTriggered: function (e) {
            console.log('media input triggered');

            this.mediaWindow.toggle();
            this.mainWindow.toggle();
            this.cancelBtn.toggle();
        },
        _onCancelAction: function (e) {
            console.log('cancel action');

            this.urlWindow.hide();
            this.mediaWindow.hide();
            this.mainWindow.toggle();
            this.cancelBtn.toggle();
        }
    };
});
