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
  "tf2_msgs/TFMessage": [
    {
      "name": "TFMessage",
      "definitions": [
        {
          "name": "transforms",
          "type": "geometry_msgs/TransformStamped",
          "isArray": true,
          "isComplex": true
        }
      ]
    }
  ]
}
```
