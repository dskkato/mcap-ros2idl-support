from mcap_ros2idl_support.message_definition import (
    MessageDefinition,
    MessageDefinitionField,
)
from mcap_ros2idl_support.rosmsg.parse import fixup_types, parse


def test_parses_single_field():
    assert parse("string name") == [
        MessageDefinition(
            name=None, definitions=[MessageDefinitionField(type="string", name="name")]
        )
    ]


def test_resolves_unqualified_names():
    message_definition = (
        "Point[] points\n" "===============\n" "MSG: geometry_msgs/Point\n" "float64 x"
    )
    assert parse(message_definition) == [
        MessageDefinition(
            name=None,
            definitions=[
                MessageDefinitionField(
                    type="geometry_msgs/Point",
                    name="points",
                    isArray=True,
                    isComplex=True,
                )
            ],
        ),
        MessageDefinition(
            name="geometry_msgs/Point",
            definitions=[MessageDefinitionField(type="float64", name="x")],
        ),
    ]


def test_normalizes_aliases():
    assert parse("char x\nbyte y") == [
        MessageDefinition(
            name=None,
            definitions=[
                MessageDefinitionField(type="uint8", name="x"),
                MessageDefinitionField(type="int8", name="y"),
            ],
        )
    ]


def test_ignores_comment_lines():
    message_definition = (
        "# your first name goes here\n"
        "string firstName\n\n"
        "# last name here\n"
        "### foo bar baz?\n"
        "string lastName\n"
    )
    assert parse(message_definition) == [
        MessageDefinition(
            name=None,
            definitions=[
                MessageDefinitionField(type="string", name="firstName"),
                MessageDefinitionField(type="string", name="lastName"),
            ],
        )
    ]


def test_parses_variable_length_array():
    assert parse("string[] names") == [
        MessageDefinition(
            name=None,
            definitions=[
                MessageDefinitionField(type="string", name="names", isArray=True)
            ],
        )
    ]


def test_parses_fixed_length_array():
    assert parse("string[3] names") == [
        MessageDefinition(
            name=None,
            definitions=[
                MessageDefinitionField(
                    type="string", name="names", isArray=True, arrayLength=3
                )
            ],
        )
    ]


def test_parses_nested_complex_types():
    message_definition = (
        "string username\n"
        "Account account\n"
        "===============\n"
        "MSG: custom_type/Account\n"
        "string name\n"
        "uint16 id"
    )
    assert parse(message_definition) == [
        MessageDefinition(
            name=None,
            definitions=[
                MessageDefinitionField(type="string", name="username"),
                MessageDefinitionField(
                    type="custom_type/Account", name="account", isComplex=True
                ),
            ],
        ),
        MessageDefinition(
            name="custom_type/Account",
            definitions=[
                MessageDefinitionField(type="string", name="name"),
                MessageDefinitionField(type="uint16", name="id"),
            ],
        ),
    ]


def test_returns_constants():
    message_definition = (
        "uint32 foo = 55\n"
        "int32 bar=-11\n"
        "float32 baz= -32.25\n"
        "bool someBoolean = 0\n"
        "string fooStr = Foo\n"
        "int64 A = 0000000000000001"
    )
    assert parse(message_definition) == [
        MessageDefinition(
            name=None,
            definitions=[
                MessageDefinitionField(
                    type="uint32", name="foo", isConstant=True, valueText="55"
                ),
                MessageDefinitionField(
                    type="int32", name="bar", isConstant=True, valueText="-11"
                ),
                MessageDefinitionField(
                    type="float32", name="baz", isConstant=True, valueText="-32.25"
                ),
                MessageDefinitionField(
                    type="bool", name="someBoolean", isConstant=True, valueText="0"
                ),
                MessageDefinitionField(
                    type="string", name="fooStr", isConstant=True, valueText="Foo"
                ),
                MessageDefinitionField(
                    type="int64",
                    name="A",
                    isConstant=True,
                    valueText="0000000000000001",
                ),
            ],
        )
    ]


def test_handles_python_boolean_values():
    message_definition = "bool Alive=True\n" "bool Dead=False"
    assert parse(message_definition) == [
        MessageDefinition(
            name=None,
            definitions=[
                MessageDefinitionField(
                    type="bool", name="Alive", isConstant=True, valueText="True"
                ),
                MessageDefinitionField(
                    type="bool", name="Dead", isConstant=True, valueText="False"
                ),
            ],
        )
    ]


def test_handles_type_names_for_fields():
    assert parse("time time") == [
        MessageDefinition(
            name=None,
            definitions=[MessageDefinitionField(type="time", name="time")],
        )
    ]

    assert parse("time time_ref") == [
        MessageDefinition(
            name=None,
            definitions=[MessageDefinitionField(type="time", name="time_ref")],
        )
    ]

    message_definition = (
        "true true\n" "===============\n" "MSG: custom/true\n" "bool false"
    )
    assert parse(message_definition) == [
        MessageDefinition(
            name=None,
            definitions=[
                MessageDefinitionField(type="custom/true", name="true", isComplex=True)
            ],
        ),
        MessageDefinition(
            name="custom/true",
            definitions=[MessageDefinitionField(type="bool", name="false")],
        ),
    ]


def test_allows_numbers_in_package_names():
    message_definition = (
        "abc1/Foo2 value0\n" "==========\n" "MSG: abc1/Foo2\n" "int32 data"
    )
    assert parse(message_definition) == [
        MessageDefinition(
            name=None,
            definitions=[
                MessageDefinitionField(type="abc1/Foo2", name="value0", isComplex=True)
            ],
        ),
        MessageDefinition(
            name="abc1/Foo2",
            definitions=[MessageDefinitionField(type="int32", name="data")],
        ),
    ]


def test_fixup_types_empty_list():
    types: list[MessageDefinition] = []
    fixup_types(types)
    assert types == []


def test_fixup_types_rewrites_names():
    message_definition = (
        "Point[] points\n" "===============\n" "MSG: geometry_msgs/Point\n" "float64 x"
    )
    types = parse(message_definition, skip_type_fixup=True)
    assert types[0].definitions[0].type == "Point"
    fixup_types(types)
    assert types[0].definitions[0].type == "geometry_msgs/Point"
