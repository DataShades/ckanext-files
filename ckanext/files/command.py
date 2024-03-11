from __future__ import print_function

import logging

import paste.script

from ckan import model
from ckan.lib.cli import CkanCommand

from ckanext.files.model.base import metadata

log = logging.getLogger(__name__)


def drop_tables():
    """Drop tables defined in model."""
    metadata.drop_all(model.meta.engine)


def create_tables():
    """Create tables defined in model."""
    metadata.create_all(model.meta.engine)


class FilesCommand(CkanCommand):
    """
    ckanext-files management commands.

    Usage::
        paster --plugin=ckanext-files files  -c ckan.ini initdb
        paster --plugin=ckanext-files files  -c ckan.ini dropdb
    """

    summary = __doc__.split("\n")[0]
    usage = __doc__

    parser = paste.script.command.Command.standard_parser(verbose=True)
    parser.add_option(
        "-c",
        "--config",
        dest="config",
        default="ckan.ini",
        help="Config file to use.",
    )

    def command(self):
        """Command itself."""
        self._load_config()

        if not len(self.args):
            print(self.usage)  # noqa

        elif self.args[0] == "initdb":
            self._init()
        elif self.args[0] == "dropdb":
            self._drop()
        elif self.args[0] == "createdb":
            self._create()

    def _init(self):
        self._drop()
        self._create()
        log.info("DB tables are reinitialized")

    def _drop(self):
        model.Session.rollback()

        drop_tables()
        log.info("DB tables are removed")

    def _create(self):
        model.Session.rollback()

        create_tables()
        log.info("DB tables are setup")
