// SPDX-License-Identifier: GPL-3.0-or-later
// Verify that only valid media requests reach YouTube's player-level API.
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const code=fs.readFileSync('data/video-speed-youtube.js','utf8');
function fixture(host='www.youtube.com'){
    const handlers={},requested=[];
    const document={addEventListener:(name,fn)=>handlers[name]=fn};
    vm.runInNewContext(code,{location:{hostname:host},document});
    const player={setPlaybackRate:value=>requested.push(value),getAvailablePlaybackRates:()=>[.25,.5,1,1.5,2]};
    function event(value,{tag='VIDEO',withPlayer=true}={}){
        return {target:{tagName:tag,closest:()=>withPlayer?player:null,getAttribute:()=>value},prevented:false,preventDefault(){this.prevented=true;}};
    }
    return {handlers,requested,event};
}
test('synchronizes an arbitrary valid speed with the actual player',()=>{
    const f=fixture(),e=f.event('1.1');f.handlers['babinium-speed-request'](e);
    assert.deepEqual(f.requested,[1.1]);assert.equal(e.prevented,true);
});
test('ignores invalid values, unrelated elements and missing player APIs',()=>{
    const f=fixture();
    for(const e of [f.event('NaN'),f.event('0'),f.event('17'),f.event('1.1',{tag:'DIV'}),f.event('1.1',{withPlayer:false})]){
        f.handlers['babinium-speed-request'](e);assert.equal(e.prevented,false);
    }
    assert.equal(f.requested.length,0);
});
test('does not limit the browser speed to YouTube menu bounds',()=>{
    const f=fixture(),e=f.event('3');f.handlers['babinium-speed-request'](e);
    assert.deepEqual(f.requested,[2]);assert.equal(e.target.playbackRate,3);assert.equal(e.prevented,true);
});
test('still requests the media rate if YouTube has not exposed its range',()=>{
    const f=fixture(),e=f.event('3');const player=e.target.closest();player.getAvailablePlaybackRates=()=>[];
    f.handlers['babinium-speed-request'](e);
    assert.deepEqual(f.requested,[3]);assert.equal(e.target.playbackRate,3);assert.equal(e.prevented,true);
});
test('works on YouTube embedded hosts and does not activate elsewhere',()=>{
    for(const host of ['youtube.com','www.youtube.com','www.youtube-nocookie.com']){
        const f=fixture(host),e=f.event('1.8');f.handlers['babinium-speed-request'](e);assert.equal(e.prevented,true);
    }
    assert.equal(fixture('example.com').handlers['babinium-speed-request'],undefined);
});
