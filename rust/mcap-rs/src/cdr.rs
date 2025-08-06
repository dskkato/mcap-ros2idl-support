use crate::{MessageType, SchemaInfo};
use byteorder::{BigEndian, LittleEndian, ReadBytesExt};
use serde_json::{Map, Number, Value};
use std::io::{Cursor, Read, Seek, SeekFrom};

#[cfg(test)]
use crate::Field;

pub struct CdrReader<'a> {
    schema: &'a SchemaInfo,
}

impl<'a> CdrReader<'a> {
    pub fn new(schema: &'a SchemaInfo) -> Self {
        Self { schema }
    }

    pub fn read(
        &self,
        type_name: &str,
        data: &[u8],
    ) -> Result<Value, Box<dyn std::error::Error>> {
        let mut cursor = Cursor::new(data);
        let mut header = [0u8; 4];
        cursor.read_exact(&mut header)?;
        if header.len() < 4 {
            return Err("Incomplete CDR header".into());
        }
        let little = (header[1] & 0x01) != 0;
        let msg_type = self
            .schema
            .type_map
            .get(type_name)
            .ok_or_else(|| format!("Unknown type: {type_name}"))?;
        let obj = self.read_message(&mut cursor, msg_type, little)?;
        Ok(Value::Object(obj))
    }

    fn read_message(
        &self,
        cursor: &mut Cursor<&[u8]>,
        msg_type: &MessageType,
        little: bool,
    ) -> Result<Map<String, Value>, Box<dyn std::error::Error>> {
        let mut result = Map::new();
        for field in &msg_type.fields {
            let value = if field.is_array {
                self.read_array(cursor, field.type_name.as_str(), field.enum_type.as_ref(), field.is_complex, little)?
            } else if field.is_complex {
                let nested = self
                    .schema
                    .type_map
                    .get(&field.type_name)
                    .ok_or_else(|| format!("Unknown type: {}", field.type_name))?;
                Value::Object(self.read_message(cursor, nested, little)?)
            } else {
                self.read_primitive(cursor, field.type_name.as_str(), field.enum_type.as_ref(), little, true)?
            };
            result.insert(field.name.clone(), value);
        }
        Ok(result)
    }

    fn read_array(
        &self,
        cursor: &mut Cursor<&[u8]>,
        type_name: &str,
        enum_type: Option<&String>,
        is_complex: bool,
        little: bool,
    ) -> Result<Value, Box<dyn std::error::Error>> {
        let length = self.read_u32(cursor, little)? as usize;
        if is_complex {
            let msg_type = self
                .schema
                .type_map
                .get(type_name)
                .ok_or_else(|| format!("Unknown type: {type_name}"))?;
            let mut vec = Vec::with_capacity(length);
            for _ in 0..length {
                vec.push(Value::Object(self.read_message(cursor, msg_type, little)?));
            }
            return Ok(Value::Array(vec));
        }
        let align_size = alignment(type_name);
        if align_size > 1 {
            self.align(cursor, align_size)?;
        }
        let mut vec = Vec::with_capacity(length);
        for _ in 0..length {
            vec.push(self.read_primitive(cursor, type_name, enum_type, little, false)?);
        }
        Ok(Value::Array(vec))
    }

    fn read_primitive(
        &self,
        cursor: &mut Cursor<&[u8]>,
        type_name: &str,
        enum_type: Option<&String>,
        little: bool,
        do_align: bool,
    ) -> Result<Value, Box<dyn std::error::Error>> {
        if do_align {
            let align_size = alignment(type_name);
            if align_size > 1 {
                self.align(cursor, align_size)?;
            }
        }
        let mut num_val: Option<i64> = None;
        let value = match type_name {
            "uint8" => {
                let v = cursor.read_u8()?;
                num_val = Some(v as i64);
                Value::Number(Number::from(v))
            }
            "int8" => {
                let v = cursor.read_i8()?;
                num_val = Some(v as i64);
                Value::Number(Number::from(v))
            }
            "bool" => {
                let v = cursor.read_u8()? != 0;
                num_val = Some(if v { 1 } else { 0 });
                Value::Bool(v)
            }
            "uint16" => {
                let v = if little {
                    cursor.read_u16::<LittleEndian>()?
                } else {
                    cursor.read_u16::<BigEndian>()?
                };
                num_val = Some(v as i64);
                Value::Number(Number::from(v))
            }
            "int16" => {
                let v = if little {
                    cursor.read_i16::<LittleEndian>()?
                } else {
                    cursor.read_i16::<BigEndian>()?
                };
                num_val = Some(v as i64);
                Value::Number(Number::from(v))
            }
            "uint32" => {
                let v = self.read_u32(cursor, little)?;
                num_val = Some(v as i64);
                Value::Number(Number::from(v))
            }
            "int32" => {
                let v = if little {
                    cursor.read_i32::<LittleEndian>()?
                } else {
                    cursor.read_i32::<BigEndian>()?
                };
                num_val = Some(v as i64);
                Value::Number(Number::from(v))
            }
            "uint64" => {
                let v = if little {
                    cursor.read_u64::<LittleEndian>()?
                } else {
                    cursor.read_u64::<BigEndian>()?
                };
                num_val = Some(v as i64);
                Value::Number(Number::from(v))
            }
            "int64" => {
                let v = if little {
                    cursor.read_i64::<LittleEndian>()?
                } else {
                    cursor.read_i64::<BigEndian>()?
                };
                num_val = Some(v);
                Value::Number(Number::from(v))
            }
            "float32" => {
                let v = if little {
                    cursor.read_f32::<LittleEndian>()?
                } else {
                    cursor.read_f32::<BigEndian>()?
                };
                Value::Number(Number::from_f64(v as f64).unwrap())
            }
            "float64" => {
                let v = if little {
                    cursor.read_f64::<LittleEndian>()?
                } else {
                    cursor.read_f64::<BigEndian>()?
                };
                Value::Number(Number::from_f64(v).unwrap())
            }
            "string" => {
                let len = self.read_u32(cursor, little)? as usize;
                let mut bytes = vec![0u8; len];
                cursor.read_exact(&mut bytes)?;
                let s = String::from_utf8(bytes[..len - 1].to_vec())?;
                Value::String(s)
            }
            _ => return Err(format!("Unknown primitive type: {type_name}").into()),
        };

        if let Some(enum_name) = enum_type {
            let num = num_val.ok_or_else(|| "Enum type on non-numeric field".to_string())?;
            let lookup = self
                .schema
                .enum_map
                .get(enum_name)
                .ok_or_else(|| format!("Unknown enum type: {enum_name}"))?;
            if let Some(name) = lookup.get(&num) {
                Ok(Value::String(name.clone()))
            } else {
                Ok(Value::String(format!("Unknown enum value: {num}")))
            }
        } else {
            Ok(value)
        }
    }

    fn read_u32(&self, cursor: &mut Cursor<&[u8]>, little: bool) -> Result<u32, std::io::Error> {
        if little {
            cursor.read_u32::<LittleEndian>()
        } else {
            cursor.read_u32::<BigEndian>()
        }
    }

    fn align(&self, cursor: &mut Cursor<&[u8]>, size: u64) -> Result<(), std::io::Error> {
        let pos = cursor.position().saturating_sub(4);
        let padding = (size - (pos % size)) % size;
        cursor.seek(SeekFrom::Current(padding as i64))?;
        Ok(())
    }
}

fn alignment(type_name: &str) -> u64 {
    match type_name {
        "uint8" | "int8" | "bool" => 1,
        "uint16" | "int16" => 2,
        "uint32" | "int32" | "float32" => 4,
        "uint64" | "int64" | "float64" => 8,
        _ => 1,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::collections::HashMap;

    #[test]
    fn enum_with_uint8() {
        let status = MessageType {
            name: "Status".to_string(),
            fields: vec![
                Field {
                    name: "UNKNOWN".to_string(),
                    type_name: "uint8".to_string(),
                    is_complex: false,
                    is_array: false,
                    array_upper_bound: None,
                    default_value: None,
                    upper_bound: None,
                    enum_type: None,
                    is_constant: Some(true),
                    value: Some(json!(0)),
                },
                Field {
                    name: "OK".to_string(),
                    type_name: "uint8".to_string(),
                    is_complex: false,
                    is_array: false,
                    array_upper_bound: None,
                    default_value: None,
                    upper_bound: None,
                    enum_type: None,
                    is_constant: Some(true),
                    value: Some(json!(2)),
                },
            ],
        };
        let msg = MessageType {
            name: "Msg".to_string(),
            fields: vec![Field {
                name: "status".to_string(),
                type_name: "uint8".to_string(),
                is_complex: false,
                is_array: false,
                array_upper_bound: None,
                default_value: None,
                upper_bound: None,
                enum_type: Some("Status".to_string()),
                is_constant: None,
                value: None,
            }],
        };
        let mut type_map = HashMap::new();
        type_map.insert("Status".to_string(), status);
        type_map.insert("Msg".to_string(), msg);
        let mut enum_map = HashMap::new();
        enum_map.insert("Status".to_string(), HashMap::from([(0, "UNKNOWN".to_string()), (2, "OK".to_string())]));
        let schema = SchemaInfo { type_map, enum_map };
        let reader = CdrReader::new(&schema);
        let data = [0u8, 0, 0, 0, 2u8];
        let value = reader.read("Msg", &data).unwrap();
        assert_eq!(value, json!({"status": "OK"}));
    }

    #[test]
    fn little_endian_uint32() {
        let msg = MessageType {
            name: "Msg".to_string(),
            fields: vec![Field {
                name: "value".to_string(),
                type_name: "uint32".to_string(),
                is_complex: false,
                is_array: false,
                array_upper_bound: None,
                default_value: None,
                upper_bound: None,
                enum_type: None,
                is_constant: None,
                value: None,
            }],
        };
        let mut type_map = HashMap::new();
        type_map.insert("Msg".to_string(), msg);
        let schema = SchemaInfo { type_map, enum_map: HashMap::new() };
        let reader = CdrReader::new(&schema);
        let mut data = vec![0u8, 1, 0, 0];
        data.extend(&0x01020304u32.to_le_bytes());
        let value = reader.read("Msg", &data).unwrap();
        assert_eq!(value, json!({"value": 0x01020304}));
    }

    #[test]
    fn big_endian_uint32() {
        let msg = MessageType {
            name: "Msg".to_string(),
            fields: vec![Field {
                name: "value".to_string(),
                type_name: "uint32".to_string(),
                is_complex: false,
                is_array: false,
                array_upper_bound: None,
                default_value: None,
                upper_bound: None,
                enum_type: None,
                is_constant: None,
                value: None,
            }],
        };
        let mut type_map = HashMap::new();
        type_map.insert("Msg".to_string(), msg);
        let schema = SchemaInfo { type_map, enum_map: HashMap::new() };
        let reader = CdrReader::new(&schema);
        let mut data = vec![0u8, 0, 0, 0];
        data.extend(&0x01020304u32.to_be_bytes());
        let value = reader.read("Msg", &data).unwrap();
        assert_eq!(value, json!({"value": 0x01020304}));
    }
}
