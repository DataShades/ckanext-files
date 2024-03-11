declare namespace ckan {
    namespace CKANEXT_FILES {
        namespace adapters {
            type GCSUploadInfo = UploadInfo & {
                storage_data: StorageData & {
                    session_url: string;
                };
            };
            class GCSMultipart extends Multipart {
                _uploadChunk(info: GCSUploadInfo, part: Blob, start: number): Promise<UploadInfo>;
            }
        }
    }
}
