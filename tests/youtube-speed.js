// Test-only driver for a real YouTube player. No seeking while an ad is present.
(() => {
    const reject=[...document.querySelectorAll('button')].find(b=>/^(Reject all|Rechazar todo|Rechazar todas)$/i.test(b.textContent.trim()));
    reject?.click();
    const play=()=>{const p=document.getElementById('movie_player'),v=document.querySelector('video');if(v&&v.paused){v.muted=true;p?.playVideo?.();v.play().catch(()=>{});}};
    play();let ticks=0,watched=null,changes=[];
    const timer=setInterval(()=>{
        if(++ticks>100){clearInterval(timer);return;}play();
        const v=document.querySelector('video'),p=document.getElementById('movie_player'),r=v?.getBoundingClientRect();
        if(v&&v!==watched){watched=v;v.addEventListener('ratechange',()=>{changes.push({at:Math.round(performance.now()),rate:v.playbackRate,player:p?.getPlaybackRate?.()});if(changes.length>4)changes.shift();});}
        const data={rate:v?.playbackRate,time:v?.currentTime,paused:v?.paused,height:v?.videoHeight,
            playerRate:p?.getPlaybackRate?.(),ad:!!document.querySelector('.ad-showing,.ad-interrupting'),
            indicator:!!document.querySelector('[data-babinium-speed]'),changes,viewport:[innerWidth,innerHeight],
            videoRect:r?{x:r.x,y:r.y,w:r.width,h:r.height}:null};
        document.title='BBYTSPD:'+btoa(JSON.stringify(data));
    },700);
    return 'YouTube speed test started';
})();
