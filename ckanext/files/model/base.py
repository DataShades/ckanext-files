from datetime import datetime

from sqlalchemy.ext.declarative import declarative_base

from ckan.model.meta import metadata

Base = declarative_base(metadata=metadata)


def now():
    return datetime.utcnow()
