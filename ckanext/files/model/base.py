from __future__ import annotations

from datetime import datetime, timezone

import ckan.plugins.toolkit as tk

Base = tk.BaseModel


def now():
    return datetime.now(timezone.utc)
