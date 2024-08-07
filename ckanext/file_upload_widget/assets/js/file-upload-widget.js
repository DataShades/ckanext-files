$.fn.isValid = function () {
    return this[0].checkValidity();
};

/**
 * Default .hide func add display: none to the element. We need to hide
 * the element by adding a class to it.
 */
$.fn.hideEl = function () {
    this[0].classList.add("hidden");
};

$.fn.showEl = function () {
    this[0].classList.remove("hidden");
};

$.fn.toggleEl = function (flag) {
    flag ? this.showEl() : this.hideEl();
};

/**
 * Generate UUID v4
 * @see https://stackoverflow.com/a/2117523
 *
 * We are generating UUID inside JS just to track the files that are uploaded
 * and to manipulate such files before we will have a real file id.
 *
 * @returns {String} - UUID v4
 */
function generateUUID4() {
    return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, (c) =>
        (
            +c ^
            (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (+c / 4)))
        ).toString(16)
    );
}

ckan.module("file-upload-widget", function ($, _) {
    "use strict";

    return {
        const: {
            fileInputButton: ".btn-file-input",
            urlInputButton: ".btn-url-input",
            mediaInputButton: ".btn-media-input",
            mainWindowBlock: ".fuw-main-window",
            urlInputBlock: ".fuw-url-input",
            mediaInputBlock: ".fuw-media-input",
            selectedBlock: ".fuw-selected-files",
            cancelBtn: ".fuw-cancel-btn",
            discardBtn: ".fuw-discard-btn",
            uploadAllSelectedBtn: ".fuw-upload-all-btn",
            closeSelectedFilesBtn: ".fuw-close-selected-btn",
            openSelectedFilesBtn: ".fuw-open-selected-btn",
            mediaSelectBtn: ".fuw-media-select-btn",
            dropZone: ".fuw-main-window__dropzone",
            selectedFiles: ".fuw-selected-files--list",
            mediaFilesContainer: ".fuw-media-input--files",
            mediaFilesEmptyContainer: ".fuw-media-input--empty",
            mediaWindowFooter: ".modal-footer--media",
            selectedFileItem: "li.fuw-selected-file",
            fileProgressContainer: ".fuw-selected-files--progress",
            uploadedFilesCounter: ".fuw-uploaded-files-counter",
            selectedFileControl: ".fuw-selected-files--file-control",

            attrFileName: "fuw-file-name",
            attrFileId: "fuw-file-id",
            attrFileSize: "fuw-file-size",
            attrFileType: "fuw-file-type",
            attrFileUploaded: "fuw-file-uploaded",
            attrContentType: "fuw-file-content-type",

            type: {
                file: "file",
                url: "url",
                media: "media",
            },
        },
        options: {
            instanceId: null,
            maxFiles: 0,
            disableUrl: false,
            disableMedia: false,
        },
        initialize: function () {
            $.proxyAll(this, /_/);

            if (!this.options.instanceId) {
                log.error("Widget instance ID is required");
                return;
            }

            // "disable" the limit if it's set to 0
            if (this.options.maxFiles === 0) {
                this.options.maxFiles = 9999;
            }

            window.fuwProgressBars = window.fuwProgressBars || {};
            window.fuwProgressBars[this.options.instanceId] = {};

            this.fileAdapter = new ckan.CKANEXT_FILES.adapters.Standard();
            this.urlAdapter = new ckan.CKANEXT_FILES.adapters.Standard({
                storage: "link",
            });

            this.lsSelectedFilesKey =
                "fuw-selected-files:" + this.options.instanceId;

            this._clearStoredData();

            this.fileInputBtn = this.el.find(this.const.fileInputButton);
            this.urlInputBtn = this.el.find(this.const.urlInputButton);
            this.mediaInputBtn = this.el.find(this.const.mediaInputButton);

            this.mainWindow = this.el.find(this.const.mainWindowBlock);
            this.urlWindow = this.el.find(this.const.urlInputBlock);
            this.mediaWindow = this.el.find(this.const.mediaInputBlock);
            this.mediaWindowFooter = this.el.find(this.const.mediaWindowFooter);
            this.selectionWindow = this.el.find(this.const.selectedBlock);

            this.fileIdsInput = this.el.find(
                `[name="${this.options.instanceId}"]`
            );
            this.fileSearchInput = this.el.find("#fuw-media-input--search");
            this.mediaSelectBtn = this.el.find(this.const.mediaSelectBtn);
            this.cancelFileSelectBtn = this.el.find(".btn-cancel-file-select");
            this.dropZoneArea = this.el.find(this.const.dropZone);
            this.fileInput = this.el.find('input[type="file"]');
            this.selectedFilesContainer = this.el.find(
                this.const.selectedFiles
            );
            this.urlImportBtn = this.urlWindow.find(".btn-url-import");
            this.mediaFilesContainer = this.el.find(
                this.const.mediaFilesContainer
            );
            this.mediaFilesEmptyContainer = this.el.find(
                this.const.mediaFilesEmptyContainer
            );
            this.uploadedFilesCounter = this.el.find(
                this.const.uploadedFilesCounter
            );

            this.cancelBtn = this.el.find(this.const.cancelBtn);
            this.discardBtn = this.el.find(this.const.discardBtn);
            this.closeSelectedFilesBtn = this.el.find(
                this.const.closeSelectedFilesBtn
            );
            this.openSelectedFilesBtn = this.el.find(
                this.const.openSelectedFilesBtn
            );
            this.uploadAllSelectedBtn = this.el.find(
                this.const.uploadAllSelectedBtn
            );

            // Bind events
            this.fileInputBtn.on("click", this._onFileInputTriggered);
            this.urlInputBtn.on("click", this._onUrlInputTriggered);
            this.cancelBtn.on("click", this._onCancelAction);
            this.fileSearchInput.on("input", this._onFileSearch);
            this.urlImportBtn.on("click", this._onUrlImport);

            this.mediaInputBtn.on("click", this._onMediaInputTriggered);
            this.mediaSelectBtn.on("click", this._onMediaFilesSelected);
            this.cancelFileSelectBtn.on("click", this._onCancelMediaFileSelect);

            this.discardBtn.on("click", this._onDiscardSelectedFiles);
            this.uploadAllSelectedBtn.on(
                "click",
                this._onUploadAllSelectedFiles
            );
            this.closeSelectedFilesBtn.on("click", this._onCloseSelectedFiles);
            this.fileInput.on("change", this._onFileSelected);
            this.openSelectedFilesBtn.on("click", this._onOpenSelectedFiles);

            this.fileAdapter.addEventListener(
                "progress",
                this._onUploadProgress
            );
            this.urlAdapter.addEventListener(
                "progress",
                this._onUploadProgress
            );
            this.fileAdapter.addEventListener("finish", this._onFinishUpload);
            this.urlAdapter.addEventListener("finish", this._onFinishUpload);
            this.fileAdapter.addEventListener("fail", this._onFailUpload);
            this.urlAdapter.addEventListener("fail", this._onFailUpload);

            // Bind events on non existing elements
            this.selectionWindow.on(
                "click",
                ".file-tile--file-remove",
                this._onRemoveSelectedFile
            );
            this.selectionWindow.on(
                "click",
                ".file-tile--file-upload",
                this._onUploadSelectedFile
            );
            this.mediaFilesContainer.on(
                "change",
                "li.files--file-item input",
                this._onMediaFileCheck
            );

            // Dropzone events
            this.dropZoneArea.on("drop", this._onDropFile);
            ["dragenter", "dragover", "dragleave", "drop"].forEach(
                (eventName) => {
                    this.dropZoneArea.on(eventName, this._preventDropDefaults);
                    $(document.body).on(eventName, this._preventDropDefaults);
                }
            );
            ["dragenter", "dragover"].forEach((eventName) => {
                this.dropZoneArea.on(eventName, this._highlightDropZone);
            });
            ["dragleave", "drop"].forEach((eventName) => {
                this.dropZoneArea.on(eventName, this._unhighlightDropZone);
            });

            // ON INIT
            this._recreateSelectedFiles();
            this._updateMediaGallery();
            this._updateUploadedFilesCounter(this._getUploadedFilesNum());

            // Disable URL input
            if (this.options.disableUrl) {
                this.urlInputBtn.hideEl();
                this.urlInputBtn.unbind();
                this.urlWindow.empty();
            }

            // Disable media input
            if (this.options.disableMedia) {
                this.mediaInputBtn.hideEl();
                this.mediaInputBtn.unbind();
                this.mediaWindow.empty();
            }

            // Default settings for iziToast
            iziToast.settings({
                timeout: 7000,
                transitionIn: "fadeInLeft",
                transitionOut: "fadeOutRight",
                messageColor: "#333",
                displayMode: 1,
            });
        },

        /**
         * Clear the file input value to allow selecting the same file
         *
         * @param {Event} e
         */
        _onFileInputTriggered: function (e) {
            if (this._isFileNumLimitReached(e)) {
                return e.preventDefault();
            }

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
            if (this._isFileNumLimitReached(e)) {
                return e.preventDefault();
            }

            this._enableUrlWindow();
            this.mainWindow.hideEl();
            this.cancelBtn.showEl();
        },

        /**
         * Handle media input trigger
         *
         * On media input trigger show media input block and hide main window
         *
         * @param {Event} e
         */
        _onMediaInputTriggered: function (e) {
            if (this._isFileNumLimitReached(e)) {
                return e.preventDefault();
            }

            this._enableMediaWindow();
            this.mainWindow.hideEl();
            this.cancelBtn.showEl();
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

            this.selectionWindow.hideEl();
            this.cancelBtn.hideEl();
            this.mainWindow.showEl();
        },

        _enableUrlWindow: function () {
            this.urlWindow.find("input").prop("disabled", false);
            this.urlWindow.showEl();
        },

        _disableUrlWindow: function () {
            this.urlWindow.find("input").prop("disabled", true);
            this.urlWindow.hideEl();
        },

        _enableMediaWindow: function () {
            this.mediaWindow.find("input").prop("disabled", false);
            this.mediaWindow.showEl();
        },

        _disableMediaWindow: function () {
            this.mediaWindow.find("input").prop("disabled", true);
            this.mediaWindowFooter.hideEl();
            this.mediaWindow.hideEl();
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

            this.mediaWindow.find("li.files--file-item").each((_, element) => {
                let title = $(element)
                    .find("label span.file-name")
                    .text()
                    .trim()
                    .toLowerCase();

                if (!!search && title.indexOf(search) === -1) {
                    $(element).hideEl();
                } else {
                    $(element).showEl();

                    isEmpty = false;

                    this._highlightText(element, search);
                }
            });

            let visibleFilesNum = this.el.find(
                "li.files--file-item:visible"
            ).length;

            if (isEmpty && !visibleFilesNum) {
                this.el.find(".fuw-media-input--empty").showEl();
                this.mediaFilesContainer.hideEl();
            } else {
                this.el.find(".fuw-media-input--empty").hideEl();
                this.mediaFilesContainer.showEl();
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
            let originalName = $(element).attr(this.const.attrFileName);

            let highlightedName = originalName;

            if (text) {
                let regex = new RegExp(text, "gi");

                highlightedName = originalName.replace(regex, function (match) {
                    return "<span class='highlight'>" + match + "</span>";
                });
            }

            $(element).find("label span.file-name").html(highlightedName);
        },

        /**
         * Handle media file item selection
         *
         * @param {Event} e
         */
        _onMediaFileCheck: function (e) {
            let checkedFilesNum = this.el
                .find("li.files--file-item input:checked")
                .not(`[name='${e.target.name}']`).length;

            if (
                this._isFileNumLimitReached(
                    e,
                    checkedFilesNum,
                    `You can't select more files than the limit: ${this.options.maxFiles}.`
                )
            ) {
                $(e.target).prop("checked", false);
                return e.preventDefault();
            }

            let selectedFilesNum = this._countSelectedMediaFiles();

            this.mediaSelectBtn.find("span").text(selectedFilesNum);
            this.el.find(".modal-footer").toggleEl(!!selectedFilesNum);
        },

        _onMediaFilesSelected: function (e) {
            let selectedFiles = this.el.find(
                "li.files--file-item input:checked"
            );

            // do extra check in case if someone smart will try to bypass the limit
            if (
                this._isFileNumLimitReached(
                    e,
                    selectedFiles.length - (this.options.maxFiles - this._calculateSelectedFilesNum()),
                    `You can't select more files than the limit: ${this.options.maxFiles}.`
                )
            ) {
                return e.preventDefault();
            }

            selectedFiles.each((_, element) => {
                let fileItem = $(element).parent("li");

                this._addFileItem(
                    fileItem.attr(this.const.attrFileId),
                    fileItem.attr(this.const.attrFileName),
                    fileItem.attr(this.const.attrFileSize),
                    this.const.type.media,
                    true,
                    fileItem.attr(this.const.attrContentType)
                );
            });

            this.el
                .find("li.files--file-item input:checked")
                .prop("checked", false);

            this._disableUrlWindow();
            this._disableMediaWindow();
            this.selectionWindow.showEl();

            this._updateFileIdsInput();
            this._toggleSelectedFilesButton();
        },

        /**
         * Count selected media files
         *
         * @returns {Number} - number of selected files
         */
        _countSelectedMediaFiles: function () {
            return this.el.find("li.files--file-item input:checked").length;
        },

        /**
         * Cancel file selection
         *
         * @param {Event} e
         */
        _onCancelMediaFileSelect: function (e) {
            this.el
                .find("li.files--file-item input:checked")
                .prop("checked", false);
            this.el.find("li.files--file-item input:first").trigger("change");
        },

        _preventDropDefaults: function (e) {
            e.preventDefault();
            e.stopPropagation();
        },

        _highlightDropZone: function (e) {
            this.dropZoneArea.addClass("active");
        },

        _unhighlightDropZone: function (e) {
            this.dropZoneArea.removeClass("active");
        },

        _onDropFile: function (e) {
            if (this._isFileNumLimitReached(e)) {
                return e.preventDefault();
            }

            let filesLimitLeft =
                this.options.maxFiles - this._calculateSelectedFilesNum();

            if (e.originalEvent.dataTransfer.items.length > filesLimitLeft) {
                iziToast.error({
                    message: `
                    You can't upload more files than the limit (${this.options.maxFiles}).
                    Select not more than ${filesLimitLeft} file(s).`,
                });

                return e.preventDefault();
            }

            // add dropped files to the file input
            let dt = new DataTransfer();

            // existing files
            let file_list = this.fileInput.get(0).files;

            for (let i = 0; i < file_list.length; i++) {
                dt.items.add(file_list[i]);
            }

            Array.from(e.originalEvent.dataTransfer.files).forEach((file) => {
                file.id = generateUUID4();
                file.fuw_type = this.const.type.file;
                this._handleFile(file);

                dt.items.add(file);
            });

            this.fileInput.get(0).files = dt.files;
        },

        _onFileSelected: function (e) {
            Array.from(e.target.files).forEach((file) => {
                file.id = generateUUID4();
                file.fuw_type = this.const.type.file;
                this._handleFile(file);
            });
        },

        _onUrlImport: function (e) {
            if (this._isFileNumLimitReached(e)) {
                return e.preventDefault();
            }

            let fileUrl = this.urlWindow.find("input").val();

            if (fileUrl.length && this.urlWindow.find("input").isValid()) {
                this.urlWindow.find("input").val("");
                this._handleFile({
                    id: generateUUID4(),
                    name: fileUrl,
                    size: 0,
                    fuw_type: this.const.type.url,
                });
            } else {
                this.urlWindow.find("input").focus();
                this.urlWindow.find("input").get(0).reportValidity();
            }
        },

        _handleFile: function (file) {
            this._addFileItem(
                file.id,
                file.name,
                file.size,
                file.fuw_type,
                false,
                file.type
            );

            this._disableUrlWindow();
            this._disableMediaWindow();

            this._toggleSelectedFilesButton();
            this.selectionWindow.showEl();
        },

        _addFileItem: function (
            fileId,
            fileName,
            fileSize,
            fileType = this.const.type.file,
            fileUploaded = false,
            fileContentType
        ) {
            const files =
                this.getDataFromLocalStorage(this.lsSelectedFilesKey) || [];
            const fileItem = $(
                this._selectedFileItemTemplate(
                    fileId,
                    fileName,
                    fileSize,
                    fileType,
                    fileUploaded,
                    fileContentType
                )
            );

            for (const file of files) {
                if (
                    (file.id && file.id === fileId) ||
                    (fileType == this.const.type.url && file.name === fileName)
                ) {
                    iziToast.error({
                        title: fileName,
                        message: `File has already been selected.`,
                    });
                    return;
                }
            }

            files.push({
                id: fileId,
                name: fileName,
                size: fileSize,
            });

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
            if (bytes === 0) return "0 Bytes";
            const k = 1024;
            const sizes = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"];
            const i = Math.floor(Math.log(bytes) / Math.log(k));

            return (
                parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
            );
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

            let files =
                this.getDataFromLocalStorage(this.lsSelectedFilesKey) || [];
            files = files.filter(
                (file) => file.name !== fileEl.attr(this.const.attrFileName)
            );

            fileEl.remove();

            // Remove file from the file input
            if (
                fileEl.attr(this.const.attrFileType) === this.const.type.file &&
                !fileEl.attr(this.const.attrFileId)
            ) {
                let dt = new DataTransfer();
                let file_list = this.fileInput.get(0).files;

                for (let i = 0; i < file_list.length; i++) {
                    if (
                        file_list[i].name !=
                        fileEl.attr(this.const.attrFileName)
                    ) {
                        dt.items.add(file_list[i]);
                    }
                }

                this.fileInput.get(0).files = dt.files;
            }

            this.storeDataInLocalStorage(this.lsSelectedFilesKey, files);

            let selectedFiles = this._calculateSelectedFilesNum() > 0;
            this._toggleFileSelectionWindow(selectedFiles);
            this._toggleSelectedFilesButton();

            // we want to update the file ids input only if the file was uploaded,
            // otherwise we woudn't save it in a file ids input
            if (fileEl.attr(this.const.attrFileUploaded) === "true") {
                this._updateFileIdsInput();
            }
        },

        _calculateSelectedFilesNum: function () {
            return this.el.find(this.const.selectedFileItem).length;
        },

        _toggleFileSelectionWindow: function (flag) {
            this.selectionWindow.toggleEl(flag);

            if (!flag) {
                this.mainWindow.showEl();
                this.cancelBtn.hideEl();
            }
        },

        _toggleSelectedFilesButton: function (fileNum = null) {
            let selectedFiles = fileNum
                ? fileNum
                : this._calculateSelectedFilesNum();

            this.openSelectedFilesBtn.find("span").text(selectedFiles);
            this.openSelectedFilesBtn.toggleEl(selectedFiles);
        },

        _onUploadSelectedFile: function (e) {
            let fileItem = $(e.target).closest(this.const.selectedFileItem);

            if (fileItem.attr(this.const.attrFileUploaded) === "true") {
                return;
            }

            fileItem.find(this.const.selectedFileControl).hideEl();
            this._uploadFile(fileItem);
        },

        /**
         * Upload file
         *
         * @param {HTMLElement} fileItem - file item to upload
         */
        _uploadFile(fileItem) {
            let fileType = fileItem.attr(this.const.attrFileType);
            let fileId = fileItem.attr(this.const.attrFileId);
            let fileProgressContainer = fileItem.find(
                this.const.fileProgressContainer
            );

            window.fuwProgressBars[this.options.instanceId][fileId] =
                new ProgressBar.Line(fileProgressContainer.get(0), {
                    easing: "easeInOut",
                });
            window.fuwProgressBars[this.options.instanceId][fileId].animate(0);

            if (fileType === this.const.type.url) {
                let url = fileItem.attr(this.const.attrFileName);
                // use url both as a content and file name
                const file = new File([url], url, {
                    type: "text/plain",
                });

                file.fuw_type = this.const.type.url;
                file.id = fileId;
                this.urlAdapter.upload(file, {});
            } else if (fileType === this.const.type.file) {
                this.fileAdapter.upload(this._getFileObjectById(fileId), {});
            }
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
        _selectedFileItemTemplate: function (
            fileId,
            fileName,
            fileSize,
            fileType,
            fileUploaded,
            fileContentType = "text/plain"
        ) {
            let mungedFileName = this._truncateFileName(fileName);
            let formattedFileSize = this._formatFileSize(fileSize);
            let isImageFile = this._isImageContentType(fileContentType);
            let fileIconType = this._getFAIconBasedOnFileType(fileContentType);

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
                        ${
                            isImageFile
                                ? `<object data="${this._createUrlForImagePreview(
                                      fileId,
                                      fileUploaded
                                  )}" type="${fileContentType}"></object>`
                                : ""
                        }
                        ${isImageFile ? "" : `<i class="${fileIconType}"></i>`}
                    </div>
                </div>
                <div class="fuw-selected-files--file-info">
                    <div class="fuw-selected-files--file-name">${mungedFileName}</div>
                    <div class="fuw-selected-files--file-size">${formattedFileSize}</div>
                </div>
                <div class="fuw-selected-files--file-control">
                    ${
                        !fileUploaded
                            ? '<i class="fa-solid fa-upload file-tile--file-upload"></i>'
                            : ""
                    }
                    <i class="fa-solid fa-times file-tile--file-remove"></i>
                </div>
                <div class="fuw-selected-files--progress"></div>
            </li>
            `;
        },

        /**
         * Create a URL for an image file preview. If it's uploaded, we
         * are using the file download endpoint, otherwise we are using the
         * URL.createObjectURL(file) method.
         *
         * @param {String} fileId - file id
         * @param {Boolean} isUploaded - is file uploaded
         *
         * @returns {String} - URL for the image preview
         */
        _createUrlForImagePreview: function (fileId, isUploaded) {
            if (isUploaded) {
                return `/file/download/${fileId}`;
            }

            let file = this._getFileObjectById(fileId);

            if (!file) {
                // TODO: maybe we need a placeholder in this case?
                // this shouldn't happen in a normal situation...
                return "";
            }

            return URL.createObjectURL(file);
        },

        /**
         * Retrieve the File object from a file input by a pseudo file ID
         * we've generated.
         *
         * @param {String} fileId - file id
         * @returns {File | null} - file object or null
         */
        _getFileObjectById: function (fileId) {
            let file = null;
            let files = this.fileInput.get(0).files;

            for (let i = 0; i < files.length; i++) {
                if (files[i].id !== fileId) {
                    continue;
                }

                file = files[i];
                break;
            }

            return file;
        },

        /**
         * Get a file item element by its ID
         *
         * @param {String} fileId - file element ID
         *
         * @returns {HTMLElement | null} - file element
         */
        _getFileItemById: function (fileId) {
            return this.el.find(`li[fuw-file-id="${fileId}"]`);
        },

        /**
         * Triggers when user want to discard all selected files for upload.
         *
         * We have to remove all files from the file input, clear the stored data
         * so user would be able to select same files again.
         *
         * @param {Event} e - event
         */
        _onDiscardSelectedFiles: function (e) {
            // remove all files from the file input
            this.fileInput.get(0).files = new DataTransfer().files;

            this._clearStoredData();

            this.el.find(this.const.selectedFileItem).remove();

            this._onCloseSelectedFiles();
            this._toggleSelectedFilesButton();
        },

        /**
         * Triggers when user wants to upload all selected files. This function
         * will upload only files marked as not uploaded.
         *
         * @param {Event} e - event
         */
        _onUploadAllSelectedFiles: function (e) {
            let files = this.el.find(
                `${this.const.selectedFileItem}[${this.const.attrFileUploaded}="false"]`
            );

            for (let i = 0; i < files.length; i++) {
                this._uploadFile($(files[i]));
            }
        },

        /**
         * Triggers when user wants to close the selected files list
         *
         * @param {Event} e - event
         */
        _onCloseSelectedFiles: function (e) {
            this.selectionWindow.hideEl();
            this.cancelBtn.hideEl();
            this.urlWindow.hideEl();
            this.mediaWindow.hideEl();
            this.mainWindow.showEl();
        },

        /**
         * Triggers when user want to open a list of selected files
         *
         * @param {Event} e - event
         */
        _onOpenSelectedFiles: function (e) {
            this.selectionWindow.showEl();
        },

        /**
         * Count files we've selected. This is not the same, as selected
         * media files. Those files are the ones that will be sent to the server
         * and saved for the field.
         *
         * @returns {Number} - number of selected files
         */
        _countSelectedUploadFiles: function () {
            return this.el.find("li.files--file-item input:checked").length;
        },

        /**
         * Triggers when the file upload is in progress.
         * We have to update the progress bar for the file.
         *
         * @param {Event} e - event
         */
        _onUploadProgress: function (e) {
            let progressbar =
                window.fuwProgressBars[this.options.instanceId][
                    e.detail.file.id
                ];

            if (progressbar) {
                progressbar.animate(e.detail.loaded / e.detail.total);
            }
        },

        /**
         * Triggers when the file upload is finished.
         *
         * We have to remove the progress bar and replace the file id with the
         * real file id. Also, we're updating some attributes for the file item.
         *
         * And we have to update the media gallery to represent the current state
         * of the user file list.
         *
         * @param {Event} e - event
         */
        _onFinishUpload: function (e) {
            let progressBar =
                window.fuwProgressBars[this.options.instanceId][
                    e.detail.file.id
                ];

            if (progressBar) {
                progressBar.destroy();
            }

            this._removeUploadButtonForFile(e.detail.file.id);
            this._getFileItemById(e.detail.file.id)
                .find(this.const.selectedFileControl)
                .showEl();

            this._replaceWithUploadedFileId(
                e.detail.file.id,
                e.detail.result.id
            );
            this._updateUploadedFileSize(
                e.detail.result.id,
                e.detail.result.size
            );

            this._updateFileIdsInput();
            this._updateMediaGallery();

            iziToast.success({
                title: e.detail.result.name,
                message: "File has been uploaded.",
            });
        },

        /**
         * Remove upload button for a file after a successful upload
         *
         * @param {String} fileId - file id
         */
        _removeUploadButtonForFile: function (fileId) {
            this.el
                .find(`li[fuw-file-id="${fileId}"] .file-tile--file-upload`)
                .remove();
        },

        /**
         * Replace a fake file uuid4 with the real file id after a success upload
         *
         * @param {String} currentId - current file id
         * @param {String} uploadedId - uploaded file id
         */
        _replaceWithUploadedFileId: function (currentId, uploadedId) {
            let fileItem = this.el.find(`li[fuw-file-id="${currentId}"]`);

            fileItem.attr(this.const.attrFileId, uploadedId);
            fileItem.attr(this.const.attrFileUploaded, true);
        },

        /**
         * Update uploaded file size
         *
         * @param {String} fileId - file id
         * @param {Number} fileSize - file size
         */
        _updateUploadedFileSize: function (fileId, fileSize) {
            let fileItem = this.el.find(`li[fuw-file-id="${fileId}"]`);

            fileItem.attr(this.const.attrFileSize, fileSize);
            fileItem
                .find(".fuw-selected-files--file-size")
                .text(this._formatFileSize(fileSize));
        },

        /**
         * Update file ids input with the selected files.
         *
         * We are doing it on:
         *  - selectin a file from media gallery
         *  - removing a selected file
         *  - uploading a file
         */
        _updateFileIdsInput: function () {
            let files = this.el.find(
                `${this.const.selectedFileItem}[${this.const.attrFileUploaded}="true"]`
            );

            let fileIds = files.map((_, element) => {
                return $(element).attr(this.const.attrFileId);
            });

            this.fileIdsInput.val(fileIds.get().join(","));
            this._updateUploadedFilesCounter(this._getUploadedFilesNum());
        },

        /**
         * Recreate selected files from the file ids input on script init
         */
        _recreateSelectedFiles: function () {
            let fileIdsVal = this.fileIdsInput.val();

            if (!fileIdsVal) {
                return;
            }

            let fileIds = this.fileIdsInput.val().split(",");

            fileIds.forEach((fileId) => {
                this.sandbox.client.call(
                    "GET",
                    "files_file_show",
                    `?id=${fileId}`,
                    (data) => {
                        this._addFileItem(
                            data.result.id,
                            data.result.name,
                            data.result.size,
                            this.const.type.file,
                            true,
                            data.result.content_type
                        );
                    },
                    (resp) => {
                        if (
                            resp.responseJSON.error.message ===
                            "Not found: file"
                        ) {
                            this._removeMissingFile(fileId);
                        }

                        iziToast.error({
                            message: `File with id ${fileId} was not found.`,
                        });
                    }
                );
            });

            this._toggleSelectedFilesButton(fileIds.length);
        },

        /**
         * Triggers when the file upload fails for some reason.
         *
         * We need to kill the progress bar and show some error message.
         *
         * @param {Event} e - event
         */
        _onFailUpload: function (e) {
            iziToast.error({
                message: "An error occurred while uploading the file.",
            });

            Object.entries(e.detail.reasons).forEach(([key, value]) => {
                if (key.startsWith("__")) {
                    return;
                }

                iziToast.error({ message: `${key}: ${value}` });
            });

            let progressBar =
                window.fuwProgressBars[this.options.instanceId][
                    e.detail.file.id
                ];

            if (progressBar) {
                progressBar.destroy();
            }

            this._getFileItemById(e.detail.file.id)
                .find(this.const.selectedFileControl)
                .showEl();
        },

        /**
         * If the file was removed from the server, we need to remove it from
         * the file ids input and the selected files list.
         *
         * This shouldn't be a really common situation, but it can happen if
         * the file was removed from the server by an admin. Or we're syndicating
         * the data from another CKAN instance and the file with the same id
         * doesn't exist for an obvious reason.
         *
         * @param {String} fileId - file id
         */
        _removeMissingFile: function (fileId) {
            let fileIds = this.fileIdsInput.val().split(",");

            fileIds = fileIds.filter((id) => id !== fileId);

            this.fileIdsInput.val(fileIds.join(","));

            let fileEl = this.el.find(`li[fuw-file-id="${fileId}"]`);
            fileEl.remove();
            this._toggleSelectedFilesButton();
        },

        /**
         * Populate media gallery with files on a script init and when we
         * upload a new file
         */
        _updateMediaGallery: function () {
            this.sandbox.client.call(
                "GET",
                "files_file_scan",
                "?rows=1000", // TODO: probably it's better to implement
                // autocomplete and do not fetch all files at once
                (data) => {
                    let mediaFiles = data.result.results;

                    this.mediaFilesContainer.toggleEl(mediaFiles.length);
                    this.mediaFilesEmptyContainer.toggleEl(
                        mediaFiles.length === 0
                    );

                    this.mediaFilesContainer.empty();

                    data.result.results.forEach((file) => {
                        this.mediaFilesContainer.append(
                            $(
                                this._mediaFileItemTemplate(
                                    file.id,
                                    file.name,
                                    file.size,
                                    file.content_type
                                )
                            )
                        );
                    });
                },
                (resp) => {
                    iziToast.error({ message: resp });
                }
            );
        },

        /**
         * Create a template for the media file item HTML element
         *
         * @param {String} fileId - file id
         * @param {String} fileName - file name
         * @param {Number} fileSize - file size
         * @param {String} fileContentType - file content type
         *
         * @returns {String} - template for the media file item
         */
        _mediaFileItemTemplate: function (
            fileId,
            fileName,
            fileSize,
            fileContentType
        ) {
            let fileIconType = this._getFAIconBasedOnFileType(fileContentType);
            let mungedFileName = this._truncateFileName(fileName);
            let formattedFileSize = this._formatFileSize(fileSize);
            let isImageFile = this._isImageContentType(fileContentType);

            let inputId = `file-item-${this.options.instanceId}-${fileId}`;

            return `
                <li
                    class="files--file-item"
                    fuw-file-name="${fileName}"
                    fuw-file-id="${fileId}"
                    fuw-file-size="${fileSize}"
                    fuw-file-type="${this.const.type.media}"
                    fuw-file-content-type="${fileContentType}">
                    <input type="checkbox" name="${inputId}" id="${inputId}">
                    <label for="${inputId}">
                        ${
                            isImageFile
                                ? `<object data="/file/download/${fileId}" type="${fileContentType}"></object>`
                                : ""
                        }
                        ${isImageFile ? "" : `<i class="${fileIconType}"></i>`}
                        <span class="file-name">${mungedFileName}</span>
                        <span class="file-size text-muted">(${formattedFileSize})</span>
                    </label>
                </li>
            `;
        },

        /**
         * Get font awesome icon class based on a file content type
         *
         * @param {String} contentType - file content type
         * @returns {String} - font awesome icon class
         */
        _getFAIconBasedOnFileType: function (contentType) {
            let iconType = "fa-file";

            if (contentType.startsWith("image")) {
                iconType = "fa-file-image";
            } else if (contentType.startsWith("audio")) {
                iconType = "fa-file-audio";
            } else if (contentType.startsWith("video")) {
                iconType = "fa-file-video";
            } else if (contentType.startsWith("text")) {
                iconType = "fa-file-alt";
            } else if (contentType.startsWith("application/pdf")) {
                iconType = "fa-file-pdf";
            } else if (contentType.startsWith("application/vnd.ms-excel")) {
                iconType = "fa-file-excel";
            } else if (contentType.startsWith("application/zip")) {
                iconType = "fa-file-archive";
            } else if (
                contentType.startsWith("application/vnd.ms-powerpoint")
            ) {
                iconType = "fa-file-powerpoint";
            } else if (
                contentType.startsWith("application/msword") ||
                contentType.startsWith(
                    "application/vnd.openxmlformats-officedocument"
                )
            ) {
                iconType = "fa-file-word";
            }

            return `fa ${iconType}`;
        },

        /**
         * Update uploaded files counter on an upload button
         *
         * @param {Number} count - number of uploaded files
         */
        _updateUploadedFilesCounter: function (count) {
            this.uploadedFilesCounter.toggleEl(count);
            this.uploadedFilesCounter.text(count);
        },

        /**
         * Check if the content type is an image
         *
         * @param {String} contentType - file content type
         *
         * @returns {Boolean} - is content type an image
         */
        _isImageContentType: function (contentType) {
            return contentType.startsWith("image");
        },

        /**
         * Calculate the number of selected files that will be saved upon form submit
         *
         * @returns {Number} - number of selected files
         */
        _getUploadedFilesNum: function () {
            return this.fileIdsInput
                .val()
                .split(",")
                .filter((i) => i).length;
        },

        /**
         * Check if the maximum number of files is reached
         *
         * @param {Event} e - event
         * @param {Number | null} selectedNum - number of selected files. We're using
         * it for media checkbox selection
         * @param {String | null} message - alternative error message
         *
         * @returns {Boolean} - is file number limit reached flag
         */
        _isFileNumLimitReached: function (
            e,
            selectedNum = null,
            message = null
        ) {
            if (selectedNum < 0) {
                return false;
            }

            if (
                selectedNum ||
                this._calculateSelectedFilesNum() >= this.options.maxFiles
            ) {
                e.preventDefault();

                iziToast.error({
                    message:
                        message ||
                        `You have reached the maximum number of files (${this.options.maxFiles})`,
                });

                return true;
            }

            return false;
        },
    };
});
