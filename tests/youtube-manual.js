// Test-only driver. Coordinates are read from YouTube; interaction is xdotool.
(() => {
    const reject=[...document.querySelectorAll('button')].find(b=>/^(Reject all|Rechazar todo|Rechazar todas)$/i.test(b.textContent.trim()));
    reject?.click();
    const play=()=>{const p=document.getElementById('movie_player'),v=document.querySelector('video');if(v&&v.paused){v.muted=true;p?.playVideo?.();v.play().catch(()=>{});}};
    play();let ticks=0;
    const timer=setInterval(()=>{
        if(++ticks>70){clearInterval(timer);return;}
        play();const p=document.getElementById('movie_player'),v=document.querySelector('video');
        const rect=e=>{if(!e)return null;const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};};
        // Keep the window title below X11's size limit; this test only needs
        // the quality entry and the 720p choice.
        const items=[...document.querySelectorAll('.ytp-menuitem')].filter(e=>e.offsetWidth&&e.offsetHeight&&/^(Quality|720p)/i.test(e.innerText.trim())).map(e=>({text:e.innerText.trim(),...rect(e)}));
        const data=JSON.stringify({viewport:[innerWidth,innerHeight],gear:rect(document.querySelector('.ytp-settings-button')),items,quality:p?.getPlaybackQuality?.(),height:v?.videoHeight,time:v?.currentTime,codecs:p?.getStatsForNerds?.()?.codecs,codecFallback:sessionStorage.getItem('babinium-codec-fallback:'+(new URL(location.href).searchParams.get('v')||''))});
        document.title='BBYT:'+btoa(unescape(encodeURIComponent(data)));
    },700);
    return 'YouTube test driver started';
})();
