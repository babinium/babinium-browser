// SPDX-License-Identifier: GPL-3.0-or-later
// Verify the one-time default, manual override and safe unsupported-page path.
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const code=fs.readFileSync('data/youtube-ambient.js','utf8');

function fixture({active=true,label='Ambient mode',saved=false,host='www.youtube.com',ad=false,ready=true}={}) {
    const listeners=new Map(),intervals=new Map(),timers=[],storage=new Map(),result={active,ad,ready,menuOpen:false,clicks:0};
    if(saved)storage.set('babinium-ambient-default-v1','1');
    let id=0,visibility='',priority='';
    const video={tagName:'VIDEO',paused:false,currentTime:2};
    const panel={hasAttribute:()=>result.active};
    const item={getAttribute:()=>result.active?'true':'false',querySelector:()=>({textContent:label}),click:()=>{result.active=false;result.clicks++;}};
    const menu={get offsetWidth(){return result.menuOpen&&result.ready?300:0;},get offsetHeight(){return result.menuOpen&&result.ready?200:0;},
        querySelectorAll:()=>[item],style:{getPropertyValue:()=>visibility,getPropertyPriority:()=>priority,
            setProperty:(key,value,p)=>{visibility=value;priority=p;},removeProperty:()=>{visibility='';priority='';}}};
    const gear={click:()=>{result.menuOpen=!result.menuOpen;}};
    const document={readyState:'complete',addEventListener:(key,fn)=>listeners.set(key,fn),removeEventListener:key=>listeners.delete(key),
        querySelector:s=>s==='video'?video:s==='ytd-watch-flexy,ytd-watch-grid'?panel:s==='.ytp-settings-button'?gear:s==='.ytp-settings-menu'?menu:s==='.html5-video-player.ad-showing,.html5-video-player.ad-interrupting'&&result.ad?{}:null};
    const context={document,location:{hostname:host},localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
        setInterval:fn=>{intervals.set(++id,fn);return id;},clearInterval:i=>intervals.delete(i),setTimeout:fn=>timers.push(fn),
        getComputedStyle:()=>({visibility:'visible',display:result.menuOpen?'block':'none'})};
    context.window=context;context.top=context;vm.createContext(context);vm.runInContext(code,context);
    result.storage=storage;result.listeners=listeners;result.intervals=intervals;
    result.tick=()=>{for(const f of [...intervals.values()])f();};
    result.flush=()=>{while(timers.length)timers.shift()();};
    result.step=()=>{result.tick();result.tick();result.flush();};
    result.manualGearClick=()=>gear.click();
    result.visibility=()=>visibility;return result;
}

test('turns ambient mode off once using YouTube setting and restores the menu',()=>{
    const f=fixture();f.step();assert.equal(f.active,false);assert.equal(f.clicks,1);assert.equal(f.menuOpen,false);
    assert.equal(f.visibility(),'');assert.equal(f.storage.get('babinium-ambient-default-v1'),'1');assert.equal(f.intervals.size,0);
});
test('recognizes Spanish and keeps an already disabled setting',()=>{
    const f=fixture({label:'Modo ambiente'});f.step();assert.equal(f.active,false);assert.equal(f.clicks,1);
    const h=fixture({label:'Iluminación cinemática'});h.step();assert.equal(h.active,false);assert.equal(h.clicks,1);
    const g=fixture({active:false});g.step();assert.equal(g.clicks,0);assert.equal(g.storage.get('babinium-ambient-default-v1'),'1');
});
test('respects an existing preference or a user opening the settings',()=>{
    const f=fixture({saved:true});f.step();assert.equal(f.active,true);assert.equal(f.clicks,0);
    const g=fixture();g.listeners.get('pointerdown')({isTrusted:true,target:{closest:()=>true}});g.step();
    assert.equal(g.active,true);assert.equal(g.clicks,0);assert.equal(g.storage.get('babinium-ambient-default-v1'),'1');
});
test('leaves the settings open when the user clicks during the automatic adjustment',()=>{
    const f=fixture();f.tick();assert.equal(f.menuOpen,true);
    f.listeners.get('pointerdown')({isTrusted:true,target:{closest:()=>true}});
    assert.equal(f.menuOpen,false);assert.equal(f.visibility(),'');
    f.manualGearClick();f.flush();
    assert.equal(f.menuOpen,true);assert.equal(f.active,true);assert.equal(f.clicks,0);
    assert.equal(f.storage.get('babinium-ambient-default-v1'),'1');
});
test('leaves an unrecognized menu untouched and does not leave it hidden',()=>{
    const f=fixture({label:'Unrecognized option'});for(let i=0;i<21;i++)f.tick();f.flush();assert.equal(f.active,true);assert.equal(f.clicks,0);
    assert.equal(f.menuOpen,false);assert.equal(f.visibility(),'');assert.equal(f.storage.has('babinium-ambient-default-v1'),false);
});
test('waits for an asynchronously opening YouTube settings menu',()=>{
    const f=fixture({ready:false});f.step();assert.equal(f.clicks,0);assert.equal(f.menuOpen,true);
    f.ready=true;f.step();assert.equal(f.clicks,1);assert.equal(f.active,false);assert.equal(f.menuOpen,false);
});
test('cancels a menu that never becomes ready',()=>{
    const f=fixture({ready:false});for(let i=0;i<21;i++)f.tick();f.flush();
    assert.equal(f.menuOpen,false);assert.equal(f.visibility(),'');assert.equal(f.clicks,0);assert.equal(f.intervals.size,0);
});
test('does nothing on unrelated websites',()=>{
    const f=fixture({host:'example.org'});f.step();assert.equal(f.clicks,0);assert.equal(f.intervals.size,0);
});
test('waits until a preroll ends before deciding the default',()=>{
    const f=fixture({ad:true});f.step();assert.equal(f.clicks,0);assert.equal(f.storage.has('babinium-ambient-default-v1'),false);
    f.ad=false;f.step();assert.equal(f.clicks,1);assert.equal(f.active,false);
});
