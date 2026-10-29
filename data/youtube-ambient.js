// SPDX-License-Identifier: GPL-3.0-or-later
// Use YouTube's own setting once per profile; later manual choices remain untouched.
(() => {
    if (!/(^|\.)youtube\.com$/.test(location.hostname) || window !== window.top) return;
    const key='babinium-ambient-default-v1';
    try { if(localStorage.getItem(key)==='1') return; } catch (_) { return; }
    let timer=null, attempts=0, busy=false, menu=null, previous='', previousPriority='', finished=false;
    function restore(){
        if(!menu)return;
        if(previous)menu.style.setProperty('visibility',previous,previousPriority);
        else menu.style.removeProperty('visibility');
        menu=null;
    }
    function stop(){
        if(timer)clearInterval(timer);timer=null;
        document.removeEventListener('play',play,true);
        document.removeEventListener('yt-navigate-finish',navigate);
        document.removeEventListener('pointerdown',user,true);
    }
    function finish(){
        finished=true;try{localStorage.setItem(key,'1');}catch(_){}restore();stop();
    }
    function user(event){
        if(event.isTrusted&&event.target?.closest?.('.ytp-settings-button,.ytp-settings-menu,.ytp-panel-menu'))finish();
    }
    function attempt(){
        if(finished||busy)return;
        if(++attempts>40){clearInterval(timer);timer=null;return;}
        const video=document.querySelector('video'),panel=document.querySelector('ytd-watch-flexy,ytd-watch-grid');
        if(!video||video.paused||video.currentTime<.5||!panel)return;
        if(!panel.hasAttribute('cinematics-active')){finish();return;}
        const gear=document.querySelector('.ytp-settings-button'),settings=document.querySelector('.ytp-settings-menu');
        if(!gear||!settings)return;
        if(settings.offsetWidth&&settings.offsetHeight&&getComputedStyle(settings).visibility!=='hidden'){finish();return;}
        menu=settings;previous=menu.style.getPropertyValue('visibility');previousPriority=menu.style.getPropertyPriority('visibility');
        menu.style.setProperty('visibility','hidden','important');busy=true;gear.click();
        setTimeout(()=>{
            if(finished)return;
            const item=[...settings.querySelectorAll('.ytp-menuitem')].find(e=>{
                const label=(e.querySelector('.ytp-menuitem-label')?.textContent?.trim()||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
                return /^(ambient mode|modo ambiente|iluminacion cinematica)$/i.test(label);
            });
            if(item?.getAttribute('aria-checked')==='true')item.click();
            setTimeout(()=>{
                if(finished)return;
                if(settings.offsetWidth&&settings.offsetHeight)gear.click();
                restore();busy=false;
                if(item&&!panel.hasAttribute('cinematics-active'))finish();
                else if(!item){clearInterval(timer);timer=null;}
            },150);
        },100);
    }
    function start(){if(finished||timer)return;attempts=0;timer=setInterval(attempt,500);}
    function play(event){if(event.target?.tagName==='VIDEO')start();}
    function navigate(){const video=document.querySelector('video');if(video&&!video.paused)start();}
    document.addEventListener('pointerdown',user,true);
    document.addEventListener('play',play,true);
    document.addEventListener('yt-navigate-finish',navigate);
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',navigate,{once:true});else navigate();
})();
