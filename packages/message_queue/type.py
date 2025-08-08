from enum import Enum
from dataclasses import dataclass

from dataclass_mixins import DataclassMixin


class RoutingKey(Enum):
    YOUR_AGGREGATE_SERVICE = 'your-aggregate-service'


class YourAggregateServiceFuntion(Enum):
    YOUR_AGGREGATE_VOIDED = 'your_aggregate_voided'


@dataclass
class YourAggregateVoided(DataclassMixin):
    your_aggregate_id: str
