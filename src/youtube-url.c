/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "youtube-url.h"
#include <glib.h>
#include <string.h>

static gboolean is_video_id(const char *id){
    if(!id||strlen(id)!=11)return FALSE;
    for(const char *p=id;*p;p++)if(!g_ascii_isalnum(*p)&&*p!='_'&&*p!='-')return FALSE;
    return TRUE;
}

static gboolean domain_is(const char *host,const char *domain){
    if(!g_ascii_strcasecmp(host,domain))return TRUE;
    gsize h=strlen(host),d=strlen(domain);
    return h>d&&host[h-d-1]=='.'&&!g_ascii_strcasecmp(host+h-d,domain);
}

gboolean youtube_site_url(const char *uri){
    GUri *u=g_uri_parse(uri?uri:"",G_URI_FLAGS_PARSE_RELAXED,NULL);
    if(!u)return FALSE;
    const char *scheme=g_uri_get_scheme(u),*host=g_uri_get_host(u);
    gboolean yes=scheme&&host&&(!g_ascii_strcasecmp(scheme,"http")||!g_ascii_strcasecmp(scheme,"https"))&&
        (domain_is(host,"youtube.com")||domain_is(host,"youtube-nocookie.com")||domain_is(host,"youtu.be"));
    g_uri_unref(u);return yes;
}

gboolean youtube_media_url(const char *uri){
    GUri *u=g_uri_parse(uri?uri:"",G_URI_FLAGS_PARSE_RELAXED,NULL);
    if(!u)return FALSE;
    const char *host=g_uri_get_host(u),*path=g_uri_get_path(u);
    gboolean yes=host&&(domain_is(host,"googlevideo.com")||
        (domain_is(host,"youtube.com")&&path&&g_str_has_prefix(path,"/api/manifest/")));
    g_uri_unref(u);return yes;
}

char *youtube_video_url(const char *uri){
    GUri *u=g_uri_parse(uri?uri:"",G_URI_FLAGS_PARSE_RELAXED|G_URI_FLAGS_ENCODED_QUERY,NULL);
    if(!u)return NULL;
    const char *scheme=g_uri_get_scheme(u),*host=g_uri_get_host(u),*path=g_uri_get_path(u),*query=g_uri_get_query(u);
    char *id=NULL,*result=NULL;
    if(!scheme||!host||!path||(g_ascii_strcasecmp(scheme,"http")&&g_ascii_strcasecmp(scheme,"https")))goto done;
    gboolean youtube=domain_is(host,"youtube.com"),nocookie=domain_is(host,"youtube-nocookie.com");
    if(youtube&&(!strcmp(path,"/watch")||!strcmp(path,"/watch/"))&&query){
        GHashTable *params=g_uri_parse_params(query,-1,"&",G_URI_PARAMS_WWW_FORM,NULL);
        if(params){id=g_strdup(g_hash_table_lookup(params,"v"));g_hash_table_unref(params);}
    }else{
        const char *candidate=NULL;
        if(domain_is(host,"youtu.be")&&path[0]=='/')candidate=path+1;
        else if(youtube||nocookie){
            const char *prefixes[]={"/shorts/","/live/","/embed/","/v/",NULL};
            for(guint i=0;prefixes[i];i++)if(g_str_has_prefix(path,prefixes[i])){candidate=path+strlen(prefixes[i]);break;}
        }
        if(candidate){id=g_strdup(candidate);gsize n=strlen(id);if(n&&id[n-1]=='/')id[n-1]='\0';}
    }
    if(is_video_id(id))result=g_strdup_printf("https://www.youtube.com/watch?v=%s",id);
done:
    g_free(id);g_uri_unref(u);return result;
}
