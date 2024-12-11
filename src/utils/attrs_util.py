# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
from datetime import datetime
from typing import Union, get_args

from attr import NOTHING, Factory, fields, has
from cattr import Converter


# Could not figure out how to make typing work, so we do this workaround
def attrs_init_replacement(cls=None):
    def init(self, **kwargs):

        for attr in fields(cls):
            if not hasattr(self, attr.name):
                value = kwargs.get(attr.name) if attr.name in kwargs else attr.default
                if isinstance(value, Factory):
                    value = value.factory()
                if value is NOTHING:
                    raise ValueError(f"Required attribute '{attr.name}' is missing and does not have a default value.")
                if isinstance(value, float):
                    value = round(value, 3)
                setattr(self, attr.name, value)

    cls.__init__ = init
    return cls


converter = Converter()


def structure_datetime(value, *_):
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    if isinstance(value, datetime):
        return value
    if value is None:
        return datetime.now()
    raise ValueError(f"Cannot structure value {value} as {datetime}")


def structure_union(value, cl):
    union_types = get_args(cl)

    for union_type in union_types:
        try:
            if isinstance(value, dict):
                if has(union_type):
                    return converter.structure(value, union_type)
                return union_type(**value)
            if union_type is datetime:
                return structure_datetime(value)
            if value.__class__ is union_type:
                return value
            return union_type(value)
        # pylint: disable=W0718
        except Exception:
            continue
    raise ValueError(f"Cannot structure value {value} as {cl}")


converter.register_structure_hook_factory(
    lambda cls: getattr(cls, "__origin__", None) is Union, lambda *_: structure_union
)
converter.register_structure_hook(datetime, structure_datetime)
converter.register_unstructure_hook(datetime, lambda d: d.isoformat())
