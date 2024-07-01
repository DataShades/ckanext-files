ckan.module("fm-htmx", function ($) {
    return {
        options: {
            formId: null,
        },
        initialize: function () {
            $.proxyAll(this, /_on/);

            document.addEventListener('htmx:confirm', this._onHTMXconfirm);
            document.addEventListener('htmx:afterRequest', this._onAfterRequest)
        },

        _onHTMXconfirm: function (evt) {
            if (evt.detail.path.includes("/files_manager/delete")) {
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
            if (evt.detail.pathInfo.requestPath.includes("/files_manager/delete/")) {
                htmx.trigger(`#${this.options.formId}`, "change");
            }
        }
    };
});
