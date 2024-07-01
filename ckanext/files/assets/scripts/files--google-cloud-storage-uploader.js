var ckan;
(function (ckan) {
    let CKANEXT_FILES;
    (function (CKANEXT_FILES) {
        let adapters;
        (function (adapters) {
            class GCSMultipart extends adapters.Multipart {
                async _uploadChunk(info, part, start) {
                    if (!part.size) {
                        throw new Error("0-length chunks are not allowed");
                    }
                    const request = new XMLHttpRequest();
                    request.open("PUT", info.storage_data.session_url);
                    request.setRequestHeader("content-range", `bytes ${start}-${start + part.size - 1}/${info.size}`);
                    request.send(part);
                    const resp = await new Promise((done, fail) => {
                        request.addEventListener("load", (event) => done(request));
                    });
                    let uploaded;
                    if ([200, 201].includes(resp.status)) {
                        uploaded = info.size;
                    }
                    else if (resp.status === 308) {
                        const range = resp.getResponseHeader("range");
                        uploaded = Number(range.split("=")[1].split("-")[1]) + 1;
                    }
                    else {
                        throw new Error(await resp.responseText);
                    }
                    if (!Number.isInteger(uploaded)) {
                        throw new Error(`Invalid uploaded size ${uploaded}`);
                    }
                    return new Promise((done, fail) => {
                        this.sandbox.client.call("POST", "files_multipart_update", {
                            id: info.id,
                            uploaded,
                        }, (data) => {
                            done(data.result);
                        }, (resp) => {
                            fail(typeof resp.responseJSON === "string"
                                ? resp.responseText
                                : resp.responseJSON.error);
                        });
                    });
                }
            }
            adapters.GCSMultipart = GCSMultipart;
        })(adapters = CKANEXT_FILES.adapters || (CKANEXT_FILES.adapters = {}));
    })(CKANEXT_FILES = ckan.CKANEXT_FILES || (ckan.CKANEXT_FILES = {}));
})(ckan || (ckan = {}));
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZmlsZXMtLWdvb2dsZS1jbG91ZC1zdG9yYWdlLXVwbG9hZGVyLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiLi4vdHMvZmlsZXMtLWdvb2dsZS1jbG91ZC1zdG9yYWdlLXVwbG9hZGVyLnRzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLElBQVUsSUFBSSxDQW9FYjtBQXBFRCxXQUFVLElBQUk7SUFDWixJQUFpQixhQUFhLENBa0U3QjtJQWxFRCxXQUFpQixhQUFhO1FBQzVCLElBQWlCLFFBQVEsQ0FnRXhCO1FBaEVELFdBQWlCLFFBQVE7WUFLdkIsTUFBYSxZQUFhLFNBQVEsU0FBQSxTQUFTO2dCQUN6QyxLQUFLLENBQUMsWUFBWSxDQUNoQixJQUFtQixFQUNuQixJQUFVLEVBQ1YsS0FBYTtvQkFFYixJQUFJLENBQUMsSUFBSSxDQUFDLElBQUksRUFBRSxDQUFDO3dCQUNmLE1BQU0sSUFBSSxLQUFLLENBQUMsaUNBQWlDLENBQUMsQ0FBQztvQkFDckQsQ0FBQztvQkFFRCxNQUFNLE9BQU8sR0FBRyxJQUFJLGNBQWMsRUFBRSxDQUFDO29CQUVyQyxPQUFPLENBQUMsSUFBSSxDQUFDLEtBQUssRUFBRSxJQUFJLENBQUMsWUFBWSxDQUFDLFdBQVcsQ0FBQyxDQUFDO29CQUNuRCxPQUFPLENBQUMsZ0JBQWdCLENBQ3RCLGVBQWUsRUFDZixTQUFTLEtBQUssSUFBSSxLQUFLLEdBQUcsSUFBSSxDQUFDLElBQUksR0FBRyxDQUFDLElBQUksSUFBSSxDQUFDLElBQUksRUFBRSxDQUN2RCxDQUFDO29CQUNGLE9BQU8sQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUM7b0JBRW5CLE1BQU0sSUFBSSxHQUFRLE1BQU0sSUFBSSxPQUFPLENBQUMsQ0FBQyxJQUFJLEVBQUUsSUFBSSxFQUFFLEVBQUU7d0JBQ2pELE9BQU8sQ0FBQyxnQkFBZ0IsQ0FBQyxNQUFNLEVBQUUsQ0FBQyxLQUFLLEVBQUUsRUFBRSxDQUFDLElBQUksQ0FBQyxPQUFPLENBQUMsQ0FBQyxDQUFDO29CQUM3RCxDQUFDLENBQUMsQ0FBQztvQkFDSCxJQUFJLFFBQVEsQ0FBQztvQkFFYixJQUFJLENBQUMsR0FBRyxFQUFFLEdBQUcsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxJQUFJLENBQUMsTUFBTSxDQUFDLEVBQUUsQ0FBQzt3QkFDckMsUUFBUSxHQUFHLElBQUksQ0FBQyxJQUFJLENBQUM7b0JBQ3ZCLENBQUM7eUJBQU0sSUFBSSxJQUFJLENBQUMsTUFBTSxLQUFLLEdBQUcsRUFBRSxDQUFDO3dCQUMvQixNQUFNLEtBQUssR0FBRyxJQUFJLENBQUMsaUJBQWlCLENBQUMsT0FBTyxDQUFDLENBQUM7d0JBQzlDLFFBQVEsR0FBRyxNQUFNLENBQUMsS0FBSyxDQUFDLEtBQUssQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsR0FBRyxDQUFDLENBQUM7b0JBQzNELENBQUM7eUJBQU0sQ0FBQzt3QkFDTixNQUFNLElBQUksS0FBSyxDQUFDLE1BQU0sSUFBSSxDQUFDLFlBQVksQ0FBQyxDQUFDO29CQUMzQyxDQUFDO29CQUVELElBQUksQ0FBQyxNQUFNLENBQUMsU0FBUyxDQUFDLFFBQVEsQ0FBQyxFQUFFLENBQUM7d0JBQ2hDLE1BQU0sSUFBSSxLQUFLLENBQUMseUJBQXlCLFFBQVEsRUFBRSxDQUFDLENBQUM7b0JBQ3ZELENBQUM7b0JBRUQsT0FBTyxJQUFJLE9BQU8sQ0FBQyxDQUFDLElBQUksRUFBRSxJQUFJLEVBQUUsRUFBRTt3QkFDaEMsSUFBSSxDQUFDLE9BQU8sQ0FBQyxNQUFNLENBQUMsSUFBSSxDQUN0QixNQUFNLEVBQ04sd0JBQXdCLEVBQ3hCOzRCQUNFLEVBQUUsRUFBRSxJQUFJLENBQUMsRUFBRTs0QkFDWCxRQUFRO3lCQUNULEVBQ0QsQ0FBQyxJQUFTLEVBQUUsRUFBRTs0QkFDWixJQUFJLENBQUMsSUFBSSxDQUFDLE1BQU0sQ0FBQyxDQUFDO3dCQUNwQixDQUFDLEVBQ0QsQ0FBQyxJQUFTLEVBQUUsRUFBRTs0QkFDWixJQUFJLENBQ0YsT0FBTyxJQUFJLENBQUMsWUFBWSxLQUFLLFFBQVE7Z0NBQ25DLENBQUMsQ0FBQyxJQUFJLENBQUMsWUFBWTtnQ0FDbkIsQ0FBQyxDQUFDLElBQUksQ0FBQyxZQUFZLENBQUMsS0FBSyxDQUM1QixDQUFDO3dCQUNKLENBQUMsQ0FDRixDQUFDO29CQUNKLENBQUMsQ0FBQyxDQUFDO2dCQUNMLENBQUM7YUFDRjtZQTFEWSxxQkFBWSxlQTBEeEIsQ0FBQTtRQUNILENBQUMsRUFoRWdCLFFBQVEsR0FBUixzQkFBUSxLQUFSLHNCQUFRLFFBZ0V4QjtJQUNILENBQUMsRUFsRWdCLGFBQWEsR0FBYixrQkFBYSxLQUFiLGtCQUFhLFFBa0U3QjtBQUNILENBQUMsRUFwRVMsSUFBSSxLQUFKLElBQUksUUFvRWIiLCJzb3VyY2VzQ29udGVudCI6WyJuYW1lc3BhY2UgY2thbiB7XG4gIGV4cG9ydCBuYW1lc3BhY2UgQ0tBTkVYVF9GSUxFUyB7XG4gICAgZXhwb3J0IG5hbWVzcGFjZSBhZGFwdGVycyB7XG4gICAgICBleHBvcnQgdHlwZSBHQ1NVcGxvYWRJbmZvID0gVXBsb2FkSW5mbyAmIHtcbiAgICAgICAgc3RvcmFnZV9kYXRhOiBTdG9yYWdlRGF0YSAmIHsgc2Vzc2lvbl91cmw6IHN0cmluZyB9O1xuICAgICAgfTtcblxuICAgICAgZXhwb3J0IGNsYXNzIEdDU011bHRpcGFydCBleHRlbmRzIE11bHRpcGFydCB7XG4gICAgICAgIGFzeW5jIF91cGxvYWRDaHVuayhcbiAgICAgICAgICBpbmZvOiBHQ1NVcGxvYWRJbmZvLFxuICAgICAgICAgIHBhcnQ6IEJsb2IsXG4gICAgICAgICAgc3RhcnQ6IG51bWJlcixcbiAgICAgICAgKTogUHJvbWlzZTxVcGxvYWRJbmZvPiB7XG4gICAgICAgICAgaWYgKCFwYXJ0LnNpemUpIHtcbiAgICAgICAgICAgIHRocm93IG5ldyBFcnJvcihcIjAtbGVuZ3RoIGNodW5rcyBhcmUgbm90IGFsbG93ZWRcIik7XG4gICAgICAgICAgfVxuXG4gICAgICAgICAgY29uc3QgcmVxdWVzdCA9IG5ldyBYTUxIdHRwUmVxdWVzdCgpO1xuXG4gICAgICAgICAgcmVxdWVzdC5vcGVuKFwiUFVUXCIsIGluZm8uc3RvcmFnZV9kYXRhLnNlc3Npb25fdXJsKTtcbiAgICAgICAgICByZXF1ZXN0LnNldFJlcXVlc3RIZWFkZXIoXG4gICAgICAgICAgICBcImNvbnRlbnQtcmFuZ2VcIixcbiAgICAgICAgICAgIGBieXRlcyAke3N0YXJ0fS0ke3N0YXJ0ICsgcGFydC5zaXplIC0gMX0vJHtpbmZvLnNpemV9YCxcbiAgICAgICAgICApO1xuICAgICAgICAgIHJlcXVlc3Quc2VuZChwYXJ0KTtcblxuICAgICAgICAgIGNvbnN0IHJlc3A6IGFueSA9IGF3YWl0IG5ldyBQcm9taXNlKChkb25lLCBmYWlsKSA9PiB7XG4gICAgICAgICAgICByZXF1ZXN0LmFkZEV2ZW50TGlzdGVuZXIoXCJsb2FkXCIsIChldmVudCkgPT4gZG9uZShyZXF1ZXN0KSk7XG4gICAgICAgICAgfSk7XG4gICAgICAgICAgbGV0IHVwbG9hZGVkO1xuXG4gICAgICAgICAgaWYgKFsyMDAsIDIwMV0uaW5jbHVkZXMocmVzcC5zdGF0dXMpKSB7XG4gICAgICAgICAgICB1cGxvYWRlZCA9IGluZm8uc2l6ZTtcbiAgICAgICAgICB9IGVsc2UgaWYgKHJlc3Auc3RhdHVzID09PSAzMDgpIHtcbiAgICAgICAgICAgIGNvbnN0IHJhbmdlID0gcmVzcC5nZXRSZXNwb25zZUhlYWRlcihcInJhbmdlXCIpO1xuICAgICAgICAgICAgdXBsb2FkZWQgPSBOdW1iZXIocmFuZ2Uuc3BsaXQoXCI9XCIpWzFdLnNwbGl0KFwiLVwiKVsxXSkgKyAxO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICB0aHJvdyBuZXcgRXJyb3IoYXdhaXQgcmVzcC5yZXNwb25zZVRleHQpO1xuICAgICAgICAgIH1cblxuICAgICAgICAgIGlmICghTnVtYmVyLmlzSW50ZWdlcih1cGxvYWRlZCkpIHtcbiAgICAgICAgICAgIHRocm93IG5ldyBFcnJvcihgSW52YWxpZCB1cGxvYWRlZCBzaXplICR7dXBsb2FkZWR9YCk7XG4gICAgICAgICAgfVxuXG4gICAgICAgICAgcmV0dXJuIG5ldyBQcm9taXNlKChkb25lLCBmYWlsKSA9PiB7XG4gICAgICAgICAgICB0aGlzLnNhbmRib3guY2xpZW50LmNhbGwoXG4gICAgICAgICAgICAgIFwiUE9TVFwiLFxuICAgICAgICAgICAgICBcImZpbGVzX211bHRpcGFydF91cGRhdGVcIixcbiAgICAgICAgICAgICAge1xuICAgICAgICAgICAgICAgIGlkOiBpbmZvLmlkLFxuICAgICAgICAgICAgICAgIHVwbG9hZGVkLFxuICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICAoZGF0YTogYW55KSA9PiB7XG4gICAgICAgICAgICAgICAgZG9uZShkYXRhLnJlc3VsdCk7XG4gICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgIChyZXNwOiBhbnkpID0+IHtcbiAgICAgICAgICAgICAgICBmYWlsKFxuICAgICAgICAgICAgICAgICAgdHlwZW9mIHJlc3AucmVzcG9uc2VKU09OID09PSBcInN0cmluZ1wiXG4gICAgICAgICAgICAgICAgICAgID8gcmVzcC5yZXNwb25zZVRleHRcbiAgICAgICAgICAgICAgICAgICAgOiByZXNwLnJlc3BvbnNlSlNPTi5lcnJvcixcbiAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgKTtcbiAgICAgICAgICB9KTtcbiAgICAgICAgfVxuICAgICAgfVxuICAgIH1cbiAgfVxufVxuIl19
