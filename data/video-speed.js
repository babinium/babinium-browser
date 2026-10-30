// SPDX-License-Identifier: GPL-3.0-or-later
// Built-in, event-driven controls for HTML media. No extension or background process.
(() => {
    'use strict';
    const states=new WeakMap();
    let indicator=null, label=null, current=null, hideTimer=0, following=false;

    function state(media){
        let s=states.get(media);
        if(!s){s={pendingRate:null,pendingAt:0,
            desiredRate:null,watching:false,retries:0,retrySince:0,settleTimer:0};states.set(media,s);}
        return s;
    }
    function watchRate(media,s){
        if(!s.watching){media.addEventListener('ratechange',rateChanged);s.watching=true;}
    }
    function releaseUnusedRate(media){
        const s=states.get(media);
        if(s&&s.watching&&s.desiredRate===null){media.removeEventListener('ratechange',rateChanged);s.watching=false;}
    }
    function editable(node){
        if(!node||node.nodeType!==1)return false;
        const name=node.tagName?.toLowerCase();
        return name==='input'||name==='textarea'||name==='select'||node.isContentEditable||
            /^(textbox|searchbox|combobox)$/i.test(node.getAttribute?.('role')||'');
    }
    function typing(event){
        if((event.composedPath?.()||[]).some(editable))return true;
        let active=document.activeElement;
        while(active){if(editable(active))return true;active=active.shadowRoot?.activeElement;}
        return false;
    }
    function score(media){
        if(!media.isConnected)return -1;
        const r=media.getBoundingClientRect(),w=window.innerWidth,h=window.innerHeight;
        const width=Math.max(0,Math.min(w,r.right)-Math.max(0,r.left));
        const height=Math.max(0,Math.min(h,r.bottom)-Math.max(0,r.top));
        const area=width*height,playing=!media.paused&&!media.ended;
        // A hidden playing audio element is useful; hidden paused media is not.
        if(!playing&&area<1600)return -1;
        return (playing?2000000000:0)+(area>=1600?1000000000:0)+Math.min(area,999999999);
    }
    function select(){
        let best=null,bestScore=-1;
        const consider=root=>{
            for(const media of root.querySelectorAll('video, audio')){
                const n=score(media);if(n>bestScore){best=media;bestScore=n;}
            }
        };
        consider(document);
        if(best)return best;
        // Open shadow roots are searched only on a shortcut, never by polling.
        const queue=[document];let examined=0,rootIndex=0;
        while(rootIndex<queue.length&&examined<4096){
            const root=queue[rootIndex++];
            const walker=document.createTreeWalker(root,NodeFilter.SHOW_ELEMENT);let node;
            while(examined<4096&&(node=walker.nextNode())){
                examined++;
                if(node.shadowRoot){consider(node.shadowRoot);queue.push(node.shadowRoot);}
            }
        }
        return best;
    }
    function position(){
        if(!indicator||!current)return;
        if(!current.isConnected){hide();return;}
        const parent=document.fullscreenElement||document.documentElement;
        if(parent&&indicator.parentNode!==parent)parent.append(indicator);
        const r=current.getBoundingClientRect();
        indicator.style.left=Math.max(4,Math.min(window.innerWidth-110,r.left+8))+'px';
        indicator.style.top=Math.max(4,Math.min(window.innerHeight-32,r.top+8))+'px';
    }
    function stopFollowing(){
        if(!following)return;
        window.removeEventListener('scroll',position,true);
        window.removeEventListener('resize',position);
        document.removeEventListener('fullscreenchange',position);
        following=false;
    }
    function hide(){
        if(hideTimer)clearTimeout(hideTimer);hideTimer=0;
        stopFollowing();
        if(current)releaseUnusedRate(current);
        if(indicator)indicator.remove();
        indicator=null;label=null;current=null;
    }
    function rateChanged(event){
        const media=event.currentTarget,s=states.get(media);
        // A site can restore its own speed after our change, including after
        // the indicator disappears. React only to actual rate-change events;
        // cap retries in a short window so a conflicting player cannot loop.
        if(s&&s.desiredRate!==null&&Math.abs(media.playbackRate-s.desiredRate)>.001){
            const now=Date.now();
            if(now-s.retrySince>2500){s.retrySince=now;s.retries=0;}
            if(s.retries<3){s.retries++;try{media.playbackRate=s.desiredRate;}catch(_){}}
        }
        if(label&&current===media)label.textContent=media.playbackRate.toFixed(2)+'×';
    }
    function show(media,message){
        if(!document.documentElement)return;
        if(current!==media){if(current)releaseUnusedRate(current);current=media;watchRate(media,state(media));}
        if(!indicator){
            indicator=document.createElement('div');
            indicator.setAttribute('role','status');indicator.setAttribute('aria-label','Velocidad de reproducción');
            indicator.setAttribute('data-babinium-speed','');
            indicator.style.cssText='all:initial;position:fixed;z-index:2147483647;pointer-events:none;display:block;padding:3px 7px;border-radius:4px;background:rgba(0,0,0,.88);color:#fff;font:14px sans-serif;box-shadow:0 1px 5px #0009;';
            label=document.createElement('span');label.setAttribute('aria-live','polite');indicator.append(label);
        }
        const parent=document.fullscreenElement||document.documentElement;
        if(indicator.parentNode!==parent)parent.append(indicator);
        label.textContent=message||media.playbackRate.toFixed(2)+'×';position();
        if(!following){
            window.addEventListener('scroll',position,{capture:true,passive:true});
            window.addEventListener('resize',position,{passive:true});
            document.addEventListener('fullscreenchange',position);following=true;
        }
        if(hideTimer)clearTimeout(hideTimer);hideTimer=0;
        hideTimer=setTimeout(hide,2500);
    }
    function currentRate(media,s){
        if(s.pendingRate!==null&&Math.abs(media.playbackRate-s.pendingRate)>.001&&Date.now()-s.pendingAt<1500)return s.pendingRate;
        s.pendingRate=null;return media.playbackRate;
    }
    function checkRateOnce(media,s){
        if(s.settleTimer)clearTimeout(s.settleTimer);
        // A reset may occur without a usable ratechange reaching this listener.
        // One delayed check covers that case; it is scheduled only after a
        // user shortcut and never repeats by itself.
        s.settleTimer=setTimeout(()=>{
            s.settleTimer=0;
            if(!media.isConnected||s.desiredRate===null)return;
            try{if(Math.abs(media.playbackRate-s.desiredRate)>.001)media.playbackRate=s.desiredRate;}catch(_){}
        },500);
    }
    function setRate(media,s,value){
        const previous=s.desiredRate;
        s.pendingRate=value;s.pendingAt=Date.now();s.desiredRate=value;s.retries=0;s.retrySince=s.pendingAt;
        watchRate(media,s);checkRateOnce(media,s);
        try{
            // YouTube may restore its player-level speed after a direct media
            // change. The small main-world adapter synchronizes that state once.
            if(/(^|\.)(youtube\.com|youtube-nocookie\.com)$/.test(location.hostname)){
                media.setAttribute('data-babinium-request-rate',String(value));
                try{
                    if(!media.dispatchEvent(new Event('babinium-speed-request',{bubbles:true,cancelable:true})))return;
                }finally{media.removeAttribute('data-babinium-request-rate');}
            }
            media.playbackRate=value;
        }catch(error){if(s.settleTimer)clearTimeout(s.settleTimer);s.settleTimer=0;s.desiredRate=previous;s.pendingRate=null;throw error;}
    }
    function apply(media,key){
        const s=state(media);let message='';
        try{
            const current=currentRate(media,s);
            const next=Math.round((current+(key==='{' ? -.5 : .5))*1000)/1000;
            // Keep valid rates and do not reverse direction if the site starts
            // outside the normal range.
            const value=Math.max(Math.min(.5,current),Math.min(Math.max(16,current),next));
            setRate(media,s,value);message=value.toFixed(2)+'×';
        }catch(_){message='Velocidad no disponible';}
        show(media,message);
    }
    // Capture at the document before a site's target listener can stop the
    // event. The per-media listener still covers media in shadow roots.
    document.addEventListener('ratechange',event=>{
        const media=event.target,s=states.get(media);
        if(s?.watching)rateChanged({currentTarget:media});
    },true);
    window.addEventListener('keydown',event=>{
        if(!event.isTrusted||event.metaKey||event.isComposing)return;
        const key=event.key;if(key!=='{'&&key!=='}')return;
        // Braces may require Shift or AltGr depending on the keyboard layout.
        const altGraph=event.getModifierState?.('AltGraph')===true;
        if(((event.ctrlKey||event.altKey)&&!altGraph)||typing(event))return;
        const media=select();if(!media)return;
        event.preventDefault();event.stopImmediatePropagation();apply(media,key);
    },true);
})();
