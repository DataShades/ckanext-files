from __future__ import annotations

import ckan.plugins as p
import ckan.plugins.toolkit as tk

import ckanext.ap_main.types as ap_types
from ckanext.ap_main.interfaces import IAdminPanel
from ckanext.ap_main.types import ColRenderer

from ckanext.collection.interfaces import ICollection, CollectionFactory

from ckanext.file_manager.collection import FileManagerCollection
from ckanext.file_manager.col_renderers import get_renderers


@tk.blanket.blueprints
class FileManagerPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(IAdminPanel, inherit=True)
    p.implements(ICollection, inherit=True)

    # IConfigurer

    def update_config(self, config_):
        tk.add_template_directory(config_, "templates")
        tk.add_public_directory(config_, "public")
        tk.add_resource("assets", "file_manager")

    # IAdminPanel

    def register_config_sections(
        self, config_list: list[ap_types.SectionConfig]
    ) -> list[ap_types.SectionConfig]:
        config_list.append(
            ap_types.SectionConfig(
                name="Files",
                configs=[
                    ap_types.ConfigurationItem(
                        name="File manager",
                        blueprint="file_manager.list",
                        info="Manage uploaded files",
                    )
                ],
            )
        )
        return config_list

    def get_col_renderers(self) -> dict[str, ColRenderer]:
        return get_renderers()

    # ICollection

    def get_collection_factories(self) -> dict[str, CollectionFactory]:
        return {"file-manager": FileManagerCollection}
