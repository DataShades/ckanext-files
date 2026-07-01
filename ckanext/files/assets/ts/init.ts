
window.ckan.sandbox.setup((sb) => {
    Object.assign(sb, {
        files: {
            upload(file: File, options: CkanextFiles.UploadOptions = {}) {
                const uploader =
                    options.uploader ||
                    this.makeUploader(
                        "Standard",
                        ...(options.uploaderArgs || []),
                    );
                return uploader.upload(file, options.requestParams || {});
            },

            makeUploader(adapter: string, ...options: any) {
                const factory = this.adapters[adapter];
                if (!factory) {
                    throw new Error(`Uploader ${adapter} is not registered`);
                }
                return new factory(...options);
            },

            defaultSettings: {
                storage: "default",
            },
            adapters: {},
        } as ISandboxFiles,
    });
});
