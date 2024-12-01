namespace ckan {
  export namespace CKANEXT_FILES {
    export namespace adapters {
      export type S3UploadInfo = UploadInfo & {
        storage_data: StorageData & { upload_url: string };
      };

      export class S3Multipart extends Multipart {
        async __x_uploadChunk(
          info: S3UploadInfo,
          part: Blob,
          start: number,
        ): Promise<UploadInfo> {
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
                  etag: resp.getResponseHeader("ETag")
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
    }
  }
}
