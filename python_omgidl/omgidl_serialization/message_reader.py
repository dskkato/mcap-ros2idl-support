from typing import Any, Dict, Iterable, List

from .message_writer import MessageDefinitionField


class MessageReader:
    """Deserializes messages based on a sequence of message definition fields."""

    def __init__(self, fields: Iterable[MessageDefinitionField]):
        self.fields: List[MessageDefinitionField] = list(fields)

    def read(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values to deserialized data.

        Constant fields are ignored and missing fields use their default value
        when provided.
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
