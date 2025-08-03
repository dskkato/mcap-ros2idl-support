# mcap-schema-cli
A command-line tool to read rosbag2 schemas and parse the CDR data format.

## Installation

This tool required node.js version 20 or higher, and python version 3.10 or higher.

```bash
npm install
npm run build
npm link
```

```bash
pip install -r requirements.txt
```

## Usage

```bash
mcap-schema-cli sample.mcap -o schemas.json
python3 -m mcap_schema_cli --type-definitions schemas.json --mcap-file sample.mcap
```
