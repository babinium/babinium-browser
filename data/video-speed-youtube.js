// SPDX-License-Identifier: GPL-3.0-or-later
// Synchronize YouTube's player state with a Babinium shortcut, without polling.
(() => {
    'use strict';
    if(!/(^|\.)(youtube\.com|youtube-nocookie\.com)$/.test(location.hostname))return;
    document.addEventListener('babinium-speed-request',event=>{
        const media=event.target;
        if(!media||!['VIDEO','AUDIO'].includes(media.tagName))return;
        const player=media.closest?.('#movie_player');
        const value=Number(media.getAttribute('data-babinium-request-rate'));
        if(!player||typeof player.setPlaybackRate!=='function'||!Number.isFinite(value)||value<.07||value>16)return;
        try{
            const rates=player.getAvailablePlaybackRates?.();
            if(Array.isArray(rates)&&rates.length){
                const low=Math.min(...rates),high=Math.max(...rates);
                player.setPlaybackRate(Math.max(low,Math.min(high,value)));
                // YouTube's menu may cap its API at 2×. Babinium's controls
                // still request the chosen rate on the underlying media.
                if(value<low||value>high)media.playbackRate=value;
            }else{
                // If the player has not exposed its range yet, still honor
                // the browser's requested media rate.
                player.setPlaybackRate(value);media.playbackRate=value;
            }
            event.preventDefault();
        }catch(_){}
    },true);
})();
