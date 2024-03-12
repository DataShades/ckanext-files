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
            Base.defaultSettings = {};
            adapters.Base = Base;
            class Standard extends Base {
                upload(file) {
                    const request = new XMLHttpRequest();
                    const promise = this._addListeners(request, file);
                    this._prepareRequest(request, file);
                    this._sendRequest(request, file);
                    return promise;
                }
                _addListeners(request, file) {
                    request.upload.addEventListener("loadstart", (event) => this.dispatchStart(file));
                    request.upload.addEventListener("progress", (event) => this.dispatchProgress(file, event.loaded, event.total));
                    return new Promise((done, fail) => {
                        request.addEventListener("load", (event) => {
                            const result = JSON.parse(request.responseText);
                            if (result.success) {
                                this.dispatchCommit(file, result.result.id);
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
                    let info;
                    try {
                        info = await this._initializeUpload(file);
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
            Multipart.defaultSettings = { chunkSize: 1024 * 1024 * 5 };
            adapters.Multipart = Multipart;
        })(adapters = CKANEXT_FILES.adapters || (CKANEXT_FILES.adapters = {}));
    })(CKANEXT_FILES = ckan.CKANEXT_FILES || (ckan.CKANEXT_FILES = {}));
})(ckan || (ckan = {}));
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZmlsZXMtLXNoYXJlZC5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uL3RzL2ZpbGVzLS1zaGFyZWQudHMiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IjtBQUFBLElBQVUsSUFBSSxDQXVYYjtBQXZYRCxXQUFVLElBQUk7SUFLWixJQUFpQixhQUFhLENBaVg3QjtJQWpYRCxXQUFpQixhQUFhO1FBTWYsb0JBQU0sR0FBRztZQUNwQixjQUFjLEVBQUUsOEJBQThCO1lBQzlDLGtCQUFrQixFQUFFLGtDQUFrQztZQUN0RCxpQkFBaUIsRUFBRSxtQ0FBbUM7U0FDdkQsQ0FBQztRQUVXLDZCQUFlLEdBQUc7WUFDN0IsT0FBTyxFQUFFLFNBQVM7U0FDbkIsQ0FBQztRQUVGLFNBQVMsTUFBTSxDQUNiLElBQVUsRUFDVixXQUEwQixJQUFJLFFBQVEsQ0FBQyxRQUFRLEVBQUU7WUFFakQsT0FBTyxRQUFRLENBQUMsTUFBTSxDQUFDLElBQUksQ0FBQyxDQUFDO1FBQy9CLENBQUM7UUFFRCxTQUFTLFlBQVksQ0FBQyxPQUFlLEVBQUUsR0FBRyxPQUFZO1lBQ3BELE1BQU0sT0FBTyxHQUE2QyxRQUFTLENBQ2pFLE9BQU8sQ0FDUixDQUFDO1lBQ0YsSUFBSSxDQUFDLE9BQU8sRUFBRSxDQUFDO2dCQUNiLE1BQU0sSUFBSSxLQUFLLENBQUMsWUFBWSxPQUFPLG9CQUFvQixDQUFDLENBQUM7WUFDM0QsQ0FBQztZQUNELE9BQU8sSUFBSSxPQUFPLENBQUMsR0FBRyxPQUFPLENBQUMsQ0FBQztRQUNqQyxDQUFDO1FBRUQsSUFBSSxDQUFDLE9BQU8sQ0FBQyxNQUFNLENBQUMsRUFBRSxLQUFLLEVBQUUsRUFBRSxNQUFNLEVBQUUsWUFBWSxFQUFFLEVBQUUsQ0FBQyxDQUFDO1FBRXpELElBQWlCLFFBQVEsQ0E2VXhCO1FBN1VELFdBQWlCLFFBQVE7WUFVdkIsTUFBYSxJQUFLLFNBQVEsV0FBVztnQkFNbkMsWUFBWSxRQUFRLEdBQUcsRUFBRTtvQkFDdkIsS0FBSyxFQUFFLENB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QUNFLEVBQUUsRUFBRSxJQUFJLENBQUMsRUFBRTtxQkFDWixFQUNELENBQUMsSUFBUyxFQUFFLEVBQUU7d0JBQ1osSUFBSSxDQUFDLElBQUksQ0FBQyxNQUFNLENBQUMsQ0FBQztvQkFDcEIsQ0FBQyxFQUNELENBQUMsSUFBUyxFQUFFLEVBQUU7d0JBQ1osSUFBSSxDQUNGLE9BQU8sSUFBSSxDQUFDLFlBQVksS0FBSyxRQUFROzRCQUNuQyxDQUFDLENBQUMsSUFBSSxDQUFDLFlBQVk7NEJBQ25CLENBQUMsQ0FBQyxJQUFJLENBQUMsWUFBWSxDQUFDLEtBQUssQ0FDNUIsQ0FBQztvQkFDSixDQUFDLENBQ0YsQ0FDRixDQUFDO2dCQUNKLENBQUM7O1lBcE1NLHlCQUFlLEdBQUcsRUFBRSxTQUFTLEVBQUUsSUFBSSxHQUFHLElBQUksR0FBRyxDQUFDLEVBQUUsQ0FBQztZQUQ3QyxrQkFBUyxZQXNNckIsQ0FBQTtRQUNILENBQUMsRUE3VWdCLFFBQVEsR0FBUixzQkFBUSxLQUFSLHNCQUFRLFFBNlV4QjtJQUNILENBQUMsRUFqWGdCLGFBQWEsR0FBYixrQkFBYSxLQUFiLGtCQUFhLFFBaVg3QjtBQUNILENBQUMsRUF2WFMsSUFBSSxLQUFKLElBQUksUUF1WGIiLCJzb3VyY2VzQ29udGVudCI6WyJuYW1lc3BhY2UgY2thbiB7XG4gIGV4cG9ydCB2YXIgc2FuZGJveDogYW55O1xuICBleHBvcnQgdmFyIHB1YnN1YjogYW55O1xuICBleHBvcnQgdmFyIG1vZHVsZTogKG5hbWU6IHN0cmluZywgaW5pdGlhbGl6ZXI6ICgkOiBhbnkpID0+IGFueSkgPT4gYW55O1xuXG4gIGV4cG9ydCBuYW1lc3BhY2UgQ0tBTkVYVF9GSUxFUyB7XG4gICAgdHlwZSBVcGxvYWRlclNldHRpbmdzID0ge1xuICAgICAgc3RvcmFnZTogc3RyaW5nO1xuICAgICAgW2tleTogc3RyaW5nXTogYW55O1xuICAgIH07XG5cbiAgICBleHBvcnQgY29uc3QgdG9waWNzID0ge1xuICAgICAgYWRkRmlsZVRvUXVldWU6IFwiY2thbmV4dDpmaWxlczpxdWV1ZTpmaWxlOmFkZFwiLFxuICAgICAgcmVzdG9yZUZpbGVJblF1ZXVlOiBcImNrYW5leHQ6ZmlsZXM6cXVldWU6ZmlsZTpyZXN0b3JlXCIsXG4gICAgICBxdWV1ZUl0ZW1VcGxvYWRlZDogXCJja2FuZXh0OmZpbGVzOnF1ZXVlOmZpbGU6dXBsb2FkZWRcIixcbiAgICB9O1xuXG4gICAgZXhwb3J0IGNvbnN0IGRlZmF1bHRTZXR0aW5ncyA9IHtcbiAgICAgIHN0b3JhZ2U6IFwiZGVmYXVsdFwiLFxuICAgIH07XG5cbiAgICBmdW5jdGlvbiB1cGxvYWQoXG4gICAgICBmaWxlOiBGaWxlLFxuICAgICAgdXBsb2FkZXI6IGFkYXB0ZXJzLkJhc2UgPSBuZXcgYWRhcHRlcnMuU3RhbmRhcmQoKSxcbiAgICApIHtcbiAgICAgIHJldHVybiB1cGxvYWRlci51cGxvYWQoZmlsZSk7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gbWFrZVVwbG9hZGVyKGFkYXB0ZXI6IHN0cmluZywgLi4ub3B0aW9uczogYW55KSB7XG4gICAgICBjb25zdCBmYWN0b3J5ID0gKDx7IFtrZXk6IHN0cmluZ106IHR5cGVvZiBhZGFwdGVycy5CYXNlIH0+YWRhcHRlcnMpW1xuICAgICAgICBhZGFwdGVyXG4gICAgICBdO1xuICAgICAgaWYgKCFmYWN0b3J5KSB7XG4gICAgICAgIHRocm93IG5ldyBFcnJvcihgVXBsb2FkZXIgJHthZGFwdGVyfSBpcyBub3QgcmVnaXN0ZXJlZGApO1xuICAgICAgfVxuICAgICAgcmV0dXJuIG5ldyBmYWN0b3J5KC4uLm9wdGlvbnMpO1xuICAgIH1cblxuICAgIGNrYW4uc2FuZGJveC5leHRlbmQoeyBmaWxlczogeyB1cGxvYWQsIG1ha2VVcGxvYWRlciB9IH0pO1xuXG4gICAgZXhwb3J0IG5hbWVzcGFjZSBhZGFwdGVycyB7XG4gICAgICBleHBvcnQgdHlwZSBTdG9yYWdlRGF0YSA9IHtcbiAgICAgICAgdXBsb2FkZWQ6IG51bWJlcjtcbiAgICAgICAgc2l6ZTogbnVtYmVyO1xuICAgICAgfTtcbiAgICAgIGV4cG9ydCB0eXBlIFVwbG9hZEluZm8gPSB7XG4gICAgICAgIGlkOiBzdHJpbmc7XG4gICAgICAgIHN0b3JhZ2VfZGF0YTogU3RvcmFnZURhdGE7XG4gICAgICB9O1xuXG4gICAgICBleHBvcnQgY2xhc3MgQmFzZSBleHRlbmRzIEV2ZW50VGFyZ2V0IHtcbiAgICAgICAgc3RhdGljIGRlZmF1bHRTZXR0aW5nczogT2JqZWN0ID0ge307XG4gICAgICAgIHByb3RlY3RlZCBzZXR0aW5nczogVXBsb2FkZXJTZXR0aW5ncztcbiAgICAgICAgcHJvdGVjdGVkIHNhbmRib3g6IGFueTtcbiAgICAgICAgcHJvdGVjdGVkIGNzcmZUb2tlbjogc3RyaW5nO1xuXG4gICAgICAgIGNvbnN0cnVjdG9yKHNldHRpbmdzID0ge30pIHtcbiAgICAgICAgICBzdXBlcigpO1xuICAgICAgICAgIHRoaXMuc2V0dGluZ3MgPSB7XG4gICAgICAgICAgICAuLi5kZWZhdWx0U2V0dGluZ3MsXG4gICAgICAgICAgICAuLi4odGhpcy5jb25zdHJ1Y3RvciBhcyB0eXBlb2YgQmFzZSkuZGVmYXVsdFNldHRpbmdzLFxuICAgICAgICAgICAgLi4uc2V0dGluZ3MsXG4gICAgICAgICAgfTtcbiAgICAgICAgICB0aGlzLnNhbmRib3ggPSBja2FuLnNhbmRib3goKTtcblxuICAgICAgICAgIGNvbnN0IGNzcmZGaWVsZCA9XG4gICAgICAgICAgICBkb2N1bWVudFxuICAgICAgICAgICAgICAucXVlcnlTZWxlY3RvcihcIm1ldGFbbmFtZT1jc3JmX2ZpZWxkX25hbWVdXCIpXG4gICAgICAgICAgICAgID8uZ2V0QXR0cmlidXRlKFwiY29udGVudFwiKSA/PyBcIl9jc3JmX3Rva2VuXCI7XG4gICAgICAgICAgdGhpcy5jc3JmVG9rZW4gPVxuICAgICAgICAgICAgZG9jdW1lbnRcbiAgICAgICAgICAgICAgLnF1ZXJ5U2VsZWN0b3IoYG1ldGFbbmFtZT0ke2NzcmZGaWVsZH1dYClcbiAgICAgICAgICAgICAgPy5nZXRBdHRyaWJ1dGUoXCJjb250ZW50XCIpIHx8IFwiXCI7XG4gICAgICAgIH1cblxuICAgICAgICB1cGxvYWQoZmlsZTogRmlsZSkge1xuICAgICAgICAgIHRocm93IG5ldyBFcnJvcihcIkJhc2UudXBsb2FkIGlzIG5vdCBpbXBsZW1lbnRlZFwiKTtcbiAgICAgICAgfVxuXG4gICAgICAgIHJlc3VtZShmaWxlOiBGaWxlLCBpZDogc3RyaW5nKSB7XG4gICAgICAgICAgdGhyb3cgbmV3IEVycm9yKFwiQmFzZS5yZXN1bWUgaXMgbm90IGltcGxlbWVudGVkXCIpO1xuICAgICAgICB9XG5cbiAgICAgICAgZGlzcGF0Y2hTdGFydChmaWxlOiBGaWxlKSB7XG4gICAgICAgICAgdGhpcy5kaXNwYXRjaEV2ZW50KG5ldyBDdXN0b21FdmVudChcInN0YXJ0XCIsIHsgZGV0YWlsOiB7IGZpbGUgfSB9KSk7XG4gICAgICAgIH1cbiAgICAgICAgZGlzcGF0Y2hDb21taXQoZmlsZTogRmlsZSwgaWQ6IHN0cmluZykge1xuICAgICAgICAgIHRoaXMuZGlzcGF0Y2hFdmVudChcbiAgICAgICAgICAgIG5ldyBDdXN0b21FdmVudChcImNvbW1pdFwiLCB7IGRldGFpbDogeyBmaWxlLCBpZCB9IH0pLFxuICAgICAgICAgICk7XG4gICAgICAgIH1cbiAgICAgICAgZGlzcGF0Y2hQcm9ncmVzcyhmaWxlOiBGaWxlLCBsb2FkZWQ6IG51bWJlciwgdG90YWw6IG51bWJlcikge1xuICAgICAgICAgIHRoaXMuZGlzcGF0Y2hFdmVudChcbiAgICAgICAgICAgIG5ldyBDdXN0b21FdmVudChcInByb2dyZXNzXCIsIHsgZGV0YWlsOiB7IGZpbGUsIGxvYWRlZCwgdG90YWwgfSB9KSxcbiAgICAgICAgICApO1xuICAgICAgICB9XG4gICAgICAgIGRpc3BhdGNoRmluaXNoKGZpbGU6IEZpbGUsIHJlc3VsdDogT2JqZWN0KSB7XG4gICAgICAgICAgdGhpcy5kaXNwYXRjaEV2ZW50KFxuICAgICAgICAgICAgbmV3IEN1c3RvbUV2ZW50KFwiZmluaXNoXCIsIHsgZGV0YWlsOiB7IGZpbGUsIHJlc3VsdCB9IH0pLFxuICAgICAgICAgICk7XG4gICAgICAgIH1cbiAgICAgICAgZGlzcGF0Y2hGYWlsKGZpbGU6IEZpbGUsIHJlYXNvbnM6IHsgW2tleTogc3RyaW5nXTogc3RyaW5nW10gfSkge1xuICAgICAgICAgIHRoaXMuZGlzcGF0Y2hFdmVudChcbiAgICAgICAgICAgIG5ldyBDdXN0b21FdmVudChcImZhaWxcIiwgeyBkZXRhaWw6IHsgZmlsZSwgcmVhc29ucyB9IH0pLFxuICAgICAgICAgICk7XG4gICAgICAgIH1cbiAgICAgICAgZGlzcGF0Y2hFcnJvcihmaWxlOiBGaWxlLCBtZXNzYWdlOiBzdHJpbmcpIHtcbiAgICAgICAgICB0aGlzLmRpc3BhdGNoRXZlbnQoXG4gICAgICAgICAgICBuZXcgQ3VzdG9tRXZlbnQoXCJlcnJvclwiLCB7IGRldGFpbDogeyBmaWxlLCBtZXNzYWdlIH0gfSksXG4gICAgICAgICAgKTtcbiAgICAgICAgfVxuICAgICAgfVxuICAgICAgZXhwb3J0IGNsYXNzIFN0YW5kYXJkIGV4dGVuZHMgQmFzZSB7XG4gICAgICAgIHVwbG9hZChmaWxlOiBGaWxlKSB7XG4gICAgICAgICAgY29uc3QgcmVxdWVzdCA9IG5ldyBYTUxIdHRwUmVxdWVzdCgpO1xuICAgICAgICAgIGNvbnN0IHByb21pc2UgPSB0aGlzLl9hZGRMaXN0ZW5lcnMocmVxdWVzdCwgZmlsZSk7XG4gICAgICAgICAgdGhpcy5fcHJlcGFyZVJlcXVlc3QocmVxdWVzdCwgZmlsZSk7XG4gICAgICAgICAgdGhpcy5fc2VuZFJlcXVlc3QocmVxdWVzdCwgZmlsZSk7XG4gICAgICAgICAgcmV0dXJuIHByb21pc2U7XG4gICAgICAgIH1cblxuICAgICAgICBfYWRkTGlzdGVuZXJzKFxuICAgICAgICAgIHJlcXVlc3Q6IFhNTEh0dHBSZXF1ZXN0LFxuICAgICAgICAgIGZpbGU6IEZpbGUsXG4gICAgICAgICk6IFByb21pc2U8VXBsb2FkSW5mbz4ge1xuICAgICAgICAgIHJlcXVlc3QudXBsb2FkLmFkZEV2ZW50TGlzdGVuZXIoXCJsb2Fkc3RhcnRcIiwgKGV2ZW50KSA9PlxuICAgICAgICAgICAgdGhpcy5kaXNwYXRjaFN0YXJ0KGZpbGUpLFxuICAgICAgICAgICk7XG5cbiAgICAgICAgICByZXF1ZXN0LnVwbG9hZC5hZGRFdmVudExpc3RlbmVyKFwicHJvZ3Jlc3NcIiwgKGV2ZW50KSA9PlxuICAgICAgICAgICAgdGhpcy5kaXNwYXRjaFByb2dyZXNzKGZpbGUsIGV2ZW50LmxvYWRlZCwgZXZlbnQudG90YWwpLFxuICAgICAgICAgICk7XG5cbiAgICAgICAgICByZXR1cm4gbmV3IFByb21pc2UoKGRvbmUsIGZhaWwpID0+IHtcbiAgICAgICAgICAgIHJlcXVlc3QuYWRkRXZlbnRMaXN0ZW5lcihcImxvYWRcIiwgKGV2ZW50KSA9PiB7XG4gICAgICAgICAgICAgIGNvbnN0IHJlc3VsdCA9IEpTT04ucGFyc2UocmVxdWVzdC5yZXNwb25zZVRleHQpO1xuICAgICAgICAgICAgICBpZiAocmVzdWx0LnN1Y2Nlc3MpIHtcbiAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoQ29tbWl0KGZpbGUsIHJlc3VsdC5yZXN1bHQuaWQpO1xuICAgICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hGaW5pc2goZmlsZSwgcmVzdWx0LnJlc3VsdCk7XG4gICAgICAgICAgICAgICAgZG9uZShyZXN1bHQucmVzdWx0KTtcbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRmFpbChmaWxlLCByZXN1bHQuZXJyb3IpO1xuXG4gICAgICAgICAgICAgICAgZmFpbChyZXN1bHQuZXJyb3IpO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9KTtcblxuICAgICAgICAgICAgcmVxdWVzdC5hZGRFdmVudExpc3RlbmVyKFwiZXJyb3JcIiwgKGV2ZW50KSA9PiB7XG4gICAgICAgICAgICAgIHRoaXMuZGlzcGF0Y2hFcnJvcihmaWxlLCByZXF1ZXN0LnJlc3BvbnNlVGV4dCk7XG4gICAgICAgICAgICAgIGZhaWwocmVxdWVzdC5yZXNwb25zZVRleHQpO1xuICAgICAgICAgICAgfSk7XG4gICAgICAgICAgfSk7XG4gICAgICAgIH1cblxuICAgICAgICBfcHJlcGFyZVJlcXVlc3QocmVxdWVzdDogWE1MSHR0cFJlcXVlc3QsIGZpbGU6IEZpbGUpIHtcbiAgICAgICAgICByZXF1ZXN0Lm9wZW4oXG4gICAgICAgICAgICBcIlBPU1RcIixcbiAgICAgICAgICAgIHRoaXMuc2FuZGJveC5jbGllbnQudXJsKFwiL2FwaS9hY3Rpb24vZmlsZXNfZmlsZV9jcmVhdGVcIiksXG4gICAgICAgICAgKTtcblxuICAgICAgICAgIGlmICh0aGlzLmNzcmZUb2tlbikge1xuICAgICAgICAgICAgcmVxdWVzdC5zZXRSZXF1ZXN0SGVhZGVyKFwiWC1DU1JGVG9rZW5cIiwgdGhpcy5jc3JmVG9rZW4pO1xuICAgICAgICAgIH1cbiAgICAgICAgfVxuXG4gICAgICAgIF9zZW5kUmVxdWVzdChyZXF1ZXN0OiBYTUxIdHRwUmVxdWVzdCwgZmlsZTogRmlsZSkge1xuICAgICAgICAgIGNvbnN0IGRhdGEgPSBuZXcgRm9ybURhdGEoKTtcbiAgICAgICAgICBkYXRhLmFwcGVuZChcInVwbG9hZFwiLCBmaWxlKTtcblxuICAgICAgICAgIGRhdGEuYXBwZW5kKFwic3RvcmFnZVwiLCB0aGlzLnNldHRpbmdzLnN0b3JhZ2UpO1xuICAgICAgICAgIHJlcXVlc3Quc2VuZChkYXRhKTtcbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICBleHBvcnQgY2xhc3MgTXVsdGlwYXJ0IGV4dGVuZHMgQmFzZSB7XG4gICAgICAgIHN0YXRpYyBkZWZhdWx0U2V0dGluZ3MgPSB7IGNodW5rU2l6ZTogMTAyNCAqIDEwMjQgKiA1IH07XG5cbiAgICAgICAgcHJpdmF0ZSBfYWN0aXZlOiBTZXQ8RmlsZT47XG5cbiAgICAgICAgY29uc3RydWN0b3Ioc2V0dGluZ3M6IE9iamVjdCkge1xuICAgICAgICAgIHN1cGVyKHNldHRpbmdzKTtcbiAgICAgICAgICB0aGlzLl9hY3RpdmUgPSBuZXcgU2V0KCk7XG4gICAgICAgIH1cblxuICAgICAgICBhc3luYyB1cGxvYWQoZmlsZTogRmlsZSkge1xuICAgICAgICAgIGlmICh0aGlzLl9hY3RpdmUuaGFzKGZpbGUpKSB7XG4gICAgICAgICAgICBjb25zb2xlLndhcm4oXCJGaWxlIHVwbG9hZCBpbiBwcm9ncmVzc1wiKTtcbiAgICAgICAgICAgIHJldHVybjtcbiAgICAgICAgICB9XG4gICAgICAgICAgdGhpcy5fYWN0aXZlLmFkZChmaWxlKTtcblxuICAgICAgICAgIGxldCBpbmZvO1xuXG4gICAgICAgICAgdHJ5IHtcbiAgICAgICAgICAgIGluZm8gPSBhd2FpdCB0aGlzLl9pbml0aWFsaXplVXBsb2FkKGZpbGUpO1xuICAgICAgICAgIH0gY2F0Y2ggKGVycikge1xuICAgICAgICAgICAgaWYgKHR5cGVvZiBlcnIgPT09IFwic3RyaW5nXCIpIHtcbiAgICAgICAgICAgICAgdGhpcy5kaXNwYXRjaEVycm9yKGZpbGUsIGVycik7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICB0aGlzLmRpc3BhdGNoRmFpbChmaWxlLCBlcnIgYXMgYW55KTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIHJldHVybjtcbiAgICAgICAgICB9XG5cbiAgICAgICAgICB0aGlzLmRpc3BhdGNoQ29tbWl0KGZpbGUsIGluZm8uaWQpO1xuICAgICAgICAgIHRoaXMuZGlzcGF0Y2hTdGFydChmaWxlKTtcblxuICAgICAgICAgIHRoaXMuX2RvVXBsb2FkKGZpbGUsIGluZm8pO1xuICAgICAgICB9XG5cbiAgICAgICAgYXN5bmMgcmVzdW1lKGZpbGU6IEZpbGUsIGlkOiBzdHJpbmcpIHtcbiAgICAgICAgICBpZiAodGhpcy5fYWN0aXZlLmhhcyhmaWxlKSkge1xuICAgICAgICAgICAgY29uc29sZS53YXJuKFwiRmlsZSB1cGxvYWQgaW4gcHJvZ3Jlc3NcIik7XG4gICAgICAgICAgICByZXR1cm47XG4gICAgICAgICAgfVxuICAgICAgICAgIHRoaXMuX2FjdGl2ZS5hZGQoZmlsZSk7XG5cbiAgICAgICAgICBsZXQgaW5mbyA9IGF3YWl0IHRoaXMuX3Nob3dVcGxvYWQoaWQpO1xuICAgICAgICAgIHRoaXMuZGlzcGF0Y2hTdGFydChmaWxlKTtcblxuICAgICAgICAgIHRoaXMuX2RvVXBsb2FkKGZpbGUsIGluZm8pO1xuICAgICAgICB9XG5cbiAgICAgICAgcGF1c2UoZmlsZTogRmlsZSkge1xuICAgICAgICAgIHRoaXMuX2FjdGl2ZS5kZWxldGUoZmlsZSk7XG4gICAgICAgIH1cblxuICAgICAgICBhc3luYyBfZG9VcGxvYWQoZmlsZTogRmlsZSwgaW5mbzogVXBsb2FkSW5mbykge1xuICAgICAgICAgIGxldCBzdGFydCA9IGluZm8uc3RvcmFnZV9kYXRhLnVwbG9hZGVkIHx8IDA7XG5cbiAgICAgICAgICB3aGlsZSAoc3RhcnQgPCBmaWxlLnNpemUpIHtcbiAgICAgICAgICAgIGlmICghdGhpcy5fYWN0aXZlLmhhcyhmaWxlKSkge1xuICAgICAgICAgICAgICBjb25zb2xlLmluZm8oXCJGaWxlIHVwbG9hZCBpcyBwYXVzZWRcIik7XG4gICAgICAgICAgICAgIHJldHVybjtcbiAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgaW5mbyA9IGF3YWl0IHRoaXMuX3VwbG9hZENodW5rKFxuICAgICAgICAgICAgICBpbmZvLFxuICAgICAgICAgICAgICBmaWxlLnNsaWNlKHN0YXJ0LCBzdGFydCArIHRoaXMuc2V0dGluZ3MuY2h1bmtTaXplKSxcbiAgICAgICAgICAgICAgc3RhcnQsXG4gICAgICAgICAgICApO1xuXG4gICAgICAgICAgICBjb25zdCB1cGxvYWRlZCA9IGluZm8uc3RvcmFnZV9kYXRhLnVwbG9hZGVkO1xuICAgICAgICAgICAgaWYgKHVwbG9hZGVkIDw9IHN0YXJ0KSB7XG4gICAgICAgICAgICAgIHRocm93IG5ldyBFcnJvcihcIlVwbG9hZGVkIHNpemUgaXMgcmVkdWNlZFwiKTtcbiAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgdGhpcy5kaXNwYXRjaFByb2dyZXNzKGZpbGUsIHVwbG9hZGVkLCBmaWxlLnNpemUpO1xuICAgICAgICAgICAgc3RhcnQgPSB1cGxvYWRlZDtcbiAgICAgICAgICB9XG5cbiAgICAgICAgICB0aGlzLmRpc3BhdGNoUHJvZ3Jlc3MoZmlsZSwgZmlsZS5zaXplLCBmaWxlLnNpemUpO1xuICAgICAgICAgIGluZm8gPSBhd2FpdCB0aGlzLl9jb21wbGV0ZVVwbG9hZChpbmZvKTtcbiAgICAgICAgICB0aGlzLmRpc3BhdGNoRmluaXNoKGZpbGUsIGluZm8pO1xuICAgICAgICB9XG5cbiAgICAgICAgX2luaXRpYWxpemVVcGxvYWQoZmlsZTogRmlsZSk6IFByb21pc2U8VXBsb2FkSW5mbz4ge1xuICAgICAgICAgIHJldHVybiBuZXcgUHJvbWlzZSgoZG9uZSwgZmFpbCkgPT5cbiAgICAgICAgICAgIHRoaXMuc2FuZGJveC5jbGllbnQuY2FsbChcbiAgICAgICAgICAgICAgXCJQT1NUXCIsXG4gICAgICAgICAgICAgIFwiZmlsZXNfdXBsb2FkX2luaXRpYWxpemVcIixcbiAgICAgICAgICAgICAge1xuICAgICAgICAgICAgICAgIHN0b3JhZ2U6IHRoaXMuc2V0dGluZ3Muc3RvcmFnZSxcbiAgICAgICAgICAgICAgICBuYW1lOiBmaWxlLm5hbWUsXG4gICAgICAgICAgICAgICAgc2l6ZTogZmlsZS5zaXplLFxuICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICAoZGF0YTogYW55KSA9PiB7XG4gICAgICAgICAgICAgICAgZG9uZShkYXRhLnJlc3VsdCk7XG4gICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgIChyZXNwOiBhbnkpID0+IHtcbiAgICAgICAgICAgICAgICBmYWlsKFxuICAgICAgICAgICAgICAgICAgdHlwZW9mIHJlc3AucmVzcG9uc2VKU09OID09PSBcInN0cmluZ1wiXG4gICAgICAgICAgICAgICAgICAgID8gcmVzcC5yZXNwb25zZVRleHRcbiAgICAgICAgICAgICAgICAgICAgOiByZXNwLnJlc3BvbnNlSlNPTi5lcnJvcixcbiAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgKSxcbiAgICAgICAgICApO1xuICAgICAgICB9XG4gICAgICAgIF9zaG93VXBsb2FkKGlkOiBzdHJpbmcpOiBQcm9taXNlPFVwbG9hZEluZm8+IHtcbiAgICAgICAgICByZXR1cm4gbmV3IFByb21pc2UoKGRvbmUsIGZhaWwpID0+XG4gICAgICAgICAgICB0aGlzLnNhbmRib3guY2xpZW50LmNhbGwoXG4gICAgICAgICAgICAgIFwiR0VUXCIsXG4gICAgICAgICAgICAgIFwiZmlsZXNfdXBsb2FkX3Nob3dcIixcbiAgICAgICAgICAgICAgYD9pZD0ke2lkfWAsXG4gICAgICAgICAgICAgIChkYXRhOiBhbnkpID0+IHtcbiAgICAgICAgICAgICAgICBkb25lKGRhdGEucmVzdWx0KTtcbiAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgKHJlc3A6IGFueSkgPT4ge1xuICAgICAgICAgICAgICAgIGZhaWwoXG4gICAgICAgICAgICAgICAgICB0eXBlb2YgcmVzcC5yZXNwb25zZUpTT04gPT09IFwic3RyaW5nXCJcbiAgICAgICAgICAgICAgICAgICAgPyByZXNwLnJlc3BvbnNlVGV4dFxuICAgICAgICAgICAgICAgICAgICA6IHJlc3AucmVzcG9uc2VKU09OLmVycm9yLFxuICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICApLFxuICAgICAgICAgICk7XG4gICAgICAgIH1cblxuICAgICAgICBfdXBsb2FkQ2h1bmsoXG4gICAgICAgICAgaW5mbzogVXBsb2FkSW5mbyxcbiAgICAgICAgICBwYXJ0OiBCbG9iLFxuICAgICAgICAgIHN0YXJ0OiBudW1iZXIsXG4gICAgICAgICk6IFByb21pc2U8VXBsb2FkSW5mbz4ge1xuICAgICAgICAgIGlmICghcGFydC5zaXplKSB7XG4gICAgICAgICAgICB0aHJvdyBuZXcgRXJyb3IoXCIwLWxlbmd0aCBjaHVua3MgYXJlIG5vdCBhbGxvd2VkXCIpO1xuICAgICAgICAgIH1cbiAgICAgICAgICBjb25zdCByZXF1ZXN0ID0gbmV3IFhNTEh0dHBSZXF1ZXN0KCk7XG5cbiAgICAgICAgICBjb25zdCByZXN1bHQgPSBuZXcgUHJvbWlzZTxVcGxvYWRJbmZvPigoZG9uZSwgZmFpbCkgPT4ge1xuICAgICAgICAgICAgcmVxdWVzdC5hZGRFdmVudExpc3RlbmVyKFwibG9hZFwiLCAoZXZlbnQpID0+IHtcbiAgICAgICAgICAgICAgY29uc3QgcmVzdWx0ID0gSlNPTi5wYXJzZShyZXF1ZXN0LnJlc3BvbnNlVGV4dCk7XG4gICAgICAgICAgICAgIGlmIChyZXN1bHQuc3VjY2Vzcykge1xuICAgICAgICAgICAgICAgIGRvbmUocmVzdWx0LnJlc3VsdCk7XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgZmFpbChyZXN1bHQuZXJyb3IpO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9KTtcblxuICAgICAgICAgICAgcmVxdWVzdC5hZGRFdmVudExpc3RlbmVyKFwiZXJyb3JcIiwgKGV2ZW50KSA9PlxuICAgICAgICAgICAgICBmYWlsKHJlcXVlc3QucmVzcG9uc2VUZXh0KSxcbiAgICAgICAgICAgICk7XG4gICAgICAgICAgfSk7XG5cbiAgICAgICAgICByZXF1ZXN0Lm9wZW4oXG4gICAgICAgICAgICBcIlBPU1RcIixcbiAgICAgICAgICAgIHRoaXMuc2FuZGJveC5jbGllbnQudXJsKFwiL2FwaS9hY3Rpb24vZmlsZXNfdXBsb2FkX3VwZGF0ZVwiKSxcbiAgICAgICAgICApO1xuXG4gICAgICAgICAgaWYgKHRoaXMuY3NyZlRva2VuKSB7XG4gICAgICAgICAgICByZXF1ZXN0LnNldFJlcXVlc3RIZWFkZXIoXCJYLUNTUkZUb2tlblwiLCB0aGlzLmNzcmZUb2tlbik7XG4gICAgICAgICAgfVxuXG4gICAgICAgICAgdGhpcy5fc2VuZFJlcXVlc3QocmVxdWVzdCwgcGFydCwgc3RhcnQsIGluZm8uaWQpO1xuXG4gICAgICAgICAgcmV0dXJuIHJlc3VsdDtcbiAgICAgICAgfVxuXG4gICAgICAgIF9zZW5kUmVxdWVzdChcbiAgICAgICAgICByZXF1ZXN0OiBYTUxIdHRwUmVxdWVzdCxcbiAgICAgICAgICBwYXJ0OiBCbG9iLFxuICAgICAgICAgIHBvc2l0aW9uOiBudW1iZXIsXG4gICAgICAgICAgaWQ6IHN0cmluZyxcbiAgICAgICAgKSB7XG4gICAgICAgICAgY29uc3QgZm9ybSA9IG5ldyBGb3JtRGF0YSgpO1xuICAgICAgICAgIGZvcm0uYXBwZW5kKFwidXBsb2FkXCIsIHBhcnQpO1xuICAgICAgICAgIGZvcm0uYXBwZW5kKFwicG9zaXRpb25cIiwgU3RyaW5nKHBvc2l0aW9uKSk7XG4gICAgICAgICAgZm9ybS5hcHBlbmQoXCJpZFwiLCBpZCk7XG4gICAgICAgICAgcmVxdWVzdC5zZW5kKGZvcm0pO1xuICAgICAgICB9XG5cbiAgICAgICAgX2NvbXBsZXRlVXBsb2FkKGluZm86IFVwbG9hZEluZm8pOiBQcm9taXNlPFVwbG9hZEluZm8+IHtcbiAgICAgICAgICByZXR1cm4gbmV3IFByb21pc2UoKGRvbmUsIGZhaWwpID0+XG4gICAgICAgICAgICB0aGlzLnNhbmRib3guY2xpZW50LmNhbGwoXG4gICAgICAgICAgICAgIFwiUE9TVFwiLFxuICAgICAgICAgICAgICBcImZpbGVzX3VwbG9hZF9jb21wbGV0ZVwiLFxuICAgICAgICAgICAgICB7XG4gICAgICAgICAgICAgICAgaWQ6IGluZm8uaWQsXG4gICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgIChkYXRhOiBhbnkpID0+IHtcbiAgICAgICAgICAgICAgICBkb25lKGRhdGEucmVzdWx0KTtcbiAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgKHJlc3A6IGFueSkgPT4ge1xuICAgICAgICAgICAgICAgIGZhaWwoXG4gICAgICAgICAgICAgICAgICB0eXBlb2YgcmVzcC5yZXNwb25zZUpTT04gPT09IFwic3RyaW5nXCJcbiAgICAgICAgICAgICAgICAgICAgPyByZXNwLnJlc3BvbnNlVGV4dFxuICAgICAgICAgICAgICAgICAgICA6IHJlc3AucmVzcG9uc2VKU09OLmVycm9yLFxuICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICApLFxuICAgICAgICAgICk7XG4gICAgICAgIH1cbiAgICAgIH1cbiAgICB9XG4gIH1cbn1cbiJdfQ==