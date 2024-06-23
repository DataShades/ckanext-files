const ckan = () => cy.window({ log: false }).then((win) => win["ckan"]);

const sandbox = () => ckan().invoke({ log: false }, "sandbox");

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

    it.only("accepts parameters for API action", () => {
        cy.intercept("/api/action/files_file_create", (req) =>
            req.reply({ success: true, result: {} }),
        ).as("makeFile");

        sandbox().then(({ files }) => {
            files.upload(new File(["test"], "test.txt"), {
                requestParams: {
                    hello: "world",
                    storage: "memory",
                    value: 42,
                },
            });
        });

        cy.wait("@makeFile").interceptFormData((data) => {
            expect(data).includes({
                storage: "memory",
                hello: "world",
                value: 42,
            });
        });
    });
});
