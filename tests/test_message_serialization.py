import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from python_omgidl.omgidl_serialization.message_reader import (  # noqa: E402
    MessageReader,
)
from python_omgidl.omgidl_serialization.message_writer import (  # noqa: E402
    MessageDefinitionField,
    MessageWriter,
)


def test_constants_and_defaults():
    fields = [
        MessageDefinitionField(
            name="CONST", type="uint32", is_constant=True, default_value=1
        ),
        MessageDefinitionField(name="value", type="uint32", default_value=5),
    ]
    writer = MessageWriter(fields)
    assert writer.write({"value": 10}) == {"value": 10}
    assert writer.write({}) == {"value": 5}

    reader = MessageReader(fields)
    assert reader.read({"value": 7}) == {"value": 7}
    assert reader.read({}) == {"value": 5}
