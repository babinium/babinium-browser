// SPDX-License-Identifier: GPL-3.0-or-later
// Verify the built-in controls without loading a browser extension or a network page.
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const code=fs.readFileSync('data/video-speed.js','utf8');

function fixture({host='example.test'}={}){
    const handlers=new Map(),timers=new Map(),media=[];let next=0;
    function element(tag){
        const e={nodeType:1,tagName:tag.toUpperCase(),style:{},children:[],attributes:{},listeners:new Map(),parentNode:null,
            setAttribute(k,v){this.attributes[k]=v;},getAttribute(k){return this.attributes[k]??null;},removeAttribute(k){delete this.attributes[k];},
            addEventListener(k,fn){this.listeners.set(k,fn);},removeEventListener(k){this.listeners.delete(k);},
            append(...children){for(const c of children){c.parentNode=this;this.children.push(c);}},
            remove(){if(this.parentNode)this.parentNode.children=this.parentNode.children.filter(c=>c!==this);this.parentNode=null;}};
        return e;
    }
    const html=element('html'),body=element('body');
    const document={documentElement:html,activeElement:body,fullscreenElement:null,roots:[],
        querySelectorAll(sel){return sel==='video, audio'?media:sel==='*'?this.roots:[];},
        createTreeWalker(root){const nodes=root===this?this.roots:(root.nodes||[]);let i=0;return {nextNode:()=>nodes[i++]||null};},
        createElement:element,addEventListener:(k,fn)=>handlers.set('document:'+k,fn),removeEventListener:k=>handlers.delete('document:'+k)};
    const context={document,location:{hostname:host},innerWidth:1200,innerHeight:800,
        NodeFilter:{SHOW_ELEMENT:1},
        Event:class {constructor(type,opts){this.type=type;Object.assign(this,opts);}},
        addEventListener:(k,fn)=>handlers.set(k,fn),removeEventListener:k=>handlers.delete(k),
        setTimeout:fn=>{timers.set(++next,fn);return next;},clearTimeout:id=>timers.delete(id)};
    context.window=context;vm.createContext(context);vm.runInContext(code,context);
    function video(options={}){
        const v=element(options.audio?'audio':'video');
        Object.assign(v,{isConnected:true,paused:false,ended:false,playbackRate:1,currentTime:30,duration:120,seekable:{length:0},
            getBoundingClientRect:()=>({left:20,top:30,right:660,bottom:390,width:640,height:360})},options);
        return v;
    }
    function key(k,extra={}){
        const e={key:k,isTrusted:true,target:body,ctrlKey:false,altKey:false,metaKey:false,shiftKey:false,isComposing:false,
            prevented:false,stopped:false,composedPath(){return [this.target,body,document];},
            preventDefault(){this.prevented=true;},stopImmediatePropagation(){this.stopped=true;},...extra};
        handlers.get('keydown')(e);return e;
    }
    return {document,html,body,media,handlers,timers,element,video,key,flush(){for(const fn of [...timers.values()])fn();timers.clear();}};
}

test('braces change speed in steps of 0.5 and show a non-interactive indicator',()=>{
    const f=fixture(),v=f.video();f.media.push(v);
    assert.equal(f.key('}',{shiftKey:true}).prevented,true);assert.equal(v.playbackRate,1.5);
    f.key('}',{shiftKey:true});assert.equal(v.playbackRate,2);
    f.key('{',{shiftKey:true});assert.equal(v.playbackRate,1.5);
    f.key('{',{shiftKey:true});f.key('{',{shiftKey:true});assert.equal(v.playbackRate,.5);
    f.key('{',{shiftKey:true});assert.equal(v.playbackRate,.5);
    assert.equal(f.html.children[0].children.length,1);
    assert.equal(f.html.children[0].children[0].textContent,'0.50×');
    assert.match(f.html.children[0].style.cssText,/pointer-events:none/);
});
test('previous built-in controls and unrelated keys are not consumed',()=>{
    const f=fixture(),v=f.video();f.media.push(v);
    for(const key of ['s','d','r','g','z','x','m','j','v','[',']']){
        assert.equal(f.key(key).prevented,false);
    }
    assert.equal(v.playbackRate,1);assert.equal(v.currentTime,30);
    assert.equal(f.html.children.length,0);assert.equal(f.timers.size,0);
});
test('accepts Shift and AltGr while preserving editing and other shortcuts',()=>{
    const f=fixture(),v=f.video();f.media.push(v);
    const input=f.element('input'),editable=f.element('div');editable.isContentEditable=true;
    for(const e of [f.key('}',{target:input}),f.key('}',{target:editable}),
        f.key('}',{ctrlKey:true}),f.key('}',{altKey:true}),f.key('}',{metaKey:true}),
        f.key('}',{isComposing:true}),f.key('}',{isTrusted:false})])assert.equal(e.prevented,false);
    assert.equal(v.playbackRate,1);
    assert.equal(f.key('}',{shiftKey:true}).prevented,true);
    const altGr={ctrlKey:true,altKey:true,getModifierState:key=>key==='AltGraph'};
    assert.equal(f.key('}',altGr).prevented,true);assert.equal(v.playbackRate,2);
});
test('does not consume keys without usable media and supports playing audio',()=>{
    const f=fixture();assert.equal(f.key('}').prevented,false);
    const paused=f.video({paused:true,getBoundingClientRect:()=>({left:0,top:0,right:0,bottom:0})});
    f.media.push(paused);assert.equal(f.key('}').prevented,false);
    const audio=f.video({audio:true,getBoundingClientRect:()=>({left:0,top:0,right:0,bottom:0})});
    f.media.push(audio);f.key('}');assert.equal(audio.playbackRate,1.5);assert.equal(paused.playbackRate,1);
});
test('finds media in an open shadow root',()=>{
    const f=fixture(),v=f.video(),root={querySelectorAll:sel=>sel==='video, audio'?[v]:[]},host=f.element('div');
    host.shadowRoot=root;f.document.roots.push(host);f.key('}');assert.equal(v.playbackRate,1.5);
});
test('temporary indicators are removed and rate resets are corrected with bounded retries',()=>{
    const f=fixture(),v=f.video();f.media.push(v);f.key('}');
    for(let i=0;i<3;i++){v.playbackRate=1;v.listeners.get('ratechange')({currentTarget:v});assert.equal(v.playbackRate,1.5);}
    v.playbackRate=1;v.listeners.get('ratechange')({currentTarget:v});assert.equal(v.playbackRate,1);
    f.flush();assert.equal(f.html.children.length,0);assert.equal(f.handlers.has('scroll'),false);
});
test('successive embedded YouTube shortcuts retain the requested rates',()=>{
    const f=fixture({host:'www.youtube.com'}),v=f.video(),requests=[];f.media.push(v);
    v.dispatchEvent=e=>{assert.equal(e.type,'babinium-speed-request');requests.push(v.getAttribute('data-babinium-request-rate'));return false;};
    f.key('}');f.key('}');f.key('{');
    assert.deepEqual(requests,['1.5','2','1.5']);assert.equal(v.getAttribute('data-babinium-request-rate'),null);
});
test('a player rejecting a speed change does not break the page',()=>{
    const f=fixture(),v=f.video();f.media.push(v);
    Object.defineProperty(v,'playbackRate',{get:()=>1,set:()=>{throw new Error('unsupported');}});
    assert.doesNotThrow(()=>f.key('}'));assert.equal(f.html.children[0].children[0].textContent,'Velocidad no disponible');
});
