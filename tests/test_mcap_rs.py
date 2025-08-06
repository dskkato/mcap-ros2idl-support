import tempfile

import mcap_rs


def test_decode_cdr_from_rust():
    schema_json = (
        '{"1":[{"name":"Msg","definitions":[{"name":"value","type":"uint32",'
        '"isComplex":false}]}]}'
    )
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write(schema_json)
        path = f.name
    reg = mcap_rs.SchemaRegistry([path])
    data = bytes([0, 1, 0, 0]) + (1234).to_bytes(4, "little")
    value = mcap_rs.decode_cdr(reg, 1, "Msg", data)
    assert value["value"] == 1234
