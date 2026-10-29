// SPDX-License-Identifier: GPL-3.0-or-later
// Runs in an isolated WebKitScriptWorld. No page can call __bbQuery.
const seenClasses=new Set(), seenIds=new Set(), installed=new Set();
let pending=[], timer=0, style;
const stats={generic:0,procedural:0,unsupported:0};
function css(selectors) {
    const fresh=selectors.filter(s=>!installed.has(s));
    if(!fresh.length)return;
    if(!document.documentElement){pending.push(document);schedule();return;}
    if(!style){style=document.createElement('style');document.documentElement.append(style);}
    for(const s of fresh){
        // Separate rules: one unsupported selector must not invalidate the rest.
        try{style.sheet.insertRule(`${s}{display:none!important}`,style.sheet.cssRules.length);installed.add(s);}catch{}
    }
}
function regex(arg) {
    if(arg.startsWith('/')&&arg.lastIndexOf('/')>0){const i=arg.lastIndexOf('/');return new RegExp(arg.slice(1,i),arg.slice(i+1));}
    return {test:s=>s.includes(arg)};
}
function select(rule) {
    let nodes=[document];
    for(const op of rule.selector){
        const a=op.arg;
        switch(op.type){
        case 'css-selector':nodes=nodes.flatMap(n=>[...n.querySelectorAll(a)]);break;
        case 'has-text':{const r=regex(a);nodes=nodes.filter(n=>r.test(n.textContent));break;}
        case 'min-text-length':nodes=nodes.filter(n=>n.textContent.length>=Number(a));break;
        case 'matches-path':if(!regex(a).test(location.pathname+location.search))return [];break;
        case 'upward':nodes=nodes.map(n=>{if(/^\d+$/.test(a)){for(let i=0;i<Number(a)&&n;i++)n=n.parentElement;return n;}return n.parentElement?.closest(a);}).filter(Boolean);break;
        case 'matches-css':case 'matches-css-before':case 'matches-css-after':{
            const i=a.indexOf(':');if(i<0)return [];const key=a.slice(0,i).trim(),r=regex(a.slice(i+1).trim());
            nodes=nodes.filter(n=>r.test(getComputedStyle(n,op.type==='matches-css'?null:op.type==='matches-css-before'?'::before':'::after').getPropertyValue(key)));break;}
        case 'matches-attr':{const m=a.match(/^([^=]+)(?:=(.*))?$/);if(!m)return [];nodes=nodes.filter(n=>n.hasAttribute(m[1])&&(!m[2]||regex(m[2]).test(n.getAttribute(m[1]))));break;}
        case 'xpath':nodes=nodes.flatMap(n=>{const r=document.evaluate(a,n,null,XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,null),out=[];for(let i=0;i<Math.min(r.snapshotLength,2000);i++)out.push(r.snapshotItem(i));return out;});break;
        default:stats.unsupported++;return [];
        }
        if(nodes.length>4000)nodes=nodes.slice(0,4000);
    }
    return nodes.filter(n=>n.nodeType===1);
}
const procedural=(config.procedural_actions||[]).flatMap(s=>{try{return [JSON.parse(s)];}catch{return [];}});
function actions() {
    const start=performance.now();
    for(const r of procedural){
        if(performance.now()-start>12)break;
        try{for(const n of select(r)){
            const a=r.action||{type:'style',arg:'display:none!important'};
            if(a.type==='remove')n.remove();
            else if(a.type==='style'){
                for(const prop of a.arg.split(';')){const i=prop.indexOf(':');if(i<0)continue;const k=prop.slice(0,i).trim(),v=prop.slice(i+1).replace(/!important\s*$/,'').trim();if(n.style.getPropertyValue(k)!==v)n.style.setProperty(k,v,'important');}
            }else if(a.type==='remove-attr')n.removeAttribute(a.arg);
            else if(a.type==='remove-class')n.classList.remove(a.arg);
            stats.procedural++;
        }}catch{stats.unsupported++;}
    }
}
function scan() {
    timer=0;
    const classes=[],ids=[];
    let count=0;
    const visit=n=>{
        if(n.nodeType!==1)return;
        for(const c of n.classList)if(!seenClasses.has(c)&&seenClasses.size<20000){seenClasses.add(c);classes.push(c);}
        if(n.id&&!seenIds.has(n.id)&&seenIds.size<20000){seenIds.add(n.id);ids.push(n.id);}
    };
    const nodes=pending;pending=[];
    for(const root of nodes){
        visit(root);
        const walk=document.createTreeWalker(root,NodeFilter.SHOW_ELEMENT);
        let n;while((n=walk.nextNode())&&count++<5000)visit(n);
        if(count>=5000)break;
    }
    if(!config.generichide){
        for(let i=0;i<Math.max(classes.length,ids.length);i+=1000){
            try{const s=JSON.parse(__bbQuery(JSON.stringify(classes.slice(i,i+1000)),JSON.stringify(ids.slice(i,i+1000))));css(s);stats.generic+=s.length;}catch{}
        }
    }
    css(config.hide_selectors||[]);actions();
}
function schedule(){if(!timer)timer=setTimeout(scan,100);}
new MutationObserver(records=>{
    for(const r of records){
        if(pending.length>=512)break;
        if(r.type==='attributes')pending.push(r.target);
        else for(const n of r.addedNodes)if(n.nodeType===1&&n!==style&&pending.length<512)pending.push(n);
    }
    if(pending.length)schedule();
}).observe(document,{childList:true,subtree:true,attributes:true,attributeFilter:['class','id']});
pending.push(document);schedule();
