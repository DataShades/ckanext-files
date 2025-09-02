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
                    const partNumber = Math.max(-1, ...keys) + 1;
                    while (start < file.size) {
                        if (!this._active.has(file)) {
                            console.info("File upload is paused");
                            return;
                        }
                        info = await this._uploadChunk(info, file.slice(start, start + this.settings.chunkSize), partNumber, {
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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZmlsZXMtLXNoYXJlZC5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uL3RzL2ZpbGVzLS1zaGFyZWQudHMiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IkFBQUEsSUFBVSxJQUFJLENBaWViO0FBamVELFdBQVUsSUFBSTtJQUlWLElBQWlCLGFBQWEsQ0E0ZDdCO0lBNWRELFdBQWlCLGFBQWE7UUFhYixvQkFBTSxHQUFHO1lBQ2xCLGNBQWMsRUFBRSw4QkFBOEI7WUFDOUMsa0JBQWtCLEVBQUUsa0NBQWtDO1lBQ3RELGlCQUFpQixFQUFFLG1DQUFtQztTQUN6RCxDQUFDO1FBRVcsNkJBQWUsR0FBRztZQUMzQixPQUFPLEVBQUUsU0FBUztTQUNyQixDQUFDO1FBRUYsU0FBUyxNQUFNLENBQUMsSUFBVSxFQUFFLFVBQXlCLEVBQUU7WUFDbkQsTUFBTSxRQUFRLEdBQ1YsT0FBTyxDQUFDLFFBQVE7Z0JBQ2hCLFlBQVksQ0FDUixPQUFPLENBQUMsT0FBTyxJQUFJLFVBQVUsRUFDN0IsR0FBRyxDQUFDLE9BQU8sQ0FBQyxZQUFZLElBQUksRUFBRSxDQUFDLENBQ2xDLENBQUM7WUFDTixPQUFPLFFBQVEsQ0FBQyxNQUFNLENBQUMsSUFBSSxFQUFFLE9BQU8sQ0FBQyxhQUFhLElBQUksRUFBRSxDQUFDLENBQUM7UUFDOUQsQ0FBQztRQUVELFNBQVMsWUFBWSxDQUFDLE9BQWUsRUFBRSxHQUFHLE9BQVk7WUFDbEQsTUFBTSxPQUFPLEdBQTZDLFFBQVMsQ0FDL0QsT0FBTyxDQUNWLENBQUM7WUFDRixJQUFJLENBQUMsT0FBTyxFQUFFLENBQUM7Z0JBQ1gsTUFBTSxJQUFJLEtBQUssQ0FBQyxZQUFZLE9BQU8sb0JBQW9CLENBQUMsQ0FBQztZQUM3RCxDQUFDO1lBQ0QsT0FBTyxJQUFJLE9BQU8sQ0FBQyxHQUFHLE9BQU8sQ0FBQyxDQUFDO1FBQ25DLENBQUM7UUFFRCxJQUFJLENBQUMsT0FBTyxDQUFDLE1BQU0sQ0FBQyxFQUFFLEtBQUssRUFBRSxFQUFFLE1BQU0s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TixDQUFDLENBQ0osQ0FDSixDQUFDO2dCQUNOLENBQUM7O1lBNVFNLHlCQUFlLEdBQUc7Z0JBQ3JCLFNBQVMsRUFBRSxJQUFJLEdBQUcsSUFBSSxHQUFHLENBQUM7Z0JBQzFCLFlBQVksRUFBRSx1QkFBdUI7YUFDeEMsQUFIcUIsQ0FHcEI7WUFKTyxrQkFBUyxZQThRckIsQ0FBQTtRQUNMLENBQUMsRUE5YWdCLFFBQVEsR0FBUixzQkFBUSxLQUFSLHNCQUFRLFFBOGF4QjtJQUNMLENBQUMsRUE1ZGdCLGFBQWEsR0FBYixrQkFBYSxLQUFiLGtCQUFhLFFBNGQ3QjtBQUNMLENBQUMsRUFqZVMsSUFBSSxLQUFKLElBQUksUUFpZWIiLCJzb3VyY2VzQ29udGVudCI6WyJuYW1lc3BhY2UgY2thbiB7XG4gICAgZXhwb3J0IHZhciBzYW5kYm94OiBhbnk7XG4gICAgZXhwb3J0IHZhciBwdWJzdWI6IGFueTtcbiAgICBleHBvcnQgdmFyIG1vZHVsZTogKG5hbWU6IHN0cmluZywgaW5pdGlhbGl6ZXI6ICgkOiBhbnkpID0+IGFueSkgPT4gYW55O1xuICAgIGV4cG9ydCBuYW1lc3BhY2UgQ0tBTkVYVF9GSUxFUyB7XG4gICAgICAgIGV4cG9ydCB0eXBlIFVwbG9hZGVyU2V0dGluZ3MgPSB7XG4gICAgICAgICAgICBzdG9yYWdlOiBzdHJpbmc7XG4gICAgICAgICAgICBba2V5OiBzdHJpbmddOiBhbnk7XG4gICAgICAgIH07XG5cbiAgICAgICAgZXhwb3J0IGludGVyZmFjZSBVcGxvYWRPcHRpb25zIHtcbiAgICAgICAgICAgIHVwbG9hZGVyPzogYWRhcHRlcnMuQmFzZTtcbiAgICAgICAgICAgIGFkYXB0ZXI/OiBzdHJpbmc7XG4gICAgICAgICAgICB1cGxvYWRlckFyZ3M/OiBhbnlbXTtcbiAgICAgICAgICAgIHJlcXVlc3RQYXJhbXM/OiB7IFtrZXk6IHN0cmluZ106IGFueSB9O1xuICAgICAgICB9XG5cbiAgICAgICAgZXhwb3J0IGNvbnN0IHRvcGljcyA9IHtcbiAgICAgICAgICAgIGFkZEZpbGVUb1F1ZXVlOiBcImNrYW5leHQ6ZmlsZXM6cXVldWU6ZmlsZTphZGRcIixcbiAgICAgICAgICAgIHJlc3RvcmVGaWxlSW5RdWV1ZTogXCJja2FuZXh0OmZpbGVzOnF1ZXVlOmZpbGU6cmVzdG9yZVwiLFxuICAgICAgICAgICAgcXVldWVJdGVtVXBsb2FkZWQ6IFwiY2thbmV4dDpmaWxlczpxdWV1ZTpmaWxlOnVwbG9hZGVkXCIsXG4gICAgICAgIH07XG5cbiAgICAgICAgZXhwb3J0IGNvbnN0IGRlZmF1bHRTZXR0aW5ncyA9IHtcbiAgICAgICAgICAgIHN0b3JhZ2U6IFwiZGVmYXVsdFwiLFxuICAgICAgICB9O1xuXG4gICAgICAgIGZ1bmN0aW9uIHVwbG9hZChmaWxlOiBGaWxlLCBvcHRpb25zOiBVcGxvYWRPcHRpb25zID0ge30pIHtcbiAgICAgICAgICAgIGNvbnN0IHVwbG9hZGVyID1cbiAgICAgICAgICAgICAgICBvcHRpb25zLnVwbG9hZGVyIHx8XG4gICAgICAgICAgICAgICAgbWFrZVVwbG9hZGVyKFxuICAgICAgICAgICAgICAgICAgICBvcHRpb25zLmFkYXB0ZXIgfHwgXCJTdGFuZGFyZFwiLFxuICAgICAgICAgICAgICAgICAgICAuLi4ob3B0aW9ucy51cGxvYWRlckFyZ3MgfHwgW10pLFxuICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICByZXR1cm4gdXBsb2FkZXIudXBsb2FkKGZpbGUsIG9wdGlvbnMucmVxdWVzdFBhcmFtcyB8fCB7fSk7XG4gICAgICAgIH1cblxuICAgICAgICBmdW5jdGlvbiBtYWtlVXBsb2FkZXIoYWRhcHRlcjogc3RyaW5nLCAuLi5vcHRpb25zOiBhbnkpIHtcbiAgICAgICAgICAgIGNvbnN0IGZhY3RvcnkgPSAoPHsgW2tleTogc3RyaW5nXTogdHlwZW9mIGFkYXB0ZXJzLkJhc2UgfT5hZGFwdGVycylbXG4gICAgICAgICAgICAgICAgYWRhcHRlclxuICAgICAgICAgICAgXTtcbiAgICAgICAgICAgIGlmICghZmFjdG9yeSkge1xuICAgICAgICAgICAgICAgIHRocm93IG5ldyBFcnJvcihgVXBsb2FkZXIgJHthZGFwdGVyfSBpcyBub3QgcmVnaXN0ZXJlZGApO1xuICAgICAgICAgICAgfVxuICAgICAgICAgICAgcmV0dXJuIG5ldyBmYWN0b3J5KC4uLm9wdGlvbnMpO1xuICAgICAgICB9XG5cbiAgICAgICAgY2thbi5zYW5kYm94LmV4dGVuZCh7IGZpbGVzOiB7IHVwbG9hZCwgbWFrZVVwbG9hZGVyIH0gfSk7XG5cbiAgICAgICAgZXhwb3J0IG5hbWVzcGFjZSBhZGFwdGVycyB7XG4gICAgICAgICAgICBleHBvcnQgdHlwZSBTdG9yYWdlRGF0YSA9IHsgW2tleTogc3RyaW5nXTogYW55IH07XG5cbiAgICAgICAgICAgIGV4cG9ydCB0eXBlIFVwbG9hZEluZm8gPSB7XG4gICAgICAgICAgICAgICAgaWQ6IHN0cmluZztcbiAgICAgICAgICAgICAgICBzdG9yYWdlX2RhdGE6IFN0b3JhZ2VEYXRhO1xuICAgICAgICAgICAgICAgIGxvY2F0aW9uOiBzdHJpbmc7XG4gICAgICAgICAgICAgICAgaGFzaDogc3RyaW5nO1xuICAgICAgICAgICAgICAgIGNvbnRlbnRfdHlwZTogc3RyaW5nO1xuICAgICAgICAgICAgICAgIHNpemU6IG51bWJlcjtcbiAgICAgICAgICAgIH07XG5cbiAgICAgICAgICAgIGV4cG9ydCBjbGFzcyBCYXNlIGV4dGVuZHMgRXZlbnRUYXJnZXQge1xuICAgICAgICAgICAgICAgIHN0YXRpYyBkZWZhdWx0U2V0dGluZ3M6IE9iamVjdCA9IHt9O1xuICAgICAgICAgICAgICAgIHByb3RlY3RlZCBzZXR0aW5nczogVXBsb2FkZXJTZXR0aW5ncztcbiAgICAgICAgICAgICAgICBwcm90ZWN0ZWQgc2FuZGJveDogYW55O1xuICAgICAgICAgICAgICAgIHByb3RlY3RlZCBjc3JmVG9rZW46IHN0cmluZztcblxuICAgICAgICAgICAgICAgIGNvbnN0cnVjdG9yKHNldHRpbmdzID0ge30pIHtcbiAgICAgICAgICAgICAgICAgICAgc3VwZXIoKTtcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5zZXR0aW5ncyA9IHtcbiAgICAgICAgICAgICAgICAgICAgICAgIC4uLmRlZmF1bHRTZXR0aW5ncyxcbiAgICAgICAgICAgICAgICAgICAgICAgIC4uLih0aGlzLmNvbnN0cnVjdG9yIGFzIHR5cGVvZiBCYXNlKS5kZWZhdWx0U2V0dGluZ3MsXG4gICAgICAgICAgICAgICAgICAgICAgICAuLi5zZXR0aW5ncyxcbiAgICAgICAgICAgICAgICAgICAgfTtcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5zYW5kYm94ID0gY2thbi5zYW5kYm94KCk7XG5cbiAgICAgICAgICAgICAgICAgICAgY29uc3QgY3NyZkZpZWxkID1cbiAgICAgICAgICAgICAgICAgICAgICAgIGRvY3VtZW50XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgLnF1ZXJ5U2VsZWN0b3IoXCJtZXRhW25hbWU9Y3NyZl9maWVsZF9uYW1lXVwiKVxuICAgICAgICAgICAgICAgICAgICAgICAgICAgID8uZ2V0QXR0cmlidXRlKFwiY29udGVudFwiKSA/PyBcIl9jc3JmX3Rva2VuXCI7XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuY3NyZlRva2VuID1cbiAgICAgICAgICAgICAgICAgICAgICAgIGRvY3VtZW50XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgLnF1ZXJ5U2VsZWN0b3IoYG1ldGFbbmFtZT0ke2NzcmZGaWVsZH1dYClcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICA/LmdldEF0dHJpYnV0ZShcImNvbnRlbnRcIikgfHwgXCJcIjtcbiAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICB1cGxvYWQoZmlsZTogRmlsZSwgcGFyYW1zOiB7IFtrZXk6IHN0cmluZ106IGFueSB9KSB7XG4gICAgICAgICAgICAgICAgICAgIHRocm93IG5ldyBFcnJvcihcIkJhc2UudXBsb2FkIGlzIG5vdCBpbXBsZW1lbnRlZFwiKTtcbiAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICByZXN1bWUoZmlsZTogRmlsZSwgaWQ6IHN0cmluZykge1xuICAgICAgICAgICAgICAgICAgICB0aHJvdyBuZXcgRXJyb3IoXCJCYXNlLnJlc3VtZSBpcyBub3QgaW1wbGVtZW50ZWRcIik7XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgZGlzcGF0Y2hTdGFydChmaWxlOiBGaWxlKSB7XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hFdmVudChcbiAgICAgICAgICAgICAgICAgICAgICAgIG5ldyBDdXN0b21FdmVudChcInN0YXJ0XCIsIHsgZGV0YWlsOiB7IGZpbGUgfSB9KSxcbiAgICAgICAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgZGlzcGF0Y2hNdWx0aXBhcnRJZChmaWxlOiBGaWxlLCBpZDogc3RyaW5nKSB7XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hFdmVudChcbiAgICAgICAgICAgICAgICAgICAgICAgIG5ldyBDdXN0b21FdmVudChcIm11bHRpcGFydGlkXCIsIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBkZXRhaWw6IHsgZmlsZSwgaWQgfSxcbiAgICAgICAgICAgICAgICAgICAgICAgIH0pLFxuICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBkaXNwYXRjaFByb2dyZXNzKGZpbGU6IEZpbGUsIGxvYWRlZDogbnVtYmVyLCB0b3RhbDogbnVtYmVyKSB7XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hFdmVudChcbiAgICAgICAgICAgICAgICAgICAgICAgIG5ldyBDdXN0b21FdmVudChcInByb2dyZXNzXCIsIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBkZXRhaWw6IHsgZmlsZSwgbG9hZGVkLCB0b3RhbCB9LFxuICAgICAgICAgICAgICAgICAgICAgICAgfSksXG4gICAgICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGRpc3BhdGNoRmluaXNoKGZpbGU6IEZpbGUsIHJlc3VsdDogT2JqZWN0KSB7XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hFdmVudChcbiAgICAgICAgICAgICAgICAgICAgICAgIG5ldyBDdXN0b21FdmVudChcImZpbmlzaFwiLCB7IGRldGFpbDogeyBmaWxlLCByZXN1bHQgfSB9KSxcbiAgICAgICAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgZGlzcGF0Y2hGYWlsKGZpbGU6IEZpbGUsIHJlYXNvbnM6IHsgW2tleTogc3RyaW5nXTogc3RyaW5nW10gfSkge1xuICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRXZlbnQoXG4gICAgICAgICAgICAgICAgICAgICAgICBuZXcgQ3VzdG9tRXZlbnQoXCJmYWlsXCIsIHsgZGV0YWlsOiB7IGZpbGUsIHJlYXNvbnMgfSB9KSxcbiAgICAgICAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgZGlzcGF0Y2hFcnJvcihmaWxlOiBGaWxlLCBtZXNzYWdlOiBzdHJpbmcpIHtcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaEV2ZW50KFxuICAgICAgICAgICAgICAgICAgICAgICAgbmV3IEN1c3RvbUV2ZW50KFwiZXJyb3JcIiwgeyBkZXRhaWw6IHsgZmlsZSwgbWVzc2FnZSB9IH0pLFxuICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgZXhwb3J0IGNsYXNzIFN0YW5kYXJkIGV4dGVuZHMgQmFzZSB7XG4gICAgICAgICAgICAgICAgc3RhdGljIGRlZmF1bHRTZXR0aW5ncyA9IHtcbiAgICAgICAgICAgICAgICAgICAgdXBsb2FkQWN0aW9uOiBcImZpbGVzX2ZpbGVfY3JlYXRlXCIsXG4gICAgICAgICAgICAgICAgfTtcblxuICAgICAgICAgICAgICAgIHVwbG9hZChmaWxlOiBGaWxlLCBwYXJhbXM6IHsgW2tleTogc3RyaW5nXTogYW55IH0pIHtcbiAgICAgICAgICAgICAgICAgICAgY29uc3QgcmVxdWVzdCA9IG5ldyBYTUxIdHRwUmVxdWVzdCgpO1xuICAgICAgICAgICAgICAgICAgICBjb25zdCBwcm9taXNlID0gdGhpcy5fYWRkTGlzdGVuZXJzKHJlcXVlc3QsIGZpbGUpO1xuICAgICAgICAgICAgICAgICAgICB0aGlzLl9wcmVwYXJlUmVxdWVzdChyZXF1ZXN0LCBmaWxlKTtcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5fc2VuZFJlcXVlc3QocmVxdWVzdCwgZmlsZSwgcGFyYW1zKTtcbiAgICAgICAgICAgICAgICAgICAgcmV0dXJuIHByb21pc2U7XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgX2FkZExpc3RlbmVycyhcbiAgICAgICAgICAgICAgICAgICAgcmVxdWVzdDogWE1MSHR0cFJlcXVlc3QsXG4gICAgICAgICAgICAgICAgICAgIGZpbGU6IEZpbGUsXG4gICAgICAgICAgICAgICAgKTogUHJvbWlzZTxVcGxvYWRJbmZvPiB7XG4gICAgICAgICAgICAgICAgICAgIHJlcXVlc3QudXBsb2FkLmFkZEV2ZW50TGlzdGVuZXIoXCJsb2Fkc3RhcnRcIiwgKGV2ZW50KSA9PlxuICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaFN0YXJ0KGZpbGUpLFxuICAgICAgICAgICAgICAgICAgICApO1xuXG4gICAgICAgICAgICAgICAgICAgIHJlcXVlc3QudXBsb2FkLmFkZEV2ZW50TGlzdGVuZXIoXCJwcm9ncmVzc1wiLCAoZXZlbnQpID0+XG4gICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoUHJvZ3Jlc3MoZmlsZSwgZXZlbnQubG9hZGVkLCBldmVudC50b3RhbCksXG4gICAgICAgICAgICAgICAgICAgICk7XG5cbiAgICAgICAgICAgICAgICAgICAgcmV0dXJuIG5ldyBQcm9taXNlKChkb25lLCBmYWlsKSA9PiB7XG4gICAgICAgICAgICAgICAgICAgICAgICByZXF1ZXN0LmFkZEV2ZW50TGlzdGVuZXIoXCJsb2FkXCIsIChldmVudCkgPT4ge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGNvbnN0IHJlc3VsdCA9IEpTT04ucGFyc2UocmVxdWVzdC5yZXNwb25zZVRleHQpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGlmICh0eXBlb2YgcmVzdWx0ID09PSBcInN0cmluZ1wiKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hFcnJvcihmaWxlLCByZXN1bHQpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBmYWlsKHJlc3VsdCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIGlmIChyZXN1bHQuc3VjY2Vzcykge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRmluaXNoKGZpbGUsIHJlc3VsdC5yZXN1bHQpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBkb25lKHJlc3VsdC5yZXN1bHQpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hGYWlsKGZpbGUsIHJlc3VsdC5lcnJvcik7XG5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZmFpbChyZXN1bHQuZXJyb3IpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgIH0pO1xuXG4gICAgICAgICAgICAgICAgICAgICAgICByZXF1ZXN0LmFkZEV2ZW50TGlzdGVuZXIoXCJlcnJvclwiLCAoZXZlbnQpID0+IHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRXJyb3IoZmlsZSwgcmVxdWVzdC5yZXNwb25zZVRleHQpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGZhaWwocmVxdWVzdC5yZXNwb25zZVRleHQpO1xuICAgICAgICAgICAgICAgICAgICAgICAgfSk7XG4gICAgICAgICAgICAgICAgICAgIH0pO1xuICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgIF9wcmVwYXJlUmVxdWVzdChyZXF1ZXN0OiBYTUxIdHRwUmVxdWVzdCwgZmlsZTogRmlsZSkge1xuICAgICAgICAgICAgICAgICAgICByZXF1ZXN0Lm9wZW4oXG4gICAgICAgICAgICAgICAgICAgICAgICBcIlBPU1RcIixcbiAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuc2FuZGJveC5jbGllbnQudXJsKFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGAvYXBpL2FjdGlvbi8ke3RoaXMuc2V0dGluZ3MudXBsb2FkQWN0aW9ufWAsXG4gICAgICAgICAgICAgICAgICAgICAgICApLFxuICAgICAgICAgICAgICAgICAgICApO1xuXG4gICAgICAgICAgICAgICAgICAgIGlmICh0aGlzLmNzcmZUb2tlbikge1xuICAgICAgICAgICAgICAgICAgICAgICAgcmVxdWVzdC5zZXRSZXF1ZXN0SGVhZGVyKFwiWC1DU1JGVG9rZW5cIiwgdGhpcy5jc3JmVG9rZW4pO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgX3NlbmRSZXF1ZXN0KFxuICAgICAgICAgICAgICAgICAgICByZXF1ZXN0OiBYTUxIdHRwUmVxdWVzdCxcbiAgICAgICAgICAgICAgICAgICAgZmlsZTogRmlsZSxcbiAgICAgICAgICAgICAgICAgICAgcGFyYW1zOiB7IFtrZXk6IHN0cmluZ106IGFueSB9LFxuICAgICAgICAgICAgICAgICkge1xuICAgICAgICAgICAgICAgICAgICBjb25zdCBkYXRhID0gbmV3IEZvcm1EYXRhKCk7XG4gICAgICAgICAgICAgICAgICAgIGRhdGEuYXBwZW5kKFwidXBsb2FkXCIsIGZpbGUpO1xuICAgICAgICAgICAgICAgICAgICBpZiAoIXBhcmFtcy5zdG9yYWdlKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBkYXRhLmFwcGVuZChcInN0b3JhZ2VcIiwgdGhpcy5zZXR0aW5ncy5zdG9yYWdlKTtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICBmb3IgKGxldCBbZmllbGQsIHZhbHVlXSBvZiBPYmplY3QuZW50cmllcyhwYXJhbXMpKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBkYXRhLmFwcGVuZChmaWVsZCwgdmFsdWUpO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIHJlcXVlc3Quc2VuZChkYXRhKTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9XG5cbiAgICAgICAgICAgIGV4cG9ydCBjbGFzcyBNdWx0aXBhcnQgZXh0ZW5kcyBCYXNlIHtcbiAgICAgICAgICAgICAgICBzdGF0aWMgZGVmYXVsdFNldHRpbmdzID0ge1xuICAgICAgICAgICAgICAgICAgICBjaHVua1NpemU6IDEwMjQgKiAxMDI0ICogNSxcbiAgICAgICAgICAgICAgICAgICAgdXBsb2FkQWN0aW9uOiBcImZpbGVzX211bHRpcGFydF9zdGFydFwiLFxuICAgICAgICAgICAgICAgIH07XG5cbiAgICAgICAgICAgICAgICBwcml2YXRlIF9hY3RpdmUgPSBuZXcgU2V0PEZpbGU+KCk7XG5cbiAgICAgICAgICAgICAgICBjb25zdHJ1Y3RvcihzZXR0aW5nczogT2JqZWN0KSB7XG4gICAgICAgICAgICAgICAgICAgIHN1cGVyKHNldHRpbmdzKTtcbiAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICBhc3luYyB1cGxvYWQoZmlsZTogRmlsZSwgcGFyYW1zOiB7IFtrZXk6IHN0cmluZ106IGFueSB9KSB7XG4gICAgICAgICAgICAgICAgICAgIGlmICh0aGlzLl9hY3RpdmUuaGFzKGZpbGUpKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBjb25zb2xlLndhcm4oXCJGaWxlIHVwbG9hZCBpbiBwcm9ncmVzc1wiKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIHJldHVybjtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICB0aGlzLl9hY3RpdmUuYWRkKGZpbGUpO1xuXG4gICAgICAgICAgICAgICAgICAgIGxldCBpbmZvO1xuXG4gICAgICAgICAgICAgICAgICAgIHRyeSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBpbmZvID0gYXdhaXQgdGhpcy5faW5pdGlhbGl6ZVVwbG9hZChmaWxlLCBwYXJhbXMpO1xuICAgICAgICAgICAgICAgICAgICB9IGNhdGNoIChlcnIpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIGlmICh0eXBlb2YgZXJyID09PSBcInN0cmluZ1wiKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaEVycm9yKGZpbGUsIGVycik7XG4gICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hGYWlsKGZpbGUsIGVyciBhcyBhbnkpO1xuICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgcmV0dXJuO1xuICAgICAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaE11bHRpcGFydElkKGZpbGUsIGluZm8uaWQpO1xuXG4gICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hTdGFydChmaWxlKTtcblxuICAgICAgICAgICAgICAgICAgICByZXR1cm4gdGhpcy5fZG9VcGxvYWQoZmlsZSwgaW5mbyk7XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgYXN5bmMgcmVzdW1lKGZpbGU6IEZpbGUsIGlkOiBzdHJpbmcpIHtcbiAgICAgICAgICAgICAgICAgICAgaWYgKHRoaXMuX2FjdGl2ZS5oYXMoZmlsZSkpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIGNvbnNvbGUud2FybihcIkZpbGUgdXBsb2FkIGluIHByb2dyZXNzXCIpO1xuICAgICAgICAgICAgICAgICAgICAgICAgcmV0dXJuO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuX2FjdGl2ZS5hZGQoZmlsZSk7XG5cbiAgICAgICAgICAgICAgICAgICAgbGV0IGluZm8gPSBhd2FpdCB0aGlzLl9zaG93VXBsb2FkKGlkKTtcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaFN0YXJ0KGZpbGUpO1xuXG4gICAgICAgICAgICAgICAgICAgIHRoaXMuX2RvVXBsb2FkKGZpbGUsIGluZm8pO1xuICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgIHBhdXNlKGZpbGU6IEZpbGUpIHtcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5fYWN0aXZlLmRlbGV0ZShmaWxlKTtcbiAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICBhc3luYyBfZG9VcGxvYWQoZmlsZTogRmlsZSwgaW5mbzogVXBsb2FkSW5mbykge1xuICAgICAgICAgICAgICAgICAgICBsZXQgc3RhcnQgPSBpbmZvLnN0b3JhZ2VfZGF0YVtcInVwbG9hZGVkXCJdIHx8IDA7XG4gICAgICAgICAgICAgICAgICAgIGNvbnN0IGtleXMgPSBPYmplY3Qua2V5cyhpbmZvLnN0b3JhZ2VfZGF0YVtcInBhcnRzXCJdIHx8IHt9KS5tYXAoayA9PiBOdW1iZXIoaykpXG4gICAgICAgICAgICAgICAgICAgIGNvbnN0IHBhcnROdW1iZXIgPSBNYXRoLm1heCgtMSwgLi4ua2V5cykgKyAxO1xuXG4gICAgICAgICAgICAgICAgICAgIHdoaWxlIChzdGFydCA8IGZpbGUuc2l6ZSkge1xuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKCF0aGlzLl9hY3RpdmUuaGFzKGZpbGUpKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgY29uc29sZS5pbmZvKFwiRmlsZSB1cGxvYWQgaXMgcGF1c2VkXCIpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHJldHVybjtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgICAgICAgICAgaW5mbyA9IGF3YWl0IHRoaXMuX3VwbG9hZENodW5rKFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGluZm8sXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgZmlsZS5zbGljZShzdGFydCwgc3RhcnQgKyB0aGlzLnNldHRpbmdzLmNodW5rU2l6ZSksXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgcGFydE51bWJlcixcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHByb2dyZXNzRGF0YToge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZmlsZSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHVwbG9hZGVkOiBpbmZvLnN0b3JhZ2VfZGF0YS51cGxvYWRlZCxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHNpemU6IGZpbGUuc2l6ZSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICAgICAgICAgICAgKTtcblxuICAgICAgICAgICAgICAgICAgICAgICAgY29uc3QgdXBsb2FkZWQgPSBpbmZvLnN0b3JhZ2VfZGF0YS51cGxvYWRlZDtcbiAgICAgICAgICAgICAgICAgICAgICAgIGlmICh1cGxvYWRlZCA8PSBzdGFydCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHRocm93IG5ldyBFcnJvcihcIlVwbG9hZGVkIHNpemUgaXMgcmVkdWNlZFwiKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaFByb2dyZXNzKGZpbGUsIHVwbG9hZGVkLCBmaWxlLnNpemUpO1xuICAgICAgICAgICAgICAgICAgICAgICAgc3RhcnQgPSB1cGxvYWRlZDtcbiAgICAgICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hQcm9ncmVzcyhmaWxlLCBmaWxlLnNpemUsIGZpbGUuc2l6ZSk7XG4gICAgICAgICAgICAgICAgICAgIHRyeSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBpbmZvID0gYXdhaXQgdGhpcy5fY29tcGxldGVVcGxvYWQoaW5mbyk7XG4gICAgICAgICAgICAgICAgICAgIH0gY2F0Y2ggKGVycikge1xuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHR5cGVvZiBlcnIgPT09IFwic3RyaW5nXCIpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRXJyb3IoZmlsZSwgZXJyKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaEZhaWwoZmlsZSwgZXJyIGFzIGFueSk7XG4gICAgICAgICAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICAgICAgICAgIHJldHVybjtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRmluaXNoKGZpbGUsIGluZm8pO1xuICAgICAgICAgICAgICAgICAgICByZXR1cm4gaW5mbztcbiAgICAgICAgICAgICAgICB9XG5cbiAgICAgICAgICAgICAgICBfaW5pdGlhbGl6ZVVwbG9hZChcbiAgICAgICAgICAgICAgICAgICAgZmlsZTogRmlsZSxcbiAgICAgICAgICAgICAgICAgICAgcGFyYW1zOiB7IFtrZXk6IHN0cmluZ106IGFueSB9LFxuICAgICAgICAgICAgICAgICk6IFByb21pc2U8VXBsb2FkSW5mbz4ge1xuICAgICAgICAgICAgICAgICAgICByZXR1cm4gbmV3IFByb21pc2UoKGRvbmUsIGZhaWwpID0+IHtcbiAgICAgICAgICAgICAgICAgICAgICAgIGNvbnN0IHVybCA9IHRoaXMuc2FuZGJveC5jbGllbnQudXJsKFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGAvYXBpL2FjdGlvbi8ke3RoaXMuc2V0dGluZ3MudXBsb2FkQWN0aW9ufWAsXG4gICAgICAgICAgICAgICAgICAgICAgICApO1xuXG4gICAgICAgICAgICAgICAgICAgICAgICBjb25zdCBkYXRhID0gbmV3IEZvcm1EYXRhKCk7XG4gICAgICAgICAgICAgICAgICAgICAgICBkYXRhLmFwcGVuZChcInN0b3JhZ2VcIiwgdGhpcy5zZXR0aW5ncy5zdG9yYWdlKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIGRhdGEuYXBwZW5kKFwibmFtZVwiLCBmaWxlLm5hbWUpO1xuICAgICAgICAgICAgICAgICAgICAgICAgZGF0YS5hcHBlbmQoXCJzaXplXCIsIFN0cmluZyhmaWxlLnNpemUpKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIGRhdGEuYXBwZW5kKFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIFwiY29udGVudF90eXBlXCIsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgZmlsZS50eXBlIHx8IFwiYXBwbGljYXRpb24vb2N0ZXQtc3RyZWFtXCIsXG4gICAgICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgICAgICAgICAgZGF0YS5hcHBlbmQoXCJzYW1wbGVcIiwgZmlsZS5zbGljZSgwLCAyMDQ4KSk7XG5cbiAgICAgICAgICAgICAgICAgICAgICAgIHZhciBjc3JmX2ZpZWxkID0gdGhpcy5zYW5kYm94XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgLmpRdWVyeShcIm1ldGFbbmFtZT1jc3JmX2ZpZWxkX25hbWVdXCIpXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgLmF0dHIoXCJjb250ZW50XCIpO1xuICAgICAgICAgICAgICAgICAgICAgICAgdmFyIGNzcmZfdG9rZW4gPSB0aGlzLnNhbmRib3hcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAualF1ZXJ5KFwibWV0YVtuYW1lPVwiICsgY3NyZl9maWVsZCArIFwiXVwiKVxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIC5hdHRyKFwiY29udGVudFwiKTtcblxuICAgICAgICAgICAgICAgICAgICAgICAgcmV0dXJuIHRoaXMuc2FuZGJveC5qUXVlcnkuYWpheCh7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgdXJsLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGNhY2hlOiBmYWxzZSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBjb250ZW50VHlwZTogZmFsc2UsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgcHJvY2Vzc0RhdGE6IGZhbHNlLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGRhdGE6IGRhdGEsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgdHlwZTogXCJQT1NUXCIsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgaGVhZGVyczoge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBcIlgtQ1NSRlRva2VuXCI6IGNzcmZfdG9rZW4sXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzdWNjZXNzOiAoZGF0YTogYW55KSA9PiB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGRvbmUoZGF0YS5yZXN1bHQpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgZXJyb3I6IChyZXNwOiBhbnkpID0+IHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZmFpbChcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHR5cGVvZiByZXNwLnJlc3BvbnNlSlNPTiA9PT0gXCJzdHJpbmdcIlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgID8gcmVzcC5yZXNwb25zZVRleHRcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA6IHJlc3AucmVzcG9uc2VKU09OLmVycm9yLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgICAgICAgICAgICB9KTtcbiAgICAgICAgICAgICAgICAgICAgfSk7XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgX3Nob3dVcGxvYWQoaWQ6IHN0cmluZyk6IFByb21pc2U8VXBsb2FkSW5mbz4ge1xuICAgICAgICAgICAgICAgICAgICByZXR1cm4gbmV3IFByb21pc2UoKGRvbmUsIGZhaWwpID0+XG4gICAgICAgICAgICAgICAgICAgICAgICB0aGlzLnNhbmRib3guY2xpZW50LmNhbGwoXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgXCJHRVRcIixcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBcImZpbGVzX211bHRpcGFydF9yZWZyZXNoXCIsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgYD9pZD0ke2lkfWAsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgKGRhdGE6IGFueSkgPT4ge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBkb25lKGRhdGEucmVzdWx0KTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIChyZXNwOiBhbnkpID0+IHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZmFpbChcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHR5cGVvZiByZXNwLnJlc3BvbnNlSlNPTiA9PT0gXCJzdHJpbmdcIlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgID8gcmVzcC5yZXNwb25zZVRleHRcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA6IHJlc3AucmVzcG9uc2VKU09OLmVycm9yLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgICAgICAgICAgICApLFxuICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgIF91cGxvYWRDaHVuayhcbiAgICAgICAgICAgICAgICAgICAgaW5mbzogVXBsb2FkSW5mbyxcbiAgICAgICAgICAgICAgICAgICAgdXBsb2FkOiBCbG9iLFxuICAgICAgICAgICAgICAgICAgICBwYXJ0OiBudW1iZXIsXG4gICAgICAgICAgICAgICAgICAgIGV4dHJhczogYW55ID0ge30sXG4gICAgICAgICAgICAgICAgKTogUHJvbWlzZTxVcGxvYWRJbmZvPiB7XG4gICAgICAgICAgICAgICAgICAgIGlmICghdXBsb2FkLnNpemUpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHRocm93IG5ldyBFcnJvcihcIjAtbGVuZ3RoIGNodW5rcyBhcmUgbm90IGFsbG93ZWRcIik7XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgY29uc3QgcmVxdWVzdCA9IG5ldyBYTUxIdHRwUmVxdWVzdCgpO1xuXG4gICAgICAgICAgICAgICAgICAgIGNvbnN0IHJlc3VsdCA9IG5ldyBQcm9taXNlPFVwbG9hZEluZm8+KChkb25lLCBmYWlsKSA9PiB7XG4gICAgICAgICAgICAgICAgICAgICAgICBpZiAoZXh0cmFzW1wicHJvZ3Jlc3NEYXRhXCJdKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgY29uc3QgeyBmaWxlLCB1cGxvYWRlZCwgc2l6ZSB9ID1cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZXh0cmFzW1wicHJvZ3Jlc3NEYXRhXCJdO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHJlcXVlc3QudXBsb2FkLmFkZEV2ZW50TGlzdGVuZXIoXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIFwicHJvZ3Jlc3NcIixcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgKGV2ZW50KSA9PiB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoUHJvZ3Jlc3MoXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZmlsZSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB1cGxvYWRlZCArIGV2ZW50LmxvYWRlZCxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzaXplLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgICAgICAgICByZXF1ZXN0LmFkZEV2ZW50TGlzdGVuZXIoXCJsb2FkXCIsIChldmVudCkgPT4ge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGNvbnN0IHJlc3VsdCA9IEpTT04ucGFyc2UocmVxdWVzdC5yZXNwb25zZVRleHQpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGlmIChyZXN1bHQuc3VjY2Vzcykge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBkb25lKHJlc3VsdC5yZXN1bHQpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGZhaWwocmVzdWx0LmVycm9yKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICB9KTtcblxuICAgICAgICAgICAgICAgICAgICAgICAgcmVxdWVzdC5hZGRFdmVudExpc3RlbmVyKFwiZXJyb3JcIiwgKGV2ZW50KSA9PlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGZhaWwocmVxdWVzdC5yZXNwb25zZVRleHQpLFxuICAgICAgICAgICAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgICAgICAgICAgfSk7XG5cbiAgICAgICAgICAgICAgICAgICAgcmVxdWVzdC5vcGVuKFxuICAgICAgICAgICAgICAgICAgICAgICAgXCJQT1NUXCIsXG4gICAgICAgICAgICAgICAgICAgICAgICB0aGlzLnNhbmRib3guY2xpZW50LnVybChcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBcIi9hcGkvYWN0aW9uL2ZpbGVzX211bHRpcGFydF91cGRhdGVcIixcbiAgICAgICAgICAgICAgICAgICAgICAgICksXG4gICAgICAgICAgICAgICAgICAgICk7XG5cbiAgICAgICAgICAgICAgICAgICAgaWYgKHRoaXMuY3NyZlRva2VuKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICByZXF1ZXN0LnNldFJlcXVlc3RIZWFkZXIoXCJYLUNTUkZUb2tlblwiLCB0aGlzLmNzcmZUb2tlbik7XG4gICAgICAgICAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgICAgICAgICB0aGlzLl9zZW5kUmVxdWVzdChyZXF1ZXN0LCB1cGxvYWQsIHBhcnQsIGluZm8uaWQpO1xuXG4gICAgICAgICAgICAgICAgICAgIHJldHVybiByZXN1bHQ7XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgX3NlbmRSZXF1ZXN0KFxuICAgICAgICAgICAgICAgICAgICByZXF1ZXN0OiBYTUxIdHRwUmVxdWVzdCxcbiAgICAgICAgICAgICAgICAgICAgdXBsb2FkOiBCbG9iLFxuICAgICAgICAgICAgICAgICAgICBwYXJ0OiBudW1iZXIsXG4gICAgICAgICAgICAgICAgICAgIGlkOiBzdHJpbmcsXG4gICAgICAgICAgICAgICAgKSB7XG4gICAgICAgICAgICAgICAgICAgIGNvbnN0IGZvcm0gPSBuZXcgRm9ybURhdGEoKTtcbiAgICAgICAgICAgICAgICAgICAgZm9ybS5hcHBlbmQoXCJ1cGxvYWRcIiwgdXBsb2FkKTtcbiAgICAgICAgICAgICAgICAgICAgZm9ybS5hcHBlbmQoXCJwYXJ0XCIsIFN0cmluZyhwYXJ0KSk7IC8vIGZvcm0tZGF0YSBleHBlY3QgYWxsIHZhbHVlcyB0byBiZSBzdHJpbmdzXG4gICAgICAgICAgICAgICAgICAgIGZvcm0uYXBwZW5kKFwiaWRcIiwgaWQpO1xuICAgICAgICAgICAgICAgICAgICByZXF1ZXN0LnNlbmQoZm9ybSk7XG4gICAgICAgICAgICAgICAgfVxuXG4gICAgICAgICAgICAgICAgX2NvbXBsZXRlVXBsb2FkKGluZm86IFVwbG9hZEluZm8pOiBQcm9taXNlPFVwbG9hZEluZm8+IHtcbiAgICAgICAgICAgICAgICAgICAgcmV0dXJuIG5ldyBQcm9taXNlKChkb25lLCBmYWlsKSA9PlxuICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5zYW5kYm94LmNsaWVudC5jYWxsKFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIFwiUE9TVFwiLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIFwiZmlsZXNfbXVsdGlwYXJ0X2NvbXBsZXRlXCIsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgT2JqZWN0LmFzc2lnbihcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAge30sXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuc2V0dGluZ3MuY29tcGxldGVQYXlsb2FkIHx8IHt9LFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZDogaW5mby5pZCxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICApLFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIChkYXRhOiBhbnkpID0+IHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZG9uZShkYXRhLnJlc3VsdCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAocmVzcDogYW55KSA9PiB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGZhaWwoXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB0eXBlb2YgcmVzcC5yZXNwb25zZUpTT04gPT09IFwic3RyaW5nXCJcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA/IHJlc3AucmVzcG9uc2VUZXh0XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgOiByZXNwLnJlc3BvbnNlSlNPTi5lcnJvcixcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICAgICAgICAgICAgKSxcbiAgICAgICAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICB9XG59XG4iXX0=
