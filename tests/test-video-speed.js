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

test('S, D, R and G control speed with a reversible 1.8x preference',()=>{
    const f=fixture(),v=f.video();f.media.push(v);
    assert.equal(f.key('d').prevented,true);assert.equal(v.playbackRate,1.1);
    f.key('s');assert.equal(v.playbackRate,1);f.key('g');assert.equal(v.playbackRate,1.8);
    f.key('g');assert.equal(v.playbackRate,1);f.key('d');f.key('r');assert.equal(v.playbackRate,1);
    assert.equal(f.html.children[0].children[1].textContent,'1.00×');
});
test('Z/X seek and M/J mark and return without exceeding the media duration',()=>{
    const f=fixture(),v=f.video();f.media.push(v);
    f.key('m');v.currentTime=75;f.key('j');assert.equal(v.currentTime,30);
    f.key('j');assert.equal(v.currentTime,75);f.key('z');assert.equal(v.currentTime,65);
    v.currentTime=119;f.key('x');assert.equal(v.currentTime,120);
});
test('V pins and hides the indicator; its buttons adjust speed',()=>{
    const f=fixture(),v=f.video();f.media.push(v);f.key('v');
    assert.equal(f.html.children.length,1);assert.equal(f.timers.size,0);
    const button=f.html.children[0].children[2];button.listeners.get('click')({stopPropagation(){}});
    assert.equal(v.playbackRate,1.1);f.key('v');assert.equal(f.html.children.length,0);
    assert.equal(v.listeners.has('ratechange'),true);assert.equal(f.timers.size,1);f.flush();assert.equal(f.timers.size,0);
});
test('does not consume typing, browser shortcuts, composition or synthetic events',()=>{
    const f=fixture(),v=f.video();f.media.push(v);
    const input=f.element('input'),editable=f.element('div');editable.isContentEditable=true;
    for(const e of [f.key('d',{target:input}),f.key('d',{target:editable}),f.key('d',{ctrlKey:true}),
        f.key('d',{altKey:true}),f.key('d',{shiftKey:true}),f.key('d',{isComposing:true}),f.key('d',{isTrusted:false})])assert.equal(e.prevented,false);
    assert.equal(v.playbackRate,1);assert.equal(f.html.children.length,0);assert.equal(f.timers.size,0);
});
test('does not consume keys when there is no usable media',()=>{
    const f=fixture();assert.equal(f.key('d').prevented,false);
    const v=f.video({paused:true,getBoundingClientRect:()=>({left:0,top:0,right:0,bottom:0})});f.media.push(v);
    assert.equal(f.key('d').prevented,false);assert.equal(f.timers.size,0);
});
test('ignores unrelated keys before inspecting page focus or media',()=>{
    const f=fixture(),v=f.video();f.media.push(v);
    assert.doesNotThrow(()=>f.key('a',{composedPath(){throw new Error('unexpected page inspection');}}));
    assert.equal(v.playbackRate,1);assert.equal(f.html.children.length,0);
});
test('chooses playing media and also supports hidden playing audio',()=>{
    const f=fixture(),paused=f.video({paused:true}),audio=f.video({audio:true,getBoundingClientRect:()=>({left:0,top:0,right:0,bottom:0})});
    f.media.push(paused,audio);f.key('d');assert.equal(audio.playbackRate,1.1);assert.equal(paused.playbackRate,1);
});
test('finds dynamically added media and media in an open shadow root',()=>{
    const f=fixture();assert.equal(f.key('d').prevented,false);
    const v=f.video(),root={querySelectorAll:sel=>sel==='video, audio'?[v]:[]},host=f.element('div');host.shadowRoot=root;f.document.roots.push(host);
    f.key('d');assert.equal(v.playbackRate,1.1);f.document.roots=[];f.media.push(v);f.key('d');assert.equal(v.playbackRate,1.2);
});
test('temporary indicators and position listeners are removed after use',()=>{
    const f=fixture(),v=f.video();f.media.push(v);f.key('d');assert.equal(f.timers.size,2);assert.equal(f.html.children.length,1);
    f.flush();assert.equal(f.html.children.length,0);assert.equal(v.listeners.has('ratechange'),true);assert.equal(f.handlers.has('scroll'),false);
    assert.equal(f.timers.size,0);
});
test('viewing the indicator alone does not leave a media listener behind',()=>{
    const f=fixture(),v=f.video();f.media.push(v);f.key('v');f.key('v');
    assert.equal(v.listeners.has('ratechange'),false);assert.equal(f.timers.size,0);
});
test('a player rejecting a speed change does not break the page',()=>{
    const f=fixture(),v=f.video();f.media.push(v);Object.defineProperty(v,'playbackRate',{get:()=>1,set:()=>{throw new Error('unsupported');}});
    assert.doesNotThrow(()=>f.key('d'));assert.equal(f.html.children[0].children[1].textContent,'Velocidad no disponible');
});
test('retries a short-lived player reset only a bounded number of times',()=>{
    const f=fixture(),v=f.video();f.media.push(v);f.key('d');
    for(let i=0;i<3;i++){v.playbackRate=1;v.listeners.get('ratechange')({currentTarget:v});assert.equal(v.playbackRate,1.1);}
    v.playbackRate=1;v.listeners.get('ratechange')({currentTarget:v});assert.equal(v.playbackRate,1);
    f.flush();assert.equal(v.listeners.has('ratechange'),true);assert.equal(f.timers.size,0);
});
test('successive YouTube shortcuts preserve pending speed while the player updates',()=>{
    const f=fixture({host:'www.youtube.com'}),v=f.video(),requests=[];f.media.push(v);
    v.dispatchEvent=e=>{assert.equal(e.type,'babinium-speed-request');requests.push(v.getAttribute('data-babinium-request-rate'));return false;};
    f.key('d');f.key('d');f.key('g');f.key('g');
    assert.deepEqual(requests,['1.1','1.2','1.8','1.2']);assert.equal(v.getAttribute('data-babinium-request-rate'),null);
});
test('YouTube reset after a browser shortcut is corrected, including after the indicator hides',()=>{
    const f=fixture({host:'www.youtube.com'}),v=f.video();f.media.push(v);
    v.dispatchEvent=()=>{v.playbackRate=Number(v.getAttribute('data-babinium-request-rate'));return false;};
    f.key('d');assert.equal(v.playbackRate,1.1);
    v.playbackRate=1;v.listeners.get('ratechange')({currentTarget:v});assert.equal(v.playbackRate,1.1);
    f.flush();assert.equal(f.html.children.length,0);assert.equal(f.timers.size,0);
    assert.equal(v.listeners.has('ratechange'),true);
    v.playbackRate=1;v.listeners.get('ratechange')({currentTarget:v});assert.equal(v.playbackRate,1.1);
});
test('a page cannot hide a rate reset by stopping the target event',()=>{
    const f=fixture(),v=f.video();f.media.push(v);f.key('d');
    const capture=f.handlers.get('document:ratechange');assert.equal(typeof capture,'function');
    v.playbackRate=1;capture({target:v});assert.equal(v.playbackRate,1.1);
});
test('a reset without a delivered ratechange does not lose the selected speed',()=>{
    const f=fixture(),v=f.video();f.media.push(v);f.key('d');
    assert.equal(v.playbackRate,1.1);
    v.playbackRate=1;f.flush();
    assert.equal(v.playbackRate,1.1);
});
test('rapid shortcuts leave only one pending rate check for the latest choice',()=>{
    const f=fixture(),v=f.video();f.media.push(v);
    for(let i=0;i<6;i++)f.key('d');
    assert.equal(v.playbackRate,1.6);assert.equal(f.timers.size,2);
    v.playbackRate=1;f.flush();assert.equal(v.playbackRate,1.6);assert.equal(f.timers.size,0);
});
test('falls back to the media element if the YouTube adapter is unavailable',()=>{
    const f=fixture({host:'youtube.com'}),v=f.video();f.media.push(v);v.dispatchEvent=()=>true;
    f.key('d');assert.equal(v.playbackRate,1.1);assert.equal(v.getAttribute('data-babinium-request-rate'),null);
});
