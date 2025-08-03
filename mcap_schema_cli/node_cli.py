import subprocess
import sys
from pathlib import Path


def main() -> None:
    js_path = Path(__file__).with_name("dist") / "index.js"
    cmd = ["node", str(js_path), *sys.argv[1:]]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
