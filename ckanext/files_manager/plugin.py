from __future__ import annotations

from typing import Any

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan.common import CKANConfig
from ckan.types import SignalMapping

from ckanext.collection.interfaces import CollectionFactory, ICollection
from ckanext.files_manager.collection import FilesManagerCollection


@tk.blanket.blueprints
class FilesManagerPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.ISignal)
    p.implements(ICollection, inherit=True)

    # IConfigurer

    def update_config(self, config_: CKANConfig):
        tk.add_template_directory(config_, "templates")
        tk.add_public_directory(config_, "public")
        tk.add_resource("assets", "files_manager")

    # ISignal

    def get_signal_subscriptions(self) -> SignalMapping:
        return {
            tk.signals.ckanext.signal("ap_main:collect_config_sections"): [
                collect_config_sections_subs,
            ],
        }

    # ICollection

    def get_collection_factories(self) -> dict[str, CollectionFactory]:
        return {"files-manager": FilesManagerCollection}


def collect_config_sections_subs(sender: None) -> dict[str, Any]:
    return {
        "name": "Files",
        "configs": [
            {
                "name": "File manager",
                "blueprint": "files_manager.list",
                "info": "Manage uploaded files",
            },
        ],
    }
