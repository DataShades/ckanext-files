from __future__ import annotations

import ckan.types as types
import ckan.plugins as p
import ckan.plugins.toolkit as tk

from ckanext.collection.interfaces import ICollection, CollectionFactory

from ckanext.file_manager.collection import FileManagerCollection


@tk.blanket.blueprints
class FileManagerPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.ISignal)
    p.implements(ICollection, inherit=True)

    # IConfigurer

    def update_config(self, config_):
        tk.add_template_directory(config_, "templates")
        tk.add_public_directory(config_, "public")
        tk.add_resource("assets", "file_manager")

    # ISignal

    def get_signal_subscriptions(self) -> types.SignalMapping:
        return {
            tk.signals.ckanext.signal("ap_main:collect_config_sections"): [
                collect_config_sections_subs
            ],
        }

    # ICollection

    def get_collection_factories(self) -> dict[str, CollectionFactory]:
        return {"file-manager": FileManagerCollection}


def collect_config_sections_subs(sender: None):
    return {
        "name": "Files",
        "configs": [
            {
                "name": "File manager",
                "blueprint": "file_manager.list",
                "info": "Manage uploaded files",
            }
        ],
    }
