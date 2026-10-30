// SPDX-License-Identifier: GPL-3.0-or-later
// Suspend indefinitely repeating CSS animations far outside the viewport.
// Events and IntersectionObserver do the work; there is no continuous polling.
(() => {
    'use strict';
    if (!window.IntersectionObserver || !window.CSSAnimation || !document.getAnimations) return;

    const targets = new Map();
    const marker = 'data-babinium-offscreen-animation';
    const token = Math.random().toString(36).slice(2);
    const maxTargets = 256;
    let cleanupTimer = 0, style = null;

    function eligible(target) {
        const animations = target.getAnimations().filter(a => a instanceof CSSAnimation &&
            a.playState !== 'idle' && a.playState !== 'finished');
        // A CSS rule affects every CSS animation on the element. Leave mixed
        // finite/infinite targets alone so finite animations can complete.
        return animations.length > 0 && animations.every(a => a.effect?.getTiming().iterations === Infinity);
    }
    function release(target) {
        if (target.getAttribute(marker) === token) target.removeAttribute(marker);
    }
    function suspend(target) {
        if (target.hasAttribute(marker) && target.getAttribute(marker) !== token) return;
        if (!style || !style.isConnected) {
            style = document.createElement('style');
            const selector = `[${marker}="${token}"]`;
            style.textContent = `${selector},${selector}::before,${selector}::after{animation-play-state:paused!important}`;
            (document.head || document.documentElement).appendChild(style);
        }
        target.setAttribute(marker, token);
    }
    function forget(target) {
        if (!targets.has(target)) return;
        release(target);
        observer.unobserve(target);
        targets.delete(target);
        if (!targets.size) mutationObserver.disconnect();
    }
    function prune() {
        cleanupTimer = 0;
        for (const target of targets.keys()) {
            if (!target.isConnected || !eligible(target)) forget(target);
        }
    }
    function queuePrune() {
        if (!cleanupTimer) cleanupTimer = setTimeout(prune, 250);
    }
    const observer = new IntersectionObserver(entries => {
        for (const entry of entries) {
            const target = entry.target, state = targets.get(target);
            if (!state) continue;
            if (!target.isConnected || !eligible(target)) { forget(target); continue; }
            state.visible = entry.isIntersecting;
            if (state.visible) release(target);
            else suspend(target);
        }
    }, {rootMargin: '100%'});
    // Disconnected targets can otherwise remain observed. Coalesce removal
    // bursts and recheck tracked elements when their own class/style changes.
    const mutationObserver = new MutationObserver(records => {
        if (records.some(record => record.removedNodes?.length ||
                (record.type === 'attributes' && targets.has(record.target)))) queuePrune();
    });
    function track(target) {
        if (!target || target.nodeType !== 1 || !target.isConnected || !target.getAnimations) return;
        if (!eligible(target)) { forget(target); return; }
        let state = targets.get(target);
        if (!state) {
            if (targets.size >= maxTargets) return;
            state = {visible: null};
            targets.set(target, state);
            if (targets.size === 1) mutationObserver.observe(document, {
                childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style']
            });
            observer.observe(target);
        } else if (state.visible === false) suspend(target);
    }
    document.addEventListener('animationstart', event => track(event.target), true);
    const ended = event => { if (targets.has(event.target)) queuePrune(); };
    document.addEventListener('animationend', ended, true);
    document.addEventListener('animationcancel', ended, true);
    const initial = () => {
        for (const animation of document.getAnimations()) {
            if (animation instanceof CSSAnimation) track(animation.effect?.target);
        }
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initial, {once: true});
    else initial();
})();
