((ckan: ICkan) => {
    type S3UploadInfo = CkanextFiles.adapters.UploadInfo & {
        storage_data: CkanextFiles.adapters.StorageData & {
            upload_url: string;
        };
    };

    ckan.sandbox.setup((sb) => {
        class S3Multipart extends sb.files.adapters.Multipart {
            async __x_uploadChunk(
                info: S3UploadInfo,
                part: Blob,
                start: number,
            ): Promise<CkanextFiles.adapters.UploadInfo> {
                if (!part.size) {
                    throw new Error("0-length chunks are not allowed");
                }

                debugger;

                const request = new XMLHttpRequest();

                request.open("PUT", info.storage_data.upload_url);
                request.send(part);

                const resp: any = await new Promise((done, fail) => {
                    request.addEventListener("load", (event) => done(request));
                });
                let uploaded;

                if ([200, 201].includes(resp.status)) {
                    uploaded = info.size;
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
                            etag: resp.getResponseHeader("ETag"),
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
            S3Multipart,
        });
    });
})(window.ckan);
