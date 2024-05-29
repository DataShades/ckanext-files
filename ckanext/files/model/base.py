from datetime import datetime

import ckan.plugins.toolkit as tk

Base = tk.BaseModel


def now():
    return datetime.utcnow()
