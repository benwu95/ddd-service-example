from dataclasses import dataclass

from dataclass_mixins import DataclassMixin


@dataclass
class ExamplePayload(DataclassMixin):
    customer_name: str
