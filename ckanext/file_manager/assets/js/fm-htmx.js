ckan.module("fm-htmx", function ($) {
    return {
        options: {
            formId: null,
        },
        initialize: function () {
            $.proxyAll(this, /_on/);

            document.addEventListener('htmx:beforeRequest', this._onHTMXbeforeRequest);
            document.addEventListener('htmx:afterSettle', this._onHTMXafterSettle);
            document.addEventListener('htmx:confirm', this._onHTMXconfirm);
            document.addEventListener('htmx:afterRequest', this._onAfterRequest)
        },

        _onHTMXbeforeRequest: function (e) {
            $(e.detail.target).find("[data-module]").unbind()

            for (const [key, _] of Object.entries(ckan.module.instances)) {
                ckan.module.instances[key] = null;
            }
        },

        _onHTMXafterSettle: function (e) {
            const doNotInitialize = ["ap-hyperscript"]

            $(e.detail.target).find("[data-module]").each(function (_, element) {
                const moduleName = $(element).attr("data-module");

                if (!doNotInitialize.includes(moduleName)) {
                    ckan.module.initializeElement(element);
                }
            })
        },

        _onHTMXconfirm: function (evt) {
            if (evt.detail.path.includes("/file_manager/delete")) {
                evt.preventDefault();

                swal({
                    text: this._("Are you sure you wish to delete a file?"),
                    icon: "warning",
                    buttons: true,
                    dangerMode: true,
                }).then((confirmed) => {
                    if (confirmed) {
                        evt.detail.issueRequest();
                        this.sandbox.publish("ap:notify", this._("A file has been removed"));
                    }
                });
            }
        },

        _onAfterRequest: function (evt) {
            if (evt.detail.pathInfo.requestPath.includes("/file_manager/delete/")) {
                htmx.trigger(`#${this.options.formId}`, "change");
            }
        }
    };
});
