export {};

declare global {
    namespace CkanextFiles {
        export type UploaderSettings = {
            storage: string;
        } & Record<string, any>;

        export interface UploadOptions {
            uploader?: Adapter;
            adapter?: string;
            uploaderArgs?: any[];
            requestParams?: Record<string, any>;
        }

        export interface Adapter extends EventTarget {
            defaultSettings: Record<string, any>;
            settings: UploaderSettings;
            sandbox: ISandbox;
            csrfToken: string;

            upload(file: File, params: Record<string, any>): void;
            resume(file: File, id: string): void;
            dispatchStart(file: File): void;
            dispatchMultipartId(file: File, id: string): void;
            dispatchProgress(file: File, loaded: number, total: number): void;
            dispatchFinish(file: File, result: Object): void;
            dispatchFail(
                file: File,
                reasons: { [key: string]: string[] },
            ): void;
            dispatchError(file: File, message: string): void;
        }
        export interface AdapterConstructor {
            new (settings?: Record<string, any>, ...rest: any): Adapter;
            defaultSettings: Record<string, any>;
        }

        export namespace adapters {
            export type StorageData = Record<string, any>;

            export type UploadInfo = {
                id: string;
                storage_data: StorageData;
                location: string;
                hash: string;
                content_type: string;
                size: number;
            };
        }
    }

    interface ISandboxFiles {
        upload(file: File, options?: CkanextFiles.UploadOptions): any;
        makeUploader(adapter: string, ...options: any): CkanextFiles.Adapter;
        defaultSettings: CkanextFiles.UploaderSettings;
        adapters: Record<string, CkanextFiles.AdapterConstructor>;
    }

    interface ISandbox {
        notify: {
            initialize: (element: JQuery | HTMLElement) => JQuery;
            create: (title: string, message: string, type?: string) => JQuery;
            (title: string, content: string, type?: string): any;
            el: JQuery;
        };

        client: {
            url(path: string): string;
            call(
                type: "GET",
                path: string,
                data?: string,
                fn?: Function,
                error?: Function,
            ): void;
            call(
                type: "POST",
                path: string,
                data?: object,
                fn?: Function,
                error?: Function,
            ): void;
        };
        jQuery: JQueryStatic;
        files: ISandboxFiles;
        publish: (topic: string, ...rest: any) => void;

        ui: any;
    }

    interface IModule {
        $: JQueryStatic;
        el: JQuery;
        sandbox: ISandbox;
        initialize(): void;
        teardown?(): void;
    }

    interface ISandboxFactory {
        (): ISandbox;
        setup: (callback: (sandbox: ISandbox) => void) => void;
        extend: (props: object) => void;
    }

    interface ICkan {
        sandbox: ISandboxFactory;
        pubsub: any;

        module: <T extends object>(
            name: string,
            initializer: ($: JQueryStatic) => T & ThisType<T & IModule>,
        ) => any;
    }
    interface Window {
        ckan: ICkan;
    }
}
