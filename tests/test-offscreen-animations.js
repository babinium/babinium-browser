// SPDX-License-Identifier: GPL-3.0-or-later
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync('data/offscreen-animations.js', 'utf8');
const marker = 'data-babinium-offscreen-animation';

function fixture(build) {
    const handlers = new Map(), timers = [], observers = {};
    class CSSAnimation {
        constructor(target, iterations = Infinity, state = 'running') {
            this.effect = {target, getTiming: () => ({iterations})};
            this.playState = state;
        }
        pause() { throw Error('Must preserve CSS control of play state'); }
        play() { throw Error('Must preserve CSS control of play state'); }
    }
    class IntersectionObserver {
        constructor(callback, options) { this.callback = callback; this.options = options; this.targets = new Set(); observers.intersection = this; }
        observe(target) { this.targets.add(target); }
        unobserve(target) { this.targets.delete(target); }
        fire(target, visible) { this.callback([{target, isIntersecting: visible}]); }
    }
    class MutationObserver {
        constructor(callback) { this.callback = callback; this.active = false; observers.mutation = this; }
        observe() { this.active = true; }
        disconnect() { this.active = false; }
        removed() { this.callback([{removedNodes: [{}]}]); }
        changed(target) { this.callback([{type: 'attributes', target}]); }
    }
    const target = () => ({
        nodeType: 1, isConnected: true, animations: [], attributes: new Map(),
        getAnimations() { return this.animations; },
        hasAttribute(name) { return this.attributes.has(name); },
        getAttribute(name) { return this.attributes.get(name) ?? null; },
        setAttribute(name, value) { this.attributes.set(name, value); },
        removeAttribute(name) { this.attributes.delete(name); },
    });
    const content = build({target, CSSAnimation});
    const document = {
        readyState: 'complete',
        head: {appendChild: element => { element.isConnected = true; }},
        createElement: () => ({isConnected: false}),
        getAnimations: () => content.animations,
        addEventListener: (name, fn) => handlers.set(name, fn),
    };
    const context = {document, CSSAnimation, IntersectionObserver, MutationObserver,
        setTimeout: fn => { timers.push(fn); return timers.length; }};
    context.window = context;
    vm.createContext(context);
    vm.runInContext(code, context);
    return {...content, observers, handlers, timers, CSSAnimation};
}

test('suspend only infinite CSS animations outside the margin and restore authored state', () => {
    const f = fixture(({target, CSSAnimation}) => {
        const far = target(), near = target(), finite = target(), alreadyPaused = target();
        const inf = new CSSAnimation(far), shown = new CSSAnimation(near);
        const oneShot = new CSSAnimation(finite, 1), paused = new CSSAnimation(alreadyPaused, Infinity, 'paused');
        for (const a of [inf, shown, oneShot, paused]) a.effect.target.animations.push(a);
        return {far, near, finite, alreadyPaused, inf, shown, oneShot, paused, animations: [inf, shown, oneShot, paused]};
    });
    const io = f.observers.intersection;
    assert.equal(io.options.rootMargin, '100%');
    assert.equal(io.targets.has(f.finite), false);
    io.fire(f.near, true);
    io.fire(f.far, false);
    io.fire(f.alreadyPaused, false);
    assert.equal(f.far.hasAttribute(marker), true);
    assert.equal(f.near.hasAttribute(marker), false);
    assert.equal(f.finite.hasAttribute(marker), false);
    io.fire(f.far, true);
    io.fire(f.alreadyPaused, true);
    assert.equal(f.far.hasAttribute(marker), false);
    assert.equal(f.paused.playState, 'paused');
    assert.equal(f.timers.length, 0);
});

test('mixed finite animations and newly removed targets regain normal CSS behavior', () => {
    const f = fixture(({target, CSSAnimation}) => {
        const node = target(), animation = new CSSAnimation(node);
        node.animations.push(animation);
        return {node, animation, animations: []};
    });
    const io = f.observers.intersection;
    f.handlers.get('animationstart')({target: f.node});
    assert.equal(f.observers.mutation.active, true);
    io.fire(f.node, false);
    assert.equal(f.node.hasAttribute(marker), true);
    f.node.animations.push(new f.CSSAnimation(f.node, 1));
    f.observers.mutation.changed(f.node);
    f.timers.shift()();
    assert.equal(f.node.hasAttribute(marker), false);
    assert.equal(io.targets.size, 0);
    assert.equal(f.observers.mutation.active, false);

    f.node.animations.pop();
    f.handlers.get('animationstart')({target: f.node});
    io.fire(f.node, false);
    f.node.isConnected = false;
    f.observers.mutation.removed();
    f.timers.shift()();
    assert.equal(io.targets.size, 0);
    assert.equal(f.node.hasAttribute(marker), false);
});

test('cap tracked elements on animation-heavy pages', () => {
    const f = fixture(({target, CSSAnimation}) => {
        const animations = Array.from({length: 300}, () => {
            const node = target(), animation = new CSSAnimation(node);
            node.animations.push(animation);
            return animation;
        });
        return {animations};
    });
    assert.equal(f.observers.intersection.targets.size, 256);
});
