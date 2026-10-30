/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <webkit2/webkit-web-extension.h>
#include <jsc/jsc.h>
#include <json-glib/json-glib.h>
#include <libsoup/soup.h>
#include <gmodule.h>
#include "blocker.h"
#include "youtube-url.h"

static BbEngine *engine;
static char *index_path, *resources_path, *cosmetic_js;
static GHashTable *disabled;
static gboolean bypass, audit;
static WebKitScriptWorld *cosmetic_world;
typedef struct { WebKitWebPage *page; guint64 checked, blocked, scripts; guint timer; char *top_uri; gboolean youtube; } Page;

static char *hostname(const char *url) {
    GUri *u=g_uri_parse(url ? url : "",G_URI_FLAGS_PARSE_RELAXED,NULL);
    char *s=u ? g_ascii_strdown(g_uri_get_host(u) ? g_uri_get_host(u) : "",-1) : g_strdup("");
    if(u) g_uri_unref(u); return s;
}
static gboolean enabled(WebKitWebPage *page) {
    if(bypass || !engine) return FALSE;
    char *host=hostname(webkit_web_page_get_uri(page));
    gboolean yes=!g_hash_table_contains(disabled,host); g_free(host); return yes;
}
static void set_disabled(const char *text) {
    g_hash_table_remove_all(disabled);
    char **lines=g_strsplit(text,"\n",-1);
    for(char **p=lines;*p;p++) if(**p) g_hash_table_add(disabled,g_strdup(*p));
    g_strfreev(lines);
}
static gboolean report(gpointer data) {
    Page *p=data; p->timer=0;
    WebKitUserMessage *m=webkit_user_message_new("bb-stats",g_variant_new("(tttb)",p->checked,p->blocked,p->scripts,engine!=NULL));
    webkit_web_page_send_message_to_view(p->page,m,NULL,NULL,NULL); return G_SOURCE_REMOVE;
}
static void changed(Page *p) { if(!p->timer) p->timer=g_timeout_add(400,report,p); }
static void free_page(gpointer data) { Page *p=data; if(p->timer)g_source_remove(p->timer);g_free(p->top_uri);g_free(p); }

/* send-request has no public resource/frame type. Prefer Fetch Metadata, then
 * headers/suffix. Unknown requests remain 'other'; do not match all types. */
static const char *request_type(WebKitWebPage *page,WebKitURIRequest *req) {
    const char *url=webkit_uri_request_get_uri(req);
    SoupMessageHeaders *h=webkit_uri_request_get_http_headers(req);
    const char *d=h?soup_message_headers_get_one(h,"Sec-Fetch-Dest"):NULL;
    if(d) {
        if(!strcmp(d,"script")||!strcmp(d,"worker")||!strcmp(d,"sharedworker"))return "script";
        if(!strcmp(d,"style"))return "stylesheet";
        if(!strcmp(d,"iframe")||!strcmp(d,"frame"))return "subdocument";
        if(!strcmp(d,"video")||!strcmp(d,"audio"))return "media";
        if(!strcmp(d,"image"))return "image";
        if(!strcmp(d,"font"))return "font";
        if(!strcmp(d,"document"))return "document";
        if(!strcmp(d,"empty"))return "xmlhttprequest";
    }
    if(!g_strcmp0(url,webkit_web_page_get_uri(page)))return "document";
    const char *accept=h?soup_message_headers_get_one(h,"Accept"):NULL;
    if(accept && g_str_has_prefix(accept,"image/"))return "image";
    if(accept && strstr(accept,"text/css"))return "stylesheet";
    if(accept && strstr(accept,"application/json"))return "xmlhttprequest";
    GUri *u=g_uri_parse(url,G_URI_FLAGS_PARSE_RELAXED,NULL);
    char *path=g_ascii_strdown(u&&g_uri_get_path(u)?g_uri_get_path(u):"",-1);
    const char *type="other";
    if(g_str_has_suffix(path,".js")||g_str_has_suffix(path,".mjs"))type="script";
    else if(g_str_has_suffix(path,".css"))type="stylesheet";
    else if(g_str_has_suffix(path,".woff2")||g_str_has_suffix(path,".woff")||g_str_has_suffix(path,".ttf"))type="font";
    else if(g_str_has_suffix(path,".jpg")||g_str_has_suffix(path,".png")||g_str_has_suffix(path,".gif")||g_str_has_suffix(path,".webp")||g_str_has_suffix(path,".svg"))type="image";
    else if(g_str_has_suffix(path,".mp4")||g_str_has_suffix(path,".webm")||strstr(url,".googlevideo.com/"))type="media";
    else if(strstr(path,"/youtubei/")||strstr(path,"/api/stats/")||strstr(path,"/pagead/"))type="xmlhttprequest";
    g_free(path);if(u)g_uri_unref(u);return type;
}
static gboolean send_request(WebKitWebPage *page,WebKitURIRequest *req,WebKitURIResponse *response,Page *p) {
    (void)response;
    const char *url=webkit_uri_request_get_uri(req),*top=webkit_web_page_get_uri(page);
    if(!url||(!g_str_has_prefix(url,"http://")&&!g_str_has_prefix(url,"https://")))return FALSE;
    if(g_strcmp0(top,p->top_uri)){g_free(p->top_uri);p->top_uri=g_strdup(top);p->youtube=youtube_site_url(top);}
    /* Only the YouTube page is affected. MPV's own traffic is independent. */
    if(p->youtube&&youtube_media_url(url))return TRUE;
    if(!enabled(page))return FALSE;
    SoupMessageHeaders *h=webkit_uri_request_get_http_headers(req);
    const char *ref=h?soup_message_headers_get_one(h,"Referer"):NULL;
    const char *type=request_type(page,req);
    char *redirect=NULL;
    int result=bb_check(engine,url,ref?ref:(top?top:url),type,webkit_uri_request_get_http_method(req),&redirect);
    p->checked++;
    if(result==1||result==2) {
        p->blocked++;
        if(audit) {
            WebKitUserMessage *m=webkit_user_message_new("bb-block",g_variant_new("(ssi)",url,type,result));
            webkit_web_page_send_message_to_view(page,m,NULL,NULL,NULL);
        }
    }
    changed(p);
    /* WebKit accepts URI changes here. Redirects are local data resources only. */
    if(result==2 && redirect && g_str_has_prefix(redirect,"data:"))webkit_uri_request_set_uri(req,redirect);
    if(result==3 && redirect)webkit_uri_request_set_uri(req,redirect);
    bb_string_free(redirect);
    return result==1;
}
static gboolean message(WebKitWebPage *page,WebKitUserMessage *msg,Page *p) {
    (void)page;
    const char *name=webkit_user_message_get_name(msg);
    if(!strcmp(name,"bb-settings")) {
        const char *s;g_variant_get(webkit_user_message_get_parameters(msg),"(&s)",&s);set_disabled(s);return TRUE;
    }
    if(!strcmp(name,"bb-reload")) {
        const char *path;g_variant_get(webkit_user_message_get_parameters(msg),"(&s)",&path);
        BbEngine *next=bb_engine_load(path,resources_path);
        if(next){bb_engine_free(engine);engine=next;g_free(index_path);index_path=g_strdup(path);}
        changed(p);return TRUE;
    }
    return FALSE;
}
static char *generic_query(const char *classes,const char *ids,gpointer uri) {
    char *r=bb_generic(engine,uri,classes,ids); char *copy=g_strdup(r?r:"[]");bb_string_free(r);return copy;
}
static void evaluate(JSCContext *ctx,const char *code) {
    JSCValue *v=jsc_context_evaluate(ctx,code,-1);g_object_unref(v);
    if(jsc_context_get_exception(ctx)) {
        if(audit)g_printerr("babinium script: %s\n",jsc_exception_get_message(jsc_context_get_exception(ctx)));
        jsc_context_clear_exception(ctx);
    }
}
static void window_cleared(WebKitScriptWorld *world,WebKitWebPage *page,WebKitFrame *frame,gpointer unused) {
    (void)world;(void)unused;
    Page *p=g_object_get_data(G_OBJECT(page),"bb-page");
    if(!enabled(page))return;
    const char *uri=webkit_frame_get_uri(frame);
    /* Inherit the parent's origin for local about:blank/srcdoc frames. */
    if(!uri||!g_str_has_prefix(uri,"http"))uri=webkit_web_page_get_uri(page);
    if(!uri)return;
    char *json=bb_cosmetics(engine,uri);
    if(!json)return;
    JsonParser *parser=json_parser_new();
    if(json_parser_load_from_data(parser,json,-1,NULL)) {
        JsonObject *obj=json_node_get_object(json_parser_get_root(parser));
        const char *script=json_object_get_string_member_with_default(obj,"injected_script","");
        if(*script) {
            JSCContext *ctx=webkit_frame_get_js_context(frame);
            char *code=g_strconcat("(()=>{const scriptletGlobals=new Map();\n",script,"\n})();",NULL);
            evaluate(ctx,code);g_free(code);g_object_unref(ctx);p->scripts++;
        }
        /* Native query function exists only in the isolated cosmetic world. */
        JSCContext *ctx=webkit_frame_get_js_context_for_script_world(frame,cosmetic_world);
        JSCValue *fn=jsc_value_new_function(ctx,"__bbQuery",G_CALLBACK(generic_query),g_strdup(uri),g_free,G_TYPE_STRING,2,G_TYPE_STRING,G_TYPE_STRING);
        jsc_context_set_value(ctx,"__bbQuery",fn);g_object_unref(fn);
        char *code=g_strconcat("(()=>{const config=",json,";\n",cosmetic_js,"\n})();",NULL);
        evaluate(ctx,code);g_free(code);g_object_unref(ctx);
    }
    g_object_unref(parser);bb_string_free(json);changed(p);
}
static void page_created(WebKitWebExtension *ext,WebKitWebPage *page,gpointer unused) {
    (void)ext;(void)unused;
    Page *p=g_new0(Page,1);p->page=page;
    g_object_set_data_full(G_OBJECT(page),"bb-page",p,free_page);
    g_signal_connect(page,"send-request",G_CALLBACK(send_request),p);
    g_signal_connect(page,"user-message-received",G_CALLBACK(message),p);changed(p);
}
G_MODULE_EXPORT void webkit_web_extension_initialize_with_user_data(WebKitWebExtension *ext,const GVariant *data) {
    const char *idx,*res,*runtime,*sites;
    g_variant_get((GVariant*)data,"(&s&s&s&sbb)",&idx,&res,&runtime,&sites,&bypass,&audit);
    index_path=g_strdup(idx);resources_path=g_strdup(res);
    disabled=g_hash_table_new_full(g_str_hash,g_str_equal,g_free,NULL);set_disabled(sites);
    g_file_get_contents(runtime,&cosmetic_js,NULL,NULL);
    if(!cosmetic_js)cosmetic_js=g_strdup("");
    if(!bypass)engine=bb_engine_load(index_path,resources_path);
    if(!bypass&&!engine){char *dir=g_path_get_dirname(resources_path),*fallback=g_build_filename(dir,"engine.bin",NULL);engine=bb_engine_load(fallback,resources_path);g_free(fallback);g_free(dir);}
    cosmetic_world=webkit_script_world_new_with_name("babinium-cosmetics");
    g_signal_connect(ext,"page-created",G_CALLBACK(page_created),NULL);
    g_signal_connect(webkit_script_world_get_default(),"window-object-cleared",G_CALLBACK(window_cleared),NULL);
}
