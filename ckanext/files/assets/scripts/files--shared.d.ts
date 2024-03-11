declare namespace ckan {
    var sandbox: any;
    var pubsub: any;
    var module: (name: string, initializer: ($: any) => any) => any;
    namespace CKANEXT_FILES {
        type UploaderSettings = {
            storage: string;
            [key: string]: any;
        };
        export const topics: {
            addFileToQueue: string;
            restoreFileInQueue: string;
            queueItemUploaded: string;
        };
        export const defaultSettings: {
            storage: string;
        };
        export namespace adapters {
            type StorageData = {
                uploaded: number;
                size: number;
            };
            type UploadInfo = {
                id: string;
                storage_data: StorageData;
            };
            class Base extends EventTarget {
                static defaultSettings: Object;
                protected settings: UploaderSettings;
                protected sandbox: any;
                protected csrfToken: string;
                constructor(settings?: {});
                upload(file: File): void;
                resume(file: File, id: string): void;
                dispatchStart(file: File): void;
                dispatchCommit(file: File, id: string): void;
                dispatchProgress(file: File, loaded: number, total: number): void;
                dispatchFinish(file: File, result: Object): void;
                dispatchFail(file: File, reasons: {
                    [key: string]: string[];
                }): void;
                dispatchError(file: File, message: string): void;
            }
            class Standard extends Base {
                upload(file: File): XMLHttpRequest;
                _addListeners(request: XMLHttpRequest, file: File): void;
                _prepareRequest(request: XMLHttpRequest, file: File): void;
                _sendRequest(request: XMLHttpRequest, file: File): void;
            }
            class Multipart extends Base {
                static defaultSettings: {
                    chunkSize: number;
                };
                private _active;
                constructor(settings: Object);
                upload(file: File): Promise<void>;
                resume(file: File, id: string): Promise<void>;
                pause(file: File): void;
                _doUpload(file: File, info: UploadInfo): Promise<void>;
                _initializeUpload(file: File): Promise<UploadInfo>;
                _showUpload(id: string): Promise<UploadInfo>;
                _uploadChunk(info: UploadInfo, part: Blob, start: number): Promise<UploadInfo>;
                _sendRequest(request: XMLHttpRequest, part: Blob, position: number, id: string): void;
                _completeUpload(info: UploadInfo): Promise<UploadInfo>;
            }
        }
        export {};
    }
}
