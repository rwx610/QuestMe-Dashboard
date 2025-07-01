# db/models.py
import json
from sqlalchemy.types import TypeDecorator
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    Float,
    Text,
)
from config import TASK_TABLE


class JSONEncodedDict(TypeDecorator):
    impl = Text

    def process_bind_param(self, value, dialect):
        return json.dumps(value) if value is not None else None

    def process_result_value(self, value, dialect):
        return json.loads(value) if value is not None else None


tables = {
    "data": {
        "id": {"type": String, "kwargs": {"nullable": True, "default": ""}},
        "address": {"type": String, "kwargs": {"primary_key": True}},
        "proxy": {"type": String, "kwargs": {"nullable": True, "default": ""}},
        "headers": {
            "type": JSONEncodedDict,
            "kwargs": {"nullable": True, "default": {}},
        },
    },
    "keys": {
        "address": {"type": String, "kwargs": {"primary_key": True}},
        "key": {"type": String, "kwargs": {"nullable": False}},
    },
    "open_proxy": {
        "proxy": {"type": String, "kwargs": {"primary_key": True}},
    },
    "dead_proxy": {
        "proxy": {"type": String, "kwargs": {"primary_key": True}},
    },
    TASK_TABLE: {
        "address": {"type": String, "kwargs": {"primary_key": True}},
        "total": {"type": Integer, "kwargs": {"nullable": True, "default": 0}},
        "faucet": {"type": Integer, "kwargs": {"nullable": True, "default": 0}},
        "deposit": {"type": Integer, "kwargs": {"nullable": True, "default": 0}},
        "completed": {"type": Boolean, "kwargs": {"nullable": True, "default": False}},
    },
}
