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
        try{player.setPlaybackRate(value);event.preventDefault();}catch(_){}
    },true);
})();
