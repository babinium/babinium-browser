// SPDX-License-Identifier: GPL-3.0-or-later
//! Small C ABI. Each engine is confined to its WebKit web-process main thread.
use adblock::{Engine, FilterSet, lists::ParseOptions, resources::{Resource, PermissionMask}, request::Request};
use std::{cell::RefCell, collections::{HashSet, VecDeque}, ffi::{CStr, CString, c_char}, fs, path::Path};

// An engine is confined to its WebKit web-process main thread. Keep only the
// small per-URL state needed for generic selectors, not the larger generated
// stylesheet/scriptlets. Reloading or freeing an engine clears these entries.
const SITE_CACHE_LIMIT: usize = 8;
struct SiteCache {
    engine: usize,
    url: String,
    generichide: bool,
    exceptions: HashSet<String>,
}
thread_local! {
    static SITES: RefCell<VecDeque<SiteCache>> = const { RefCell::new(VecDeque::new()) };
}
fn clear_sites() { SITES.with(|sites| sites.borrow_mut().clear()); }
fn remember_site(engine: usize, url: &str, generichide: bool, exceptions: HashSet<String>) {
    SITES.with(|sites| {
        let mut sites=sites.borrow_mut();
        if let Some(i)=sites.iter().position(|s| s.engine==engine && s.url==url) { sites.remove(i); }
        sites.push_front(SiteCache { engine, url:url.to_owned(), generichide, exceptions });
        if sites.len()>SITE_CACHE_LIMIT { sites.pop_back(); }
    });
}
fn generic_selectors(engine: &Engine, url: &str, classes: Vec<String>, ids: Vec<String>) -> Vec<String> {
    let key=engine as *const Engine as usize;
    SITES.with(|sites| {
        let mut sites=sites.borrow_mut();
        if let Some(i)=sites.iter().position(|s| s.engine==key && s.url==url) {
            let site=sites.remove(i).unwrap();sites.push_front(site);
        } else {
            let r=engine.url_cosmetic_resources(url);
            sites.push_front(SiteCache { engine:key,url:url.to_owned(),generichide:r.generichide,exceptions:r.exceptions });
            if sites.len()>SITE_CACHE_LIMIT { sites.pop_back(); }
        }
        let site=sites.front().unwrap();
        if site.generichide { Vec::new() } else { engine.hidden_class_id_selectors(classes,ids,&site.exceptions) }
    })
}

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
        Ok(e) => { clear_sites();Box::into_raw(Box::new(e)) },
        Err(e) => { eprintln!("babinium: filter engine: {e}"); std::ptr::null_mut() }
    }
}
#[unsafe(no_mangle)]
pub unsafe extern "C" fn bb_engine_free(p: *mut Engine) { if !p.is_null() { clear_sites();drop(unsafe { Box::from_raw(p) }); } }
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
    let e=unsafe { &*p };let url=unsafe { string(url) };let r=e.url_cosmetic_resources(url);
    let json=serde_json::to_string(&r).unwrap();
    remember_site(p as usize,url,r.generichide,r.exceptions);
    returned(json)
}
#[unsafe(no_mangle)]
pub unsafe extern "C" fn bb_generic(p: *const Engine, url: *const c_char, classes: *const c_char, ids: *const c_char) -> *mut c_char {
    if p.is_null() { return returned("[]".into()); }
    let c: Vec<String> = serde_json::from_str(unsafe { string(classes) }).unwrap_or_default();
    let i: Vec<String> = serde_json::from_str(unsafe { string(ids) }).unwrap_or_default();
    if c.len() + i.len() > 4096 { return returned("[]".into()); }
    returned(serde_json::to_string(&generic_selectors(unsafe { &*p },unsafe { string(url) },c,i)).unwrap())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn engine() -> Engine {
        let mut s = FilterSet::new(false);
        s.add_filter_list(["||ads.example^", "@@||ads.example/allowed.js", "example.org##.sponsor", "##.generic-ad", "example.org#@#.generic-ad"].join("\n"), Default::default());
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
    #[test] fn procedural_operator_is_not_treated_as_css() {
        let mut s=FilterSet::new(false);
        s.add_filter_list("example.org###ad:has-text(Sponsored):remove()".into(),Default::default());
        let e=Engine::new_with_filter_set(s);let r=e.url_cosmetic_resources("https://example.org/");
        assert!(r.procedural_actions.iter().any(|v|v.contains("\"type\":\"has-text\"")));
    }
    #[test] fn cached_generic_respects_exceptions_and_engine_lifetime() {
        clear_sites();
        let e=engine();
        let classes=vec!["generic-ad".to_string()];
        for _ in 0..3 {
            assert!(generic_selectors(&e,"https://example.org/",classes.clone(),vec![]).is_empty());
            assert_eq!(generic_selectors(&e,"https://other.test/",classes.clone(),vec![]),vec![".generic-ad"]);
        }
        let mut set=FilterSet::new(false);set.add_filter_list("##.generic-ad".into(),Default::default());
        let other=Engine::new_with_filter_set(set);
        assert_eq!(generic_selectors(&other,"https://example.org/",classes.clone(),vec![]),vec![".generic-ad"]);
        for n in 0..12 { let url=format!("https://{n}.test/");generic_selectors(&other,&url,classes.clone(),vec![]); }
        SITES.with(|sites| assert!(sites.borrow().len()<=SITE_CACHE_LIMIT));
        let owned=Box::into_raw(Box::new(engine()));
        generic_selectors(unsafe { &*owned },"https://example.org/",classes,vec![]);
        unsafe { bb_engine_free(owned) };
        SITES.with(|sites| assert!(sites.borrow().is_empty()));
    }
    #[test] fn cached_generic_obeys_generichide_per_site() {
        clear_sites();
        let mut set=FilterSet::new(false);
        set.add_filter_list("##.generic-ad\n@@||example.org^$generichide".into(),Default::default());
        let e=Engine::new_with_filter_set(set);let classes=vec!["generic-ad".to_string()];
        for _ in 0..3 {
            assert!(generic_selectors(&e,"https://example.org/",classes.clone(),vec![]).is_empty());
            assert_eq!(generic_selectors(&e,"https://other.test/",classes.clone(),vec![]),vec![".generic-ad"]);
        }
    }
}
