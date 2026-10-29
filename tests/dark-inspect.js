// Test-only inspection of the rendered page; no account data is collected.
JSON.stringify({url:location.origin,background:getComputedStyle(document.body).backgroundColor,
    darkStyles:document.querySelectorAll('style.darkreader').length,
    darkPreference:matchMedia('(prefers-color-scheme: dark)').matches});
