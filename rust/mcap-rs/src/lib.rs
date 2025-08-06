use mcap::{McapResult, MessageStream};
use serde::Deserialize;
use std::{collections::HashMap, fs::File};

pub mod cdr;
pub use cdr::CdrReader;

#[derive(Debug, Clone, Deserialize)]
pub struct Field {
    pub name: String,
    #[serde(rename = "type")]
    pub type_name: String,
    #[serde(rename = "isComplex")]
    pub is_complex: bool,
    #[serde(default, rename = "isArray")]
    pub is_array: bool,
    #[serde(rename = "arrayUpperBound")]
    pub array_upper_bound: Option<u32>,
    #[serde(rename = "defaultValue")]
    pub default_value: Option<serde_json::Value>,
    #[serde(rename = "upperBound")]
    pub upper_bound: Option<u32>,
    #[serde(rename = "enumType")]
    pub enum_type: Option<String>,
    #[serde(rename = "isConstant")]
    pub is_constant: Option<bool>,
    pub value: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Deserialize)]
struct TypeDef {
    name: String,
    definitions: Vec<Field>,
}

#[derive(Debug, Clone)]
pub struct MessageType {
    pub name: String,
    pub fields: Vec<Field>,
}

#[derive(Debug)]
pub struct SchemaInfo {
    pub type_map: HashMap<String, MessageType>,
    pub enum_map: HashMap<String, HashMap<i64, String>>, // enum type -> value -> name
}

/// Load type and enum definitions from a JSON file produced by `@foxglove/ros2idl-parser`.
pub fn load_idl(path: &str) -> Result<HashMap<u32, SchemaInfo>, Box<dyn std::error::Error>> {
    let file = File::open(path)?;
    let raw: HashMap<String, Vec<TypeDef>> = serde_json::from_reader(file)?;
    let mut id_to_schema = HashMap::new();
    for (id_str, schema_defs) in raw {
        let mut type_map = HashMap::new();
        let mut enum_map: HashMap<String, HashMap<i64, String>> = HashMap::new();
        for type_def in schema_defs {
            let message_type = MessageType {
                name: type_def.name.clone(),
                fields: type_def.definitions.clone(),
            };
            let enum_candidates: Vec<&Field> = message_type
                .fields
                .iter()
                .filter(|f| f.is_constant.unwrap_or(false))
                .collect();
            if !enum_candidates.is_empty() {
                let mut lookup = HashMap::new();
                for field in enum_candidates {
                    if let (Some(serde_json::Value::Number(n)), name) = (&field.value, &field.name)
                    {
                        if let Some(v) = n.as_i64() {
                            lookup.insert(v, name.clone());
                        }
                    }
                }
                enum_map.insert(message_type.name.clone(), lookup);
            }
            type_map.insert(message_type.name.clone(), message_type);
        }
        id_to_schema.insert(id_str.parse::<u32>()?, SchemaInfo { type_map, enum_map });
    }
    Ok(id_to_schema)
}

/// Count the number of messages in the given MCAP byte slice.
///
/// This function demonstrates how to iterate over messages using the
/// [`mcap`] crate's [`MessageStream`]. It returns the total number of
/// messages or an error if parsing fails.
pub fn count_messages(buf: &[u8]) -> McapResult<usize> {
    let mut count = 0;
    for msg in MessageStream::new(buf)? {
        msg?; // propagate parse errors
        count += 1;
    }
    Ok(count)
}

#[cfg(test)]
mod tests {
    use super::*;
    use mcap::{WriteOptions, records::MessageHeader};
    use std::{collections::BTreeMap, io::Cursor};

    // Build a simple MCAP containing a single message for testing.
    fn build_sample_mcap() -> Vec<u8> {
        let mut data = Vec::new();
        {
            let mut cursor = Cursor::new(&mut data);
            let mut writer = WriteOptions::new()
                .create(&mut cursor)
                .expect("create writer");
            let channel_id = writer
                .add_channel(0, "example", "application/octet-stream", &BTreeMap::new())
                .expect("add channel");
            let header = MessageHeader {
                channel_id,
                sequence: 1,
                log_time: 0,
                publish_time: 0,
            };
            writer
                .write_to_known_channel(&header, b"abc")
                .expect("write message");
            writer.finish().expect("finish writer");
        }
        data
    }

    #[test]
    fn counts_single_message() {
        let mcap = build_sample_mcap();
        let count = count_messages(&mcap).expect("count messages");
        assert_eq!(count, 1);
    }

    #[test]
    fn parses_idl_json() {
        use std::fs;
        let data = r#"{"1":[{"name":"Foo","definitions":[{"name":"bar","type":"string","isComplex":false},{"name":"BAZ","type":"int32","isComplex":false,"isConstant":true,"value":0}]}]}"#;
        let path = std::env::temp_dir().join("types.json");
        fs::write(&path, data).expect("write temp json");
        let schemas = load_idl(path.to_str().unwrap()).expect("load idl");
        fs::remove_file(&path).ok();
        assert!(schemas.contains_key(&1));
        let info = schemas.get(&1).unwrap();
        assert!(info.type_map.contains_key("Foo"));
        assert_eq!(info.enum_map["Foo"].get(&0), Some(&"BAZ".to_string()));
    }
}
