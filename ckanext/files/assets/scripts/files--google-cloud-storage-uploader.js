"use strict";
var ckan;
(function (ckan) {
    let CKANEXT_FILES;
    (function (CKANEXT_FILES) {
        let adapters;
        (function (adapters) {
            class GCSMultipart extends adapters.Multipart {
                async _uploadChunk(info, part, start) {
                    if (!part.size) {
                        throw new Error("0-length chunks are not allowed");
                    }
                    const request = new XMLHttpRequest();
                    request.open("PUT", info.storage_data.session_url);
                    request.setRequestHeader("content-range", `bytes ${start}-${start + part.size - 1}/${info.storage_data.size}`);
                    request.send(part);
                    const resp = await new Promise((done, fail) => {
                        request.addEventListener("load", (event) => done(request));
                    });
                    let uploaded;
                    if ([200, 201].includes(resp.status)) {
                        uploaded = info.storage_data.size;
                    }
                    else if (resp.status === 308) {
                        const range = resp.getResponseHeader("range");
                        uploaded = Number(range.split("=")[1].split("-")[1]) + 1;
                    }
                    else {
                        throw new Error(await resp.responseText);
                    }
                    if (!Number.isInteger(uploaded)) {
                        throw new Error(`Invalid uploaded size ${uploaded}`);
                    }
                    return new Promise((done, fail) => {
                        this.sandbox.client.call("POST", "files_upload_update", {
                            id: info.id,
                            uploaded,
                        }, (data) => {
                            done(data.result);
                        }, (resp) => {
                            fail(typeof resp.responseJSON === "string"
                                ? resp.responseText
                                : resp.responseJSON.error);
                        });
                    });
                }
            }
            adapters.GCSMultipart = GCSMultipart;
        })(adapters = CKANEXT_FILES.adapters || (CKANEXT_FILES.adapters = {}));
    })(CKANEXT_FILES = ckan.CKANEXT_FILES || (ckan.CKANEXT_FILES = {}));
})(ckan || (ckan = {}));
