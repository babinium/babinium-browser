/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "site-name.h"
#include <gio/gio.h>
#include <libsoup/soup.h>
#include <string.h>

static char *uri_host(const char *uri){
    GUri *parsed=g_uri_parse(uri?uri:"",G_URI_FLAGS_PARSE_RELAXED,NULL);
    const char *source=parsed?g_uri_get_host(parsed):NULL;
    char *host=g_ascii_strdown(source?source:"",-1);
    if(parsed)g_uri_unref(parsed);
    gsize length=strlen(host);
    while(length&&host[length-1]=='.')host[--length]='\0';
    return host;
}

static gboolean starts_with_host(const char *title,const char *host){
    gsize n=strlen(host);
    return n&&!g_ascii_strncasecmp(title,host,n)&&(!title[n]||strchr("/?#:",title[n]));
}

gboolean favorite_title_is_address(const char *title,const char *uri){
    if(!title||!*title)return FALSE;
    if(!g_ascii_strncasecmp(title,"http://",7)||!g_ascii_strncasecmp(title,"https://",8)||!g_ascii_strncasecmp(title,"www.",4))return TRUE;
    char *host=uri_host(uri);
    const char *bare=g_str_has_prefix(host,"www.")?host+4:host;
    gboolean address=starts_with_host(title,host)||starts_with_host(title,bare);
    g_free(host);return address;
}

char *favorite_site_name(const char *uri){
    char *host=uri_host(uri);
    if(!*host){g_free(host);return g_strdup("Sitio");}
    if(g_hostname_is_ip_address(host))return host;

    /* libsoup already depends on the system public-suffix list. */
    const char *base=soup_tld_get_base_domain(host,NULL);
    char *name;
    if(base){const char *dot=strchr(base,'.');name=dot?g_strndup(base,dot-base):g_strdup(base);}
    else name=g_strdup(g_str_has_prefix(host,"www.")&&host[4]?host+4:host);
    g_free(host);
    char *unicode=g_hostname_to_unicode(name);
    if(unicode){g_free(name);name=unicode;}
    return name;
}
