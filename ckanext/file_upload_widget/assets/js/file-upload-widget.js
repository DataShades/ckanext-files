ckan.module("file-upload-widget", function ($, _) {
    "use strict";

    return {
        const: {
            fileInputButton: '.btn-file-input',
            urlInputButton: '.btn-url-input',
            mediaInputButton: '.btn-media-input',
            mainWindowBlock: '.fuw-main-window',
            urlInputBlock: '.fuw-url-input',
            mediaInputBlock: '.fuw-media-input',
            cancelBtn: '.fuw-cancel-btn',
            dropZone: '.fuw-main-window__dropzone'
        },
        initialize: function () {
            $.proxyAll(this, /_/);

            console.log('file-upload-widget initialized');

            this.fileInputBtn = this.el.find(this.const.fileInputButton);
            this.urlInputBtn = this.el.find(this.const.urlInputButton);
            this.mediaInputBtn = this.el.find(this.const.mediaInputButton);

            this.mainWindow = this.el.find(this.const.mainWindowBlock);
            this.urlWindow = this.el.find(this.const.urlInputBlock);
            this.mediaWindow = this.el.find(this.const.mediaInputBlock);

            this.fileSearchInput = this.el.find('#fuw-media-input--search');
            this.fileSelectBtn = this.el.find('.btn-file-select');
            this.cancelFileSelectBtn = this.el.find('.btn-cancel-file-select');
            this.dropZoneArea = this.el.find(this.const.dropZone);
            this.fileInput = this.el.find('input[type="file"]');

            this.cancelBtn = this.el.find(this.const.cancelBtn);

            // Bind events
            this.fileInputBtn.on("click", this._onFileInputTriggered);
            this.urlInputBtn.on("click", this._onUrlInputTriggered);
            this.mediaInputBtn.on("click", this._onMediaInputTriggered);
            this.cancelBtn.on("click", this._onCancelAction);
            this.fileSearchInput.on('input', this._onFileSearch);
            this.el.find('li.files--file-item input').on('change', this._onFileSelect);
            this.cancelFileSelectBtn.on("click", this._onCancelFileSelect);
            this.fileInput.on('change', this._onFileSelected);

            // Dropzone events
            this.dropZoneArea.on("drop", this._onDropFile);

            // Prevent default drag behaviors
            ;["dragenter", "dragover", "dragleave", "drop"].forEach(eventName => {
                this.dropZoneArea.on(eventName, this._preventDropDefaults)
                $(document.body).on(eventName, this._preventDropDefaults)
            });

            // Highlight drop area when item is dragged over it
            ;["dragenter", "dragover"].forEach(eventName => {
                this.dropZoneArea.on(eventName, this._highlightDropZone)
            });

            // Unhighlight drop area when item is dragged out of it
            ;["dragleave", "drop"].forEach(eventName => {
                this.dropZoneArea.on(eventName, this._unhighlightDropZone)
            })
        },

        /**
         * Handle file input trigger
         *
         * On file input trigger show an HTML file selector
         *
         * @param {Event} e
         */
        _onFileInputTriggered: function (e) {
            console.log('file input triggered');
        },

        /**
         * Handle url input trigger
         *
         * On url input trigger show url input block and hide main window
         *
         * @param {Event} e
         */
        _onUrlInputTriggered: function (e) {
            this.urlWindow.toggle();
            this.mainWindow.toggle();
            this.cancelBtn.toggle();
        },

        /**
         * Handle media input trigger
         *
         * On media input trigger show media input block and hide main window
         *
         * @param {Event} e
         */
        _onMediaInputTriggered: function (e) {
            this.mediaWindow.toggle();
            this.mainWindow.toggle();
            this.cancelBtn.toggle();
        },

        /**
         * Handle cancel action
         *
         * On cancel action hide url and media input blocks and show main window
         * and hide the cancel button.
         *
         * @param {Event} e
         */
        _onCancelAction: function (e) {
            this.urlWindow.hide();
            this.mediaWindow.hide();
            this.mainWindow.toggle();
            this.cancelBtn.toggle();
        },

        /**
         * Handle file search input
         *
         * On file search input change hide files that don't match search query
         * and highlight text that matches search query.
         *
         * If there are no visible files show empty state message.
         *
         * @param {Event} e
         */
        _onFileSearch: function (e) {
            let search = this.fileSearchInput.val().toLowerCase();
            let isEmpty = true;

            this.mediaWindow.find('li.files--file-item').each((_, element) => {
                let title = $(element).find("label span").text().trim().toLowerCase();

                if (!!search && title.indexOf(search) === -1) {
                    $(element).hide();
                } else {
                    $(element).show();

                    isEmpty = false;

                    this._highlightText(element, search);
                };
            });

            let visibleFilesNum = this.el.find("li.files--file-item:visible").length;

            if (isEmpty && !visibleFilesNum) {
                this.el.find(".fuw-media-input--empty").show();
                this.el.find(".fuw-media-input--files").hide();
            } else {
                this.el.find(".fuw-media-input--empty").hide();
                this.el.find(".fuw-media-input--files").show();
            }
        },

        /**
         * Highlight text in file name
         *
         * If text is provided highlight it in file name
         * If text is empty remove highlight using the original file name
         *
         * @param {HTMLElement} element - file li item
         * @param {String} text - text to highlight
         */
        _highlightText: function (element, text) {
            let originalName = $(element).attr("fuw-original-file-name");

            let highlightedName = originalName;

            if (text) {
                let regex = new RegExp(text, 'gi'); // 'g' for global, 'i' for case-insensitive

                highlightedName = originalName.replace(regex, function (match) {
                    return "<span class='highlight'>" + match + "</span>";
                });
            }

            $(element).find("label span").html(highlightedName);
        },

        /**
         * Handle file selection
         *
         * @param {Event} e
         */
        _onFileSelect: function (e) {
            let selectedFilesNum = this._countSelectedFiles();

            this.fileSelectBtn.find("span").text(selectedFilesNum);
            this.el.find(".modal-footer").toggle(!!selectedFilesNum);
        },

        /**
         * Count selected files
         *
         * @returns {Number} - number of selected files
         */
        _countSelectedFiles: function () {
            return this.el.find('li.files--file-item input:checked').length;
        },

        /**
         * Cancel file selection
         *
         * @param {Event} e
         */
        _onCancelFileSelect: function (e) {
            this.el.find('li.files--file-item input:checked').prop('checked', false);
            this.el.find('li.files--file-item input:first').trigger('change');
        },

        _preventDropDefaults: function (e) {
            e.preventDefault()
            e.stopPropagation()
        },

        _highlightDropZone: function (e) {
            this.dropZoneArea.addClass('active');
        },

        _unhighlightDropZone: function (e) {
            this.dropZoneArea.removeClass('active');
        },

        _onDropFile: function (e) {
            console.log(e.originalEvent.dataTransfer.files)
        },

        _onFileSelected: function (e) {
            Array.from(e.target.files).forEach(file => {
                this._handleFile(file);
            })
        },

        _handleFile(file) {
            console.log(file)
        }
    };
});
