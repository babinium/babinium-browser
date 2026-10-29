// SPDX-License-Identifier: GPL-3.0-or-later
// Best-effort default for the full YouTube player, not an official YouTube API.
// Keep user changes possible and stop polling after the player is ready or 40 s.
(() => {
    if (!/(^|\.)youtube\.com$/.test(location.hostname) || window !== window.top) return;
    let timer = null;
    let lastVideo = '';
    let userChose = false;
    document.addEventListener('pointerdown', event => {
        if (event.isTrusted && event.target.closest?.('.ytp-settings-button, .ytp-panel-menu')) {
            userChose = true;
            try { document.getElementById('movie_player')?.setPlaybackQualityRange?.('small', 'highres'); } catch (_) {}
            if (timer) clearInterval(timer);
        }
    }, true);
    function applyDefault() {
        const video = new URL(location.href).searchParams.get('v') || '';
        if (!video || video === lastVideo || userChose) return;
        lastVideo = video;
        if (timer) clearInterval(timer);
        let attempts = 0;
        timer = setInterval(() => {
            const player = document.getElementById('movie_player');
            if (++attempts >= 80 || userChose) { clearInterval(timer); timer = null; return; }
            try {
                if (typeof player?.setPlaybackQualityRange !== 'function' || !player.getPlayerResponse?.()?.videoDetails) return;
                player.setPlaybackQualityRange('medium', 'medium'); // 360p when offered.
                clearInterval(timer); timer = null;
            } catch (_) { /* The player can be replaced while navigating. */ }
        }, 500);
    }
    document.addEventListener('yt-navigate-finish', applyDefault);
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', applyDefault, {once:true});
    else applyDefault();
})();
