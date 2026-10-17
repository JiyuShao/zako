use crate::config::Config;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::os::unix::fs::OpenOptionsExt;
use toml_edit::{DocumentMut, Item, Value};

pub const EXAMPLE: &str = include_str!("../config.example.toml");

pub fn run(args: &[String]) -> Result<(), String> {
    match args
        .iter()
        .map(String::as_str)
        .collect::<Vec<_>>()
        .as_slice()
    {
        ["path"] => println!("{}", Config::path().display()),
        ["show"] => print!(
            "{}",
            toml::to_string_pretty(&Config::load().map_err(|e| e.to_string())?)
                .map_err(|e| e.to_string())?
        ),
        ["init"] => write_config(EXAMPLE, true)?,
        ["set", key, raw] => {
            let path = Config::path();
            let source = match fs::read_to_string(&path) {
                Ok(text) => text,
                Err(e) if e.kind() == std::io::ErrorKind::NotFound => String::new(),
                Err(e) => return Err(e.to_string()),
            };
            let mut doc: DocumentMut = source
                .parse()
                .map_err(|e: toml_edit::TomlError| e.to_string())?;
            let (section, field) = key.split_once('.').ok_or("配置键应为 section.field")?;
            let defaults = toml::Value::try_from(Config::default()).map_err(|e| e.to_string())?;
            let expected = defaults
                .get(section)
                .and_then(|s| s.get(field))
                .ok_or("未知配置键")?;
            let value = if expected.is_str() {
                Value::from(*raw)
            } else {
                let parsed: DocumentMut = format!("value = {raw}")
                    .parse()
                    .map_err(|e: toml_edit::TomlError| e.to_string())?;
                if parsed.len() != 1 {
                    return Err("只允许一个配置值".into());
                }
                parsed["value"].as_value().ok_or("配置值无效")?.clone()
            };
            if doc.get(section).is_none() {
                doc[section] = Item::Table(toml_edit::Table::new());
            }
            let table = doc[section].as_table_like_mut().ok_or("配置节必须为表")?;
            // Preserve inline comments on an existing value as well as all other keys.
            let mut value = value;
            if let Some(old) = table.get(field).and_then(Item::as_value) {
                *value.decor_mut() = old.decor().clone();
            }
            table.insert(field, Item::Value(value));
            write_config(&doc.to_string(), false)?;
        }
        _ => {
            return Err("用法：zako config path | show | init | set <section.field> <value>".into())
        }
    }
    Ok(())
}

fn write_config(source: &str, create_only: bool) -> Result<(), String> {
    let config: Config = toml::from_str(source).map_err(|e| e.to_string())?;
    config.validate().map_err(|e| e.to_string())?;
    let path = Config::path();
    let parent = path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(std::path::Path::new("."));
    fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    if create_only {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o600)
            .open(&path)
            .map_err(|e| format!("无法创建 {}（不会覆盖已有配置）: {e}", path.display()))?;
        file.write_all(source.as_bytes())
            .map_err(|e| e.to_string())?;
        file.sync_all().map_err(|e| e.to_string())?;
    } else {
        if fs::symlink_metadata(&path).is_ok_and(|m| m.file_type().is_symlink()) {
            return Err("配置是符号链接，请直接编辑链接目标".into());
        }
        let stamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|e| e.to_string())?
            .as_nanos();
        let temporary = parent.join(format!(".zako-{}-{stamp}.tmp", std::process::id()));
        let result = (|| {
            let mut file = OpenOptions::new()
                .write(true)
                .create_new(true)
                .mode(0o600)
                .open(&temporary)?;
            if let Ok(metadata) = fs::metadata(&path) {
                file.set_permissions(metadata.permissions())?;
            }
            file.write_all(source.as_bytes())?;
            file.sync_all()?;
            fs::rename(&temporary, &path)
        })();
        if result.is_err() {
            let _ = fs::remove_file(&temporary);
        }
        result.map_err(|e| e.to_string())?;
    }
    println!("已保存 {}；新开终端后生效。", path.display());
    Ok(())
}
