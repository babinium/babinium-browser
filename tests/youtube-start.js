// Explicit test driver, never installed as a browsing content script.
(() => {
    const buttons=[...document.querySelectorAll('button')];
    const reject=buttons.find(b=>/^(Reject all|Rechazar todo|Rechazar todas|Rechazar cookies|No aceptar)$/i.test(b.textContent.trim()));
    if(reject)reject.click();
    const player=document.getElementById('movie_player');
    try{player?.setPlaybackQualityRange?.('medium','medium');player?.setPlaybackQuality?.('medium');}catch{}
    const video=document.querySelector('video');
    if(video){video.muted=true;player?.playVideo?.();video.play().catch(()=>{});}
    // YouTube may replace its video element while negotiating a stream. Retry
    // play on the new element for 30 s; never seek, skip, or remove ad elements.
    let retries=20;
    function resumeReplacement(){
        const v=document.querySelector('video');
        if(v&&v.paused){v.muted=true;document.getElementById('movie_player')?.playVideo?.();v.play().catch(()=>{});}
        if(--retries>0)setTimeout(resumeReplacement,1500);
    }
    setTimeout(resumeReplacement,1500);
    const response=player?.getPlayerResponse?.();
    const initial=window.ytInitialPlayerResponse;
    return JSON.stringify({url:location.href,title:document.title,consentRejected:!!reject,videoFound:!!video,quality:player?.getPlaybackQuality?.(),videoId:response?.videoDetails?.videoId,playerResponse:response?.playabilityStatus,initialAds:{placements:initial?.adPlacements?.length??0,slots:initial?.adSlots?.length??0,playerAds:initial?.playerAds?.length??0},playerAds:{placements:response?.adPlacements?.length??0,slots:response?.adSlots?.length??0,playerAds:response?.playerAds?.length??0},bodyPreview:document.body?.innerText.slice(0,600)});
})();
