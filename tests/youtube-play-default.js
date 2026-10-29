// Test-only driver: reject consent and start muted playback. It deliberately
// does not set quality or codecs; those remain Babinium/YouTube defaults.
(() => {
    const reject=[...document.querySelectorAll('button')].find(b=>/^(Reject all|Rechazar todo|Rechazar todas|Rechazar cookies|No aceptar)$/i.test(b.textContent.trim()));
    reject?.click();
    let retries=30;
    function play() {
        const player=document.getElementById('movie_player'),v=document.querySelector('video');
        if(v&&v.paused){v.muted=true;player?.playVideo?.();v.play().catch(()=>{});}
        if(--retries>0)setTimeout(play,1500);
    }
    play();
    const p=document.getElementById('movie_player'),r=p?.getPlayerResponse?.();
    return JSON.stringify({url:location.href,title:document.title,consentRejected:!!reject,videoFound:!!document.querySelector('video'),quality:p?.getPlaybackQuality?.(),stats:p?.getStatsForNerds?.(),videoId:r?.videoDetails?.videoId,ads:{placements:r?.adPlacements?.length??0,slots:r?.adSlots?.length??0,playerAds:r?.playerAds?.length??0}});
})();
