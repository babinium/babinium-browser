/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "site-name.h"
#include <gio/gio.h>
#include <libsoup/soup.h>
#include <string.h>

char *favorite_site_name(const char *uri){
    GUri *parsed=g_uri_parse(uri?uri:"",G_URI_FLAGS_PARSE_RELAXED,NULL);
    const char *source=parsed?g_uri_get_host(parsed):NULL;
    if(!source||!*source){if(parsed)g_uri_unref(parsed);return g_strdup("Sitio");}
    char *host=g_ascii_strdown(source,-1);
    g_uri_unref(parsed);
    gsize length=strlen(host);
    while(length&&host[length-1]=='.')host[--length]='\0';
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
