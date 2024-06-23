const ckan = () => cy.window({ log: false }).then((win) => win["ckan"]);

const sandbox = () => ckan().invoke({ log: false }, "sandbox");

const intercept = (
    action: string,
    success: boolean = true,
    result: any = {},
    alias: string = "request",
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

    it("uploads files", () => {
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

    it.only("accepts params and even can override storage", () => {
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
