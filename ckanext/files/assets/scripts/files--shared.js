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
        function upload(file, options = {}) {
            const uploader = options.uploader ||
                makeUploader(options.adapter || "Standard", ...(options.uploaderArgs || []));
            return uploader.upload(file, options.requestParams || {});
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
                upload(file, params) {
                    throw new Error("Base.upload is not implemented");
                }
                resume(file, id) {
                    throw new Error("Base.resume is not implemented");
                }
                dispatchStart(file) {
                    this.dispatchEvent(new CustomEvent("start", { detail: { file } }));
                }
                dispatchMultipartId(file, id) {
                    this.dispatchEvent(new CustomEvent("multipartid", {
                        detail: { file, id },
                    }));
                }
                dispatchProgress(file, loaded, total) {
                    this.dispatchEvent(new CustomEvent("progress", {
                        detail: { file, loaded, total },
                    }));
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
            Base.defaultSettings = {};
            adapters.Base = Base;
            class Standard extends Base {
                upload(file, params) {
                    const request = new XMLHttpRequest();
                    const promise = this._addListeners(request, file);
                    this._prepareRequest(request, file);
                    this._sendRequest(request, file, params);
                    return promise;
                }
                _addListeners(request, file) {
                    request.upload.addEventListener("loadstart", (event) => this.dispatchStart(file));
                    request.upload.addEventListener("progress", (event) => this.dispatchProgress(file, event.loaded, event.total));
                    return new Promise((done, fail) => {
                        request.addEventListener("load", (event) => {
                            const result = JSON.parse(request.responseText);
                            if (typeof result === "string") {
                                this.dispatchError(file, result);
                                fail(result);
                            }
                            else if (result.success) {
                                this.dispatchFinish(file, result.result);
                                done(result.result);
                            }
                            else {
                                this.dispatchFail(file, result.error);
                                fail(result.error);
                            }
                        });
                        request.addEventListener("error", (event) => {
                            this.dispatchError(file, request.responseText);
                            fail(request.responseText);
                        });
                    });
                }
                _prepareRequest(request, file) {
                    request.open("POST", this.sandbox.client.url(`/api/action/${this.settings.uploadAction}`));
                    if (this.csrfToken) {
                        request.setRequestHeader("X-CSRFToken", this.csrfToken);
                    }
                }
                _sendRequest(request, file, params) {
                    const data = new FormData();
                    data.append("upload", file);
                    if (!params.storage) {
                        data.append("storage", this.settings.storage);
                    }
                    for (let [field, value] of Object.entries(params)) {
                        data.append(field, value);
                    }
                    request.send(data);
                }
            }
            Standard.defaultSettings = {
                uploadAction: "files_file_create",
            };
            adapters.Standard = Standard;
            class Multipart extends Base {
                constructor(settings) {
                    super(settings);
                    this._active = new Set();
                }
                async upload(file, params) {
                    if (this._active.has(file)) {
                        console.warn("File upload in progress");
                        return;
                    }
                    this._active.add(file);
                    let info;
                    try {
                        info = await this._initializeUpload(file, params);
                    }
                    catch (err) {
                        if (typeof err === "string") {
                            this.dispatchError(file, err);
                        }
                        else {
                            this.dispatchFail(file, err);
                        }
                        return;
                    }
                    this.dispatchMultipartId(file, info.id);
                    this.dispatchStart(file);
                    return this._doUpload(file, info);
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
                    let start = info.storage_data["uploaded"] || 0;
                    while (start < file.size) {
                        if (!this._active.has(file)) {
                            console.info("File upload is paused");
                            return;
                        }
                        info = await this._uploadChunk(info, file.slice(start, start + this.settings.chunkSize), start, {
                            progressData: {
                                file,
                                uploaded: info.storage_data.uploaded,
                                size: file.size,
                            },
                        });
                        const uploaded = info.storage_data.uploaded;
                        if (uploaded <= start) {
                            throw new Error("Uploaded size is reduced");
                        }
                        this.dispatchProgress(file, uploaded, file.size);
                        start = uploaded;
                    }
                    this.dispatchProgress(file, file.size, file.size);
                    try {
                        info = await this._completeUpload(info);
                    }
                    catch (err) {
                        if (typeof err === "string") {
                            this.dispatchError(file, err);
                        }
                        else {
                            this.dispatchFail(file, err);
                        }
                        return;
                    }
                    this.dispatchFinish(file, info);
                    return info;
                }
                _initializeUpload(file, params) {
                    return new Promise((done, fail) => this.sandbox.client.call("POST", this.settings.uploadAction, Object.assign({}, {
                        storage: this.settings.storage,
                        name: file.name,
                        size: file.size,
                        content_type: file.type || "application/octet-stream",
                    }, params), (data) => {
                        done(data.result);
                    }, (resp) => {
                        fail(typeof resp.responseJSON === "string"
                            ? resp.responseText
                            : resp.responseJSON.error);
                    }));
                }
                _showUpload(id) {
                    return new Promise((done, fail) => this.sandbox.client.call("GET", "files_multipart_refresh", `?id=${id}`, (data) => {
                        done(data.result);
                    }, (resp) => {
                        fail(typeof resp.responseJSON === "string"
                            ? resp.responseText
                            : resp.responseJSON.error);
                    }));
                }
                _uploadChunk(info, part, start, extras = {}) {
                    if (!part.size) {
                        throw new Error("0-length chunks are not allowed");
                    }
                    const request = new XMLHttpRequest();
                    const result = new Promise((done, fail) => {
                        if (extras["progressData"]) {
                            const { file, uploaded, size } = extras["progressData"];
                            request.upload.addEventListener("progress", (event) => {
                                this.dispatchProgress(file, uploaded + event.loaded, size);
                            });
                        }
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
                    request.open("POST", this.sandbox.client.url("/api/action/files_multipart_update"));
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
                    return new Promise((done, fail) => this.sandbox.client.call("POST", "files_multipart_complete", Object.assign({}, this.settings.completePayload || {}, {
                        id: info.id,
                    }), (data) => {
                        done(data.result);
                    }, (resp) => {
                        fail(typeof resp.responseJSON === "string"
                            ? resp.responseText
                            : resp.responseJSON.error);
                    }));
                }
            }
            Multipart.defaultSettings = {
                chunkSize: 1024 * 1024 * 5,
                uploadAction: "files_multipart_start",
            };
            adapters.Multipart = Multipart;
        })(adapters = CKANEXT_FILES.adapters || (CKANEXT_FILES.adapters = {}));
    })(CKANEXT_FILES = ckan.CKANEXT_FILES || (ckan.CKANEXT_FILES = {}));
})(ckan || (ckan = {}));
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZmlsZXMtLXNoYXJlZC5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uL3RzL2ZpbGVzLS1zaGFyZWQudHMiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IkFBQUEsSUFBVSxJQUFJLENBOGNiO0FBOWNELFdBQVUsSUFBSTtJQUlWLElBQWlCLGFBQWEsQ0F5YzdCO0lBemNELFdBQWlCLGFBQWE7UUFhYixvQkFBTSxHQUFHO1lBQ2xCLGNBQWMsRUFBRSw4QkFBOEI7WUFDOUMsa0JBQWtCLEVBQUUsa0NBQWtDO1lBQ3RELGlCQUFpQixFQUFFLG1DQUFtQztTQUN6RCxDQUFDO1FBRVcsNkJBQWUsR0FBRztZQUMzQixPQUFPLEVBQUUsU0FBUztTQUNyQixDQUFDO1FBRUYsU0FBUyxNQUFNLENBQUMsSUFBVSxFQUFFLFVBQXlCLEVBQUU7WUFDbkQsTUFBTSxRQUFRLEdBQ1YsT0FBTyxDQUFDLFFBQVE7Z0JBQ2hCLFlBQVksQ0FDUixPQUFPLENBQUMsT0FBTyxJQUFJLFVBQVUsRUFDN0IsR0FBRyxDQUFDLE9BQU8sQ0FBQyxZQUFZLElBQUksRUFBRSxDQUFDLENBQ2xDLENBQUM7WUFDTixPQUFPLFFBQVEsQ0FBQyxNQUFNLENBQUMsSUFBSSxFQUFFLE9BQU8sQ0FBQyxhQUFhLElBQUksRUFBRSxDQUFDLENBQUM7UUFDOUQsQ0FBQztRQUVELFNBQVMsWUFBWSxDQUFDLE9BQWUsRUFBRSxHQUFHLE9BQVk7WUFDbEQsTUFBTSxPQUFPLEdBQTZDLFFBQVMsQ0FDL0QsT0FBTyxDQUNWLENBQUM7WUFDRixJQUFJLENBQUMsT0FBTyxFQUFFLENBQUM7Z0JBQ1gsTUFBTSxJQUFJLEtBQUssQ0FBQyxZQUFZLE9BQU8sb0JBQW9CLENBQUMsQ0FBQztZQUM3RCxDQUFDO1lBQ0QsT0FBTyxJQUFJLE9BQU8sQ0FBQyxHQUFHLE9BQU8sQ0FBQyxDQUFDO1FBQ25DLENBQUM7UUFFRCxJQUFJLENBQUMsT0FBTyxDQUFDLE1BQU0sQ0FBQyxFQUFFLEtBQUssRUFBRSxFQUFFLE1BQU0s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QUFTLEVBQUUsSUFBSSxHQUFHLElBQUksR0FBRyxDQUFDO2dCQUMxQixZQUFZLEVBQUUsdUJBQXVCO2FBQ3hDLEFBSHFCLENBR3BCO1lBSk8sa0JBQVMsWUEyUHJCLENBQUE7UUFDTCxDQUFDLEVBM1pnQixRQUFRLEdBQVIsc0JBQVEsS0FBUixzQkFBUSxRQTJaeEI7SUFDTCxDQUFDLEVBemNnQixhQUFhLEdBQWIsa0JBQWEsS0FBYixrQkFBYSxRQXljN0I7QUFDTCxDQUFDLEVBOWNTLElBQUksS0FBSixJQUFJLFFBOGNiIiwic291cmNlc0NvbnRlbnQiOlsibmFtZXNwYWNlIGNrYW4ge1xuICAgIGV4cG9ydCB2YXIgc2FuZGJveDogYW55O1xuICAgIGV4cG9ydCB2YXIgcHVic3ViOiBhbnk7XG4gICAgZXhwb3J0IHZhciBtb2R1bGU6IChuYW1lOiBzdHJpbmcsIGluaXRpYWxpemVyOiAoJDogYW55KSA9PiBhbnkpID0+IGFueTtcbiAgICBleHBvcnQgbmFtZXNwYWNlIENLQU5FWFRfRklMRVMge1xuICAgICAgICBleHBvcnQgdHlwZSBVcGxvYWRlclNldHRpbmdzID0ge1xuICAgICAgICAgICAgc3RvcmFnZTogc3RyaW5nO1xuICAgICAgICAgICAgW2tleTogc3RyaW5nXTogYW55O1xuICAgICAgICB9O1xuXG4gICAgICAgIGV4cG9ydCBpbnRlcmZhY2UgVXBsb2FkT3B0aW9ucyB7XG4gICAgICAgICAgICB1cGxvYWRlcj86IGFkYXB0ZXJzLkJhc2U7XG4gICAgICAgICAgICBhZGFwdGVyPzogc3RyaW5nO1xuICAgICAgICAgICAgdXBsb2FkZXJBcmdzPzogYW55W107XG4gICAgICAgICAgICByZXF1ZXN0UGFyYW1zPzogeyBba2V5OiBzdHJpbmddOiBhbnkgfTtcbiAgICAgICAgfVxuXG4gICAgICAgIGV4cG9ydCBjb25zdCB0b3BpY3MgPSB7XG4gICAgICAgICAgICBhZGRGaWxlVG9RdWV1ZTogXCJja2FuZXh0OmZpbGVzOnF1ZXVlOmZpbGU6YWRkXCIsXG4gICAgICAgICAgICByZXN0b3JlRmlsZUluUXVldWU6IFwiY2thbmV4dDpmaWxlczpxdWV1ZTpmaWxlOnJlc3RvcmVcIixcbiAgICAgICAgICAgIHF1ZXVlSXRlbVVwbG9hZGVkOiBcImNrYW5leHQ6ZmlsZXM6cXVldWU6ZmlsZTp1cGxvYWRlZFwiLFxuICAgICAgICB9O1xuXG4gICAgICAgIGV4cG9ydCBjb25zdCBkZWZhdWx0U2V0dGluZ3MgPSB7XG4gICAgICAgICAgICBzdG9yYWdlOiBcImRlZmF1bHRcIixcbiAgICAgICAgfTtcblxuICAgICAgICBmdW5jdGlvbiB1cGxvYWQoZmlsZTogRmlsZSwgb3B0aW9uczogVXBsb2FkT3B0aW9ucyA9IHt9KSB7XG4gICAgICAgICAgICBjb25zdCB1cGxvYWRlciA9XG4gICAgICAgICAgICAgICAgb3B0aW9ucy51cGxvYWRlciB8fFxuICAgICAgICAgICAgICAgIG1ha2VVcGxvYWRlcihcbiAgICAgICAgICAgICAgICAgICAgb3B0aW9ucy5hZGFwdGVyIHx8IFwiU3RhbmRhcmRcIixcbiAgICAgICAgICAgICAgICAgICAgLi4uKG9wdGlvbnMudXBsb2FkZXJBcmdzIHx8IFtdKSxcbiAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgcmV0dXJuIHVwbG9hZGVyLnVwbG9hZChmaWxlLCBvcHRpb25zLnJlcXVlc3RQYXJhbXMgfHwge30pO1xuICAgICAgICB9XG5cbiAgICAgICAgZnVuY3Rpb24gbWFrZVVwbG9hZGVyKGFkYXB0ZXI6IHN0cmluZywgLi4ub3B0aW9uczogYW55KSB7XG4gICAgICAgICAgICBjb25zdCBmYWN0b3J5ID0gKDx7IFtrZXk6IHN0cmluZ106IHR5cGVvZiBhZGFwdGVycy5CYXNlIH0+YWRhcHRlcnMpW1xuICAgICAgICAgICAgICAgIGFkYXB0ZXJcbiAgICAgICAgICAgIF07XG4gICAgICAgICAgICBpZiAoIWZhY3RvcnkpIHtcbiAgICAgICAgICAgICAgICB0aHJvdyBuZXcgRXJyb3IoYFVwbG9hZGVyICR7YWRhcHRlcn0gaXMgbm90IHJlZ2lzdGVyZWRgKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIHJldHVybiBuZXcgZmFjdG9yeSguLi5vcHRpb25zKTtcbiAgICAgICAgfVxuXG4gICAgICAgIGNrYW4uc2FuZGJveC5leHRlbmQoeyBmaWxlczogeyB1cGxvYWQsIG1ha2VVcGxvYWRlciB9IH0pO1xuXG4gICAgICAgIGV4cG9ydCBuYW1lc3BhY2UgYWRhcHRlcnMge1xuICAgICAgICAgICAgZXhwb3J0IHR5cGUgU3RvcmFnZURhdGEgPSB7IFtrZXk6IHN0cmluZ106IGFueSB9O1xuXG4gICAgICAgICAgICBleHBvcnQgdHlwZSBVcGxvYWRJbmZvID0ge1xuICAgICAgICAgICAgICAgIGlkOiBzdHJpbmc7XG4gICAgICAgICAgICAgICAgc3RvcmFnZV9kYXRhOiBTdG9yYWdlRGF0YTtcbiAgICAgICAgICAgICAgICBsb2NhdGlvbjogc3RyaW5nO1xuICAgICAgICAgICAgICAgIGhhc2g6IHN0cmluZztcbiAgICAgICAgICAgICAgICBjb250ZW50X3R5cGU6IHN0cmluZztcbiAgICAgICAgICAgICAgICBzaXplOiBudW1iZXI7XG4gICAgICAgICAgICB9O1xuXG4gICAgICAgICAgICBleHBvcnQgY2xhc3MgQmFzZSBleHRlbmRzIEV2ZW50VGFyZ2V0IHtcbiAgICAgICAgICAgICAgICBzdGF0aWMgZGVmYXVsdFNldHRpbmdzOiBPYmplY3QgPSB7fTtcbiAgICAgICAgICAgICAgICBwcm90ZWN0ZWQgc2V0dGluZ3M6IFVwbG9hZGVyU2V0dGluZ3M7XG4gICAgICAgICAgICAgICAgcHJvdGVjdGVkIHNhbmRib3g6IGFueTtcbiAgICAgICAgICAgICAgICBwcm90ZWN0ZWQgY3NyZlRva2VuOiBzdHJpbmc7XG5cbiAgICAgICAgICAgICAgICBjb25zdHJ1Y3RvcihzZXR0aW5ncyA9IHt9KSB7XG4gICAgICAgICAgICAgICAgICAgIHN1cGVyKCk7XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuc2V0dGluZ3MgPSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAuLi5kZWZhdWx0U2V0dGluZ3MsXG4gICAgICAgICAgICAgICAgICAgICAgICAuLi4odGhpcy5jb25zdHJ1Y3RvciBhcyB0eXBlb2YgQmFzZSkuZGVmYXVsdFNldHRpbmdzLFxuICAgICAgICAgICAgICAgICAgICAgICAgLi4uc2V0dGluZ3MsXG4gICAgICAgICAgICAgICAgICAgIH07XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuc2FuZGJveCA9IGNrYW4uc2FuZGJveCgpO1xuXG4gICAgICAgICAgICAgICAgICAgIGNvbnN0IGNzcmZGaWVsZCA9XG4gICAgICAgICAgICAgICAgICAgICAgICBkb2N1bWVudFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIC5xdWVyeVNlbGVjdG9yKFwibWV0YVtuYW1lPWNzcmZfZmllbGRfbmFtZV1cIilcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICA/LmdldEF0dHJpYnV0ZShcImNvbnRlbnRcIikgPz8gXCJfY3NyZl90b2tlblwiO1xuICAgICAgICAgICAgICAgICAgICB0aGlzLmNzcmZUb2tlbiA9XG4gICAgICAgICAgICAgICAgICAgICAgICBkb2N1bWVudFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIC5xdWVyeVNlbGVjdG9yKGBtZXRhW25hbWU9JHtjc3JmRmllbGR9XWApXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgPy5nZXRBdHRyaWJ1dGUoXCJjb250ZW50XCIpIHx8IFwiXCI7XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgdXBsb2FkKGZpbGU6IEZpbGUsIHBhcmFtczogeyBba2V5OiBzdHJpbmddOiBhbnkgfSkge1xuICAgICAgICAgICAgICAgICAgICB0aHJvdyBuZXcgRXJyb3IoXCJCYXNlLnVwbG9hZCBpcyBub3QgaW1wbGVtZW50ZWRcIik7XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgcmVzdW1lKGZpbGU6IEZpbGUsIGlkOiBzdHJpbmcpIHtcbiAgICAgICAgICAgICAgICAgICAgdGhyb3cgbmV3IEVycm9yKFwiQmFzZS5yZXN1bWUgaXMgbm90IGltcGxlbWVudGVkXCIpO1xuICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgIGRpc3BhdGNoU3RhcnQoZmlsZTogRmlsZSkge1xuICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRXZlbnQoXG4gICAgICAgICAgICAgICAgICAgICAgICBuZXcgQ3VzdG9tRXZlbnQoXCJzdGFydFwiLCB7IGRldGFpbDogeyBmaWxlIH0gfSksXG4gICAgICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGRpc3BhdGNoTXVsdGlwYXJ0SWQoZmlsZTogRmlsZSwgaWQ6IHN0cmluZykge1xuICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRXZlbnQoXG4gICAgICAgICAgICAgICAgICAgICAgICBuZXcgQ3VzdG9tRXZlbnQoXCJtdWx0aXBhcnRpZFwiLCB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgZGV0YWlsOiB7IGZpbGUsIGlkIH0sXG4gICAgICAgICAgICAgICAgICAgICAgICB9KSxcbiAgICAgICAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgZGlzcGF0Y2hQcm9ncmVzcyhmaWxlOiBGaWxlLCBsb2FkZWQ6IG51bWJlciwgdG90YWw6IG51bWJlcikge1xuICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRXZlbnQoXG4gICAgICAgICAgICAgICAgICAgICAgICBuZXcgQ3VzdG9tRXZlbnQoXCJwcm9ncmVzc1wiLCB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgZGV0YWlsOiB7IGZpbGUsIGxvYWRlZCwgdG90YWwgfSxcbiAgICAgICAgICAgICAgICAgICAgICAgIH0pLFxuICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBkaXNwYXRjaEZpbmlzaChmaWxlOiBGaWxlLCByZXN1bHQ6IE9iamVjdCkge1xuICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRXZlbnQoXG4gICAgICAgICAgICAgICAgICAgICAgICBuZXcgQ3VzdG9tRXZlbnQoXCJmaW5pc2hcIiwgeyBkZXRhaWw6IHsgZmlsZSwgcmVzdWx0IH0gfSksXG4gICAgICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGRpc3BhdGNoRmFpbChmaWxlOiBGaWxlLCByZWFzb25zOiB7IFtrZXk6IHN0cmluZ106IHN0cmluZ1tdIH0pIHtcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaEV2ZW50KFxuICAgICAgICAgICAgICAgICAgICAgICAgbmV3IEN1c3RvbUV2ZW50KFwiZmFpbFwiLCB7IGRldGFpbDogeyBmaWxlLCByZWFzb25zIH0gfSksXG4gICAgICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGRpc3BhdGNoRXJyb3IoZmlsZTogRmlsZSwgbWVzc2FnZTogc3RyaW5nKSB7XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hFdmVudChcbiAgICAgICAgICAgICAgICAgICAgICAgIG5ldyBDdXN0b21FdmVudChcImVycm9yXCIsIHsgZGV0YWlsOiB7IGZpbGUsIG1lc3NhZ2UgfSB9KSxcbiAgICAgICAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9XG5cbiAgICAgICAgICAgIGV4cG9ydCBjbGFzcyBTdGFuZGFyZCBleHRlbmRzIEJhc2Uge1xuICAgICAgICAgICAgICAgIHN0YXRpYyBkZWZhdWx0U2V0dGluZ3MgPSB7XG4gICAgICAgICAgICAgICAgICAgIHVwbG9hZEFjdGlvbjogXCJmaWxlc19maWxlX2NyZWF0ZVwiLFxuICAgICAgICAgICAgICAgIH07XG5cbiAgICAgICAgICAgICAgICB1cGxvYWQoZmlsZTogRmlsZSwgcGFyYW1zOiB7IFtrZXk6IHN0cmluZ106IGFueSB9KSB7XG4gICAgICAgICAgICAgICAgICAgIGNvbnN0IHJlcXVlc3QgPSBuZXcgWE1MSHR0cFJlcXVlc3QoKTtcbiAgICAgICAgICAgICAgICAgICAgY29uc3QgcHJvbWlzZSA9IHRoaXMuX2FkZExpc3RlbmVycyhyZXF1ZXN0LCBmaWxlKTtcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5fcHJlcGFyZVJlcXVlc3QocmVxdWVzdCwgZmlsZSk7XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuX3NlbmRSZXF1ZXN0KHJlcXVlc3QsIGZpbGUsIHBhcmFtcyk7XG4gICAgICAgICAgICAgICAgICAgIHJldHVybiBwcm9taXNlO1xuICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgIF9hZGRMaXN0ZW5lcnMoXG4gICAgICAgICAgICAgICAgICAgIHJlcXVlc3Q6IFhNTEh0dHBSZXF1ZXN0LFxuICAgICAgICAgICAgICAgICAgICBmaWxlOiBGaWxlLFxuICAgICAgICAgICAgICAgICk6IFByb21pc2U8VXBsb2FkSW5mbz4ge1xuICAgICAgICAgICAgICAgICAgICByZXF1ZXN0LnVwbG9hZC5hZGRFdmVudExpc3RlbmVyKFwibG9hZHN0YXJ0XCIsIChldmVudCkgPT5cbiAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hTdGFydChmaWxlKSxcbiAgICAgICAgICAgICAgICAgICAgKTtcblxuICAgICAgICAgICAgICAgICAgICByZXF1ZXN0LnVwbG9hZC5hZGRFdmVudExpc3RlbmVyKFwicHJvZ3Jlc3NcIiwgKGV2ZW50KSA9PlxuICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaFByb2dyZXNzKGZpbGUsIGV2ZW50LmxvYWRlZCwgZXZlbnQudG90YWwpLFxuICAgICAgICAgICAgICAgICAgICApO1xuXG4gICAgICAgICAgICAgICAgICAgIHJldHVybiBuZXcgUHJvbWlzZSgoZG9uZSwgZmFpbCkgPT4ge1xuICAgICAgICAgICAgICAgICAgICAgICAgcmVxdWVzdC5hZGRFdmVudExpc3RlbmVyKFwibG9hZFwiLCAoZXZlbnQpID0+IHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBjb25zdCByZXN1bHQgPSBKU09OLnBhcnNlKHJlcXVlc3QucmVzcG9uc2VUZXh0KTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiAodHlwZW9mIHJlc3VsdCA9PT0gXCJzdHJpbmdcIikge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRXJyb3IoZmlsZSwgcmVzdWx0KTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZmFpbChyZXN1bHQpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSBpZiAocmVzdWx0LnN1Y2Nlc3MpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaEZpbmlzaChmaWxlLCByZXN1bHQucmVzdWx0KTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZG9uZShyZXN1bHQucmVzdWx0KTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRmFpbChmaWxlLCByZXN1bHQuZXJyb3IpO1xuXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGZhaWwocmVzdWx0LmVycm9yKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICB9KTtcblxuICAgICAgICAgICAgICAgICAgICAgICAgcmVxdWVzdC5hZGRFdmVudExpc3RlbmVyKFwiZXJyb3JcIiwgKGV2ZW50KSA9PiB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaEVycm9yKGZpbGUsIHJlcXVlc3QucmVzcG9uc2VUZXh0KTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBmYWlsKHJlcXVlc3QucmVzcG9uc2VUZXh0KTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH0pO1xuICAgICAgICAgICAgICAgICAgICB9KTtcbiAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICBfcHJlcGFyZVJlcXVlc3QocmVxdWVzdDogWE1MSHR0cFJlcXVlc3QsIGZpbGU6IEZpbGUpIHtcbiAgICAgICAgICAgICAgICAgICAgcmVxdWVzdC5vcGVuKFxuICAgICAgICAgICAgICAgICAgICAgICAgXCJQT1NUXCIsXG4gICAgICAgICAgICAgICAgICAgICAgICB0aGlzLnNhbmRib3guY2xpZW50LnVybChcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBgL2FwaS9hY3Rpb24vJHt0aGlzLnNldHRpbmdzLnVwbG9hZEFjdGlvbn1gLFxuICAgICAgICAgICAgICAgICAgICAgICAgKSxcbiAgICAgICAgICAgICAgICAgICAgKTtcblxuICAgICAgICAgICAgICAgICAgICBpZiAodGhpcy5jc3JmVG9rZW4pIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHJlcXVlc3Quc2V0UmVxdWVzdEhlYWRlcihcIlgtQ1NSRlRva2VuXCIsIHRoaXMuY3NyZlRva2VuKTtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgIF9zZW5kUmVxdWVzdChcbiAgICAgICAgICAgICAgICAgICAgcmVxdWVzdDogWE1MSHR0cFJlcXVlc3QsXG4gICAgICAgICAgICAgICAgICAgIGZpbGU6IEZpbGUsXG4gICAgICAgICAgICAgICAgICAgIHBhcmFtczogeyBba2V5OiBzdHJpbmddOiBhbnkgfSxcbiAgICAgICAgICAgICAgICApIHtcbiAgICAgICAgICAgICAgICAgICAgY29uc3QgZGF0YSA9IG5ldyBGb3JtRGF0YSgpO1xuICAgICAgICAgICAgICAgICAgICBkYXRhLmFwcGVuZChcInVwbG9hZFwiLCBmaWxlKTtcbiAgICAgICAgICAgICAgICAgICAgaWYgKCFwYXJhbXMuc3RvcmFnZSkge1xuICAgICAgICAgICAgICAgICAgICAgICAgZGF0YS5hcHBlbmQoXCJzdG9yYWdlXCIsIHRoaXMuc2V0dGluZ3Muc3RvcmFnZSk7XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgZm9yIChsZXQgW2ZpZWxkLCB2YWx1ZV0gb2YgT2JqZWN0LmVudHJpZXMocGFyYW1zKSkge1xuICAgICAgICAgICAgICAgICAgICAgICAgZGF0YS5hcHBlbmQoZmllbGQsIHZhbHVlKTtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICByZXF1ZXN0LnNlbmQoZGF0YSk7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICBleHBvcnQgY2xhc3MgTXVsdGlwYXJ0IGV4dGVuZHMgQmFzZSB7XG4gICAgICAgICAgICAgICAgc3RhdGljIGRlZmF1bHRTZXR0aW5ncyA9IHtcbiAgICAgICAgICAgICAgICAgICAgY2h1bmtTaXplOiAxMDI0ICogMTAyNCAqIDUsXG4gICAgICAgICAgICAgICAgICAgIHVwbG9hZEFjdGlvbjogXCJmaWxlc19tdWx0aXBhcnRfc3RhcnRcIixcbiAgICAgICAgICAgICAgICB9O1xuXG4gICAgICAgICAgICAgICAgcHJpdmF0ZSBfYWN0aXZlID0gbmV3IFNldDxGaWxlPigpO1xuXG4gICAgICAgICAgICAgICAgY29uc3RydWN0b3Ioc2V0dGluZ3M6IE9iamVjdCkge1xuICAgICAgICAgICAgICAgICAgICBzdXBlcihzZXR0aW5ncyk7XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgYXN5bmMgdXBsb2FkKGZpbGU6IEZpbGUsIHBhcmFtczogeyBba2V5OiBzdHJpbmddOiBhbnkgfSkge1xuICAgICAgICAgICAgICAgICAgICBpZiAodGhpcy5fYWN0aXZlLmhhcyhmaWxlKSkge1xuICAgICAgICAgICAgICAgICAgICAgICAgY29uc29sZS53YXJuKFwiRmlsZSB1cGxvYWQgaW4gcHJvZ3Jlc3NcIik7XG4gICAgICAgICAgICAgICAgICAgICAgICByZXR1cm47XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgdGhpcy5fYWN0aXZlLmFkZChmaWxlKTtcblxuICAgICAgICAgICAgICAgICAgICBsZXQgaW5mbztcblxuICAgICAgICAgICAgICAgICAgICB0cnkge1xuICAgICAgICAgICAgICAgICAgICAgICAgaW5mbyA9IGF3YWl0IHRoaXMuX2luaXRpYWxpemVVcGxvYWQoZmlsZSwgcGFyYW1zKTtcbiAgICAgICAgICAgICAgICAgICAgfSBjYXRjaCAoZXJyKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBpZiAodHlwZW9mIGVyciA9PT0gXCJzdHJpbmdcIikge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hFcnJvcihmaWxlLCBlcnIpO1xuICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRmFpbChmaWxlLCBlcnIgYXMgYW55KTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgIHJldHVybjtcbiAgICAgICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hNdWx0aXBhcnRJZChmaWxlLCBpbmZvLmlkKTtcblxuICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoU3RhcnQoZmlsZSk7XG5cbiAgICAgICAgICAgICAgICAgICAgcmV0dXJuIHRoaXMuX2RvVXBsb2FkKGZpbGUsIGluZm8pO1xuICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgIGFzeW5jIHJlc3VtZShmaWxlOiBGaWxlLCBpZDogc3RyaW5nKSB7XG4gICAgICAgICAgICAgICAgICAgIGlmICh0aGlzLl9hY3RpdmUuaGFzKGZpbGUpKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBjb25zb2xlLndhcm4oXCJGaWxlIHVwbG9hZCBpbiBwcm9ncmVzc1wiKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIHJldHVybjtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICB0aGlzLl9hY3RpdmUuYWRkKGZpbGUpO1xuXG4gICAgICAgICAgICAgICAgICAgIGxldCBpbmZvID0gYXdhaXQgdGhpcy5fc2hvd1VwbG9hZChpZCk7XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hTdGFydChmaWxlKTtcblxuICAgICAgICAgICAgICAgICAgICB0aGlzLl9kb1VwbG9hZChmaWxlLCBpbmZvKTtcbiAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICBwYXVzZShmaWxlOiBGaWxlKSB7XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuX2FjdGl2ZS5kZWxldGUoZmlsZSk7XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgYXN5bmMgX2RvVXBsb2FkKGZpbGU6IEZpbGUsIGluZm86IFVwbG9hZEluZm8pIHtcbiAgICAgICAgICAgICAgICAgICAgbGV0IHN0YXJ0ID0gaW5mby5zdG9yYWdlX2RhdGFbXCJ1cGxvYWRlZFwiXSB8fCAwO1xuXG4gICAgICAgICAgICAgICAgICAgIHdoaWxlIChzdGFydCA8IGZpbGUuc2l6ZSkge1xuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKCF0aGlzLl9hY3RpdmUuaGFzKGZpbGUpKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgY29uc29sZS5pbmZvKFwiRmlsZSB1cGxvYWQgaXMgcGF1c2VkXCIpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHJldHVybjtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgICAgICAgICAgaW5mbyA9IGF3YWl0IHRoaXMuX3VwbG9hZENodW5rKFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGluZm8sXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgZmlsZS5zbGljZShzdGFydCwgc3RhcnQgKyB0aGlzLnNldHRpbmdzLmNodW5rU2l6ZSksXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgc3RhcnQsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBwcm9ncmVzc0RhdGE6IHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGZpbGUsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB1cGxvYWRlZDogaW5mby5zdG9yYWdlX2RhdGEudXBsb2FkZWQsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzaXplOiBmaWxlLnNpemUsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgICAgICAgICAgICk7XG5cbiAgICAgICAgICAgICAgICAgICAgICAgIGNvbnN0IHVwbG9hZGVkID0gaW5mby5zdG9yYWdlX2RhdGEudXBsb2FkZWQ7XG4gICAgICAgICAgICAgICAgICAgICAgICBpZiAodXBsb2FkZWQgPD0gc3RhcnQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB0aHJvdyBuZXcgRXJyb3IoXCJVcGxvYWRlZCBzaXplIGlzIHJlZHVjZWRcIik7XG4gICAgICAgICAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hQcm9ncmVzcyhmaWxlLCB1cGxvYWRlZCwgZmlsZS5zaXplKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIHN0YXJ0ID0gdXBsb2FkZWQ7XG4gICAgICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoUHJvZ3Jlc3MoZmlsZSwgZmlsZS5zaXplLCBmaWxlLnNpemUpO1xuICAgICAgICAgICAgICAgICAgICB0cnkge1xuICAgICAgICAgICAgICAgICAgICAgICAgaW5mbyA9IGF3YWl0IHRoaXMuX2NvbXBsZXRlVXBsb2FkKGluZm8pO1xuICAgICAgICAgICAgICAgICAgICB9IGNhdGNoIChlcnIpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIGlmICh0eXBlb2YgZXJyID09PSBcInN0cmluZ1wiKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaEVycm9yKGZpbGUsIGVycik7XG4gICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hGYWlsKGZpbGUsIGVyciBhcyBhbnkpO1xuICAgICAgICAgICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgICAgICAgICByZXR1cm47XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaEZpbmlzaChmaWxlLCBpbmZvKTtcbiAgICAgICAgICAgICAgICAgICAgcmV0dXJuIGluZm87XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgX2luaXRpYWxpemVVcGxvYWQoXG4gICAgICAgICAgICAgICAgICAgIGZpbGU6IEZpbGUsXG4gICAgICAgICAgICAgICAgICAgIHBhcmFtczogeyBba2V5OiBzdHJpbmddOiBhbnkgfSxcbiAgICAgICAgICAgICAgICApOiBQcm9taXNlPFVwbG9hZEluZm8+IHtcbiAgICAgICAgICAgICAgICAgICAgcmV0dXJuIG5ldyBQcm9taXNlKChkb25lLCBmYWlsKSA9PlxuICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5zYW5kYm94LmNsaWVudC5jYWxsKFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIFwiUE9TVFwiLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuc2V0dGluZ3MudXBsb2FkQWN0aW9uLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIE9iamVjdC5hc3NpZ24oXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHt9LFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzdG9yYWdlOiB0aGlzLnNldHRpbmdzLnN0b3JhZ2UsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBuYW1lOiBmaWxlLm5hbWUsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzaXplOiBmaWxlLnNpemUsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBjb250ZW50X3R5cGU6XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZmlsZS50eXBlIHx8IFwiYXBwbGljYXRpb24vb2N0ZXQtc3RyZWFtXCIsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHBhcmFtcyxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICApLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIChkYXRhOiBhbnkpID0+IHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZG9uZShkYXRhLnJlc3VsdCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAocmVzcDogYW55KSA9PiB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGZhaWwoXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB0eXBlb2YgcmVzcC5yZXNwb25zZUpTT04gPT09IFwic3RyaW5nXCJcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA/IHJlc3AucmVzcG9uc2VUZXh0XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgOiByZXNwLnJlc3BvbnNlSlNPTi5lcnJvcixcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICAgICAgICAgICAgKSxcbiAgICAgICAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICBfc2hvd1VwbG9hZChpZDogc3RyaW5nKTogUHJvbWlzZTxVcGxvYWRJbmZvPiB7XG4gICAgICAgICAgICAgICAgICAgIHJldHVybiBuZXcgUHJvbWlzZSgoZG9uZSwgZmFpbCkgPT5cbiAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuc2FuZGJveC5jbGllbnQuY2FsbChcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBcIkdFVFwiLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIFwiZmlsZXNfbXVsdGlwYXJ0X3JlZnJlc2hcIixcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBgP2lkPSR7aWR9YCxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAoZGF0YTogYW55KSA9PiB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGRvbmUoZGF0YS5yZXN1bHQpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgKHJlc3A6IGFueSkgPT4ge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBmYWlsKFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgdHlwZW9mIHJlc3AucmVzcG9uc2VKU09OID09PSBcInN0cmluZ1wiXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgPyByZXNwLnJlc3BvbnNlVGV4dFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDogcmVzcC5yZXNwb25zZUpTT04uZXJyb3IsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgICAgICAgICAgICksXG4gICAgICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgX3VwbG9hZENodW5rKFxuICAgICAgICAgICAgICAgICAgICBpbmZvOiBVcGxvYWRJbmZvLFxuICAgICAgICAgICAgICAgICAgICBwYXJ0OiBCbG9iLFxuICAgICAgICAgICAgICAgICAgICBzdGFydDogbnVtYmVyLFxuICAgICAgICAgICAgICAgICAgICBleHRyYXM6IGFueSA9IHt9LFxuICAgICAgICAgICAgICAgICk6IFByb21pc2U8VXBsb2FkSW5mbz4ge1xuICAgICAgICAgICAgICAgICAgICBpZiAoIXBhcnQuc2l6ZSkge1xuICAgICAgICAgICAgICAgICAgICAgICAgdGhyb3cgbmV3IEVycm9yKFwiMC1sZW5ndGggY2h1bmtzIGFyZSBub3QgYWxsb3dlZFwiKTtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICBjb25zdCByZXF1ZXN0ID0gbmV3IFhNTEh0dHBSZXF1ZXN0KCk7XG5cbiAgICAgICAgICAgICAgICAgICAgY29uc3QgcmVzdWx0ID0gbmV3IFByb21pc2U8VXBsb2FkSW5mbz4oKGRvbmUsIGZhaWwpID0+IHtcbiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChleHRyYXNbXCJwcm9ncmVzc0RhdGFcIl0pIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBjb25zdCB7IGZpbGUsIHVwbG9hZGVkLCBzaXplIH0gPVxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBleHRyYXNbXCJwcm9ncmVzc0RhdGFcIl07XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgcmVxdWVzdC51cGxvYWQuYWRkRXZlbnRMaXN0ZW5lcihcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgXCJwcm9ncmVzc1wiLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAoZXZlbnQpID0+IHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hQcm9ncmVzcyhcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBmaWxlLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHVwbG9hZGVkICsgZXZlbnQubG9hZGVkLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHNpemUsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICAgICAgICAgIHJlcXVlc3QuYWRkRXZlbnRMaXN0ZW5lcihcImxvYWRcIiwgKGV2ZW50KSA9PiB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgY29uc3QgcmVzdWx0ID0gSlNPTi5wYXJzZShyZXF1ZXN0LnJlc3BvbnNlVGV4dCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHJlc3VsdC5zdWNjZXNzKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGRvbmUocmVzdWx0LnJlc3VsdCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZmFpbChyZXN1bHQuZXJyb3IpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgIH0pO1xuXG4gICAgICAgICAgICAgICAgICAgICAgICByZXF1ZXN0LmFkZEV2ZW50TGlzdGVuZXIoXCJlcnJvclwiLCAoZXZlbnQpID0+XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgZmFpbChyZXF1ZXN0LnJlc3BvbnNlVGV4dCksXG4gICAgICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgICAgICB9KTtcblxuICAgICAgICAgICAgICAgICAgICByZXF1ZXN0Lm9wZW4oXG4gICAgICAgICAgICAgICAgICAgICAgICBcIlBPU1RcIixcbiAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuc2FuZGJveC5jbGllbnQudXJsKFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIFwiL2FwaS9hY3Rpb24vZmlsZXNfbXVsdGlwYXJ0X3VwZGF0ZVwiLFxuICAgICAgICAgICAgICAgICAgICAgICAgKSxcbiAgICAgICAgICAgICAgICAgICAgKTtcblxuICAgICAgICAgICAgICAgICAgICBpZiAodGhpcy5jc3JmVG9rZW4pIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHJlcXVlc3Quc2V0UmVxdWVzdEhlYWRlcihcIlgtQ1NSRlRva2VuXCIsIHRoaXMuY3NyZlRva2VuKTtcbiAgICAgICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgICAgIHRoaXMuX3NlbmRSZXF1ZXN0KHJlcXVlc3QsIHBhcnQsIHN0YXJ0LCBpbmZvLmlkKTtcblxuICAgICAgICAgICAgICAgICAgICByZXR1cm4gcmVzdWx0O1xuICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgIF9zZW5kUmVxdWVzdChcbiAgICAgICAgICAgICAgICAgICAgcmVxdWVzdDogWE1MSHR0cFJlcXVlc3QsXG4gICAgICAgICAgICAgICAgICAgIHBhcnQ6IEJsb2IsXG4gICAgICAgICAgICAgICAgICAgIHBvc2l0aW9uOiBudW1iZXIsXG4gICAgICAgICAgICAgICAgICAgIGlkOiBzdHJpbmcsXG4gICAgICAgICAgICAgICAgKSB7XG4gICAgICAgICAgICAgICAgICAgIGNvbnN0IGZvcm0gPSBuZXcgRm9ybURhdGEoKTtcbiAgICAgICAgICAgICAgICAgICAgZm9ybS5hcHBlbmQoXCJ1cGxvYWRcIiwgcGFydCk7XG4gICAgICAgICAgICAgICAgICAgIGZvcm0uYXBwZW5kKFwicG9zaXRpb25cIiwgU3RyaW5nKHBvc2l0aW9uKSk7XG4gICAgICAgICAgICAgICAgICAgIGZvcm0uYXBwZW5kKFwiaWRcIiwgaWQpO1xuICAgICAgICAgICAgICAgICAgICByZXF1ZXN0LnNlbmQoZm9ybSk7XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgX2NvbXBsZXRlVXBsb2FkKGluZm86IFVwbG9hZEluZm8pOiBQcm9taXNlPFVwbG9hZEluZm8+IHtcbiAgICAgICAgICAgICAgICAgICAgcmV0dXJuIG5ldyBQcm9taXNlKChkb25lLCBmYWlsKSA9PlxuICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5zYW5kYm94LmNsaWVudC5jYWxsKFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIFwiUE9TVFwiLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIFwiZmlsZXNfbXVsdGlwYXJ0X2NvbXBsZXRlXCIsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgT2JqZWN0LmFzc2lnbihcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAge30sXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuc2V0dGluZ3MuY29tcGxldGVQYXlsb2FkIHx8IHt9LFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZDogaW5mby5pZCxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICApLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIChkYXRhOiBhbnkpID0+IHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZG9uZShkYXRhLnJlc3VsdCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAocmVzcDogYW55KSA9PiB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGZhaWwoXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB0eXBlb2YgcmVzcC5yZXNwb25zZUpTT04gPT09IFwic3RyaW5nXCJcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA/IHJlc3AucmVzcG9uc2VUZXh0XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgOiByZXNwLnJlc3BvbnNlSlNPTi5lcnJvcixcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICAgICAgICAgICAgKSxcbiAgICAgICAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICB9XG59XG4iXX0=
