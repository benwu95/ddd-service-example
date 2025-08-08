# ref: https://connexion.readthedocs.io/en/latest/validation.html#custom-type-formats

import re

from jsonschema import Draft4Validator


__all__ = [
    'is_uuid',
]


@Draft4Validator.FORMAT_CHECKER.checks('uuid')
def is_uuid(val) -> bool:
    if not isinstance(val, str):
        return True
    pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    )
    return bool(pattern.match(val))
