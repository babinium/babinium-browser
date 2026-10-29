// SPDX-License-Identifier: GPL-3.0-or-later
// Built-in, event-driven controls for HTML media. No extension or background process.
(() => {
    'use strict';
    const keys=new Set(['s','d','r','z','x','g','v','m','j']);
    const states=new WeakMap();
    let indicator=null, label=null, current=null, pinned=false, hideTimer=0, following=false;

    function state(media){
        let s=states.get(media);
        if(!s){s={previousFast:null,mark:null,beforeJump:null};states.set(media,s);}
        return s;
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
        const queue=[document];let examined=0;
        while(queue.length&&examined<4096){
            const root=queue.shift();
            for(const node of root.querySelectorAll('*')){
                if(++examined>4096)break;
                if(node.shadowRoot){consider(node.shadowRoot);queue.push(node.shadowRoot);}
            }
        }
        return best;
    }
    function position(){
        if(!indicator||!current)return;
        if(!current.isConnected){pinned=false;hide();return;}
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
        if(current)current.removeEventListener('ratechange',rateChanged);
        if(indicator)indicator.remove();
        indicator=null;label=null;current=null;
    }
    function rateChanged(){if(label&&current)label.textContent=current.playbackRate.toFixed(2)+'×';}
    function show(media,message){
        if(!document.documentElement)return;
        if(current!==media){if(current)current.removeEventListener('ratechange',rateChanged);current=media;current.addEventListener('ratechange',rateChanged);}
        if(!indicator){
            indicator=document.createElement('div');
            indicator.setAttribute('role','group');indicator.setAttribute('aria-label','Velocidad de reproducción');
            indicator.setAttribute('data-babinium-speed','');
            indicator.style.cssText='all:initial;position:fixed;z-index:2147483647;display:flex;align-items:center;gap:4px;padding:3px 5px;border-radius:4px;background:rgba(0,0,0,.88);color:#fff;font:14px sans-serif;box-shadow:0 1px 5px #0009;';
            const minus=document.createElement('button'),plus=document.createElement('button');label=document.createElement('span');
            for(const button of [minus,plus]){
                button.type='button';button.style.cssText='all:initial;cursor:pointer;color:#fff;font:16px sans-serif;padding:0 5px;';
                button.addEventListener('pointerdown',e=>e.stopPropagation());
            }
            minus.textContent='−';minus.title='Reducir velocidad (S)';minus.setAttribute('aria-label',minus.title);
            plus.textContent='+';plus.title='Aumentar velocidad (D)';plus.setAttribute('aria-label',plus.title);
            minus.addEventListener('click',e=>{e.stopPropagation();if(current)apply(current,'s');});
            plus.addEventListener('click',e=>{e.stopPropagation();if(current)apply(current,'d');});
            label.setAttribute('aria-live','polite');indicator.append(minus,label,plus);
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
        if(!pinned)hideTimer=setTimeout(hide,2500);
    }
    function seek(media,value){
        let target=Math.max(0,value);
        if(Number.isFinite(media.duration))target=Math.min(target,media.duration);
        if(media.seekable?.length){
            try{target=Math.max(media.seekable.start(0),Math.min(target,media.seekable.end(media.seekable.length-1)));}catch(_){}
        }
        media.currentTime=target;
    }
    function apply(media,key){
        const s=state(media);let message='';
        try{
            switch(key){
            case 's':case 'd':{
                const next=Math.round((media.playbackRate+(key==='s'?-.1:.1))*100)/100;
                media.playbackRate=Math.max(.07,Math.min(16,next));break;
            }
            case 'r':media.playbackRate=1;break;
            case 'g':
                if(Math.abs(media.playbackRate-1.8)<.001){media.playbackRate=s.previousFast??1;s.previousFast=null;}
                else{s.previousFast=media.playbackRate;media.playbackRate=1.8;}
                break;
            case 'z':seek(media,media.currentTime-10);break;
            case 'x':seek(media,media.currentTime+10);break;
            case 'm':s.mark=media.currentTime;s.beforeJump=null;message='Marca guardada';break;
            case 'j':
                if(s.mark===null){message='Sin marca';break;}
                if(s.beforeJump!==null&&Math.abs(media.currentTime-s.mark)<.05){const back=s.beforeJump;s.beforeJump=null;seek(media,back);}
                else{s.beforeJump=media.currentTime;seek(media,s.mark);}
                message='Marca';break;
            case 'v':pinned=!pinned;if(!pinned){hide();return;}break;
            }
        }catch(_){message='Velocidad no disponible';}
        show(media,message);
    }
    window.addEventListener('keydown',event=>{
        if(!event.isTrusted||event.ctrlKey||event.altKey||event.metaKey||event.shiftKey||event.isComposing||typing(event))return;
        const key=event.key?.toLowerCase();if(!keys.has(key))return;
        const media=select();if(!media)return;
        event.preventDefault();event.stopImmediatePropagation();apply(media,key);
    },true);
})();
