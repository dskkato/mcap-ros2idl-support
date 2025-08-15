from mcap_ros2idl_support.message_definition import (
    MessageDefinition,
    MessageDefinitionField,
    is_msg_def_equal,
)


def test_is_msg_def_equal() -> None:
    a = MessageDefinition(
        name="Foo",
        definitions=[MessageDefinitionField(type="string", name="data")],
    )
    b = MessageDefinition(
        name="Foo",
        definitions=[MessageDefinitionField(type="string", name="data")],
    )
    c = MessageDefinition(
        name="Bar",
        definitions=[MessageDefinitionField(type="string", name="data")],
    )

    assert is_msg_def_equal(a, b)
    assert not is_msg_def_equal(a, c)
