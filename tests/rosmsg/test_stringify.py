from mcap_ros2idl_support.rosmsg import parse, stringify


def test_round_trip_definition():
    message_definition = (
        "uint32 foo = 55\n"
        "int32 bar=-11 # Comment # another comment\n"
        "string test\n"
        "float32 baz= \t -32.25\n"
        "bool someBoolean = 0\n"
        "Point[] points\n"
        "int64 A = 0000000000000001\n"
        "string fooStr = Foo    \n"
        'string EXAMPLE="Hello world"\n'
        "===============\n"
        "MSG: geometry_msgs/Point\n"
        "float64 x"
    )
    types = parse(message_definition)
    output = stringify(types)
    assert (
        output == "uint32 foo = 55\n"
        "int32 bar = -11\n"
        "float32 baz = -32.25\n"
        "bool someBoolean = 0\n"
        "int64 A = 0000000000000001\n"
        "string fooStr = Foo\n"
        'string EXAMPLE = "Hello world"\n'
        "\n"
        "string test\n"
        "geometry_msgs/Point[] points\n"
        "\n"
        "================================================================================\n"  # noqa: E501
        "MSG: geometry_msgs/Point\n"
        "\n"
        "float64 x"
    )


def test_ros2_features():
    message_definition = (
        "string<=5 str1 'abc'\n"
        'string str2 "def"\n'
        "int8[<=2] arr1 [ 1 ,-1 ]    \n"
        "string<=1[<=3] arr2   # comment\n"
        "bool a  true\n"
        "float32 b  -1.0\n"
        "float64 c  42.42\n"
        "int8 d -100\n"
        "uint8 e 100\n"
        "int16 f -1000\n"
        "uint16 g 1000\n"
        "int32 h -100000\n"
        "uint32 i 100000\n"
        "int64 j -5000000000\n"
        "uint64 k 5000000000\n"
        'string my_string1 "I heard \\"Hello\\""# is valid\n'
        "string my_string2 \"I heard 'Hello'\" # is valid\n"
        "string my_string4 'I heard \"Hello\"'   # is valid\n"
    )
    types = parse(message_definition, ros2=True)
    output = stringify(types)
    assert (
        output == 'string<=5 str1 "abc"\n'
        'string str2 "def"\n'
        "int8[<=2] arr1 [1, -1]\n"
        "string<=1[<=3] arr2\n"
        "bool a true\n"
        "float32 b -1\n"
        "float64 c 42.42\n"
        "int8 d -100\n"
        "uint8 e 100\n"
        "int16 f -1000\n"
        "uint16 g 1000\n"
        "int32 h -100000\n"
        "uint32 i 100000\n"
        "int64 j -5000000000\n"
        "uint64 k 5000000000\n"
        'string my_string1 "I heard \\"Hello\\""\n'
        "string my_string2 \"I heard 'Hello'\"\n"
        'string my_string4 "I heard \\"Hello\\""'
    )
