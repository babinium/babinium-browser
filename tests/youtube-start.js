// Explicit test driver, never installed as a browsing content script.
(() => {
    const buttons=[...document.querySelectorAll('button')];
    const reject=buttons.find(b=>/^(Reject all|Rechazar todo|Rechazar todas|Rechazar cookies|No aceptar)$/i.test(b.textContent.trim()));
    if(reject)reject.click();
    const player=document.getElementById('movie_player');
    player?.setPlaybackQualityRange?.('medium','medium');
    player?.setPlaybackQuality?.('medium');
    const video=document.querySelector('video');
    if(video){video.muted=true;video.play().catch(()=>{});}
    const response=player?.getPlayerResponse?.();
    const initial=window.ytInitialPlayerResponse;
    return JSON.stringify({url:location.href,title:document.title,consentRejected:!!reject,videoFound:!!video,quality:player?.getPlaybackQuality?.(),videoId:response?.videoDetails?.videoId,playerResponse:response?.playabilityStatus,initialAds:{placements:initial?.adPlacements?.length??0,slots:initial?.adSlots?.length??0,playerAds:initial?.playerAds?.length??0},playerAds:{placements:response?.adPlacements?.length??0,slots:response?.adSlots?.length??0,playerAds:response?.playerAds?.length??0},bodyPreview:document.body.innerText.slice(0,600)});
})();
