// Test-only driver for a real YouTube player. No seeking while an ad is present.
(() => {
    const reject=[...document.querySelectorAll('button')].find(b=>/^(Reject all|Rechazar todo|Rechazar todas)$/i.test(b.textContent.trim()));
    reject?.click();
    const play=()=>{const p=document.getElementById('movie_player'),v=document.querySelector('video');if(v&&v.paused){v.muted=true;p?.playVideo?.();v.play().catch(()=>{});}};
    play();let ticks=0,watched=null,mediaSerial=0,changes=[],lifecycle=[],forcedResets=0,forcedRate=null,keyEvents=[],rateExperiments=[];
    window.addEventListener('keydown',event=>{
        if(!['d','D','F8'].includes(event.key))return;
        keyEvents.push({key:event.key,trusted:event.isTrusted,target:event.target?.tagName,
            active:document.activeElement?.tagName,ctrl:event.ctrlKey,shift:event.shiftKey});
        if(keyEvents.length>6)keyEvents.shift();
    },true);
    // Test only: imitate a site that restores its own speed after the
    // indicator has disappeared. The key must be sent by the real UI driver.
    window.addEventListener('keydown',event=>{
        if(!event.isTrusted||event.key!=='F8')return;
        event.preventDefault();event.stopImmediatePropagation();
        const v=document.querySelector('video'),p=document.getElementById('movie_player');
        if(v){p?.setPlaybackRate?.(1);v.playbackRate=1;forcedRate=v.playbackRate;forcedResets++;}
    },true);
    // Development-only comparison of the player API and the underlying media.
    window.addEventListener('keydown',event=>{
        if(!event.isTrusted||!['F6','F7'].includes(event.key))return;
        event.preventDefault();event.stopImmediatePropagation();
        const v=document.querySelector('video'),p=document.getElementById('movie_player');
        if(!v)return;
        if(event.key==='F6')p?.setPlaybackRate?.(1.1);else v.playbackRate=1.1;
        rateExperiments.push({key:event.key,media:v.playbackRate,player:p?.getPlaybackRate?.()});
    },true);
    const timer=setInterval(()=>{
        if(++ticks>100){clearInterval(timer);return;}play();
        const v=document.querySelector('video'),p=document.getElementById('movie_player'),r=v?.getBoundingClientRect();
        if(v&&v!==watched){watched=v;const serial=++mediaSerial;
            v.addEventListener('ratechange',()=>{changes.push([Math.round(performance.now()),serial,document.querySelector('video')===v,v.playbackRate,p?.getPlaybackRate?.()]);if(changes.length>4)changes.shift();});
            for(const type of ['play','pause'])v.addEventListener(type,()=>{lifecycle.push([Math.round(performance.now()),serial,type,v.currentTime]);if(lifecycle.length>3)lifecycle.shift();});}
        const data={rate:v?.playbackRate,time:v?.currentTime,paused:v?.paused,height:v?.videoHeight,
            playerRate:p?.getPlaybackRate?.(),availableRates:p?.getAvailablePlaybackRates?.(),ad:!!document.querySelector('.ad-showing,.ad-interrupting'),
            indicator:!!document.querySelector('[data-babinium-speed]'),mediaSerial,
            mediaCount:document.querySelectorAll('video, audio').length,changes,lifecycle,forcedResets,forcedRate,keyEvents,rateExperiments,
            bbTrace:document.documentElement?.getAttribute('data-bb-rate-trace'),viewport:[innerWidth,innerHeight],
            videoRect:r?{x:r.x,y:r.y,w:r.width,h:r.height}:null};
        document.title='BBYTSPD:'+btoa(JSON.stringify(data));
    },700);
    return 'YouTube speed test started';
})();
