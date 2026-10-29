// SPDX-License-Identifier: GPL-3.0-or-later
//! Small C ABI. Each engine is confined to its WebKit web-process main thread.
use adblock::{Engine, FilterSet, lists::ParseOptions, resources::{Resource, PermissionMask}, request::Request};
use std::{ffi::{CStr, CString, c_char}, fs, path::Path};

pub fn load(index: &Path, resources: &Path) -> Result<Engine, String> {
    let mut engine = Engine::default();
    engine.deserialize(&fs::read(index).map_err(|e| e.to_string())?).map_err(|e| format!("{e:?}"))?;
    let res: Vec<Resource> = serde_json::from_slice(&fs::read(resources).map_err(|e| e.to_string())?).map_err(|e| e.to_string())?;
    engine.use_resources(res);
    Ok(engine)
}

pub fn compile(lists: &Path, output: &Path) -> Result<(), String> {
    let mut set = FilterSet::new(false);
    let mut paths: Vec<_> = fs::read_dir(lists).map_err(|e| e.to_string())?.filter_map(Result::ok)
        .map(|e| e.path()).filter(|p| p.extension().is_some_and(|e| e == "txt")).collect();
    paths.sort();
    if paths.is_empty() { return Err("No filter lists".into()); }
    for path in paths {
        let text = fs::read_to_string(&path).map_err(|e| e.to_string())?;
        // Only the fixed uAssets sources are trusted for privileged scriptlets.
        let trusted = path.file_name().unwrap().to_string_lossy().starts_with("ubo-");
        set.add_filter_list(text, ParseOptions { permissions: PermissionMask::from_bits(if trusted { 1 } else { 0 }), ..Default::default() });
    }
    let data = Engine::new_with_filter_set(set).serialize();
    fs::write(output, data).map_err(|e| e.to_string())
}

unsafe fn string<'a>(p: *const c_char) -> &'a str {
    if p.is_null() { "" } else { unsafe { CStr::from_ptr(p) }.to_str().unwrap_or("") }
}
fn returned(s: String) -> *mut c_char { CString::new(s).map_or(std::ptr::null_mut(), CString::into_raw) }

#[unsafe(no_mangle)]
pub unsafe extern "C" fn bb_engine_load(index: *const c_char, resources: *const c_char) -> *mut Engine {
    match load(Path::new(unsafe { string(index) }), Path::new(unsafe { string(resources) })) {
        Ok(e) => Box::into_raw(Box::new(e)),
        Err(e) => { eprintln!("babinium: filter engine: {e}"); std::ptr::null_mut() }
    }
}
#[unsafe(no_mangle)]
pub unsafe extern "C" fn bb_engine_free(p: *mut Engine) { if !p.is_null() { drop(unsafe { Box::from_raw(p) }); } }
#[unsafe(no_mangle)]
pub unsafe extern "C" fn bb_string_free(p: *mut c_char) { if !p.is_null() { drop(unsafe { CString::from_raw(p) }); } }

/// 0=allow, 1=block, 2=local replacement, 3=removeparam. Caller owns *redirect.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn bb_check(p: *const Engine, url: *const c_char, source: *const c_char,
    kind: *const c_char, method: *const c_char, redirect: *mut *mut c_char) -> i32 {
    if !redirect.is_null() { unsafe { *redirect = std::ptr::null_mut() }; }
    if p.is_null() { return 0; }
    let Ok(req) = Request::new(unsafe { string(url) }, unsafe { string(source) }, unsafe { string(kind) }, unsafe { string(method) }) else { return 0; };
    let result = unsafe { &*p }.check_network_request(&req);
    if result.should_block() {
        if let Some(data) = result.redirect {
            if !redirect.is_null() { unsafe { *redirect = returned(data) }; return 2; }
        }
        return 1;
    }
    if let Some(url)=result.rewritten_url {
        if !redirect.is_null() { unsafe { *redirect=returned(url) }; return 3; }
    }
    0
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn bb_cosmetics(p: *const Engine, url: *const c_char) -> *mut c_char {
    if p.is_null() { return returned("{}".into()); }
    returned(serde_json::to_string(&unsafe { &*p }.url_cosmetic_resources(unsafe { string(url) })).unwrap())
}
#[unsafe(no_mangle)]
pub unsafe extern "C" fn bb_generic(p: *const Engine, url: *const c_char, classes: *const c_char, ids: *const c_char) -> *mut c_char {
    if p.is_null() { return returned("[]".into()); }
    let e = unsafe { &*p };
    let r = e.url_cosmetic_resources(unsafe { string(url) });
    if r.generichide { return returned("[]".into()); }
    let c: Vec<String> = serde_json::from_str(unsafe { string(classes) }).unwrap_or_default();
    let i: Vec<String> = serde_json::from_str(unsafe { string(ids) }).unwrap_or_default();
    if c.len() + i.len() > 4096 { return returned("[]".into()); }
    returned(serde_json::to_string(&e.hidden_class_id_selectors(c, i, &r.exceptions)).unwrap())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;
    fn engine() -> Engine {
        let mut s = FilterSet::new(false);
        s.add_filters(["||ads.example^", "@@||ads.example/allowed.js", "example.org##.sponsor", "##.generic-ad", "example.org#@#.generic-ad"], Default::default());
        Engine::new_with_filter_set(s)
    }
    #[test] fn network_and_exception() {
        let e = engine();
        assert!(e.check_network_request(&Request::new("https://ads.example/a.js", "https://example.org/", "script", "GET").unwrap()).should_block());
        assert!(!e.check_network_request(&Request::new("https://ads.example/allowed.js", "https://example.org/", "script", "GET").unwrap()).should_block());
    }
    #[test] fn cosmetics_and_exception() {
        let e = engine(); let r = e.url_cosmetic_resources("https://example.org/");
        assert!(r.hide_selectors.contains(".sponsor"));
        assert!(e.hidden_class_id_selectors(["generic-ad"], Vec::<String>::new(), &r.exceptions).is_empty());
        assert!(!e.hidden_class_id_selectors(["generic-ad"], Vec::<String>::new(), &HashSet::new()).is_empty());
    }
    #[test] fn serialization_roundtrip() {
        let e=engine(); let mut copy=Engine::default(); copy.deserialize(&e.serialize()).unwrap();
        assert!(copy.url_cosmetic_resources("https://example.org/").hide_selectors.contains(".sponsor"));
    }
}
