import importlib
import pathlib
import subprocess
import sys
import tempfile

try:  # pragma: no cover - installation step
    import mcap_rs  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - executed when extension missing
    manifest = pathlib.Path(__file__).parents[1] / "rust" / "mcap-rs" / "Cargo.toml"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "maturin",
            "build",
            "--manifest-path",
            str(manifest),
            "--interpreter",
            sys.executable,
        ],
        check=True,
    )
    wheel_dir = manifest.parent / "target" / "wheels"
    wheel = next(wheel_dir.glob("mcap_rs-*.whl"))
    subprocess.run([sys.executable, "-m", "pip", "install", str(wheel)], check=True)
    mcap_rs = importlib.import_module("mcap_rs")


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
