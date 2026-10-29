// Development-only inspection; no account information is collected.
(() => {
    const reject=[...document.querySelectorAll('button')].find(b=>/^(Reject all|Rechazar todo|Rechazar todas)$/i.test(b.textContent.trim()));
    reject?.click();
    const play=()=>{const p=document.getElementById('movie_player'),v=document.querySelector('video');if(v&&v.paused){v.muted=true;p?.playVideo?.();v.play().catch(()=>{});}};
    play();let ticks=0;const initialCookie=document.cookie;
    const flags=()=>{try{const c=document.cookie.split('; ').find(s=>s.startsWith('PREF='));
        return Object.fromEntries([...new URLSearchParams(decodeURIComponent(c?.slice(5)||''))].filter(([k,v])=>/^f\d+$/.test(k)&&/^[0-9a-f]+$/i.test(v)));}catch(_){return {};}};
    const initialFlags=flags();
    let playerInfo=null;
    const timer=setInterval(()=>{
        if(++ticks>90){clearInterval(timer);return;}
        play();const p=document.getElementById('movie_player'),v=document.querySelector('video');
        const rect=e=>{if(!e)return null;const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};};
        const items=[...document.querySelectorAll('.ytp-menuitem')].filter(e=>e.offsetWidth&&e.offsetHeight&&/ambient mode|modo ambiente|iluminación cinemática/i.test(e.innerText)).map(e=>({text:e.innerText.trim(),checked:e.getAttribute('aria-checked'),...rect(e)}));
        const panel=document.querySelector('ytd-watch-flexy,ytd-watch-grid');
        if(!playerInfo&&p){
            try{const options=p.getOptions?.();const names=new Set();for(let x=p;x;x=Object.getPrototypeOf(x))
                for(const k of Object.getOwnPropertyNames(x))if(/ambient|cinematic|options/i.test(k))names.add(k);
                playerInfo={options:Array.isArray(options)?options.filter(x=>/ambient|cinematic/i.test(x)):null,methods:[...names].slice(0,12)};}catch(_){playerInfo={};}
        }
        const data=JSON.stringify({viewport:[innerWidth,innerHeight],gear:rect(document.querySelector('.ytp-settings-button')),items,
            ambient:panel?.hasAttribute('cinematics-active'),ambientEnabled:panel?.hasAttribute('cinematics-enabled'),
            quality:p?.getPlaybackQuality?.(),height:v?.videoHeight,time:v?.currentTime,frames:v?.getVideoPlaybackQuality?.().totalVideoFrames,
            dropped:v?.getVideoPlaybackQuality?.().droppedVideoFrames,codecs:p?.getStatsForNerds?.()?.codecs,
            preferences:Object.fromEntries(Object.keys(localStorage).filter(k=>/ambient|cinematic/i.test(k)).map(k=>[k,localStorage.getItem(k)])),cookieChanged:document.cookie!==initialCookie,
            flags:flags(),initialFlags,playerInfo,
            ad:!!document.querySelector('.ad-showing,.ad-interrupting')});
        document.title='BBAMBIENT:'+btoa(unescape(encodeURIComponent(data)));
    },2000);
    return 'Ambient comparison driver started';
})();
