// SPDX-License-Identifier: GPL-3.0-or-later
// Use YouTube's own setting once per profile; later manual choices remain untouched.
(() => {
    if (!/(^|\.)youtube\.com$/.test(location.hostname) || window !== window.top) return;
    const key='babinium-ambient-default-v1';
    try { if(localStorage.getItem(key)==='1') return; } catch (_) { return; }
    let timer=null, menuTimer=null, attempts=0, adAttempts=0, busy=false, menuObserved=false;
    let menu=null, previous='', previousPriority='', finished=false;
    function restore(){
        if(!menu)return;
        if(previous)menu.style.setProperty('visibility',previous,previousPriority);
        else menu.style.removeProperty('visibility');
        menu=null;
    }
    function stop(){
        if(timer)clearInterval(timer);timer=null;
        if(menuTimer)clearInterval(menuTimer);menuTimer=null;
        document.removeEventListener('play',play,true);
        document.removeEventListener('yt-navigate-finish',navigate);
        document.removeEventListener('pointerdown',user,true);
    }
    function finish(){
        finished=true;try{localStorage.setItem(key,'1');}catch(_){}restore();stop();
    }
    function user(event){
        if(!event.isTrusted||!event.target?.closest?.('.ytp-settings-button,.ytp-settings-menu,.ytp-panel-menu'))return;
        // If our hidden menu is still opening, close it before the user's
        // subsequent click so that their first click opens the settings.
        if(busy&&menu&&event.target.closest('.ytp-settings-button')){
            const style=getComputedStyle(menu);
            if(!menuObserved||(menu.offsetWidth&&menu.offsetHeight)||style.display!=='none')document.querySelector('.ytp-settings-button')?.click();
        }
        finish();
    }
    function attempt(){
        if(finished||busy)return;
        // A preroll is not the content video. Wait for it to finish instead of
        // mistaking its player state for the user's ambient-mode preference.
        if(document.querySelector('.html5-video-player.ad-showing,.html5-video-player.ad-interrupting')){
            if(++adAttempts>=180){clearInterval(timer);timer=null;}
            return;
        }
        if(++attempts>40){clearInterval(timer);timer=null;return;}
        const video=document.querySelector('video'),panel=document.querySelector('ytd-watch-flexy,ytd-watch-grid');
        if(!video||video.paused||video.currentTime<.5||!panel)return;
        if(!panel.hasAttribute('cinematics-active')){finish();return;}
        const gear=document.querySelector('.ytp-settings-button'),settings=document.querySelector('.ytp-settings-menu');
        if(!gear||!settings)return;
        if(settings.offsetWidth&&settings.offsetHeight&&getComputedStyle(settings).visibility!=='hidden'){finish();return;}
        menu=settings;previous=menu.style.getPropertyValue('visibility');previousPriority=menu.style.getPropertyPriority('visibility');
        menu.style.setProperty('visibility','hidden','important');busy=true;menuObserved=false;gear.click();
        let menuChecks=0;
        menuTimer=setInterval(()=>{
            if(finished)return;
            if(settings.offsetWidth&&settings.offsetHeight)menuObserved=true;
            const item=[...settings.querySelectorAll('.ytp-menuitem')].find(e=>{
                const label=(e.querySelector('.ytp-menuitem-label')?.textContent?.trim()||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
                return /^(ambient mode|modo ambiente|iluminacion cinematica)$/i.test(label);
            });
            // YouTube may populate/open its menu asynchronously, especially
            // during playback startup. Wait at most two seconds, then stop.
            if((!menuObserved||!item)&&++menuChecks<20)return;
            clearInterval(menuTimer);menuTimer=null;
            if(!menuObserved){
                // Cancel our pending open if the site never made the menu ready.
                gear.click();restore();busy=false;clearInterval(timer);timer=null;return;
            }
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
    function start(){if(finished||timer)return;attempts=0;adAttempts=0;timer=setInterval(attempt,500);}
    function play(event){if(event.target?.tagName==='VIDEO')start();}
    function navigate(){const video=document.querySelector('video');if(video&&!video.paused)start();}
    document.addEventListener('pointerdown',user,true);
    document.addEventListener('play',play,true);
    document.addEventListener('yt-navigate-finish',navigate);
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',navigate,{once:true});else navigate();
})();
