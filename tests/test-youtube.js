// SPDX-License-Identifier: GPL-3.0-or-later
// Test the selection policy and the failure recovery without contacting YouTube.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync('data/youtube.js','utf8');

async function fixture({avc=true,vp9=false,av1=false,retried=false}={}) {
    const handlers={}, storage=new Map(), intervals=[], result={reloads:0,handlers,storage,intervals};
    if(retried)storage.set('babinium-codec-fallback:video','1');
    class MediaElement { canPlayType(){return 'probably';} }
    const supported={avc,vp9,av1};
    const capabilities={decodingInfo:async config=>{
        const type=config.video.contentType;
        const name=type.includes('avc1')?'avc':type.includes('vp09')?'vp9':'av1';
        return {supported:true,smooth:true,powerEfficient:supported[name]};
    }};
    const context={
        URL,location:{hostname:'www.youtube.com',href:'https://www.youtube.com/watch?v=video',reload:()=>result.reloads++},
        navigator:{mediaCapabilities:capabilities},MediaSource:{isTypeSupported:()=>true},HTMLMediaElement:MediaElement,
        sessionStorage:{getItem:key=>storage.get(key),setItem:(key,value)=>storage.set(key,value)},
        document:{readyState:'complete',addEventListener:(name,handler)=>handlers[name]=handler,querySelector:()=>null,getElementById:()=>({getPlayerResponse:()=>result.response})},
        setInterval:fn=>{intervals.push(fn);return intervals.length;},clearInterval:()=>{}
    };
    context.window=context;context.top=context;vm.createContext(context);vm.runInContext(code,context);
    await new Promise(resolve=>setImmediate(resolve));
    result.context=context;return result;
}

test('prefer AVC only when it is reported efficient and competing codecs are not',async()=>{
    const {context:c}=await fixture();
    assert.equal(c.MediaSource.isTypeSupported('video/webm; codecs="vp09.00.10.08"'),false);
    assert.equal(c.MediaSource.isTypeSupported('video/mp4; codecs="av01.0.04M.08"'),false);
    assert.equal(c.MediaSource.isTypeSupported('video/mp4; codecs="avc1.4d401e"'),true);
    assert.equal(c.MediaSource.isTypeSupported('audio/webm; codecs="opus"'),true);
    assert.equal(new c.HTMLMediaElement().canPlayType('video/webm; codecs="vp9"'),'');
    assert.equal((await c.navigator.mediaCapabilities.decodingInfo({video:{contentType:'video/webm; codecs="vp09.00.10.08"'}})).supported,false);
});
test('keep VP9 and AV1 available when they are reported efficient',async()=>{
    const {context:c}=await fixture({vp9:true,av1:true});
    assert.equal(c.MediaSource.isTypeSupported('video/webm; codecs="vp9"'),true);
    assert.equal(c.MediaSource.isTypeSupported('video/mp4; codecs="av01.0.04M.08"'),true);
});
test('do not force AVC when it is not reported efficient',async()=>{
    const {context:c}=await fixture({avc:false});
    assert.equal(c.MediaSource.isTypeSupported('video/webm; codecs="vp9"'),true);
});
test('on video failure retry once with normal codec negotiation',async()=>{
    const f=await fixture();f.handlers.error({target:{tagName:'VIDEO',error:{code:4}}});
    assert.equal(f.reloads,1);assert.equal(f.storage.get('babinium-codec-fallback:video'),'1');
    assert.equal(f.context.MediaSource.isTypeSupported('video/webm; codecs="vp9"'),true);
    const retried=await fixture({retried:true});
    assert.equal(retried.context.MediaSource.isTypeSupported('video/webm; codecs="vp9"'),true);
});
test('retry with normal codecs if a video offers no AVC stream',async()=>{
    const f=await fixture();
    f.response={streamingData:{adaptiveFormats:[{mimeType:'video/webm; codecs="vp9"'}]}};
    f.intervals[0]();
    assert.equal(f.reloads,1);
    assert.equal(f.context.MediaSource.isTypeSupported('video/webm; codecs="vp9"'),true);
});
