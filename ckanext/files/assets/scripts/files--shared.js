"use strict";
var ckan;
(function (ckan) {
    let CKANEXT_FILES;
    (function (CKANEXT_FILES) {
        CKANEXT_FILES.topics = {
            addFileToQueue: "ckanext:files:queue:file:add",
            restoreFileInQueue: "ckanext:files:queue:file:restore",
            queueItemUploaded: "ckanext:files:queue:file:uploaded",
        };
        CKANEXT_FILES.defaultSettings = {
            storage: "default",
        };
        function upload(file, uploader = new adapters.Standard()) {
            return uploader.upload(file);
        }
        function makeUploader(adapter, ...options) {
            const factory = adapters[adapter];
            if (!factory) {
                throw new Error(`Uploader ${adapter} is not registered`);
            }
            return new factory(...options);
        }
        ckan.sandbox.extend({ files: { upload, makeUploader } });
        let adapters;
        (function (adapters) {
            class Base extends EventTarget {
                static defaultSettings = {};
                settings;
                sandbox;
                csrfToken;
                constructor(settings = {}) {
                    super();
                    this.settings = {
                        ...CKANEXT_FILES.defaultSettings,
                        ...this.constructor.defaultSettings,
                        ...settings,
                    };
                    this.sandbox = ckan.sandbox();
                    const csrfField = document
                        .querySelector("meta[name=csrf_field_name]")
                        ?.getAttribute("content") ?? "_csrf_token";
                    this.csrfToken =
                        document
                            .querySelector(`meta[name=${csrfField}]`)
                            ?.getAttribute("content") || "";
                }
                upload(file) {
                    throw new Error("Base.upload is not implemented");
                }
                resume(file, id) {
                    throw new Error("Base.resume is not implemented");
                }
                dispatchStart(file) {
                    this.dispatchEvent(new CustomEvent("start", { detail: { file } }));
                }
                dispatchCommit(file, id) {
                    this.dispatchEvent(new CustomEvent("commit", { detail: { file, id } }));
                }
                dispatchProgress(file, loaded, total) {
                    this.dispatchEvent(new CustomEvent("progress", { detail: { file, loaded, total } }));
                }
                dispatchFinish(file, result) {
                    this.dispatchEvent(new CustomEvent("finish", { detail: { file, result } }));
                }
                dispatchFail(file, reasons) {
                    this.dispatchEvent(new CustomEvent("fail", { detail: { file, reasons } }));
                }
                dispatchError(file, message) {
                    this.dispatchEvent(new CustomEvent("error", { detail: { file, message } }));
                }
            }
            adapters.Base = Base;
            class Standard extends Base {
                upload(file) {
                    const request = new XMLHttpRequest();
                    this._prepareRequest(request, file);
                    this._sendRequest(request, file);
                    return request;
                }
                _addListeners(request, file) {
                    request.upload.addEventListener("loadstart", (event) => this.dispatchStart(file));
                    request.upload.addEventListener("progress", (event) => this.dispatchProgress(file, event.loaded, event.total));
                    request.addEventListener("load", (event) => {
                        const result = JSON.parse(request.responseText);
                        if (result.success) {
                            this.dispatchCommit(file, result.result.id);
                            this.dispatchFinish(file, result.result);
                        }
                        else {
                            this.dispatchFail(file, result.error);
                        }
                    });
                    request.addEventListener("error", (event) => this.dispatchError(file, request.responseText));
                }
                _prepareRequest(request, file) {
                    this._addListeners(request, file);
                    request.open("POST", this.sandbox.client.url("/api/action/files_file_create"));
                    if (this.csrfToken) {
                        request.setRequestHeader("X-CSRFToken", this.csrfToken);
                    }
                }
                _sendRequest(request, file) {
                    const data = new FormData();
                    data.append("upload", file);
                    data.append("storage", this.settings.storage);
                    request.send(data);
                }
            }
            adapters.Standard = Standard;
            class Multipart extends Base {
                static defaultSettings = { chunkSize: 1024 * 1024 * 5 };
                _active;
                constructor(settings) {
                    super(settings);
                    this._active = new Set();
                }
                async upload(file) {
                    if (this._active.has(file)) {
                        console.warn("File upload in progress");
                        return;
                    }
                    this._active.add(file);
                    let info = await this._initializeUpload(file);
                    this.dispatchCommit(file, info.id);
                    this.dispatchStart(file);
                    this._doUpload(file, info);
                }
                async resume(file, id) {
                    if (this._active.has(file)) {
                        console.warn("File upload in progress");
                        return;
                    }
                    this._active.add(file);
                    let info = await this._showUpload(id);
                    this.dispatchStart(file);
                    this._doUpload(file, info);
                }
                pause(file) {
                    this._active.delete(file);
                }
                async _doUpload(file, info) {
                    let start = info.storage_data.uploaded || 0;
                    while (start < file.size) {
                        if (!this._active.has(file)) {
                            console.info("File upload is paused");
                            return;
                        }
                        info = await this._uploadChunk(info, file.slice(start, start + this.settings.chunkSize), start);
                        const uploaded = info.storage_data.uploaded;
                        if (uploaded <= start) {
                            throw new Error("Uploaded size is reduced");
                        }
                        this.dispatchProgress(file, uploaded, file.size);
                        start = uploaded;
                    }
                    this.dispatchProgress(file, file.size, file.size);
                    info = await this._completeUpload(info);
                    this.dispatchFinish(file, info);
                }
                _initializeUpload(file) {
                    return new Promise((done, fail) => this.sandbox.client.call("POST", "files_upload_initialize", {
                        storage: this.settings.storage,
                        name: file.name,
                        size: file.size,
                    }, (data) => {
                        done(data.result);
                    }, (resp) => {
                        fail(typeof resp.responseJSON === "string"
                            ? resp.responseText
                            : resp.responseJSON.error);
                    }));
                }
                _showUpload(id) {
                    return new Promise((done, fail) => this.sandbox.client.call("GET", "files_upload_show", `?id=${id}`, (data) => {
                        done(data.result);
                    }, (resp) => {
                        fail(typeof resp.responseJSON === "string"
                            ? resp.responseText
                            : resp.responseJSON.error);
                    }));
                }
                _uploadChunk(info, part, start) {
                    if (!part.size) {
                        throw new Error("0-length chunks are not allowed");
                    }
                    const request = new XMLHttpRequest();
                    const result = new Promise((done, fail) => {
                        request.addEventListener("load", (event) => {
                            const result = JSON.parse(request.responseText);
                            if (result.success) {
                                done(result.result);
                            }
                            else {
                                fail(result.error);
                            }
                        });
                        request.addEventListener("error", (event) => fail(request.responseText));
                    });
                    request.open("POST", this.sandbox.client.url("/api/action/files_upload_update"));
                    if (this.csrfToken) {
                        request.setRequestHeader("X-CSRFToken", this.csrfToken);
                    }
                    this._sendRequest(request, part, start, info.id);
                    return result;
                }
                _sendRequest(request, part, position, id) {
                    const form = new FormData();
                    form.append("upload", part);
                    form.append("position", String(position));
                    form.append("id", id);
                    request.send(form);
                }
                _completeUpload(info) {
                    return new Promise((done, fail) => this.sandbox.client.call("POST", "files_upload_complete", {
                        id: info.id,
                    }, (data) => {
                        done(data.result);
                    }, (resp) => {
                        fail(typeof resp.responseJSON === "string"
                            ? resp.responseText
                            : resp.responseJSON.error);
                    }));
                }
            }
            adapters.Multipart = Multipart;
        })(adapters = CKANEXT_FILES.adapters || (CKANEXT_FILES.adapters = {}));
    })(CKANEXT_FILES = ckan.CKANEXT_FILES || (ckan.CKANEXT_FILES = {}));
})(ckan || (ckan = {}));
