from dataclasses import dataclass
from typing import Any, Dict, Iterable, List


@dataclass
class MessageDefinitionField:
    """Represents a field within a message definition.

    Attributes:
        name: Field name.
        type: Field type name.
        is_constant: If True, the field represents a constant and should not be
            serialized.
        default_value: Value to use when no value is provided for a field.
    """

    name: str
    type: str
    is_constant: bool = False
    default_value: Any | None = None


class MessageWriter:
    """Serializes messages based on a sequence of message definition fields."""

    def __init__(self, fields: Iterable[MessageDefinitionField]):
        self.fields: List[MessageDefinitionField] = list(fields)

    def write(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a message for serialization.

        Constant fields are omitted and fields with missing values will use the
        field's default value when provided.
        """

        result: Dict[str, Any] = {}
        for field in self.fields:
            if field.is_constant:
                continue
            if field.name in data:
                result[field.name] = data[field.name]
            elif field.default_value is not None:
                result[field.name] = field.default_value
            else:
                raise KeyError(f"Missing value for field '{field.name}'")
        return result
