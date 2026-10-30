/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "../src/site-name.h"
#include <glib.h>

static void check(const char *uri,const char *expected){
    char *name=favorite_site_name(uri);
    g_assert_cmpstr(name,==,expected);
    g_free(name);
}

static void test_domains(void){
    check("https://www.youtube.com/watch?v=example","youtube");
    check("https://music.youtube.com/playlist?list=example","youtube");
    check("https://es.wikipedia.org/wiki/Example","wikipedia");
    check("https://news.bbc.co.uk/path","bbc");
    check("https://www.google.com.ar/search?q=example","google");
    check("https://project.github.io/path","project");
    check("https://www.xn--bcher-kva.de/","bücher");
    check("https://www.youtube.com@evil.com/path","evil");
    check("https://YouTube.com./path","youtube");
}

static void test_local_and_invalid(void){
    check("http://localhost:1234/private/path","localhost");
    check("http://127.0.0.1:8080/private/path","127.0.0.1");
    check("http://[::1]:8080/private/path","::1");
    check("http://www.intranet.internal/private/path","intranet.internal");
    check(NULL,"Sitio");
    check("not a URL","Sitio");
}

int main(int argc,char **argv){
    g_test_init(&argc,&argv,NULL);
    g_test_add_func("/favorite-site/domains",test_domains);
    g_test_add_func("/favorite-site/local-and-invalid",test_local_and_invalid);
    return g_test_run();
}
