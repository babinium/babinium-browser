// Diagnostic, run only in an isolated test profile on a local or public page.
(() => {
    const codecs={avc:'video/mp4; codecs="avc1.4d401e"',vp9:'video/webm; codecs="vp09.00.10.08"',av1:'video/mp4; codecs="av01.0.04M.08"'};
    Promise.all(Object.entries(codecs).map(async ([name,contentType]) => {
        try {
            const value=await navigator.mediaCapabilities.decodingInfo({type:'media-source',video:{contentType,width:640,height:360,bitrate:1000000,framerate:30}});
            return [name,{supported:value.supported,smooth:value.smooth,powerEfficient:value.powerEfficient,mse:MediaSource.isTypeSupported(contentType)}];
        } catch(e) { return [name,{error:String(e)}]; }
    })).then(items => {document.title='BB-CAPS:'+btoa(JSON.stringify(Object.fromEntries(items)));});
    return 'Waiting for codec capabilities';
})();
