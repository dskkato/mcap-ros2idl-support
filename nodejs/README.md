# Node.js Development

Requires Node.js ≥20.

## Setup

From this directory:

```bash
npm install
```

## Linting and formatting

```bash
npm run lint
npm run format
```

## Tests

```bash
npm test
```

## Build

To bundle the CLI for use by the Python package:

```bash
npm run deploy
```

## Example

Run the CLI against an MCAP file and write schema definitions:

> **Note:** The example below assumes you have an MCAP file named `sample.mcap` in your working directory. You can use your own MCAP file, or download a sample from [the MCAP sample data repository](https://github.com/foxglove/mcap/tree/main/testdata) or generate one using your data.
```bash
npm run dev -- sample.mcap -o types.json
```

If the file contains `tf` messages, the output `types.json` may include:

```json
{
  "1": [
    {
      "name": "tf2_msgs/msg/TFMessage",
      "definitions": [
        {
          "name": "transforms",
          "type": "geometry_msgs/msg/TransformStamped",
          "isComplex": true,
          "arrayUpperBound": 120,
          "isArray": true
        }
      ]
    },
    {
      "name": "geometry_msgs/msg/TransformStamped",
      "definitions": [
        {
          "name": "header",
          "type": "std_msgs/msg/Header",
          "isComplex": true
        },
        {
          "name": "child_frame_id",
          "type": "string",
          "isComplex": false,
          "upperBound": 255
        },
        {
          "name": "transform",
          "type": "geometry_msgs/msg/Transform",
          "isComplex": true
        }
      ]
    }
  ]
}
```

Here, the key values are the schema IDs, and the corresponding values are arrays of message definitions extracted from the MCAP file.
