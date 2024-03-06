import logging

from flask import Blueprint

log = logging.getLogger(__name__)
bp = Blueprint("files", __name__)


def get_blueprints():
    return [bp]
