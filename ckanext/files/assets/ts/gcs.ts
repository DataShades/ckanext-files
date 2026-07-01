((ckan: ICkan) => {
    type GCSUploadInfo = CkanextFiles.adapters.UploadInfo & {
        storage_data: CkanextFiles.adapters.StorageData & {
            session_url: string;
        };
    };

    ckan.sandbox.setup((sb) => {
        class GCSMultipart extends sb.files.adapters.Multipart {
            async _uploadChunk(
                info: GCSUploadInfo,
                part: Blob,
                start: number,
            ): Promise<CkanextFiles.adapters.UploadInfo> {
                if (!part.size) {
                    throw new Error("0-length chunks are not allowed");
                }

                const request = new XMLHttpRequest();

                request.open("PUT", info.storage_data.session_url);
                request.setRequestHeader(
                    "content-range",
                    `bytes ${start}-${start + part.size - 1}/${info.size}`,
                );
                request.send(part);

                const resp: any = await new Promise((done, fail) => {
                    request.addEventListener("load", (event) => done(request));
                });
                let uploaded;

                if ([200, 201].includes(resp.status)) {
                    uploaded = info.size;
                } else if (resp.status === 308) {
                    const range = resp.getResponseHeader("range");
                    uploaded = Number(range.split("=")[1].split("-")[1]) + 1;
                } else {
                    throw new Error(await resp.responseText);
                }

                if (!Number.isInteger(uploaded)) {
                    throw new Error(`Invalid uploaded size ${uploaded}`);
                }

                return new Promise((done, fail) => {
                    this.sandbox.client.call(
                        "POST",
                        "files_multipart_update",
                        {
                            id: info.id,
                            uploaded,
                        },
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
                    );
                });
            }
        }

        Object.assign(sb.files.adapters, {
            GCSMultipart,
        });
    });
})(window.ckan);
