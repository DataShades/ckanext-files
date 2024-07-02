$.fn.isValid = function () {
    return this[0].checkValidity()
}

$.fn.hideEl = function () {
    this[0].addClass('hidden');
}

$.fn.showEl = function () {
    this[0].removeClass('hidden');
}

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
            selectedBlock: '.fuw-selected-files',
            cancelBtn: '.fuw-cancel-btn',
            cancelAllSelectedBtn: '.btn-cancel-all',
            closeSelectedFilesBtn: '.fuw-close-selected-btn',
            openSelectedFilesBtn: '.fuw-open-selected-btn',
            dropZone: '.fuw-main-window__dropzone',
            selectedFiles: '.fuw-selected-files--list',
            mediaWindowFooter: '.modal-footer--media',
            selectedFileItem: 'li.fuw-selected-file',
        },
        options: {
            instanceId: null,
        },
        initialize: function () {
            $.proxyAll(this, /_/);

            if (!this.options.instanceId) {
                log.error("Widget instance ID is required");
                return
            };

            this.lsSelectedFilesKey = 'fuw-selected-files:' + this.options.instanceId,

            this._clearStoredData();

            this.fileInputBtn = this.el.find(this.const.fileInputButton);
            this.urlInputBtn = this.el.find(this.const.urlInputButton);
            this.mediaInputBtn = this.el.find(this.const.mediaInputButton);

            this.mainWindow = this.el.find(this.const.mainWindowBlock);
            this.urlWindow = this.el.find(this.const.urlInputBlock);
            this.mediaWindow = this.el.find(this.const.mediaInputBlock);
            this.mediaWindowFooter = this.mediaWindow.find(this.const.mediaWindowFooter);
            this.selectionWindow = this.el.find(this.const.selectedBlock);

            this.fileSearchInput = this.el.find('#fuw-media-input--search');
            this.fileSelectBtn = this.el.find('.btn-file-select');
            this.cancelFileSelectBtn = this.el.find('.btn-cancel-file-select');
            this.dropZoneArea = this.el.find(this.const.dropZone);
            this.fileInput = this.el.find('input[type="file"]');
            this.selectedFilesContainer = this.el.find(this.const.selectedFiles);
            this.urlImportBtn = this.urlWindow.find(".btn-url-import");

            this.cancelBtn = this.el.find(this.const.cancelBtn);
            this.cancelAllSelectedBtn = this.el.find(this.const.cancelAllSelectedBtn);
            this.closeSelectedFilesBtn = this.el.find(this.const.closeSelectedFilesBtn);
            this.openSelectedFilesBtn = this.el.find(this.const.openSelectedFilesBtn);

            // Bind events
            this.fileInputBtn.on("click", this._onFileInputTriggered);
            this.urlInputBtn.on("click", this._onUrlInputTriggered);
            this.mediaInputBtn.on("click", this._onMediaInputTriggered);
            this.cancelBtn.on("click", this._onCancelAction);
            this.fileSearchInput.on('input', this._onFileSearch);
            this.el.find('li.files--file-item input').on('change', this._onMediaFileSelect);
            this.cancelFileSelectBtn.on("click", this._onCancelMediaFileSelect);
            this.urlImportBtn.on('click', this._onUrlImport);
            this.fileSelectBtn.on('click', this._onMediaFileSelected);
            this.cancelAllSelectedBtn.on('click', this._onCancelAllSelectedFiles);
            this.closeSelectedFilesBtn.on('click', this._onCloseSelectedFiles);
            this.fileInput.on('change', this._onFileSelected);
            this.openSelectedFilesBtn.on('click', this._onOpenSelectedFiles);

            // Bind events on non existing elements
            $("body").on("click", ".file-tile--file-remove", this._onRemoveSelectedFile);

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
         * Clear the file input value to allow selecting the same file
         *
         * @param {Event} e
         */
        _onFileInputTriggered: function (e) {
            this.fileInput.val("");
        },

        /**
         * Handle url input trigger
         *
         * On url input trigger show url input block and hide main window
         *
         * @param {Event} e
         */
        _onUrlInputTriggered: function (e) {
            this._enableUrlWindow();
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
            this._enableMediaWindow();
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
            this._disableUrlWindow();
            this._disableMediaWindow();

            this.selectionWindow.hide();
            this.cancelBtn.hide();
            this.mainWindow.show();
        },

        _enableUrlWindow: function () {
            this.urlWindow.find("input").prop("disabled", false);
            this.urlWindow.show();
        },

        _disableUrlWindow: function () {
            this.urlWindow.find("input").prop("disabled", true);
            this.urlWindow.hide();
        },

        _enableMediaWindow: function () {
            this.mediaWindow.find("input").prop("disabled", false);
            this.mediaWindow.show();
        },

        _disableMediaWindow: function () {
            this.mediaWindow.find("input").prop("disabled", true);
            this.mediaWindowFooter.hide();
            this.mediaWindow.hide();
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
                let title = $(element).find("label span.file-name").text().trim().toLowerCase();

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
            let originalName = $(element).attr("fuw-file-name");

            let highlightedName = originalName;

            if (text) {
                let regex = new RegExp(text, 'gi');

                highlightedName = originalName.replace(regex, function (match) {
                    return "<span class='highlight'>" + match + "</span>";
                });
            }

            $(element).find("label span.file-name").html(highlightedName);
        },

        /**
         * Handle file selection
         *
         * @param {Event} e
         */
        _onMediaFileSelect: function (e) {
            let selectedFilesNum = this._countSelectedMediaFiles();

            this.fileSelectBtn.find("span").text(selectedFilesNum);
            this.el.find(".modal-footer").toggle(!!selectedFilesNum);
        },

        _onMediaFileSelected: function (e) {
            this.el.find('li.files--file-item input:checked').each((_, element) => {
                let fileItem = $(element).parent("li");

                this._addFileItem(
                    fileItem.attr("fuw-file-id"),
                    fileItem.attr("fuw-file-name"),
                    fileItem.attr("fuw-file-size")
                );
            });

            this._disableUrlWindow();
            this._disableMediaWindow();
            this.selectionWindow.show();
        },

        /**
         * Count selected media files
         *
         * @returns {Number} - number of selected files
         */
        _countSelectedMediaFiles: function () {
            return this.el.find('li.files--file-item input:checked').length;
        },

        /**
         * Cancel file selection
         *
         * @param {Event} e
         */
        _onCancelMediaFileSelect: function (e) {
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
            Array.from(e.originalEvent.dataTransfer.files).forEach(file => {
                file.id = "";
                file.fuw_type = "file";
                this._handleFile(file);
            });
        },

        _onFileSelected: function (e) {
            console.log(e);
            Array.from(e.target.files).forEach(file => {
                file.id = "";
                file.fuw_type = "file";
                this._handleFile(file);
            })
        },

        _onUrlImport: function (e) {
            let fileUrl = this.urlWindow.find("input").val();

            if (fileUrl.length && this.urlWindow.find("input").isValid()) {
                this.urlWindow.find("input").val("");
                this._handleFile({ id: "", name: fileUrl, size: 0, fuw_type: "url" });
            } else {
                this.urlWindow.find("input").focus();
                this.urlWindow.find("input").get(0).reportValidity();
            }

        },

        _handleFile: function (file) {
            this._addFileItem(file.id, file.name, file.size, file.fuw_type);

            this._disableUrlWindow();
            this._disableMediaWindow();
            this.selectionWindow.show();
        },

        _addFileItem: function (fileId, fileName, fileSize, fileType = "file", fileUploaded = false) {
            const files = this.getDataFromLocalStorage(this.lsSelectedFilesKey) || [];
            const fileItem = $(this._selectedFileItemTemplate(
                fileId,
                fileName,
                fileSize,
                fileType,
                fileUploaded
            ));

            for (const file of files) {
                if (file.name === fileName) {
                    alert("File already selected");
                    return;
                }
            }

            files.push({ id: fileId, name: fileName, size: fileSize });

            this.storeDataInLocalStorage(this.lsSelectedFilesKey, files);
            this.selectedFilesContainer.append(fileItem);
        },

        /**
         * Format file size in human readable format
         *
         * @param {Number} bytes
         *
         * @returns {String} formatted file size
         */
        _formatFileSize: function (bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));

            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },

        /**
         * Truncate file name if it is longer than the maximum length
         *
         * @param {String} fileName - file name
         * @param {Number} maxLength - maximum length of the file name
         *
         * @returns {String} truncated file name
         */
        _truncateFileName: function (fileName, maxLength = 35) {
            // Ensure the file name is longer than the maximum length
            if (fileName.length <= maxLength) {
                return fileName;
            }

            // Calculate lengths for the beginning and end parts
            const keepLength = Math.floor((maxLength - 3) / 2);
            const start = fileName.substring(0, keepLength);
            const end = fileName.substring(fileName.length - keepLength);

            // Return the truncated file name with ellipsis
            return `${start}...${end}`;
        },

        _onRemoveSelectedFile: function (e) {
            let fileEl = $(e.target).closest(this.const.selectedFileItem);

            let files = this.getDataFromLocalStorage(this.lsSelectedFilesKey) || [];
            files = files.filter(file => file.name !== fileEl.attr("fuw-file-name"));

            fileEl.remove();

            // Remove file from the file input
            if (fileEl.attr("fuw-file-type") === "file" && !fileEl.attr("fuw-file-id")) {
                let dt = new DataTransfer();
                let file_list = this.fileInput.get(0).files;

                for (let i = 0; i < file_list.length; i++) {
                    if (file_list[i].name != fileEl.attr("fuw-file-name")) {
                        dt.items.add(file_list[i]);
                    };

                }

                this.fileInput.get(0).files = dt.files;
            };

            this.storeDataInLocalStorage(this.lsSelectedFilesKey, files);

            let selectedFiles = this._calculateSelectedFilesNum() > 0;
            this._toggleFileSelectionWindow(selectedFiles);
            this._toggleSelectedFilesButton(selectedFiles);
        },

        _calculateSelectedFilesNum: function () {
            return this.el.find(this.const.selectedFileItem).length;
        },

        _toggleFileSelectionWindow: function (flag) {
            this.selectionWindow.toggle(flag);

            if (!flag) {
                this.mainWindow.show();
                this.cancelBtn.hide();
            }
        },

        _toggleSelectedFilesButton: function (flag) {
            this.openSelectedFilesBtn.toggle(flag);
        },

        /**
         * Get data from a local storage
         *
         * @param {String} key - key to get data from local storage
         * @returns {Object | null} - data from local storage
         */
        getDataFromLocalStorage: function (key) {
            const jsonString = localStorage.getItem(key);

            if (jsonString) {
                return JSON.parse(jsonString);
            }

            return null;
        },

        /**
         * Store data in local storage
         *
         * @param {String} key - key to store data in a local storage
         * @param {Object | Array} data - data retrieved from the local storage
         */
        storeDataInLocalStorage: function (key, data) {
            localStorage.setItem(key, JSON.stringify(data));
        },

        /**
         * When we initialize the widget, we need to clear the stored data
         * in the local storage
         */
        _clearStoredData: function () {
            localStorage.removeItem(this.lsSelectedFilesKey);
        },

        /**
         * Create a template for the selected file element
         *
         * @param {String} fileId - file id
         * @param {String} fileName - file name
         * @param {Number} fileSize - file size
         * @param {String} fileType - file type
         * @param {Boolean} fileUploaded - is file already uploaded
         *
         * @returns {String} - template for the selected file element
         */
        _selectedFileItemTemplate: function (fileId, fileName, fileSize, fileType, fileUploaded) {
            let mungedFileName = this._truncateFileName(fileName);
            let formattedFileSize = this._formatFileSize(fileSize);

            return `<li
                class="fuw-selected-files--file-item-wrapper fuw-selected-file"
                fuw-file-name="${fileName}"
                fuw-file-id="${fileId}"
                fuw-file-size="${fileSize}"
                fuw-file-type="${fileType}"
                fuw-file-uploaded="${fileUploaded}"
                >
                <div class="fuw-selected-files--file-preview">
                    <div class="file-tile--file-icon">
                        <svg aria-hidden="true" focusable="false" width="25" height="25" viewBox="0 0 25 25">
                            <g fill="#A7AFB7" fill-rule="nonzero">
                                <path d="M5.5 22a.5.5 0 0 1-.5-.5v-18a.5.5 0 0 1 .5-.5h10.719a.5.5 0 0 1 .367.16l3.281 3.556a.5.5 0 0 1 .133.339V21.5a.5.5 0 0 1-.5.5h-14zm.5-1h13V7.25L16 4H6v17z"></path>
                                <path d="M15 4v3a1 1 0 0 0 1 1h3V7h-3V4h-1z"></path>
                            </g>
                        </svg>
                    </div>
                </div>
                <div class="fuw-selected-files--file-info">
                    <div class="fuw-selected-files--file-name">${mungedFileName}</div>
                    <div class="fuw-selected-files--file-size">${formattedFileSize}</div>
                </div>
                ${!fileUploaded ? '<i class="fa-solid fa-upload file-tile--file-upload"></i>' : ""}
                <i class="fa-solid fa-times file-tile--file-remove"></i>
            </li>
            `
        },

        _onCancelAllSelectedFiles: function (e) {
            // remove all files from the file input
            this.fileInput.get(0).files = new DataTransfer().files;

            this._clearStoredData();

            this.el.find(this.const.selectedFileItem).remove();

            this._onCloseSelectedFiles();
        },

        _onCloseSelectedFiles: function (e) {
            // this._onCancelAction();
            this.selectionWindow.hide();
        },

        _onOpenSelectedFiles: function (e) {
            this.selectionWindow.show();
        },


        /**
         * Count files we've selected. This is not the same, as selected
         * media files. Those files are the ones that will be sent to the server
         * and saved for the field.
         *
         * @returns {Number} - number of selected files
         */
        _countSelectedUploadFiles: function () {
            return this.el.find('li.files--file-item input:checked').length;
        },
    };
});
