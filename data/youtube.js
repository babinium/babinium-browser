// SPDX-License-Identifier: GPL-3.0-or-later
// Best-effort default for the full YouTube player, not an official YouTube API.
// Keep user changes possible and stop polling after the player is ready or 40 s.
(() => {
    if (!/(^|\.)youtube\.com$/.test(location.hostname) || window !== window.top) return;
    // Only prefer AVC when the engine reports it as efficient at the target
    // resolution and reports the competing codec as less efficient. Do not
    // assume a particular CPU, GPU or codec is better on every machine.
    const capabilities=navigator.mediaCapabilities;
    const source=window.MediaSource;
    const nativeDecode=capabilities?.decodingInfo?.bind(capabilities);
    const nativeMse=source?.isTypeSupported?.bind(source);
    const blocked=new Set();
    const key=()=>'babinium-codec-fallback:'+(new URL(location.href).searchParams.get('v')||'');
    let previouslyFailed=false;
    try { previouslyFailed=sessionStorage.getItem(key())==='1'; } catch (_) {}
    const denied = value => {
        if (typeof value!=='string'||!/^video\//i.test(value)) return false;
        return (blocked.has('vp9')&&/\bvp0?9\b/i.test(value))||(blocked.has('av1')&&/\bav01\b/i.test(value));
    };
    const fallback = () => {
        if (!blocked.size) return;
        blocked.clear();
        try { sessionStorage.setItem(key(),'1');location.reload(); } catch (_) {}
    };
    if (!previouslyFailed && nativeDecode && nativeMse && window.HTMLMediaElement) {
        const originalPlay=HTMLMediaElement.prototype.canPlayType;
        source.isTypeSupported=function(type){return denied(type)?false:nativeMse(type);};
        HTMLMediaElement.prototype.canPlayType=function(type){return denied(type)?'':originalPlay.call(this,type);};
        try { capabilities.decodingInfo=async function(config){
            const result=await nativeDecode(config);
            return denied(config?.video?.contentType)?{...result,supported:false,smooth:false,powerEfficient:false}:result;
        }; } catch (_) {}
        const types={avc:'video/mp4; codecs="avc1.4d401e"',vp9:'video/webm; codecs="vp09.00.10.08"',av1:'video/mp4; codecs="av01.0.04M.08"'};
        Promise.all(Object.entries(types).map(async ([name,contentType])=>{
            const info=await nativeDecode({type:'media-source',video:{contentType,width:640,height:360,bitrate:1000000,framerate:30}});
            return [name,info];
        })).then(entries=>{
            const info=Object.fromEntries(entries),video=document.querySelector('video');
            if (video?.readyState>0||!info.avc.supported||!info.avc.smooth||!info.avc.powerEfficient||!nativeMse(types.avc)) return;
            for (const codec of ['vp9','av1']) if (info[codec].supported&&!info[codec].powerEfficient) blocked.add(codec);
        }).catch(()=>{});
        document.addEventListener('error',event=>{if(event.target?.tagName==='VIDEO'&&event.target.error)fallback();},true);
        // Some videos have no AVC stream at all. Retry once with normal codec
        // negotiation instead of leaving such a video unplayable.
        let checks=0;
        const guard=setInterval(()=>{
            if(++checks>40){clearInterval(guard);return;}
            const player=document.getElementById('movie_player'),video=document.querySelector('video');
            if(video?.currentTime>0){clearInterval(guard);return;}
            const data=player?.getPlayerResponse?.()?.streamingData;
            const streams=[...(data?.formats||[]),...(data?.adaptiveFormats||[])].filter(x=>/^video\//i.test(x.mimeType||''));
            if(blocked.size&&streams.length&&!streams.some(x=>/\bavc1\b/i.test(x.mimeType))){clearInterval(guard);fallback();}
        },1000);
    }
    let timer = null;
    let lastVideo = '';
    let userChose = false;
    document.addEventListener('pointerdown', event => {
        if (event.isTrusted && event.target.closest?.('.ytp-settings-button, .ytp-panel-menu')) {
            userChose = true;
            try { document.getElementById('movie_player')?.setPlaybackQualityRange?.('small', 'highres'); } catch (_) {}
            if (timer) clearInterval(timer);
        }
    }, true);
    function applyDefault() {
        const video = new URL(location.href).searchParams.get('v') || '';
        if (!video || video === lastVideo || userChose) return;
        lastVideo = video;
        if (timer) clearInterval(timer);
        let attempts = 0;
        timer = setInterval(() => {
            const player = document.getElementById('movie_player');
            if (++attempts >= 80 || userChose) { clearInterval(timer); timer = null; return; }
            try {
                if (typeof player?.setPlaybackQualityRange !== 'function' || !player.getPlayerResponse?.()?.videoDetails) return;
                player.setPlaybackQualityRange('medium', 'medium'); // 360p when offered.
                clearInterval(timer); timer = null;
            } catch (_) { /* The player can be replaced while navigating. */ }
        }, 500);
    }
    document.addEventListener('yt-navigate-finish', applyDefault);
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', applyDefault, {once:true});
    else applyDefault();
})();
