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
                    const keys = Object.keys(info.storage_data["parts"] || {}).map(k => Number(k));
                    let partNumber = Math.max(-1, ...keys) + 1;
                    while (start < file.size) {
                        if (!this._active.has(file)) {
                            console.info("File upload is paused");
                            return;
                        }
                        info = await this._uploadChunk(info, file.slice(start, start + this.settings.chunkSize), partNumber++, {
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
                    return new Promise((done, fail) => {
                        const url = this.sandbox.client.url(`/api/action/${this.settings.uploadAction}`);
                        const data = new FormData();
                        data.append("storage", this.settings.storage);
                        data.append("name", file.name);
                        data.append("size", String(file.size));
                        data.append("content_type", file.type || "application/octet-stream");
                        data.append("sample", file.slice(0, 2048));
                        for (let [k, v] of Object.entries(params)) {
                            data.append(k, v);
                        }
                        var csrf_field = this.sandbox
                            .jQuery("meta[name=csrf_field_name]")
                            .attr("content");
                        var csrf_token = this.sandbox
                            .jQuery("meta[name=" + csrf_field + "]")
                            .attr("content");
                        return this.sandbox.jQuery.ajax({
                            url,
                            cache: false,
                            contentType: false,
                            processData: false,
                            data: data,
                            type: "POST",
                            headers: {
                                "X-CSRFToken": csrf_token,
                            },
                            success: (data) => {
                                done(data.result);
                            },
                            error: (resp) => {
                                fail(typeof resp.responseJSON === "string"
                                    ? resp.responseText
                                    : resp.responseJSON.error);
                            },
                        });
                    });
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
                _uploadChunk(info, upload, part, extras = {}) {
                    if (!upload.size) {
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
                    this._sendRequest(request, upload, part, info.id);
                    return result;
                }
                _sendRequest(request, upload, part, id) {
                    const form = new FormData();
                    form.append("upload", upload);
                    form.append("part", String(part)); // form-data expect all values to be strings
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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZmlsZXMtLXNoYXJlZC5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uL3RzL2ZpbGVzLS1zaGFyZWQudHMiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IkFBQUEsSUFBVSxJQUFJLENBbWViO0FBbmVELFdBQVUsSUFBSTtJQUlWLElBQWlCLGFBQWEsQ0E4ZDdCO0lBOWRELFdBQWlCLGFBQWE7UUFhYixvQkFBTSxHQUFHO1lBQ2xCLGNBQWMsRUFBRSw4QkFBOEI7WUFDOUMsa0JBQWtCLEVBQUUsa0NBQWtDO1lBQ3RELGlCQUFpQixFQUFFLG1DQUFtQztTQUN6RCxDQUFDO1FBRVcsNkJBQWUsR0FBRztZQUMzQixPQUFPLEVBQUUsU0FBUztTQUNyQixDQUFDO1FBRUYsU0FBUyxNQUFNLENBQUMsSUFBVSxFQUFFLFVBQXlCLEVBQUU7WUFDbkQsTUFBTSxRQUFRLEdBQ1YsT0FBTyxDQUFDLFFBQVE7Z0JBQ2hCLFlBQVksQ0FDUixPQUFPLENBQUMsT0FBTyxJQUFJLFVBQVUsRUFDN0IsR0FBRyxDQUFDLE9BQU8sQ0FBQyxZQUFZLElBQUksRUFBRSxDQUFDLENBQ2xDLENBQUM7WUFDTixPQUFPLFFBQVEsQ0FBQyxNQUFNLENBQUMsSUFBSSxFQUFFLE9BQU8sQ0FBQyxhQUFhLElBQUksRUFBRSxDQUFDLENBQUM7UUFDOUQsQ0FBQztRQUVELFNBQVMsWUFBWSxDQUFDLE9BQWUsRUFBRSxHQUFHLE9BQVk7WUFDbEQsTUFBTSxPQUFPLEdBQTZDLFFBQVMsQ0FDL0QsT0FBTyxDQUNWLENBQUM7WUFDRixJQUFJLENBQUMsT0FBTyxFQUFFLENBQUM7Z0JBQ1gsTUFBTSxJQUFJLEtBQUssQ0FBQyxZQUFZLE9BQU8sb0JBQW9CLENBQUMsQ0FBQztZQUM3RCxDQUFDO1lBQ0QsT0FBTyxJQUFJLE9BQU8sQ0FBQyxHQUFHLE9BQU8sQ0FBQyxDQUFDO1FBQ25DLENBQUM7UUFFRCxJQUFJLENBQUMsT0FBTyxDQUFDLE1BQU0sQ0FBQyxFQUFFLEtBQUssRUFBRSxFQUFFLE1BQU0s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Q0FBQyxJQUFTLEVBQUUsRUFBRTt3QkFDVixJQUFJLENBQ0EsT0FBTyxJQUFJLENBQUMsWUFBWSxLQUFLLFFBQVE7NEJBQ2pDLENBQUMsQ0FBQyxJQUFJLENBQUMsWUFBWTs0QkFDbkIsQ0FBQyxDQUFDLElBQUksQ0FBQyxZQUFZLENBQUMsS0FBSyxDQUNoQyxDQUFDO29CQUNOLENBQUMsQ0FDSixDQUNKLENBQUM7Z0JBQ04sQ0FBQzs7WUE5UU0seUJBQWUsR0FBRztnQkFDckIsU0FBUyxFQUFFLElBQUksR0FBRyxJQUFJLEdBQUcsQ0FBQztnQkFDMUIsWUFBWSxFQUFFLHVCQUF1QjthQUN4QyxBQUhxQixDQUdwQjtZQUpPLGtCQUFTLFlBZ1JyQixDQUFBO1FBQ0wsQ0FBQyxFQWhiZ0IsUUFBUSxHQUFSLHNCQUFRLEtBQVIsc0JBQVEsUUFnYnhCO0lBQ0wsQ0FBQyxFQTlkZ0IsYUFBYSxHQUFiLGtCQUFhLEtBQWIsa0JBQWEsUUE4ZDdCO0FBQ0wsQ0FBQyxFQW5lUyxJQUFJLEtBQUosSUFBSSxRQW1lYiIsInNvdXJjZXNDb250ZW50IjpbIm5hbWVzcGFjZSBja2FuIHtcbiAgICBleHBvcnQgdmFyIHNhbmRib3g6IGFueTtcbiAgICBleHBvcnQgdmFyIHB1YnN1YjogYW55O1xuICAgIGV4cG9ydCB2YXIgbW9kdWxlOiAobmFtZTogc3RyaW5nLCBpbml0aWFsaXplcjogKCQ6IGFueSkgPT4gYW55KSA9PiBhbnk7XG4gICAgZXhwb3J0IG5hbWVzcGFjZSBDS0FORVhUX0ZJTEVTIHtcbiAgICAgICAgZXhwb3J0IHR5cGUgVXBsb2FkZXJTZXR0aW5ncyA9IHtcbiAgICAgICAgICAgIHN0b3JhZ2U6IHN0cmluZztcbiAgICAgICAgICAgIFtrZXk6IHN0cmluZ106IGFueTtcbiAgICAgICAgfTtcblxuICAgICAgICBleHBvcnQgaW50ZXJmYWNlIFVwbG9hZE9wdGlvbnMge1xuICAgICAgICAgICAgdXBsb2FkZXI/OiBhZGFwdGVycy5CYXNlO1xuICAgICAgICAgICAgYWRhcHRlcj86IHN0cmluZztcbiAgICAgICAgICAgIHVwbG9hZGVyQXJncz86IGFueVtdO1xuICAgICAgICAgICAgcmVxdWVzdFBhcmFtcz86IHsgW2tleTogc3RyaW5nXTogYW55IH07XG4gICAgICAgIH1cblxuICAgICAgICBleHBvcnQgY29uc3QgdG9waWNzID0ge1xuICAgICAgICAgICAgYWRkRmlsZVRvUXVldWU6IFwiY2thbmV4dDpmaWxlczpxdWV1ZTpmaWxlOmFkZFwiLFxuICAgICAgICAgICAgcmVzdG9yZUZpbGVJblF1ZXVlOiBcImNrYW5leHQ6ZmlsZXM6cXVldWU6ZmlsZTpyZXN0b3JlXCIsXG4gICAgICAgICAgICBxdWV1ZUl0ZW1VcGxvYWRlZDogXCJja2FuZXh0OmZpbGVzOnF1ZXVlOmZpbGU6dXBsb2FkZWRcIixcbiAgICAgICAgfTtcblxuICAgICAgICBleHBvcnQgY29uc3QgZGVmYXVsdFNldHRpbmdzID0ge1xuICAgICAgICAgICAgc3RvcmFnZTogXCJkZWZhdWx0XCIsXG4gICAgICAgIH07XG5cbiAgICAgICAgZnVuY3Rpb24gdXBsb2FkKGZpbGU6IEZpbGUsIG9wdGlvbnM6IFVwbG9hZE9wdGlvbnMgPSB7fSkge1xuICAgICAgICAgICAgY29uc3QgdXBsb2FkZXIgPVxuICAgICAgICAgICAgICAgIG9wdGlvbnMudXBsb2FkZXIgfHxcbiAgICAgICAgICAgICAgICBtYWtlVXBsb2FkZXIoXG4gICAgICAgICAgICAgICAgICAgIG9wdGlvbnMuYWRhcHRlciB8fCBcIlN0YW5kYXJkXCIsXG4gICAgICAgICAgICAgICAgICAgIC4uLihvcHRpb25zLnVwbG9hZGVyQXJncyB8fCBbXSksXG4gICAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgIHJldHVybiB1cGxvYWRlci51cGxvYWQoZmlsZSwgb3B0aW9ucy5yZXF1ZXN0UGFyYW1zIHx8IHt9KTtcbiAgICAgICAgfVxuXG4gICAgICAgIGZ1bmN0aW9uIG1ha2VVcGxvYWRlcihhZGFwdGVyOiBzdHJpbmcsIC4uLm9wdGlvbnM6IGFueSkge1xuICAgICAgICAgICAgY29uc3QgZmFjdG9yeSA9ICg8eyBba2V5OiBzdHJpbmddOiB0eXBlb2YgYWRhcHRlcnMuQmFzZSB9PmFkYXB0ZXJzKVtcbiAgICAgICAgICAgICAgICBhZGFwdGVyXG4gICAgICAgICAgICBdO1xuICAgICAgICAgICAgaWYgKCFmYWN0b3J5KSB7XG4gICAgICAgICAgICAgICAgdGhyb3cgbmV3IEVycm9yKGBVcGxvYWRlciAke2FkYXB0ZXJ9IGlzIG5vdCByZWdpc3RlcmVkYCk7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICByZXR1cm4gbmV3IGZhY3RvcnkoLi4ub3B0aW9ucyk7XG4gICAgICAgIH1cblxuICAgICAgICBja2FuLnNhbmRib3guZXh0ZW5kKHsgZmlsZXM6IHsgdXBsb2FkLCBtYWtlVXBsb2FkZXIgfSB9KTtcblxuICAgICAgICBleHBvcnQgbmFtZXNwYWNlIGFkYXB0ZXJzIHtcbiAgICAgICAgICAgIGV4cG9ydCB0eXBlIFN0b3JhZ2VEYXRhID0geyBba2V5OiBzdHJpbmddOiBhbnkgfTtcblxuICAgICAgICAgICAgZXhwb3J0IHR5cGUgVXBsb2FkSW5mbyA9IHtcbiAgICAgICAgICAgICAgICBpZDogc3RyaW5nO1xuICAgICAgICAgICAgICAgIHN0b3JhZ2VfZGF0YTogU3RvcmFnZURhdGE7XG4gICAgICAgICAgICAgICAgbG9jYXRpb246IHN0cmluZztcbiAgICAgICAgICAgICAgICBoYXNoOiBzdHJpbmc7XG4gICAgICAgICAgICAgICAgY29udGVudF90eXBlOiBzdHJpbmc7XG4gICAgICAgICAgICAgICAgc2l6ZTogbnVtYmVyO1xuICAgICAgICAgICAgfTtcblxuICAgICAgICAgICAgZXhwb3J0IGNsYXNzIEJhc2UgZXh0ZW5kcyBFdmVudFRhcmdldCB7XG4gICAgICAgICAgICAgICAgc3RhdGljIGRlZmF1bHRTZXR0aW5nczogT2JqZWN0ID0ge307XG4gICAgICAgICAgICAgICAgcHJvdGVjdGVkIHNldHRpbmdzOiBVcGxvYWRlclNldHRpbmdzO1xuICAgICAgICAgICAgICAgIHByb3RlY3RlZCBzYW5kYm94OiBhbnk7XG4gICAgICAgICAgICAgICAgcHJvdGVjdGVkIGNzcmZUb2tlbjogc3RyaW5nO1xuXG4gICAgICAgICAgICAgICAgY29uc3RydWN0b3Ioc2V0dGluZ3MgPSB7fSkge1xuICAgICAgICAgICAgICAgICAgICBzdXBlcigpO1xuICAgICAgICAgICAgICAgICAgICB0aGlzLnNldHRpbmdzID0ge1xuICAgICAgICAgICAgICAgICAgICAgICAgLi4uZGVmYXVsdFNldHRpbmdzLFxuICAgICAgICAgICAgICAgICAgICAgICAgLi4uKHRoaXMuY29uc3RydWN0b3IgYXMgdHlwZW9mIEJhc2UpLmRlZmF1bHRTZXR0aW5ncyxcbiAgICAgICAgICAgICAgICAgICAgICAgIC4uLnNldHRpbmdzLFxuICAgICAgICAgICAgICAgICAgICB9O1xuICAgICAgICAgICAgICAgICAgICB0aGlzLnNhbmRib3ggPSBja2FuLnNhbmRib3goKTtcblxuICAgICAgICAgICAgICAgICAgICBjb25zdCBjc3JmRmllbGQgPVxuICAgICAgICAgICAgICAgICAgICAgICAgZG9jdW1lbnRcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAucXVlcnlTZWxlY3RvcihcIm1ldGFbbmFtZT1jc3JmX2ZpZWxkX25hbWVdXCIpXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgPy5nZXRBdHRyaWJ1dGUoXCJjb250ZW50XCIpID8/IFwiX2NzcmZfdG9rZW5cIjtcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5jc3JmVG9rZW4gPVxuICAgICAgICAgICAgICAgICAgICAgICAgZG9jdW1lbnRcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAucXVlcnlTZWxlY3RvcihgbWV0YVtuYW1lPSR7Y3NyZkZpZWxkfV1gKVxuICAgICAgICAgICAgICAgICAgICAgICAgICAgID8uZ2V0QXR0cmlidXRlKFwiY29udGVudFwiKSB8fCBcIlwiO1xuICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgIHVwbG9hZChmaWxlOiBGaWxlLCBwYXJhbXM6IHsgW2tleTogc3RyaW5nXTogYW55IH0pIHtcbiAgICAgICAgICAgICAgICAgICAgdGhyb3cgbmV3IEVycm9yKFwiQmFzZS51cGxvYWQgaXMgbm90IGltcGxlbWVudGVkXCIpO1xuICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgIHJlc3VtZShmaWxlOiBGaWxlLCBpZDogc3RyaW5nKSB7XG4gICAgICAgICAgICAgICAgICAgIHRocm93IG5ldyBFcnJvcihcIkJhc2UucmVzdW1lIGlzIG5vdCBpbXBsZW1lbnRlZFwiKTtcbiAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICBkaXNwYXRjaFN0YXJ0KGZpbGU6IEZpbGUpIHtcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaEV2ZW50KFxuICAgICAgICAgICAgICAgICAgICAgICAgbmV3IEN1c3RvbUV2ZW50KFwic3RhcnRcIiwgeyBkZXRhaWw6IHsgZmlsZSB9IH0pLFxuICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBkaXNwYXRjaE11bHRpcGFydElkKGZpbGU6IEZpbGUsIGlkOiBzdHJpbmcpIHtcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaEV2ZW50KFxuICAgICAgICAgICAgICAgICAgICAgICAgbmV3IEN1c3RvbUV2ZW50KFwibXVsdGlwYXJ0aWRcIiwge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGRldGFpbDogeyBmaWxlLCBpZCB9LFxuICAgICAgICAgICAgICAgICAgICAgICAgfSksXG4gICAgICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGRpc3BhdGNoUHJvZ3Jlc3MoZmlsZTogRmlsZSwgbG9hZGVkOiBudW1iZXIsIHRvdGFsOiBudW1iZXIpIHtcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaEV2ZW50KFxuICAgICAgICAgICAgICAgICAgICAgICAgbmV3IEN1c3RvbUV2ZW50KFwicHJvZ3Jlc3NcIiwge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGRldGFpbDogeyBmaWxlLCBsb2FkZWQsIHRvdGFsIH0sXG4gICAgICAgICAgICAgICAgICAgICAgICB9KSxcbiAgICAgICAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgZGlzcGF0Y2hGaW5pc2goZmlsZTogRmlsZSwgcmVzdWx0OiBPYmplY3QpIHtcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaEV2ZW50KFxuICAgICAgICAgICAgICAgICAgICAgICAgbmV3IEN1c3RvbUV2ZW50KFwiZmluaXNoXCIsIHsgZGV0YWlsOiB7IGZpbGUsIHJlc3VsdCB9IH0pLFxuICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBkaXNwYXRjaEZhaWwoZmlsZTogRmlsZSwgcmVhc29uczogeyBba2V5OiBzdHJpbmddOiBzdHJpbmdbXSB9KSB7XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hFdmVudChcbiAgICAgICAgICAgICAgICAgICAgICAgIG5ldyBDdXN0b21FdmVudChcImZhaWxcIiwgeyBkZXRhaWw6IHsgZmlsZSwgcmVhc29ucyB9IH0pLFxuICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBkaXNwYXRjaEVycm9yKGZpbGU6IEZpbGUsIG1lc3NhZ2U6IHN0cmluZykge1xuICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRXZlbnQoXG4gICAgICAgICAgICAgICAgICAgICAgICBuZXcgQ3VzdG9tRXZlbnQoXCJlcnJvclwiLCB7IGRldGFpbDogeyBmaWxlLCBtZXNzYWdlIH0gfSksXG4gICAgICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICBleHBvcnQgY2xhc3MgU3RhbmRhcmQgZXh0ZW5kcyBCYXNlIHtcbiAgICAgICAgICAgICAgICBzdGF0aWMgZGVmYXVsdFNldHRpbmdzID0ge1xuICAgICAgICAgICAgICAgICAgICB1cGxvYWRBY3Rpb246IFwiZmlsZXNfZmlsZV9jcmVhdGVcIixcbiAgICAgICAgICAgICAgICB9O1xuXG4gICAgICAgICAgICAgICAgdXBsb2FkKGZpbGU6IEZpbGUsIHBhcmFtczogeyBba2V5OiBzdHJpbmddOiBhbnkgfSkge1xuICAgICAgICAgICAgICAgICAgICBjb25zdCByZXF1ZXN0ID0gbmV3IFhNTEh0dHBSZXF1ZXN0KCk7XG4gICAgICAgICAgICAgICAgICAgIGNvbnN0IHByb21pc2UgPSB0aGlzLl9hZGRMaXN0ZW5lcnMocmVxdWVzdCwgZmlsZSk7XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuX3ByZXBhcmVSZXF1ZXN0KHJlcXVlc3QsIGZpbGUpO1xuICAgICAgICAgICAgICAgICAgICB0aGlzLl9zZW5kUmVxdWVzdChyZXF1ZXN0LCBmaWxlLCBwYXJhbXMpO1xuICAgICAgICAgICAgICAgICAgICByZXR1cm4gcHJvbWlzZTtcbiAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICBfYWRkTGlzdGVuZXJzKFxuICAgICAgICAgICAgICAgICAgICByZXF1ZXN0OiBYTUxIdHRwUmVxdWVzdCxcbiAgICAgICAgICAgICAgICAgICAgZmlsZTogRmlsZSxcbiAgICAgICAgICAgICAgICApOiBQcm9taXNlPFVwbG9hZEluZm8+IHtcbiAgICAgICAgICAgICAgICAgICAgcmVxdWVzdC51cGxvYWQuYWRkRXZlbnRMaXN0ZW5lcihcImxvYWRzdGFydFwiLCAoZXZlbnQpID0+XG4gICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoU3RhcnQoZmlsZSksXG4gICAgICAgICAgICAgICAgICAgICk7XG5cbiAgICAgICAgICAgICAgICAgICAgcmVxdWVzdC51cGxvYWQuYWRkRXZlbnRMaXN0ZW5lcihcInByb2dyZXNzXCIsIChldmVudCkgPT5cbiAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hQcm9ncmVzcyhmaWxlLCBldmVudC5sb2FkZWQsIGV2ZW50LnRvdGFsKSxcbiAgICAgICAgICAgICAgICAgICAgKTtcblxuICAgICAgICAgICAgICAgICAgICByZXR1cm4gbmV3IFByb21pc2UoKGRvbmUsIGZhaWwpID0+IHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHJlcXVlc3QuYWRkRXZlbnRMaXN0ZW5lcihcImxvYWRcIiwgKGV2ZW50KSA9PiB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgY29uc3QgcmVzdWx0ID0gSlNPTi5wYXJzZShyZXF1ZXN0LnJlc3BvbnNlVGV4dCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHR5cGVvZiByZXN1bHQgPT09IFwic3RyaW5nXCIpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaEVycm9yKGZpbGUsIHJlc3VsdCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGZhaWwocmVzdWx0KTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2UgaWYgKHJlc3VsdC5zdWNjZXNzKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hGaW5pc2goZmlsZSwgcmVzdWx0LnJlc3VsdCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGRvbmUocmVzdWx0LnJlc3VsdCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaEZhaWwoZmlsZSwgcmVzdWx0LmVycm9yKTtcblxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBmYWlsKHJlc3VsdC5lcnJvcik7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgfSk7XG5cbiAgICAgICAgICAgICAgICAgICAgICAgIHJlcXVlc3QuYWRkRXZlbnRMaXN0ZW5lcihcImVycm9yXCIsIChldmVudCkgPT4ge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hFcnJvcihmaWxlLCByZXF1ZXN0LnJlc3BvbnNlVGV4dCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgZmFpbChyZXF1ZXN0LnJlc3BvbnNlVGV4dCk7XG4gICAgICAgICAgICAgICAgICAgICAgICB9KTtcbiAgICAgICAgICAgICAgICAgICAgfSk7XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgX3ByZXBhcmVSZXF1ZXN0KHJlcXVlc3Q6IFhNTEh0dHBSZXF1ZXN0LCBmaWxlOiBGaWxlKSB7XG4gICAgICAgICAgICAgICAgICAgIHJlcXVlc3Qub3BlbihcbiAgICAgICAgICAgICAgICAgICAgICAgIFwiUE9TVFwiLFxuICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5zYW5kYm94LmNsaWVudC51cmwoXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgYC9hcGkvYWN0aW9uLyR7dGhpcy5zZXR0aW5ncy51cGxvYWRBY3Rpb259YCxcbiAgICAgICAgICAgICAgICAgICAgICAgICksXG4gICAgICAgICAgICAgICAgICAgICk7XG5cbiAgICAgICAgICAgICAgICAgICAgaWYgKHRoaXMuY3NyZlRva2VuKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICByZXF1ZXN0LnNldFJlcXVlc3RIZWFkZXIoXCJYLUNTUkZUb2tlblwiLCB0aGlzLmNzcmZUb2tlbik7XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICBfc2VuZFJlcXVlc3QoXG4gICAgICAgICAgICAgICAgICAgIHJlcXVlc3Q6IFhNTEh0dHBSZXF1ZXN0LFxuICAgICAgICAgICAgICAgICAgICBmaWxlOiBGaWxlLFxuICAgICAgICAgICAgICAgICAgICBwYXJhbXM6IHsgW2tleTogc3RyaW5nXTogYW55IH0sXG4gICAgICAgICAgICAgICAgKSB7XG4gICAgICAgICAgICAgICAgICAgIGNvbnN0IGRhdGEgPSBuZXcgRm9ybURhdGEoKTtcbiAgICAgICAgICAgICAgICAgICAgZGF0YS5hcHBlbmQoXCJ1cGxvYWRcIiwgZmlsZSk7XG4gICAgICAgICAgICAgICAgICAgIGlmICghcGFyYW1zLnN0b3JhZ2UpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIGRhdGEuYXBwZW5kKFwic3RvcmFnZVwiLCB0aGlzLnNldHRpbmdzLnN0b3JhZ2UpO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIGZvciAobGV0IFtmaWVsZCwgdmFsdWVdIG9mIE9iamVjdC5lbnRyaWVzKHBhcmFtcykpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIGRhdGEuYXBwZW5kKGZpZWxkLCB2YWx1ZSk7XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgcmVxdWVzdC5zZW5kKGRhdGEpO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgZXhwb3J0IGNsYXNzIE11bHRpcGFydCBleHRlbmRzIEJhc2Uge1xuICAgICAgICAgICAgICAgIHN0YXRpYyBkZWZhdWx0U2V0dGluZ3MgPSB7XG4gICAgICAgICAgICAgICAgICAgIGNodW5rU2l6ZTogMTAyNCAqIDEwMjQgKiA1LFxuICAgICAgICAgICAgICAgICAgICB1cGxvYWRBY3Rpb246IFwiZmlsZXNfbXVsdGlwYXJ0X3N0YXJ0XCIsXG4gICAgICAgICAgICAgICAgfTtcblxuICAgICAgICAgICAgICAgIHByaXZhdGUgX2FjdGl2ZSA9IG5ldyBTZXQ8RmlsZT4oKTtcblxuICAgICAgICAgICAgICAgIGNvbnN0cnVjdG9yKHNldHRpbmdzOiBPYmplY3QpIHtcbiAgICAgICAgICAgICAgICAgICAgc3VwZXIoc2V0dGluZ3MpO1xuICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgIGFzeW5jIHVwbG9hZChmaWxlOiBGaWxlLCBwYXJhbXM6IHsgW2tleTogc3RyaW5nXTogYW55IH0pIHtcbiAgICAgICAgICAgICAgICAgICAgaWYgKHRoaXMuX2FjdGl2ZS5oYXMoZmlsZSkpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIGNvbnNvbGUud2FybihcIkZpbGUgdXBsb2FkIGluIHByb2dyZXNzXCIpO1xuICAgICAgICAgICAgICAgICAgICAgICAgcmV0dXJuO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuX2FjdGl2ZS5hZGQoZmlsZSk7XG5cbiAgICAgICAgICAgICAgICAgICAgbGV0IGluZm87XG5cbiAgICAgICAgICAgICAgICAgICAgdHJ5IHtcbiAgICAgICAgICAgICAgICAgICAgICAgIGluZm8gPSBhd2FpdCB0aGlzLl9pbml0aWFsaXplVXBsb2FkKGZpbGUsIHBhcmFtcyk7XG4gICAgICAgICAgICAgICAgICAgIH0gY2F0Y2ggKGVycikge1xuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHR5cGVvZiBlcnIgPT09IFwic3RyaW5nXCIpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRXJyb3IoZmlsZSwgZXJyKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaEZhaWwoZmlsZSwgZXJyIGFzIGFueSk7XG4gICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICByZXR1cm47XG4gICAgICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoTXVsdGlwYXJ0SWQoZmlsZSwgaW5mby5pZCk7XG5cbiAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaFN0YXJ0KGZpbGUpO1xuXG4gICAgICAgICAgICAgICAgICAgIHJldHVybiB0aGlzLl9kb1VwbG9hZChmaWxlLCBpbmZvKTtcbiAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICBhc3luYyByZXN1bWUoZmlsZTogRmlsZSwgaWQ6IHN0cmluZykge1xuICAgICAgICAgICAgICAgICAgICBpZiAodGhpcy5fYWN0aXZlLmhhcyhmaWxlKSkge1xuICAgICAgICAgICAgICAgICAgICAgICAgY29uc29sZS53YXJuKFwiRmlsZSB1cGxvYWQgaW4gcHJvZ3Jlc3NcIik7XG4gICAgICAgICAgICAgICAgICAgICAgICByZXR1cm47XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgdGhpcy5fYWN0aXZlLmFkZChmaWxlKTtcblxuICAgICAgICAgICAgICAgICAgICBsZXQgaW5mbyA9IGF3YWl0IHRoaXMuX3Nob3dVcGxvYWQoaWQpO1xuICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoU3RhcnQoZmlsZSk7XG5cbiAgICAgICAgICAgICAgICAgICAgdGhpcy5fZG9VcGxvYWQoZmlsZSwgaW5mbyk7XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgcGF1c2UoZmlsZTogRmlsZSkge1xuICAgICAgICAgICAgICAgICAgICB0aGlzLl9hY3RpdmUuZGVsZXRlKGZpbGUpO1xuICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgIGFzeW5jIF9kb1VwbG9hZChmaWxlOiBGaWxlLCBpbmZvOiBVcGxvYWRJbmZvKSB7XG4gICAgICAgICAgICAgICAgICAgIGxldCBzdGFydCA9IGluZm8uc3RvcmFnZV9kYXRhW1widXBsb2FkZWRcIl0gfHwgMDtcbiAgICAgICAgICAgICAgICAgICAgY29uc3Qga2V5cyA9IE9iamVjdC5rZXlzKGluZm8uc3RvcmFnZV9kYXRhW1wicGFydHNcIl0gfHwge30pLm1hcChrID0+IE51bWJlcihrKSlcbiAgICAgICAgICAgICAgICAgICAgbGV0IHBhcnROdW1iZXIgPSBNYXRoLm1heCgtMSwgLi4ua2V5cykgKyAxO1xuXG4gICAgICAgICAgICAgICAgICAgIHdoaWxlIChzdGFydCA8IGZpbGUuc2l6ZSkge1xuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKCF0aGlzLl9hY3RpdmUuaGFzKGZpbGUpKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgY29uc29sZS5pbmZvKFwiRmlsZSB1cGxvYWQgaXMgcGF1c2VkXCIpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHJldHVybjtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgICAgICAgICAgaW5mbyA9IGF3YWl0IHRoaXMuX3VwbG9hZENodW5rKFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGluZm8sXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgZmlsZS5zbGljZShzdGFydCwgc3RhcnQgKyB0aGlzLnNldHRpbmdzLmNodW5rU2l6ZSksXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgcGFydE51bWJlcisrLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgcHJvZ3Jlc3NEYXRhOiB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBmaWxlLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgdXBsb2FkZWQ6IGluZm8uc3RvcmFnZV9kYXRhLnVwbG9hZGVkLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgc2l6ZTogZmlsZS5zaXplLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgICAgICAgICAgICApO1xuXG4gICAgICAgICAgICAgICAgICAgICAgICBjb25zdCB1cGxvYWRlZCA9IGluZm8uc3RvcmFnZV9kYXRhLnVwbG9hZGVkO1xuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHVwbG9hZGVkIDw9IHN0YXJ0KSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgdGhyb3cgbmV3IEVycm9yKFwiVXBsb2FkZWQgc2l6ZSBpcyByZWR1Y2VkXCIpO1xuICAgICAgICAgICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoUHJvZ3Jlc3MoZmlsZSwgdXBsb2FkZWQsIGZpbGUuc2l6ZSk7XG4gICAgICAgICAgICAgICAgICAgICAgICBzdGFydCA9IHVwbG9hZGVkO1xuICAgICAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaFByb2dyZXNzKGZpbGUsIGZpbGUuc2l6ZSwgZmlsZS5zaXplKTtcbiAgICAgICAgICAgICAgICAgICAgdHJ5IHtcbiAgICAgICAgICAgICAgICAgICAgICAgIGluZm8gPSBhd2FpdCB0aGlzLl9jb21wbGV0ZVVwbG9hZChpbmZvKTtcbiAgICAgICAgICAgICAgICAgICAgfSBjYXRjaCAoZXJyKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBpZiAodHlwZW9mIGVyciA9PT0gXCJzdHJpbmdcIikge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hFcnJvcihmaWxlLCBlcnIpO1xuICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRmFpbChmaWxlLCBlcnIgYXMgYW55KTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgICAgICAgICAgcmV0dXJuO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hGaW5pc2goZmlsZSwgaW5mbyk7XG4gICAgICAgICAgICAgICAgICAgIHJldHVybiBpbmZvO1xuICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgIF9pbml0aWFsaXplVXBsb2FkKFxuICAgICAgICAgICAgICAgICAgICBmaWxlOiBGaWxlLFxuICAgICAgICAgICAgICAgICAgICBwYXJhbXM6IHsgW2tleTogc3RyaW5nXTogYW55IH0sXG4gICAgICAgICAgICAgICAgKTogUHJvbWlzZTxVcGxvYWRJbmZvPiB7XG4gICAgICAgICAgICAgICAgICAgIHJldHVybiBuZXcgUHJvbWlzZSgoZG9uZSwgZmFpbCkgPT4ge1xuICAgICAgICAgICAgICAgICAgICAgICAgY29uc3QgdXJsID0gdGhpcy5zYW5kYm94LmNsaWVudC51cmwoXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgYC9hcGkvYWN0aW9uLyR7dGhpcy5zZXR0aW5ncy51cGxvYWRBY3Rpb259YCxcbiAgICAgICAgICAgICAgICAgICAgICAgICk7XG5cbiAgICAgICAgICAgICAgICAgICAgICAgIGNvbnN0IGRhdGEgPSBuZXcgRm9ybURhdGEoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIGRhdGEuYXBwZW5kKFwic3RvcmFnZVwiLCB0aGlzLnNldHRpbmdzLnN0b3JhZ2UpO1xuICAgICAgICAgICAgICAgICAgICAgICAgZGF0YS5hcHBlbmQoXCJuYW1lXCIsIGZpbGUubmFtZSk7XG4gICAgICAgICAgICAgICAgICAgICAgICBkYXRhLmFwcGVuZChcInNpemVcIiwgU3RyaW5nKGZpbGUuc2l6ZSkpO1xuICAgICAgICAgICAgICAgICAgICAgICAgZGF0YS5hcHBlbmQoXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgXCJjb250ZW50X3R5cGVcIixcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBmaWxlLnR5cGUgfHwgXCJhcHBsaWNhdGlvbi9vY3RldC1zdHJlYW1cIixcbiAgICAgICAgICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICAgICAgICAgICAgICBkYXRhLmFwcGVuZChcInNhbXBsZVwiLCBmaWxlLnNsaWNlKDAsIDIwNDgpKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIGZvciAobGV0IFtrLHZdIG9mIE9iamVjdC5lbnRyaWVzKHBhcmFtcykpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBkYXRhLmFwcGVuZChrLCB2KVxuICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgdmFyIGNzcmZfZmllbGQgPSB0aGlzLnNhbmRib3hcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAualF1ZXJ5KFwibWV0YVtuYW1lPWNzcmZfZmllbGRfbmFtZV1cIilcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAuYXR0cihcImNvbnRlbnRcIik7XG4gICAgICAgICAgICAgICAgICAgICAgICB2YXIgY3NyZl90b2tlbiA9IHRoaXMuc2FuZGJveFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIC5qUXVlcnkoXCJtZXRhW25hbWU9XCIgKyBjc3JmX2ZpZWxkICsgXCJdXCIpXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgLmF0dHIoXCJjb250ZW50XCIpO1xuXG4gICAgICAgICAgICAgICAgICAgICAgICByZXR1cm4gdGhpcy5zYW5kYm94LmpRdWVyeS5hamF4KHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB1cmwsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgY2FjaGU6IGZhbHNlLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGNvbnRlbnRUeXBlOiBmYWxzZSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBwcm9jZXNzRGF0YTogZmFsc2UsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgZGF0YTogZGF0YSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB0eXBlOiBcIlBPU1RcIixcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBoZWFkZXJzOiB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIFwiWC1DU1JGVG9rZW5cIjogY3NyZl90b2tlbixcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHN1Y2Nlc3M6IChkYXRhOiBhbnkpID0+IHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZG9uZShkYXRhLnJlc3VsdCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBlcnJvcjogKHJlc3A6IGFueSkgPT4ge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBmYWlsKFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgdHlwZW9mIHJlc3AucmVzcG9uc2VKU09OID09PSBcInN0cmluZ1wiXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgPyByZXNwLnJlc3BvbnNlVGV4dFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDogcmVzcC5yZXNwb25zZUpTT04uZXJyb3IsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgICAgICAgICAgIH0pO1xuICAgICAgICAgICAgICAgICAgICB9KTtcbiAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICBfc2hvd1VwbG9hZChpZDogc3RyaW5nKTogUHJvbWlzZTxVcGxvYWRJbmZvPiB7XG4gICAgICAgICAgICAgICAgICAgIHJldHVybiBuZXcgUHJvbWlzZSgoZG9uZSwgZmFpbCkgPT5cbiAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuc2FuZGJveC5jbGllbnQuY2FsbChcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBcIkdFVFwiLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIFwiZmlsZXNfbXVsdGlwYXJ0X3JlZnJlc2hcIixcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBgP2lkPSR7aWR9YCxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAoZGF0YTogYW55KSA9PiB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGRvbmUoZGF0YS5yZXN1bHQpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgKHJlc3A6IGFueSkgPT4ge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBmYWlsKFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgdHlwZW9mIHJlc3AucmVzcG9uc2VKU09OID09PSBcInN0cmluZ1wiXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgPyByZXNwLnJlc3BvbnNlVGV4dFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDogcmVzcC5yZXNwb25zZUpTT04uZXJyb3IsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgICAgICAgICAgICksXG4gICAgICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgX3VwbG9hZENodW5rKFxuICAgICAgICAgICAgICAgICAgICBpbmZvOiBVcGxvYWRJbmZvLFxuICAgICAgICAgICAgICAgICAgICB1cGxvYWQ6IEJsb2IsXG4gICAgICAgICAgICAgICAgICAgIHBhcnQ6IG51bWJlcixcbiAgICAgICAgICAgICAgICAgICAgZXh0cmFzOiBhbnkgPSB7fSxcbiAgICAgICAgICAgICAgICApOiBQcm9taXNlPFVwbG9hZEluZm8+IHtcbiAgICAgICAgICAgICAgICAgICAgaWYgKCF1cGxvYWQuc2l6ZSkge1xuICAgICAgICAgICAgICAgICAgICAgICAgdGhyb3cgbmV3IEVycm9yKFwiMC1sZW5ndGggY2h1bmtzIGFyZSBub3QgYWxsb3dlZFwiKTtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICBjb25zdCByZXF1ZXN0ID0gbmV3IFhNTEh0dHBSZXF1ZXN0KCk7XG5cbiAgICAgICAgICAgICAgICAgICAgY29uc3QgcmVzdWx0ID0gbmV3IFByb21pc2U8VXBsb2FkSW5mbz4oKGRvbmUsIGZhaWwpID0+IHtcbiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChleHRyYXNbXCJwcm9ncmVzc0RhdGFcIl0pIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBjb25zdCB7IGZpbGUsIHVwbG9hZGVkLCBzaXplIH0gPVxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBleHRyYXNbXCJwcm9ncmVzc0RhdGFcIl07XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgcmVxdWVzdC51cGxvYWQuYWRkRXZlbnRMaXN0ZW5lcihcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgXCJwcm9ncmVzc1wiLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAoZXZlbnQpID0+IHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hQcm9ncmVzcyhcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBmaWxlLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHVwbG9hZGVkICsgZXZlbnQubG9hZGVkLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHNpemUsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICAgICAgICAgIHJlcXVlc3QuYWRkRXZlbnRMaXN0ZW5lcihcImxvYWRcIiwgKGV2ZW50KSA9PiB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgY29uc3QgcmVzdWx0ID0gSlNPTi5wYXJzZShyZXF1ZXN0LnJlc3BvbnNlVGV4dCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHJlc3VsdC5zdWNjZXNzKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGRvbmUocmVzdWx0LnJlc3VsdCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZmFpbChyZXN1bHQuZXJyb3IpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgIH0pO1xuXG4gICAgICAgICAgICAgICAgICAgICAgICByZXF1ZXN0LmFkZEV2ZW50TGlzdGVuZXIoXCJlcnJvclwiLCAoZXZlbnQpID0+XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgZmFpbChyZXF1ZXN0LnJlc3BvbnNlVGV4dCksXG4gICAgICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgICAgICB9KTtcblxuICAgICAgICAgICAgICAgICAgICByZXF1ZXN0Lm9wZW4oXG4gICAgICAgICAgICAgICAgICAgICAgICBcIlBPU1RcIixcbiAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuc2FuZGJveC5jbGllbnQudXJsKFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIFwiL2FwaS9hY3Rpb24vZmlsZXNfbXVsdGlwYXJ0X3VwZGF0ZVwiLFxuICAgICAgICAgICAgICAgICAgICAgICAgKSxcbiAgICAgICAgICAgICAgICAgICAgKTtcblxuICAgICAgICAgICAgICAgICAgICBpZiAodGhpcy5jc3JmVG9rZW4pIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHJlcXVlc3Quc2V0UmVxdWVzdEhlYWRlcihcIlgtQ1NSRlRva2VuXCIsIHRoaXMuY3NyZlRva2VuKTtcbiAgICAgICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgICAgIHRoaXMuX3NlbmRSZXF1ZXN0KHJlcXVlc3QsIHVwbG9hZCwgcGFydCwgaW5mby5pZCk7XG5cbiAgICAgICAgICAgICAgICAgICAgcmV0dXJuIHJlc3VsdDtcbiAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICBfc2VuZFJlcXVlc3QoXG4gICAgICAgICAgICAgICAgICAgIHJlcXVlc3Q6IFhNTEh0dHBSZXF1ZXN0LFxuICAgICAgICAgICAgICAgICAgICB1cGxvYWQ6IEJsb2IsXG4gICAgICAgICAgICAgICAgICAgIHBhcnQ6IG51bWJlcixcbiAgICAgICAgICAgICAgICAgICAgaWQ6IHN0cmluZyxcbiAgICAgICAgICAgICAgICApIHtcbiAgICAgICAgICAgICAgICAgICAgY29uc3QgZm9ybSA9IG5ldyBGb3JtRGF0YSgpO1xuICAgICAgICAgICAgICAgICAgICBmb3JtLmFwcGVuZChcInVwbG9hZFwiLCB1cGxvYWQpO1xuICAgICAgICAgICAgICAgICAgICBmb3JtLmFwcGVuZChcInBhcnRcIiwgU3RyaW5nKHBhcnQpKTsgLy8gZm9ybS1kYXRhIGV4cGVjdCBhbGwgdmFsdWVzIHRvIGJlIHN0cmluZ3NcbiAgICAgICAgICAgICAgICAgICAgZm9ybS5hcHBlbmQoXCJpZFwiLCBpZCk7XG4gICAgICAgICAgICAgICAgICAgIHJlcXVlc3Quc2VuZChmb3JtKTtcbiAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICBfY29tcGxldGVVcGxvYWQoaW5mbzogVXBsb2FkSW5mbyk6IFByb21pc2U8VXBsb2FkSW5mbz4ge1xuICAgICAgICAgICAgICAgICAgICByZXR1cm4gbmV3IFByb21pc2UoKGRvbmUsIGZhaWwpID0+XG4gICAgICAgICAgICAgICAgICAgICAgICB0aGlzLnNhbmRib3guY2xpZW50LmNhbGwoXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgXCJQT1NUXCIsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgXCJmaWxlc19tdWx0aXBhcnRfY29tcGxldGVcIixcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBPYmplY3QuYXNzaWduKFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB7fSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5zZXR0aW5ncy5jb21wbGV0ZVBheWxvYWQgfHwge30sXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGlkOiBpbmZvLmlkLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICksXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgKGRhdGE6IGFueSkgPT4ge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBkb25lKGRhdGEucmVzdWx0KTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIChyZXNwOiBhbnkpID0+IHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZmFpbChcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHR5cGVvZiByZXNwLnJlc3BvbnNlSlNPTiA9PT0gXCJzdHJpbmdcIlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgID8gcmVzcC5yZXNwb25zZVRleHRcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA6IHJlc3AucmVzcG9uc2VKU09OLmVycm9yLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgICAgICAgICAgICApLFxuICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgIH1cbn1cbiJdfQ==