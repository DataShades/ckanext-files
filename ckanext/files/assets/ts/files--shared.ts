namespace ckan {
    export var sandbox: any;
    export var pubsub: any;
    export var module: (name: string, initializer: ($: any) => any) => any;
    export namespace CKANEXT_FILES {
        export type UploaderSettings = {
            storage: string;
            [key: string]: any;
        };

        export interface UploadOptions {
            uploader?: adapters.Base;
            adapter?: string;
            uploaderArgs?: any[];
            requestParams?: { [key: string]: any };
        }

        export const topics = {
            addFileToQueue: "ckanext:files:queue:file:add",
            restoreFileInQueue: "ckanext:files:queue:file:restore",
            queueItemUploaded: "ckanext:files:queue:file:uploaded",
        };

        export const defaultSettings = {
            storage: "default",
        };

        function upload(file: File, options: UploadOptions = {}) {
            const uploader =
                options.uploader ||
                makeUploader(
                    options.adapter || "Standard",
                    ...(options.uploaderArgs || []),
                );
            return uploader.upload(file, options.requestParams || {});
        }

        function makeUploader(adapter: string, ...options: any) {
            const factory = (<{ [key: string]: typeof adapters.Base }>adapters)[
                adapter
            ];
            if (!factory) {
                throw new Error(`Uploader ${adapter} is not registered`);
            }
            return new factory(...options);
        }

        ckan.sandbox.extend({ files: { upload, makeUploader } });

        export namespace adapters {
            export type StorageData = { [key: string]: any };

            export type UploadInfo = {
                id: string;
                storage_data: StorageData;
                location: string;
                hash: string;
                content_type: string;
                size: number;
            };

            export class Base extends EventTarget {
                static defaultSettings: Object = {};
                protected settings: UploaderSettings;
                protected sandbox: any;
                protected csrfToken: string;

                constructor(settings = {}) {
                    super();
                    this.settings = {
                        ...defaultSettings,
                        ...(this.constructor as typeof Base).defaultSettings,
                        ...settings,
                    };
                    this.sandbox = ckan.sandbox();

                    const csrfField =
                        document
                            .querySelector("meta[name=csrf_field_name]")
                            ?.getAttribute("content") ?? "_csrf_token";
                    this.csrfToken =
                        document
                            .querySelector(`meta[name=${csrfField}]`)
                            ?.getAttribute("content") || "";
                }

                upload(file: File, params: { [key: string]: any }) {
                    throw new Error("Base.upload is not implemented");
                }

                resume(file: File, id: string) {
                    throw new Error("Base.resume is not implemented");
                }

                dispatchStart(file: File) {
                    this.dispatchEvent(
                        new CustomEvent("start", { detail: { file } }),
                    );
                }
                dispatchMultipartId(file: File, id: string) {
                    this.dispatchEvent(
                        new CustomEvent("multipartid", {
                            detail: { file, id },
                        }),
                    );
                }
                dispatchProgress(file: File, loaded: number, total: number) {
                    this.dispatchEvent(
                        new CustomEvent("progress", {
                            detail: { file, loaded, total },
                        }),
                    );
                }
                dispatchFinish(file: File, result: Object) {
                    this.dispatchEvent(
                        new CustomEvent("finish", { detail: { file, result } }),
                    );
                }
                dispatchFail(file: File, reasons: { [key: string]: string[] }) {
                    this.dispatchEvent(
                        new CustomEvent("fail", { detail: { file, reasons } }),
                    );
                }
                dispatchError(file: File, message: string) {
                    this.dispatchEvent(
                        new CustomEvent("error", { detail: { file, message } }),
                    );
                }
            }

            export class Standard extends Base {
                static defaultSettings = {
                    uploadAction: "files_file_create",
                };

                upload(file: File, params: { [key: string]: any }) {
                    const request = new XMLHttpRequest();
                    const promise = this._addListeners(request, file);
                    this._prepareRequest(request, file);
                    this._sendRequest(request, file, params);
                    return promise;
                }

                _addListeners(
                    request: XMLHttpRequest,
                    file: File,
                ): Promise<UploadInfo> {
                    request.upload.addEventListener("loadstart", (event) =>
                        this.dispatchStart(file),
                    );

                    request.upload.addEventListener("progress", (event) =>
                        this.dispatchProgress(file, event.loaded, event.total),
                    );

                    return new Promise((done, fail) => {
                        request.addEventListener("load", (event) => {
                            const result = JSON.parse(request.responseText);
                            if (typeof result === "string") {
                                this.dispatchError(file, result);
                                fail(result);
                            } else if (result.success) {
                                this.dispatchFinish(file, result.result);
                                done(result.result);
                            } else {
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

                _prepareRequest(request: XMLHttpRequest, file: File) {
                    request.open(
                        "POST",
                        this.sandbox.client.url(
                            `/api/action/${this.settings.uploadAction}`,
                        ),
                    );

                    if (this.csrfToken) {
                        request.setRequestHeader("X-CSRFToken", this.csrfToken);
                    }
                }

                _sendRequest(
                    request: XMLHttpRequest,
                    file: File,
                    params: { [key: string]: any },
                ) {
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

            export class Multipart extends Base {
                static defaultSettings = {
                    chunkSize: 1024 * 1024 * 5,
                    uploadAction: "files_multipart_start",
                };

                private _active = new Set<File>();

                constructor(settings: Object) {
                    super(settings);
                }

                async upload(file: File, params: { [key: string]: any }) {
                    if (this._active.has(file)) {
                        console.warn("File upload in progress");
                        return;
                    }
                    this._active.add(file);

                    let info;

                    try {
                        info = await this._initializeUpload(file, params);
                    } catch (err) {
                        if (typeof err === "string") {
                            this.dispatchError(file, err);
                        } else {
                            this.dispatchFail(file, err as any);
                        }
                        return;
                    }

                    this.dispatchMultipartId(file, info.id);

                    this.dispatchStart(file);

                    return this._doUpload(file, info);
                }

                async resume(file: File, id: string) {
                    if (this._active.has(file)) {
                        console.warn("File upload in progress");
                        return;
                    }
                    this._active.add(file);

                    let info = await this._showUpload(id);
                    this.dispatchStart(file);

                    this._doUpload(file, info);
                }

                pause(file: File) {
                    this._active.delete(file);
                }

                async _doUpload(file: File, info: UploadInfo) {
                    let start = info.storage_data["uploaded"] || 0;

                    while (start < file.size) {
                        if (!this._active.has(file)) {
                            console.info("File upload is paused");
                            return;
                        }

                        info = await this._uploadChunk(
                            info,
                            file.slice(start, start + this.settings.chunkSize),
                            start,
                            {
                                progressData: {
                                    file,
                                    uploaded: info.storage_data.uploaded,
                                    size: file.size,
                                },
                            },
                        );

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
                    } catch (err) {
                        if (typeof err === "string") {
                            this.dispatchError(file, err);
                        } else {
                            this.dispatchFail(file, err as any);
                        }

                        return;
                    }
                    this.dispatchFinish(file, info);
                    return info;
                }

                _initializeUpload(
                    file: File,
                    params: { [key: string]: any },
                ): Promise<UploadInfo> {
                    return new Promise((done, fail) => {
                        const url = this.sandbox.client.url(
                            `/api/action/${this.settings.uploadAction}`,
                        );

                        const data = new FormData();
                        data.append("storage", this.settings.storage);
                        data.append("name", file.name);
                        data.append("size", String(file.size));
                        data.append(
                            "content_type",
                            file.type || "application/octet-stream",
                        );
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
                            success: (data: any) => {
                                done(data.result);
                            },
                            error: (resp: any) => {
                                fail(
                                    typeof resp.responseJSON === "string"
                                        ? resp.responseText
                                        : resp.responseJSON.error,
                                );
                            },
                        });
                    });
                }

                _showUpload(id: string): Promise<UploadInfo> {
                    return new Promise((done, fail) =>
                        this.sandbox.client.call(
                            "GET",
                            "files_multipart_refresh",
                            `?id=${id}`,
                            (data: any) => {
                                done(data.result);
                            },
                            (resp: any) => {
                                fail(
                                    typeof resp.responseJSON === "string"
                                        ? resp.responseText
                                        : resp.responseJSON.error,
                                );
                            },
                        ),
                    );
                }

                _uploadChunk(
                    info: UploadInfo,
                    part: Blob,
                    start: number,
                    extras: any = {},
                ): Promise<UploadInfo> {
                    if (!part.size) {
                        throw new Error("0-length chunks are not allowed");
                    }
                    const request = new XMLHttpRequest();

                    const result = new Promise<UploadInfo>((done, fail) => {
                        if (extras["progressData"]) {
                            const { file, uploaded, size } =
                                extras["progressData"];
                            request.upload.addEventListener(
                                "progress",
                                (event) => {
                                    this.dispatchProgress(
                                        file,
                                        uploaded + event.loaded,
                                        size,
                                    );
                                },
                            );
                        }

                        request.addEventListener("load", (event) => {
                            const result = JSON.parse(request.responseText);
                            if (result.success) {
                                done(result.result);
                            } else {
                                fail(result.error);
                            }
                        });

                        request.addEventListener("error", (event) =>
                            fail(request.responseText),
                        );
                    });

                    request.open(
                        "POST",
                        this.sandbox.client.url(
                            "/api/action/files_multipart_update",
                        ),
                    );

                    if (this.csrfToken) {
                        request.setRequestHeader("X-CSRFToken", this.csrfToken);
                    }

                    this._sendRequest(request, part, start, info.id);

                    return result;
                }

                _sendRequest(
                    request: XMLHttpRequest,
                    part: Blob,
                    position: number,
                    id: string,
                ) {
                    const form = new FormData();
                    form.append("upload", part);
                    form.append("position", String(position));
                    form.append("id", id);
                    request.send(form);
                }

                _completeUpload(info: UploadInfo): Promise<UploadInfo> {
                    return new Promise((done, fail) =>
                        this.sandbox.client.call(
                            "POST",
                            "files_multipart_complete",
                            Object.assign(
                                {},
                                this.settings.completePayload || {},
                                {
                                    id: info.id,
                                },
                            ),
                            (data: any) => {
                                done(data.result);
                            },
                            (resp: any) => {
                                fail(
                                    typeof resp.responseJSON === "string"
                                        ? resp.responseText
                                        : resp.responseJSON.error,
                                );
                            },
                        ),
                    );
                }
            }
        }
    }
}
