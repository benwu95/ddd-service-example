from dataclasses import dataclass, field

from dataclass_mixins import DataclassMixin


# example usage
@dataclass
class YourAggregateExcel(DataclassMixin):
    id: str = field(metadata={'alias': 'ID'})
    property_a: str = field(metadata={'alias': 'Property A'})
    property_b: int = field(metadata={'alias': 'Property B'})
    status: str = field(metadata={'alias': 'Status'})
    creator: str | None = field(metadata={'alias': 'Creator'})
    created_at: str = field(metadata={'alias': 'Created At'})
