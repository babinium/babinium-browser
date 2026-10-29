// Test-only: inspect labels in YouTube's settings without collecting account data.
(() => {
    const p=document.getElementById('movie_player'),v=document.querySelector('video');
    if(v){v.muted=true;p?.playVideo?.();v.play().catch(()=>{});}
    let count=0;const timer=setInterval(()=>{
        if(++count>55){clearInterval(timer);return;}
        const gear=document.querySelector('.ytp-settings-button')?.getBoundingClientRect();
        const items=[...document.querySelectorAll('.ytp-menuitem')].filter(e=>e.offsetWidth&&e.offsetHeight)
            .map(e=>({label:e.querySelector('.ytp-menuitem-label')?.textContent?.trim(),checked:e.getAttribute('aria-checked')}));
        const data=JSON.stringify({viewport:[innerWidth,innerHeight],gear:gear?{x:gear.x,y:gear.y,w:gear.width,h:gear.height}:null,items});
        document.title='BBMENU:'+btoa(unescape(encodeURIComponent(data)));
    },1000);
    return 'Inspecting YouTube menu';
})();
