const ckan = () => cy.window({ log: false }).then((win) => win["ckan"]);

const sandbox = () => ckan().invoke({ log: false }, "sandbox");

const intercept = (
    action: string,
    alias: string = "request",
    result: any = {},
    success: boolean = true,
) =>
    cy
        .intercept("/api/action/" + action, (req) =>
            req.reply(
                Object.assign(
                    { success },
                    success ? { result } : { error: result },
                ),
            ),
        )
        .as(alias);

beforeEach(() => {
    cy.login();
    cy.visit("/about");
});

describe("ckan.CKANEXT_FILES", () => {
    it("has expected properties", () => {
        ckan()
            .its("CKANEXT_FILES")
            .should("have.all.keys", "adapters", "defaultSettings", "topics");
    });
    it("has basic adapters", () => {
        const adapters = ckan().its("CKANEXT_FILES").its("adapters");
        adapters.should("include.all.keys", "Base", "Standard", "Multipart");
    });
});

describe("Sandbox extension", () => {
    it("contains upload and makeUploader functions", () => {
        sandbox()
            .should("have.property", "files")
            .should("have.all.keys", "upload", "makeUploader");
    });
});

describe("sandbox.files.upload", () => {
    it("uses Standard uploader by default", () => {
        const file = new File(["hello"], "test.txt");

        const upload = cy.stub().log(false);
        ckan().then(
            ({
                CKANEXT_FILES: {
                    adapters: { Standard },
                },
            }) => {
                Standard.prototype.upload = upload;
            },
        );

        sandbox()
            .then(({ files }) => files.upload(file))
            .then(() => expect(upload).to.be.calledWith(file));
    });

    it("accepts different adapter name", () => {
        const file = new File(["hello"], "test.txt");
        const upload = cy.stub().log(false);
        ckan().then(
            ({
                CKANEXT_FILES: {
                    adapters: { Multipart },
                },
            }) => {
                Multipart.prototype.upload = upload;
            },
        );

        sandbox()
            .then(({ files }) => files.upload(file, { adapter: "Multipart" }))
            .then(() => expect(upload).to.be.calledWith(file));
    });

    it("passes parameters to adapter", () => {
        const file = new File(["hello"], "test.txt");
        const uploader = { upload: () => {} };
        const adapter = cy.stub().log(false).returns(uploader);

        ckan().then(({ CKANEXT_FILES: { adapters } }) => {
            adapters.Standard = adapter;
        });

        sandbox()
            .then(({ files }) =>
                files.upload(file, { uploaderArgs: ["a", "b", "c"] }),
            )
            .then(() => expect(adapter).to.be.calledWith("a", "b", "c"));
    });

    it("accepts external uploader", () => {
        const file = new File(["hello"], "test.txt");
        const upload = cy.stub().log(false);
        ckan()
            .then(
                ({
                    CKANEXT_FILES: {
                        adapters: { Standard },
                    },
                }) => {
                    const uploader = new Standard();
                    uploader.upload = upload;
                    return uploader;
                },
            )
            .as("uploader");

        sandbox()
            .then(({ files }) =>
                cy
                    .get("@uploader", { log: false })
                    .then((uploader) => files.upload(file, { uploader })),
            )
            .then(() => expect(upload).to.be.calledWith(file));
    });

    it("creates a file", () => {
        const content = "content";
        sandbox()
            .then(({ files }) => files.upload(new File([content], "test.txt")))
            .then((info) => {
                expect(info).to.include({
                    content_type: "text/plain",
                    size: content.length,
                    name: "test.txt",
                    storage: "default",
                });
            });
    });

    it("accepts parameters for API action", () => {
        intercept("files_file_create");
        sandbox().then(({ files }) => {
            files.upload(new File(["test"], "test.txt"), {
                requestParams: {
                    hello: "world",
                    storage: "memory",
                    value: 42,
                },
            });
        });

        cy.wait("@request").interceptFormData((data) => {
            expect(data).includes({
                storage: "memory",
                hello: "world",
                value: "42",
            });
        });
    });
});

describe("Standard uploader", () => {
    beforeEach(() =>
        ckan()
            .then(
                ({
                    CKANEXT_FILES: {
                        adapters: { Standard },
                    },
                }) => Standard,
            )
            .as("adapter"),
    );

    it("sends expected data to server", () => {
        intercept("files_file_create");
        cy.get("@adapter").then((adapter: any) =>
            new adapter().upload(new File(["test"], "test.txt"), {}),
        );

        cy.wait("@request").interceptFormData((data) => {
            expect(data).deep.equal({
                storage: "default",
                upload: "test.txt",
            });
        });
    });

    it("accepts params and even can override storage", () => {
        intercept("files_file_create");
        cy.get("@adapter").then((adapter: any) =>
            new adapter().upload(new File(["test"], "test.txt"), {
                storage: "memory",
                field: "value",
            }),
        );

        cy.wait("@request").interceptFormData((data) => {
            expect(data).deep.equal({
                storage: "memory",
                field: "value",
                upload: "test.txt",
            });
        });
    });
});

describe("Multipart uploader", () => {
    beforeEach(() =>
        ckan()
            .then(
                ({
                    CKANEXT_FILES: {
                        adapters: { Multipart },
                    },
                }) => Multipart,
            )
            .as("adapter"),
    );

    it("sends expected data to server", () => {
        const content = "hello,world";
        const chunkSize = 6;
        let sizes = [content.length, chunkSize];

        intercept("files_multipart_start", "start", {
            id: "1",
            storage_data: { uploaded: 0 },
        });

        cy.intercept("/api/action/files_multipart_update", (req) => {
            return req.reply({
                success: true,
                result: {
                    id: "1",
                    storage_data: {
                        uploaded: sizes.pop(),
                    },
                },
            });
        }).as("update");

        intercept("files_multipart_complete", "complete");

        cy.get("@adapter").then((adapter: any) =>
            new adapter({ chunkSize: chunkSize }).upload(
                new File([content], "test.txt", { type: "text/plain" }),
                {},
            ),
        );

        cy.wait("@start").then(({ request: { body } }) => {
            expect(body).deep.equal({
                size: content.length,
                content_type: "text/plain",
                storage: "default",
                name: "test.txt",
            });
        });

        cy.wait("@update").interceptFormData(
            (data) => {
                expect(data).includes({
                    id: "1",
                    position: "0",
                });

                cy.wrap(data.upload.slice().text()).should(
                    "be.equal",
                    content.slice(0, chunkSize),
                );
            },
            { loadFileContent: true },
        );

        cy.wait("@update").interceptFormData(
            (data) => {
                expect(data).includes({
                    id: "1",
                    position: String(chunkSize),
                });

                cy.wrap(data.upload.slice().text()).should(
                    "be.equal",
                    content.slice(chunkSize, content.length),
                );
            },
            { loadFileContent: true },
        );
        cy.wait("@complete").then(({ request: { body } }) => {
            expect(body).deep.equal({ id: "1" });
        });
    });
});
