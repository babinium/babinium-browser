// SPDX-License-Identifier: GPL-3.0-or-later
use std::{env, path::Path, fs};
fn main() {
    let a: Vec<String> = env::args().collect();
    let result = match a.get(1).map(String::as_str) {
        Some("compile") if a.len()==4 => babinium_blocker::compile(Path::new(&a[2]), Path::new(&a[3])),
        Some("validate") if a.len()==4 => babinium_blocker::load(Path::new(&a[2]),Path::new(&a[3])).map(|_| ()),
        Some("resources") if a.len()==5 => {
            let r=adblock::resources::resource_assembler::assemble_web_accessible_resources(Path::new(&a[2]),Path::new(&a[3]));
            fs::write(&a[4],serde_json::to_vec(&r).unwrap()).map_err(|e| e.to_string())
        },
        Some("cosmetics") if a.len()==5 => babinium_blocker::load(Path::new(&a[2]),Path::new(&a[3])).map(|e|println!("{}",serde_json::to_string(&e.url_cosmetic_resources(&a[4])).unwrap())),
        _ => Err("Usage: babinium-filter compile LIST_DIR INDEX | validate INDEX RESOURCES | resources WAR_DIR MAPPING OUT | cosmetics INDEX RESOURCES URL".into())
    };
    if let Err(e)=result { eprintln!("{e}"); std::process::exit(1); }
}
