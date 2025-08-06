use std::{collections::HashMap, env, fs, path::PathBuf, process::Command};

use mcap::MessageStream;
use mcap_rs::{load_idl, CdrReader};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mcap_path = env::args().nth(1).expect("usage: mcap-rs <mcap-file>");

    // Extract type definitions using the bundled Node.js CLI.
    let mut types_path = env::temp_dir();
    types_path.push(format!("mcap_types_{}.json", std::process::id()));
    let js_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../mcap_ros2idl_support/dist/index.js");
    let status = Command::new("node")
        .arg(js_path)
        .arg(&mcap_path)
        .arg("-o")
        .arg(&types_path)
        .status()?;
    if !status.success() {
        return Err("failed to run Node CLI".into());
    }

    let schemas = load_idl(types_path.to_str().unwrap())?;
    fs::remove_file(&types_path).ok();

    let mut readers = HashMap::new();
    for (id, info) in &schemas {
        readers.insert(*id as u16, CdrReader::new(info));
    }

    let data = fs::read(&mcap_path)?;
    for msg in MessageStream::new(&data)? {
        let msg = msg?;
        if let Some(schema) = &msg.channel.schema {
            let schema_id = schema.id;
            if let Some(reader) = readers.get(&schema_id) {
                match reader.read(&schema.name, &msg.data) {
                    Ok(json) => {
                        println!("Topic: {}, Schema ID: {}", msg.channel.topic, schema_id);
                        println!("{}", serde_json::to_string_pretty(&json)?);
                    }
                    Err(err) => {
                        eprintln!("failed to decode schema {}: {}", schema_id, err);
                    }
                }
            } else {
                eprintln!("schema {} not found in type definitions", schema_id);
            }
        } else {
            eprintln!("channel {} missing schema", msg.channel.id);
        }
    }

    Ok(())
}
