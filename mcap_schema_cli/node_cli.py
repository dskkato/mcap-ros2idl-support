import subprocess
import sys
from pathlib import Path


def main() -> None:
    js_path = Path(__file__).with_name("dist") / "index.js"
    cmd = ["node", str(js_path), *sys.argv[1:]]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(
            f"Error: Node.js CLI execution failed with exit code {e.returncode}.",
            file=sys.stderr,
        )
        if e.output:
            print("Output:", e.output, file=sys.stderr)
        if e.stderr:
            print("Error output:", e.stderr, file=sys.stderr)
        sys.exit(e.returncode if e.returncode is not None else 1)


if __name__ == "__main__":
    main()
