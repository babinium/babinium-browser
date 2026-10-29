// No credentials are supplied; this only inspects the first sign-in page.
JSON.stringify({origin:location.origin,title:document.title,
    inputs:[...document.querySelectorAll('input')].map(i=>i.type),
    text:document.body?.innerText.slice(0,700)});
