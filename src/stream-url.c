/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "stream-url.h"
#include <glib.h>
#include <string.h>

/* Recognize HLS (.m3u8), DASH (.mpd) and IPTV playlist (.m3u) URLs, with or
 * without a query string. Sites like telelibre.st hand out these links for a
 * dedicated player; Babinium routes them to MPV instead of loading a page. */
gboolean media_stream_url(const char *uri){
    GUri *u=g_uri_parse(uri?uri:"",G_URI_FLAGS_PARSE_RELAXED|G_URI_FLAGS_ENCODED_QUERY,NULL);
    if(!u)return FALSE;
    const char *scheme=g_uri_get_scheme(u),*path=g_uri_get_path(u);
    gboolean yes=FALSE;
    if(scheme&&path&&(!g_ascii_strcasecmp(scheme,"http")||!g_ascii_strcasecmp(scheme,"https"))){
        static const char *suffixes[]={".m3u8",".mpd",".m3u",NULL};
        gsize n=strlen(path);
        for(guint i=0;suffixes[i];i++){
            gsize m=strlen(suffixes[i]);
            if(n>m&&!g_ascii_strcasecmp(path+n-m,suffixes[i])){yes=TRUE;break;}
        }
    }
    g_uri_unref(u);return yes;
}
