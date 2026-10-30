/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <gtk/gtk.h>
#include <webkit2/webkit2.h>
#include <json-glib/json-glib.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "site-name.h"

typedef struct Tab { GtkWidget *view,*label,*box,*placeholder,*help; guint64 checked,blocked,scripts; gboolean engine_ok,engine_seen; } Tab;
static GtkWidget *window,*root,*toolbar,*address,*notebook,*back,*forward,*reload_btn,*shield,*dark_button,*favorite_button,*favorites_box,*favorites_pop,*favorites_scroll,*downloads_box,*downloads_pop,*list_status;
static WebKitWebContext *context;
static WebKitUserContentManager *content;
static GHashTable *disabled,*light_sites;
static GKeyFile *favorites;
static GPtrArray *tabs;
static char *profile,*data_dir,*ext_dir,*bin_dir,*index_path,*sites_path,*light_path,*favorites_path,*filters_dir;
static char *opt_profile,*opt_data,*opt_telemetry,*opt_eval,*opt_screenshot;
static int quit_after,eval_after=10,snapshot_after=15,probe_interval;
static gboolean no_block,no_update,autoplay,audit,updating,setting_shield,setting_dark,favorites_readonly;
static gint64 start_time;
static FILE *telemetry;
static guint mapped_once,frame_once;
static void ensure_context(void);
static void attach_view(Tab *t,WebKitWebView *related);
static void install_scripts(void);
static void toggle_favorite(GtkButton *button,gpointer unused);
static void extension_init(WebKitWebContext *ctx,gpointer unused);
static void extension_data(WebKitWebContext *ctx);

static Tab *current(void){int n=gtk_notebook_get_current_page(GTK_NOTEBOOK(notebook));return n<0?NULL:g_object_get_data(G_OBJECT(gtk_notebook_get_nth_page(GTK_NOTEBOOK(notebook),n)),"tab");}
static void log_event(const char *event,const char *value) {
    if(!telemetry)return;
    JsonBuilder *b=json_builder_new();json_builder_begin_object(b);
    json_builder_set_member_name(b,"event");json_builder_add_string_value(b,event);
    json_builder_set_member_name(b,"elapsed_ms");json_builder_add_double_value(b,(g_get_monotonic_time()-start_time)/1000.0);
    json_builder_set_member_name(b,"monotonic_us");json_builder_add_int_value(b,g_get_monotonic_time());
    json_builder_set_member_name(b,"value");json_builder_add_string_value(b,value?value:"");
    json_builder_end_object(b);JsonGenerator *g=json_generator_new();JsonNode *n=json_builder_get_root(b);json_generator_set_root(g,n);
    char *s=json_generator_to_data(g,NULL);fprintf(telemetry,"%s\n",s);fflush(telemetry);
    g_free(s);json_node_free(n);g_object_unref(g);g_object_unref(b);
}
static char *host_of(const char *uri){GUri *u=g_uri_parse(uri?uri:"",G_URI_FLAGS_PARSE_RELAXED,NULL);char *h=g_ascii_strdown(u&&g_uri_get_host(u)?g_uri_get_host(u):"",-1);if(u)g_uri_unref(u);return h;}
static gboolean site_enabled(Tab *t){if(!t->view)return !no_block;char *h=host_of(webkit_web_view_get_uri(WEBKIT_WEB_VIEW(t->view)));gboolean yes=!no_block&&!g_hash_table_contains(disabled,h);g_free(h);return yes;}
static char *hash_text(GHashTable *table){GString *s=g_string_new("");GHashTableIter it;gpointer key;g_hash_table_iter_init(&it,table);while(g_hash_table_iter_next(&it,&key,NULL)){g_string_append(s,key);g_string_append_c(s,'\n');}return g_string_free(s,FALSE);}
static char *sites_text(void){return hash_text(disabled);}
static void file_error(const char *what,GError *err){GtkWidget *dialog=gtk_message_dialog_new(GTK_WINDOW(window),GTK_DIALOG_MODAL,GTK_MESSAGE_ERROR,GTK_BUTTONS_CLOSE,"%s: %s",what,err?err->message:"error desconocido");gtk_dialog_run(GTK_DIALOG(dialog));gtk_widget_destroy(dialog);}
static char *favorite_id(const char *uri){return g_compute_checksum_for_string(G_CHECKSUM_SHA256,uri,-1);}
static gboolean bookmarkable(const char *uri){return uri&&(g_str_has_prefix(uri,"http://")||g_str_has_prefix(uri,"https://"));}
static gboolean favorite_has(const char *uri){if(!bookmarkable(uri))return FALSE;char *id=favorite_id(uri);gboolean found=g_key_file_has_group(favorites,id);g_free(id);return found;}
static void refresh_extra(Tab *t){
    const char *uri=t&&t->view?webkit_web_view_get_uri(WEBKIT_WEB_VIEW(t->view)):NULL;char *h=host_of(uri);
    gtk_widget_set_sensitive(favorite_button,bookmarkable(uri));gtk_button_set_label(GTK_BUTTON(favorite_button),favorite_has(uri)?"★":"☆");
    gtk_widget_set_tooltip_text(favorite_button,favorite_has(uri)?"Quitar de favoritos (Ctrl+D)":"Guardar en favoritos (Ctrl+D)");
    gtk_widget_set_sensitive(dark_button,*h!=0);setting_dark=TRUE;gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(dark_button),!g_hash_table_contains(light_sites,h));setting_dark=FALSE;
    gtk_button_set_label(GTK_BUTTON(dark_button),g_hash_table_contains(light_sites,h)?"Claro":"Oscuro");g_free(h);
}
static void sync_sites(void){char *text=sites_text();g_file_set_contents(sites_path,text,-1,NULL);for(guint i=0;i<tabs->len;i++){Tab *t=g_ptr_array_index(tabs,i);if(t->view)webkit_web_view_send_message_to_page(WEBKIT_WEB_VIEW(t->view),webkit_user_message_new("bb-settings",g_variant_new("(s)",text)),NULL,NULL,NULL);}g_free(text);if(context)extension_data(context);}
static void refresh_controls(void) {
    Tab *t=current();if(!t)return;refresh_extra(t);
    if(!t->view){
        if(!gtk_widget_has_focus(address))gtk_entry_set_text(GTK_ENTRY(address),"");
        gtk_widget_set_sensitive(back,FALSE);gtk_widget_set_sensitive(forward,FALSE);gtk_widget_set_sensitive(reload_btn,FALSE);gtk_widget_set_sensitive(shield,FALSE);
        setting_shield=TRUE;gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(shield),!no_block);setting_shield=FALSE;
        gtk_button_set_label(GTK_BUTTON(shield),no_block?"Sin bloqueo":"Bloqueo activado");gtk_window_set_title(GTK_WINDOW(window),t->help?"Ayuda de Babinium":"Nueva pestaña — Babinium");return;
    }
    gtk_widget_set_sensitive(reload_btn,TRUE);gtk_widget_set_sensitive(shield,!no_block);
    WebKitWebView *v=WEBKIT_WEB_VIEW(t->view);
    const char *uri=webkit_web_view_get_uri(v),*title=webkit_web_view_get_title(v);
    if(!gtk_widget_has_focus(address))gtk_entry_set_text(GTK_ENTRY(address),uri?uri:"");
    gtk_widget_set_sensitive(back,webkit_web_view_can_go_back(v));gtk_widget_set_sensitive(forward,webkit_web_view_can_go_forward(v));
    gtk_button_set_label(GTK_BUTTON(reload_btn),webkit_web_view_is_loading(v)?"Detener":"Recargar");
    char *s=g_strdup_printf("%s — Babinium",title?title:"Nueva pestaña");gtk_window_set_title(GTK_WINDOW(window),s);g_free(s);
    gboolean on=site_enabled(t);setting_shield=TRUE;gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(shield),on);setting_shield=FALSE;
    s=g_strdup_printf("%s · %"G_GUINT64_FORMAT,on?(t->engine_ok?"Bloqueo":t->engine_seen?"Error bloqueo":"Iniciando"):"Sin bloqueo",t->blocked);
    gtk_button_set_label(GTK_BUTTON(shield),s);g_free(s);
    gtk_widget_set_tooltip_text(shield,"Activar o desactivar el bloqueo para este sitio (Ctrl+B). Se recarga la pestaña.");
}
static void go(Tab *t,const char *input) {
    char *text=g_strdup(input);g_strstrip(text);if(!*text){g_free(text);return;}
    char *url;
    const char *scheme=g_uri_peek_scheme(text);
    if(scheme&&(strstr(text,"://")||g_ascii_strcasecmp(scheme,"about")==0||g_ascii_strcasecmp(scheme,"file")==0||g_ascii_strcasecmp(scheme,"data")==0))url=g_strdup(text);
    else if(strchr(text,' ')||(scheme&&!g_ascii_isdigit(strchr(text,':')[1]))||(!strchr(text,'.')&&!strchr(text,':')&&strcmp(text,"localhost"))){char *q=g_uri_escape_string(text,NULL,TRUE);url=g_strconcat("https://www.google.com/search?q=",q,NULL);g_free(q);}
    else url=g_strconcat("https://",text,NULL);
    if(strcmp(url,"about:blank")||t->view){if(!t->view)attach_view(t,NULL);webkit_web_view_load_uri(WEBKIT_WEB_VIEW(t->view),url);}
    g_free(url);g_free(text);
}
static void entry_activate(GtkEntry *e,gpointer unused){(void)unused;Tab *t=current();if(t){go(t,gtk_entry_get_text(e));if(t->view)gtk_widget_grab_focus(t->view);}}
static void title_changed(GObject *obj,GParamSpec *ps,Tab *t){(void)ps;const char *s=webkit_web_view_get_title(WEBKIT_WEB_VIEW(obj));gtk_label_set_text(GTK_LABEL(t->label),s?s:"Nueva pestaña");if(t==current())refresh_controls();}
static void changed(GObject *obj,GParamSpec *ps,Tab *t){(void)obj;(void)ps;if(t==current())refresh_controls();}
static void load_changed(WebKitWebView *v,WebKitLoadEvent event,Tab *t){
    if(event==WEBKIT_LOAD_STARTED)log_event("load_started",webkit_web_view_get_uri(v));
    if(event==WEBKIT_LOAD_COMMITTED)log_event("load_committed",webkit_web_view_get_uri(v));
    if(event==WEBKIT_LOAD_FINISHED)log_event("load_finished",webkit_web_view_get_uri(v));
    if(t==current())refresh_controls();
}
static gboolean load_failed(WebKitWebView *v,WebKitLoadEvent event,const char *uri,GError *e,Tab *t){(void)v;(void)event;(void)uri;(void)t;log_event("load_failed",e->message);return FALSE;}
static gboolean policy(WebKitWebView *v,WebKitPolicyDecision *d,WebKitPolicyDecisionType type,gpointer unused){
    (void)v;(void)unused;
    if(type==WEBKIT_POLICY_DECISION_TYPE_RESPONSE&&!webkit_response_policy_decision_is_mime_type_supported(WEBKIT_RESPONSE_POLICY_DECISION(d))){webkit_policy_decision_download(d);return TRUE;}
    return FALSE;
}
static gboolean page_message(WebKitWebView *v,WebKitUserMessage *m,Tab *t){
    (void)v;const char *name=webkit_user_message_get_name(m);
    if(!strcmp(name,"bb-stats")){
        g_variant_get(webkit_user_message_get_parameters(m),"(tttb)",&t->checked,&t->blocked,&t->scripts,&t->engine_ok);
        t->engine_seen=TRUE;
        char *s=g_strdup_printf("{\"checked\":%"G_GUINT64_FORMAT",\"blocked\":%"G_GUINT64_FORMAT",\"script_batches\":%"G_GUINT64_FORMAT",\"engine\":%s}",t->checked,t->blocked,t->scripts,t->engine_ok?"true":"false");log_event("block_stats",s);g_free(s);if(t==current())refresh_controls();return TRUE;
    }
    if(!strcmp(name,"bb-block")){char *s=g_variant_print(webkit_user_message_get_parameters(m),FALSE);log_event("blocked_request",s);g_free(s);return TRUE;}
    return FALSE;
}
static void close_tab(GtkWidget *button,Tab *t){
    (void)button;int n=gtk_notebook_page_num(GTK_NOTEBOOK(notebook),t->box);if(n<0)return;
    g_ptr_array_remove(tabs,t);gtk_notebook_remove_page(GTK_NOTEBOOK(notebook),n);g_free(t);
    if(!tabs->len)gtk_widget_destroy(window);else refresh_controls();
}
static Tab *new_tab(const char *uri,gboolean select);
static void popup_ready(WebKitWebView *v,Tab *t){gtk_widget_show(GTK_WIDGET(v));int n=gtk_notebook_page_num(GTK_NOTEBOOK(notebook),t->box);if(n>=0)gtk_notebook_set_current_page(GTK_NOTEBOOK(notebook),n);}
static WebKitWebView *create_view(WebKitWebView *v,WebKitNavigationAction *action,gpointer unused){(void)action;(void)unused;Tab *t=new_tab(NULL,FALSE);attach_view(t,v);gtk_widget_hide(t->view);g_signal_connect(t->view,"ready-to-show",G_CALLBACK(popup_ready),t);return WEBKIT_WEB_VIEW(t->view);}
static void web_close(WebKitWebView *v,Tab *t){(void)v;close_tab(NULL,t);}
static gboolean fullscreen_enter(WebKitWebView *v,gpointer unused){(void)v;(void)unused;gtk_widget_hide(toolbar);gtk_notebook_set_show_tabs(GTK_NOTEBOOK(notebook),FALSE);gtk_window_fullscreen(GTK_WINDOW(window));return FALSE;}
static gboolean fullscreen_leave(WebKitWebView *v,gpointer unused){(void)v;(void)unused;gtk_widget_show(toolbar);gtk_notebook_set_show_tabs(GTK_NOTEBOOK(notebook),TRUE);gtk_window_unfullscreen(GTK_WINDOW(window));return FALSE;}
static void terminated(WebKitWebView *v,WebKitWebProcessTerminationReason reason,Tab *t){(void)v;(void)t;char *s=g_strdup_printf("Proceso web terminado (%d); recargá la pestaña",reason);log_event("web_process_terminated",s);gtk_window_set_title(GTK_WINDOW(window),s);g_free(s);}
static void attach_view(Tab *t,WebKitWebView *related){
    ensure_context();
    if(t->placeholder){gtk_widget_destroy(t->placeholder);t->placeholder=NULL;}
    if(t->help){gtk_widget_destroy(t->help);t->help=NULL;}
    t->view=related?webkit_web_view_new_with_related_view(related):GTK_WIDGET(g_object_new(WEBKIT_TYPE_WEB_VIEW,"web-context",context,"user-content-manager",content,NULL));
    GdkRGBA black={0,0,0,1};webkit_web_view_set_background_color(WEBKIT_WEB_VIEW(t->view),&black);
    WebKitSettings *s=webkit_web_view_get_settings(WEBKIT_WEB_VIEW(t->view));
    webkit_settings_set_enable_developer_extras(s,audit);
    webkit_settings_set_media_playback_requires_user_gesture(s,!autoplay);
    if(autoplay)webkit_web_view_set_is_muted(WEBKIT_WEB_VIEW(t->view),TRUE);
    webkit_settings_set_enable_page_cache(s,FALSE); /* Avoid retained back/forward DOMs. */
    webkit_settings_set_enable_dns_prefetching(s,FALSE);
    webkit_settings_set_javascript_can_open_windows_automatically(s,FALSE);
    gtk_box_pack_start(GTK_BOX(t->box),t->view,TRUE,TRUE,0);
    g_signal_connect(t->view,"notify::title",G_CALLBACK(title_changed),t);
    g_signal_connect(t->view,"notify::uri",G_CALLBACK(changed),t);
    g_signal_connect(t->view,"notify::is-loading",G_CALLBACK(changed),t);
    g_signal_connect(t->view,"load-changed",G_CALLBACK(load_changed),t);
    g_signal_connect(t->view,"load-failed",G_CALLBACK(load_failed),t);
    g_signal_connect(t->view,"decide-policy",G_CALLBACK(policy),NULL);
    g_signal_connect(t->view,"user-message-received",G_CALLBACK(page_message),t);
    g_signal_connect(t->view,"create",G_CALLBACK(create_view),NULL);g_signal_connect(t->view,"close",G_CALLBACK(web_close),t);
    g_signal_connect(t->view,"enter-fullscreen",G_CALLBACK(fullscreen_enter),NULL);g_signal_connect(t->view,"leave-fullscreen",G_CALLBACK(fullscreen_leave),NULL);
    g_signal_connect(t->view,"web-process-terminated",G_CALLBACK(terminated),t);
    gtk_widget_show_all(t->box);
}
static Tab *new_tab(const char *uri,gboolean select){
    Tab *t=g_new0(Tab,1);t->box=gtk_box_new(GTK_ORIENTATION_VERTICAL,0);gtk_widget_set_name(t->box,"bb-empty-tab");
    t->placeholder=gtk_label_new("Nueva pestaña");gtk_box_pack_start(GTK_BOX(t->box),t->placeholder,TRUE,TRUE,0);
    GtkWidget *header=gtk_box_new(GTK_ORIENTATION_HORIZONTAL,3);t->label=gtk_label_new("Nueva pestaña");
    gtk_label_set_ellipsize(GTK_LABEL(t->label),PANGO_ELLIPSIZE_END);gtk_label_set_width_chars(GTK_LABEL(t->label),18);gtk_label_set_max_width_chars(GTK_LABEL(t->label),24);
    GtkWidget *close=gtk_button_new_with_label("×");gtk_button_set_relief(GTK_BUTTON(close),GTK_RELIEF_NONE);
    gtk_box_pack_start(GTK_BOX(header),t->label,TRUE,TRUE,0);gtk_box_pack_start(GTK_BOX(header),close,FALSE,FALSE,0);gtk_widget_show_all(header);
    g_object_set_data(G_OBJECT(t->box),"tab",t);g_ptr_array_add(tabs,t);
    int n=gtk_notebook_append_page(GTK_NOTEBOOK(notebook),t->box,header);gtk_notebook_set_tab_reorderable(GTK_NOTEBOOK(notebook),t->box,TRUE);
    g_signal_connect(close,"clicked",G_CALLBACK(close_tab),t);
    gtk_widget_show_all(t->box);if(select)gtk_notebook_set_current_page(GTK_NOTEBOOK(notebook),n);
    if(uri)go(t,uri);
    return t;
}
static void switch_page(GtkNotebook *n,GtkWidget *page,guint num,gpointer unused){(void)n;(void)page;(void)num;(void)unused;Tab *t=current();const char *uri=t&&t->view?webkit_web_view_get_uri(WEBKIT_WEB_VIEW(t->view)):NULL;gtk_entry_set_text(GTK_ENTRY(address),uri?uri:"");refresh_controls();}
static void navigate(GtkButton *b,gpointer which){(void)b;Tab *t=current();if(!t||!t->view)return;WebKitWebView *v=WEBKIT_WEB_VIEW(t->view);switch(GPOINTER_TO_INT(which)){case 0:webkit_web_view_go_back(v);break;case 1:webkit_web_view_go_forward(v);break;default:if(webkit_web_view_is_loading(v))webkit_web_view_stop_loading(v);else webkit_web_view_reload(v);}}
static void add_tab(GtkButton *b,gpointer unused){(void)b;(void)unused;new_tab("about:blank",TRUE);gtk_entry_set_text(GTK_ENTRY(address),"");gtk_widget_grab_focus(address);}
static void open_help(GtkButton *button,gpointer unused){
    (void)button;(void)unused;
    Tab *t=new_tab(NULL,TRUE);if(t->placeholder){gtk_widget_destroy(t->placeholder);t->placeholder=NULL;}
    t->help=gtk_scrolled_window_new(NULL,NULL);gtk_widget_set_name(t->help,"bb-help");
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(t->help),GTK_POLICY_NEVER,GTK_POLICY_AUTOMATIC);
    GtkWidget *body=gtk_box_new(GTK_ORIENTATION_VERTICAL,16);gtk_container_set_border_width(GTK_CONTAINER(body),28);
    gtk_widget_set_halign(body,GTK_ALIGN_CENTER);gtk_widget_set_valign(body,GTK_ALIGN_START);
    GtkWidget *heading=gtk_label_new(NULL);gtk_label_set_markup(GTK_LABEL(heading),"<span size='xx-large' weight='bold'>Babinium</span>");
    gtk_label_set_xalign(GTK_LABEL(heading),0);gtk_box_pack_start(GTK_BOX(body),heading,FALSE,FALSE,0);
    GtkWidget *subtitle=gtk_label_new(NULL);gtk_label_set_markup(GTK_LABEL(subtitle),"<span size='large' weight='bold'>Controles de velocidad</span>");
    gtk_label_set_xalign(GTK_LABEL(subtitle),0);gtk_box_pack_start(GTK_BOX(body),subtitle,FALSE,FALSE,0);
    GtkWidget *grid=gtk_grid_new();gtk_grid_set_column_spacing(GTK_GRID(grid),24);gtk_grid_set_row_spacing(GTK_GRID(grid),10);
    static const char *rows[][2]={
        {"S / D","Reducir / aumentar la velocidad en 0,1×"},
        {"R","Volver a la velocidad normal (1×)"},
        {"G","Alternar entre 1,8× y la velocidad anterior"},
        {"Z / X","Retroceder / avanzar 10 segundos"},
        {"M / J","Guardar una marca / volver a ella"},
        {"V","Mostrar o esconder el indicador de velocidad"}
    };
    for(guint i=0;i<G_N_ELEMENTS(rows);i++){
        GtkWidget *key=gtk_label_new(rows[i][0]),*description=gtk_label_new(rows[i][1]);
        gtk_widget_set_name(key,"bb-help-key");gtk_label_set_xalign(GTK_LABEL(key),0);gtk_label_set_xalign(GTK_LABEL(description),0);
        gtk_label_set_line_wrap(GTK_LABEL(description),TRUE);gtk_grid_attach(GTK_GRID(grid),key,0,i,1,1);gtk_grid_attach(GTK_GRID(grid),description,1,i,1,1);
    }
    gtk_box_pack_start(GTK_BOX(body),grid,FALSE,FALSE,0);
    GtkWidget *note=gtk_label_new("Los atajos controlan el video o audio activo y no se aplican mientras escribís.\nSi el reproductor está incrustado, hacé clic en él para darle el foco.\nAlgunos reproductores o contenidos pueden limitar la velocidad.");
    gtk_label_set_line_wrap(GTK_LABEL(note),TRUE);gtk_label_set_xalign(GTK_LABEL(note),0);gtk_box_pack_start(GTK_BOX(body),note,FALSE,FALSE,0);
    gtk_container_add(GTK_CONTAINER(t->help),body);gtk_box_pack_start(GTK_BOX(t->box),t->help,TRUE,TRUE,0);
    gtk_label_set_text(GTK_LABEL(t->label),"Ayuda de Babinium");gtk_widget_show_all(t->help);refresh_controls();
}
static void toggle_block(GtkToggleButton *button,gpointer unused){
    (void)unused;if(setting_shield)return;Tab *t=current();if(!t||!t->view)return;char *h=host_of(webkit_web_view_get_uri(WEBKIT_WEB_VIEW(t->view)));
    if(!*h){g_free(h);refresh_controls();return;}
    if(gtk_toggle_button_get_active(button))g_hash_table_remove(disabled,h);else g_hash_table_add(disabled,g_strdup(h));
    g_free(h);sync_sites();webkit_web_view_reload(WEBKIT_WEB_VIEW(t->view));refresh_controls();
}
static void toggle_dark(GtkToggleButton *button,gpointer unused){
    (void)unused;if(setting_dark)return;Tab *t=current();if(!t||!t->view)return;char *h=host_of(webkit_web_view_get_uri(WEBKIT_WEB_VIEW(t->view)));
    if(!*h){g_free(h);refresh_controls();return;}
    gboolean on=gtk_toggle_button_get_active(button);
    if(on)g_hash_table_remove(light_sites,h);else g_hash_table_add(light_sites,g_strdup(h));
    char *text=hash_text(light_sites);GError *err=NULL;
    if(!g_file_set_contents(light_path,text,-1,&err)){
        if(on)g_hash_table_add(light_sites,g_strdup(h));else g_hash_table_remove(light_sites,h);
        file_error("No se pudo guardar la preferencia de modo oscuro",err);g_clear_error(&err);
    }else{install_scripts();webkit_web_view_reload(WEBKIT_WEB_VIEW(t->view));}
    g_free(text);g_free(h);refresh_controls();
}
static gboolean save_favorites(const char *before){
    GError *err=NULL;if(favorites_readonly){g_key_file_load_from_data(favorites,before,-1,G_KEY_FILE_NONE,NULL);file_error("El archivo de favoritos no se puede leer y no será sobrescrito",NULL);return FALSE;}if(g_key_file_save_to_file(favorites,favorites_path,&err))return TRUE;
    g_key_file_load_from_data(favorites,before,-1,G_KEY_FILE_NONE,NULL);file_error("No se pudieron guardar los favoritos",err);g_clear_error(&err);return FALSE;
}
static void toggle_favorite(GtkButton *button,gpointer unused){
    (void)button;(void)unused;Tab *t=current();if(!t||!t->view)return;WebKitWebView *v=WEBKIT_WEB_VIEW(t->view);
    const char *uri=webkit_web_view_get_uri(v);if(!bookmarkable(uri))return;char *id=favorite_id(uri),*before=g_key_file_to_data(favorites,NULL,NULL);
    if(g_key_file_has_group(favorites,id))g_key_file_remove_group(favorites,id,NULL);
    else{const char *title=webkit_web_view_get_title(v);g_key_file_set_string(favorites,id,"uri",uri);g_key_file_set_string(favorites,id,"title",title&&*title?title:uri);}
    save_favorites(before);g_free(before);g_free(id);refresh_controls();
}
static void favorites_rebuild(void);
static void favorite_open(GtkButton *b,gpointer unused){(void)unused;char *uri=g_strdup(g_object_get_data(G_OBJECT(b),"uri"));gtk_popover_popdown(GTK_POPOVER(favorites_pop));Tab *t=current();if(t)go(t,uri);g_free(uri);}
static void favorite_remove(GtkButton *b,gpointer unused){
    (void)unused;char *id=g_strdup(g_object_get_data(G_OBJECT(b),"id")),*before=g_key_file_to_data(favorites,NULL,NULL);
    g_key_file_remove_group(favorites,id,NULL);save_favorites(before);g_free(before);g_free(id);refresh_controls();favorites_rebuild();
}
static void favorites_rebuild(void){
    GList *children=gtk_container_get_children(GTK_CONTAINER(favorites_box));for(GList *i=children;i;i=i->next)gtk_widget_destroy(GTK_WIDGET(i->data));g_list_free(children);
    gsize n=0;char **groups=g_key_file_get_groups(favorites,&n);
    if(!n)gtk_box_pack_start(GTK_BOX(favorites_box),gtk_label_new("Todavía no hay favoritos"),FALSE,FALSE,0);
    for(gsize i=0;i<n;i++){
        char *uri=g_key_file_get_string(favorites,groups[i],"uri",NULL),*title=g_key_file_get_string(favorites,groups[i],"title",NULL);
        if(!bookmarkable(uri)){g_free(uri);g_free(title);continue;}
        char *site=favorite_site_name(uri),*clean=g_strdup(title?title:"");g_strstrip(clean);
        gboolean title_is_url=!g_ascii_strncasecmp(clean,"http://",7)||!g_ascii_strncasecmp(clean,"https://",8);
        const char *shown=*clean&&!title_is_url?clean:site;
        GtkWidget *row=gtk_box_new(GTK_ORIENTATION_HORIZONTAL,3),*open=gtk_button_new(),*remove=gtk_button_new_with_label("×");
        GtkWidget *content=gtk_box_new(GTK_ORIENTATION_VERTICAL,2),*label=gtk_label_new(shown);
        gtk_label_set_xalign(GTK_LABEL(label),0);gtk_label_set_line_wrap(GTK_LABEL(label),TRUE);
        gtk_label_set_line_wrap_mode(GTK_LABEL(label),PANGO_WRAP_WORD_CHAR);gtk_label_set_width_chars(GTK_LABEL(label),1);gtk_label_set_max_width_chars(GTK_LABEL(label),70);
        gtk_widget_set_hexpand(label,TRUE);gtk_box_pack_start(GTK_BOX(content),label,FALSE,FALSE,0);
        if(g_ascii_strcasecmp(shown,site)){
            GtkWidget *site_label=gtk_label_new(site);gtk_label_set_xalign(GTK_LABEL(site_label),0);
            gtk_box_pack_start(GTK_BOX(content),site_label,FALSE,FALSE,0);
        }
        gtk_container_add(GTK_CONTAINER(open),content);
        gtk_widget_set_tooltip_text(open,shown);gtk_widget_set_tooltip_text(remove,"Quitar de favoritos");
        g_object_set_data_full(G_OBJECT(open),"uri",g_strdup(uri),g_free);g_object_set_data_full(G_OBJECT(remove),"id",g_strdup(groups[i]),g_free);
        g_signal_connect(open,"clicked",G_CALLBACK(favorite_open),NULL);g_signal_connect(remove,"clicked",G_CALLBACK(favorite_remove),NULL);
        gtk_box_pack_start(GTK_BOX(row),open,TRUE,TRUE,0);gtk_box_pack_start(GTK_BOX(row),remove,FALSE,FALSE,0);gtk_box_pack_start(GTK_BOX(favorites_box),row,FALSE,FALSE,0);
        g_free(site);g_free(clean);g_free(uri);g_free(title);
    }
    g_strfreev(groups);gtk_widget_show_all(favorites_box);
}
static void favorites_show(GtkWidget *w,gpointer unused){
    (void)w;(void)unused;
    int width=MAX(80,MIN(620,gtk_widget_get_allocated_width(window)-32));
    int height=MAX(100,MIN(480,gtk_widget_get_allocated_height(window)-120));
    gtk_widget_set_size_request(favorites_scroll,width,-1);
    gtk_scrolled_window_set_max_content_height(GTK_SCROLLED_WINDOW(favorites_scroll),height);
    favorites_rebuild();
}
typedef struct {WebKitDownload *download;GtkWidget *progress,*cancel;} Download;
static void cancel_download(GtkButton *b,Download *d){(void)b;webkit_download_cancel(d->download);}
static void download_progress(GObject *o,GParamSpec *ps,Download *d){(void)ps;gtk_progress_bar_set_fraction(GTK_PROGRESS_BAR(d->progress),webkit_download_get_estimated_progress(WEBKIT_DOWNLOAD(o)));}
static void download_done(WebKitDownload *w,Download *d){(void)w;gtk_widget_set_sensitive(d->cancel,FALSE);gtk_progress_bar_set_fraction(GTK_PROGRESS_BAR(d->progress),1);g_object_unref(d->download);g_free(d);}
static void download_failed(WebKitDownload *w,GError *e,Download *d){(void)w;gtk_progress_bar_set_text(GTK_PROGRESS_BAR(d->progress),e->message);log_event("download_failed",e->message);}
static gboolean destination(WebKitDownload *w,const char *suggested,Download *d){
    char *base=g_path_get_basename(suggested&&*suggested?suggested:"descarga");const char *dir=g_get_user_special_dir(G_USER_DIRECTORY_DOWNLOAD);if(!dir)dir=g_get_home_dir();
    char *path=g_build_filename(dir,base,NULL);for(int n=1;g_file_test(path,G_FILE_TEST_EXISTS);n++){g_free(path);path=g_strdup_printf("%s/%d-%s",dir,n,base);}
    char *uri=g_filename_to_uri(path,NULL,NULL);webkit_download_set_destination(w,uri);gtk_progress_bar_set_text(GTK_PROGRESS_BAR(d->progress),base);
    log_event("download_destination",path);g_free(uri);g_free(path);g_free(base);return TRUE;
}
static void download_started(WebKitWebContext *ctx,WebKitDownload *w,gpointer unused){
    (void)ctx;(void)unused;Download *d=g_new0(Download,1);d->download=g_object_ref(w);
    GtkWidget *row=gtk_box_new(GTK_ORIENTATION_HORIZONTAL,6);d->progress=gtk_progress_bar_new();gtk_progress_bar_set_show_text(GTK_PROGRESS_BAR(d->progress),TRUE);gtk_widget_set_size_request(d->progress,280,-1);d->cancel=gtk_button_new_with_label("Cancelar");
    gtk_box_pack_start(GTK_BOX(row),d->progress,TRUE,TRUE,0);gtk_box_pack_start(GTK_BOX(row),d->cancel,FALSE,FALSE,0);gtk_box_pack_start(GTK_BOX(downloads_box),row,FALSE,FALSE,0);gtk_widget_show_all(row);gtk_popover_popup(GTK_POPOVER(downloads_pop));
    g_signal_connect(d->cancel,"clicked",G_CALLBACK(cancel_download),d);g_signal_connect(w,"decide-destination",G_CALLBACK(destination),d);g_signal_connect(w,"notify::estimated-progress",G_CALLBACK(download_progress),d);g_signal_connect(w,"failed",G_CALLBACK(download_failed),d);g_signal_connect(w,"finished",G_CALLBACK(download_done),d);
}
static void updater_finished(GObject *o,GAsyncResult *res,gpointer unused){
    (void)unused;GError *error=NULL;gboolean ok=g_subprocess_wait_check_finish(G_SUBPROCESS(o),res,&error);updating=FALSE;
    log_event(ok?"lists_updated":"lists_update_failed",error?error->message:"");
    gtk_label_set_text(GTK_LABEL(list_status),ok?"Listas verificadas · actualización automática cada 6 h":"Falló la actualización · se conservan las listas anteriores");
    if(ok){char *idx=g_build_filename(filters_dir,"current","engine.bin",NULL);if(g_file_test(idx,G_FILE_TEST_IS_REGULAR)){g_free(index_path);index_path=g_strdup(idx);if(context)extension_data(context);for(guint i=0;i<tabs->len;i++){Tab *t=g_ptr_array_index(tabs,i);if(t->view)webkit_web_view_send_message_to_page(WEBKIT_WEB_VIEW(t->view),webkit_user_message_new("bb-reload",g_variant_new("(s)",idx)),NULL,NULL,NULL);}}g_free(idx);}
    g_clear_error(&error);g_object_unref(o);
}
static gboolean update_lists(gpointer force){
    if(updating||no_update||no_block)return G_SOURCE_REMOVE;
    char *helper=g_build_filename(bin_dir,"babinium-filter-update",NULL);char *compiler=g_build_filename(bin_dir,"babinium-filter",NULL);
    GError *err=NULL;GSubprocess *p=g_subprocess_new(G_SUBPROCESS_FLAGS_NONE,&err,helper,"--cache",filters_dir,"--data",data_dir,"--compiler",compiler,force?"--force":"--if-due",NULL);
    if(p){updating=TRUE;gtk_label_set_text(GTK_LABEL(list_status),"Actualizando listas en segundo plano…");g_subprocess_wait_check_async(p,NULL,updater_finished,NULL);}else{log_event("lists_update_failed",err->message);gtk_label_set_text(GTK_LABEL(list_status),"No se pudo iniciar la actualización");g_clear_error(&err);}g_free(helper);g_free(compiler);return G_SOURCE_REMOVE;
}
static gboolean update_tick(gpointer unused){(void)unused;update_lists(NULL);return G_SOURCE_CONTINUE;}
static void manual_update(GtkButton *b,gpointer unused){(void)b;(void)unused;update_lists(GINT_TO_POINTER(1));}
static gboolean key_press(GtkWidget *w,GdkEventKey *e,gpointer unused){
    (void)w;(void)unused;Tab *t=current();guint k=gdk_keyval_to_lower(e->keyval);gboolean ctrl=e->state&GDK_CONTROL_MASK;
    if(ctrl){switch(k){case GDK_KEY_l:gtk_widget_grab_focus(address);gtk_editable_select_region(GTK_EDITABLE(address),0,-1);return TRUE;
    case GDK_KEY_t:add_tab(NULL,NULL);return TRUE;case GDK_KEY_w:if(t)close_tab(NULL,t);return TRUE;
    case GDK_KEY_r:if(t&&t->view){if(e->state&GDK_SHIFT_MASK)webkit_web_view_reload_bypass_cache(WEBKIT_WEB_VIEW(t->view));else webkit_web_view_reload(WEBKIT_WEB_VIEW(t->view));}return TRUE;
    case GDK_KEY_b:if(t&&t->view&&!no_block)gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(shield),!gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(shield)));return TRUE;
    case GDK_KEY_m:if(e->state&GDK_SHIFT_MASK){if(t&&t->view)gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(dark_button),!gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(dark_button)));return TRUE;}break;
    case GDK_KEY_d:if(e->state&GDK_SHIFT_MASK)gtk_popover_popup(GTK_POPOVER(favorites_pop));else toggle_favorite(NULL,NULL);return TRUE;case GDK_KEY_j:gtk_popover_popup(GTK_POPOVER(downloads_pop));return TRUE;
    case GDK_KEY_ISO_Left_Tab:case GDK_KEY_Tab:{int n=gtk_notebook_get_current_page(GTK_NOTEBOOK(notebook)),count=gtk_notebook_get_n_pages(GTK_NOTEBOOK(notebook));gtk_notebook_set_current_page(GTK_NOTEBOOK(notebook),(n+((e->state&GDK_SHIFT_MASK)?count-1:1))%count);return TRUE;}
    default:if(k>=GDK_KEY_1&&k<=GDK_KEY_9){gtk_notebook_set_current_page(GTK_NOTEBOOK(notebook),k==GDK_KEY_9?-1:(int)(k-GDK_KEY_1));return TRUE;}}}
    if((e->state&GDK_MOD1_MASK)&&k==GDK_KEY_Left){navigate(NULL,GINT_TO_POINTER(0));return TRUE;}
    if((e->state&GDK_MOD1_MASK)&&k==GDK_KEY_Right){navigate(NULL,GINT_TO_POINTER(1));return TRUE;}
    if(k==GDK_KEY_F5){navigate(NULL,GINT_TO_POINTER(2));return TRUE;}
    return FALSE;
}
static gboolean mapped(GtkWidget *w,GdkEvent *e,gpointer unused){(void)w;(void)e;(void)unused;if(!mapped_once++){log_event("ui_mapped","");}return FALSE;}
static gboolean drawn(GtkWidget *w,cairo_t *cr,gpointer unused){(void)w;(void)cr;(void)unused;if(!frame_once++)log_event("ui_first_draw","");return FALSE;}
static gboolean quit_timer(gpointer unused){(void)unused;gtk_widget_destroy(window);return G_SOURCE_REMOVE;}
static void eval_result(GObject *o,GAsyncResult *res,gpointer unused){(void)unused;GError *e=NULL;JSCValue *v=webkit_web_view_evaluate_javascript_finish(WEBKIT_WEB_VIEW(o),res,&e);if(v){char *s=jsc_value_to_string(v);log_event("javascript",s);g_free(s);g_object_unref(v);}else log_event("javascript_error",e?e->message:"");g_clear_error(&e);}
static gboolean eval_timer(gpointer unused){(void)unused;Tab *t=current();char *s=NULL;if(t&&t->view&&opt_eval&&g_file_get_contents(opt_eval,&s,NULL,NULL)){webkit_web_view_evaluate_javascript(WEBKIT_WEB_VIEW(t->view),s,-1,NULL,NULL,NULL,eval_result,NULL);g_free(s);}return G_SOURCE_REMOVE;}
static gboolean probe(gpointer unused){(void)unused;Tab *t=current();if(t&&t->view)webkit_web_view_evaluate_javascript(WEBKIT_WEB_VIEW(t->view),"JSON.stringify({url:location.href,title:document.title,ready:document.readyState,video:[...document.querySelectorAll('video')].map(v=>({time:v.currentTime,duration:v.duration,paused:v.paused,ready:v.readyState,width:v.videoWidth,height:v.videoHeight,frames:v.getVideoPlaybackQuality?.().totalVideoFrames,dropped:v.getVideoPlaybackQuality?.().droppedVideoFrames,error:v.error?.message})),codecs:document.getElementById('movie_player')?.getStatsForNerds?.()?.codecs,ad:!!document.querySelector('.ad-showing,.ad-interrupting'),error:document.querySelector('.ytp-error-content-wrap')?.innerText,playability:window.ytInitialPlayerResponse?.playabilityStatus?.status})",-1,NULL,NULL,NULL,eval_result,NULL);return G_SOURCE_CONTINUE;}
static gboolean screenshot(gpointer unused){(void)unused;GdkWindow *gw=gtk_widget_get_window(window);int width=gtk_widget_get_allocated_width(window),height=gtk_widget_get_allocated_height(window);GdkPixbuf *p=gdk_pixbuf_get_from_window(gw,0,0,width,height);if(p){GError *e=NULL;gdk_pixbuf_save(p,opt_screenshot,"png",&e,NULL);log_event("screenshot",e?e->message:opt_screenshot);g_clear_error(&e);g_object_unref(p);}return G_SOURCE_REMOVE;}
static GtkWidget *button(const char *label,GCallback cb,gpointer data){GtkWidget *b=gtk_button_new_with_label(label);g_signal_connect(b,"clicked",cb,data);gtk_box_pack_start(GTK_BOX(toolbar),b,FALSE,FALSE,0);return b;}
static void install_scripts(void){
    if(!content)return;
    static char *dark_js,*youtube_js,*ambient_js,*speed_js,*speed_youtube_js;
    static const char *youtube_uris[]={"http://youtube.com/*","https://youtube.com/*","http://*.youtube.com/*","https://*.youtube.com/*",NULL};
    static const char *speed_youtube_uris[]={"http://youtube.com/*","https://youtube.com/*","http://*.youtube.com/*","https://*.youtube.com/*","http://youtube-nocookie.com/*","https://youtube-nocookie.com/*","http://*.youtube-nocookie.com/*","https://*.youtube-nocookie.com/*",NULL};
    if(!dark_js){char *path=g_build_filename(data_dir,"darkreader.js",NULL);if(!g_file_get_contents(path,&dark_js,NULL,NULL))g_warning("Falta Dark Reader: %s",path);g_free(path);}
    if(!youtube_js){char *path=g_build_filename(data_dir,"youtube.js",NULL);if(!g_file_get_contents(path,&youtube_js,NULL,NULL))g_warning("Falta la preferencia de YouTube: %s",path);g_free(path);}
    if(!ambient_js){char *path=g_build_filename(data_dir,"youtube-ambient.js",NULL);if(!g_file_get_contents(path,&ambient_js,NULL,NULL))g_warning("Falta la preferencia de modo ambiente: %s",path);g_free(path);}
    if(!speed_js){char *path=g_build_filename(data_dir,"video-speed.js",NULL);if(!g_file_get_contents(path,&speed_js,NULL,NULL))g_warning("Falta el control de velocidad: %s",path);g_free(path);}
    if(!speed_youtube_js){char *path=g_build_filename(data_dir,"video-speed-youtube.js",NULL);if(!g_file_get_contents(path,&speed_youtube_js,NULL,NULL))g_warning("Falta el adaptador de velocidad de YouTube: %s",path);g_free(path);}
    webkit_user_content_manager_remove_all_scripts(content);
    if(dark_js){
        JsonBuilder *b=json_builder_new();json_builder_begin_array(b);GHashTableIter it;gpointer key;g_hash_table_iter_init(&it,light_sites);while(g_hash_table_iter_next(&it,&key,NULL))json_builder_add_string_value(b,key);json_builder_end_array(b);
        JsonNode *node=json_builder_get_root(b);JsonGenerator *gen=json_generator_new();json_generator_set_root(gen,node);char *list=json_generator_to_data(gen,NULL);
        char *script=g_strdup_printf("(function(){let host=location.hostname;try{host=window.top.location.hostname;}catch(e){try{if(document.referrer)host=new URL(document.referrer).hostname;}catch(_){}}if(%s.includes(host)||/(^|\\.)youtube\\.com$/.test(host))return;try{const bg=(e,fallback=255)=>{for(;e;e=e.parentElement){const p=getComputedStyle(e).backgroundColor.match(/[\\d.]+/g);if(p&&p.length>=3&&(p.length<4||Number(p[3])>=0.95))return 0.2126*Number(p[0])+0.7152*Number(p[1])+0.0722*Number(p[2]);}return fallback;};const points=[[.1,.1],[.5,.2],[.5,.5],[.2,.85],[.8,.85]],base=bg(document.body);if(document.body&&base<60&&points.every(([x,y])=>bg(document.elementFromPoint(innerWidth*x,innerHeight*y),base)<60))return;}catch(_){}\n%s\nDarkReader.enable({brightness:100,contrast:100,sepia:0});})();",list,dark_js);
        WebKitUserScript *u=webkit_user_script_new_for_world(script,WEBKIT_USER_CONTENT_INJECT_ALL_FRAMES,WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_END,"babinium-dark",NULL,youtube_uris);webkit_user_content_manager_add_script(content,u);webkit_user_script_unref(u);
        g_free(script);g_free(list);json_node_free(node);g_object_unref(gen);g_object_unref(b);
    }
    if(youtube_js){WebKitUserScript *u=webkit_user_script_new(youtube_js,WEBKIT_USER_CONTENT_INJECT_TOP_FRAME,WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_START,youtube_uris,NULL);webkit_user_content_manager_add_script(content,u);webkit_user_script_unref(u);}
    if(ambient_js){WebKitUserScript *u=webkit_user_script_new(ambient_js,WEBKIT_USER_CONTENT_INJECT_TOP_FRAME,WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_START,youtube_uris,NULL);webkit_user_content_manager_add_script(content,u);webkit_user_script_unref(u);}
    if(speed_youtube_js){WebKitUserScript *u=webkit_user_script_new(speed_youtube_js,WEBKIT_USER_CONTENT_INJECT_ALL_FRAMES,WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_START,speed_youtube_uris,NULL);webkit_user_content_manager_add_script(content,u);webkit_user_script_unref(u);}
    if(speed_js){WebKitUserScript *u=webkit_user_script_new_for_world(speed_js,WEBKIT_USER_CONTENT_INJECT_ALL_FRAMES,WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_START,"babinium-speed",NULL,NULL);webkit_user_content_manager_add_script(content,u);webkit_user_script_unref(u);}
}
static void extension_data(WebKitWebContext *ctx){
    char *res=g_build_filename(data_dir,"resources.json",NULL),*js=g_build_filename(data_dir,"cosmetic.js",NULL),*sites=sites_text();
    webkit_web_context_set_web_extensions_initialization_user_data(ctx,g_variant_new("(ssssbb)",index_path,res,js,sites,no_block,audit));g_free(res);g_free(js);g_free(sites);
}
static void extension_init(WebKitWebContext *ctx,gpointer unused){(void)unused;webkit_web_context_set_web_extensions_directory(ctx,ext_dir);extension_data(ctx);}
static void ensure_context(void){
    if(context)return;
    content=webkit_user_content_manager_new();install_scripts();
    char *cache=g_build_filename(profile,"cache",NULL),*storage=g_build_filename(profile,"web-data",NULL);
    WebKitWebsiteDataManager *dm=webkit_website_data_manager_new("base-data-directory",storage,"base-cache-directory",cache,NULL);context=webkit_web_context_new_with_website_data_manager(dm);g_object_unref(dm);g_free(cache);g_free(storage);
    webkit_web_context_set_sandbox_enabled(context,TRUE);
    webkit_web_context_add_path_to_sandbox(context,data_dir,TRUE);webkit_web_context_add_path_to_sandbox(context,filters_dir,TRUE);webkit_web_context_add_path_to_sandbox(context,ext_dir,TRUE);
    webkit_web_context_set_cache_model(context,WEBKIT_CACHE_MODEL_DOCUMENT_VIEWER);
    WebKitCookieManager *cookies=webkit_web_context_get_cookie_manager(context);char *cookiepath=g_build_filename(profile,"cookies.sqlite",NULL);webkit_cookie_manager_set_persistent_storage(cookies,cookiepath,WEBKIT_COOKIE_PERSISTENT_STORAGE_SQLITE);g_free(cookiepath);webkit_cookie_manager_set_accept_policy(cookies,WEBKIT_COOKIE_POLICY_ACCEPT_NO_THIRD_PARTY);
    g_signal_connect(context,"initialize-web-extensions",G_CALLBACK(extension_init),NULL);g_signal_connect(context,"download-started",G_CALLBACK(download_started),NULL);
}
int main(int argc,char **argv){
    start_time=g_get_monotonic_time();setlocale(LC_ALL,"");
    GOptionEntry options[]={
        {"profile",0,0,G_OPTION_ARG_FILENAME,&opt_profile,"Directorio de perfil aislado","DIR"},
        {"data-dir",0,0,G_OPTION_ARG_FILENAME,&opt_data,"Datos del programa","DIR"},
        {"no-block",0,0,G_OPTION_ARG_NONE,&no_block,"Desactivar bloqueo para comparación",NULL},
        {"no-update",0,0,G_OPTION_ARG_NONE,&no_update,"No actualizar listas en esta ejecución",NULL},
        {"telemetry",0,0,G_OPTION_ARG_FILENAME,&opt_telemetry,"Diagnóstico JSONL explícito (incluye URLs)","FILE"},
        {"audit",0,0,G_OPTION_ARG_NONE,&audit,"Registrar solicitudes bloqueadas y habilitar inspector",NULL},
        {"autoplay",0,0,G_OPTION_ARG_NONE,&autoplay,"Permitir reproducción sin gesto para pruebas",NULL},
        {"quit-after",0,0,G_OPTION_ARG_INT,&quit_after,"Cerrar después de N segundos","N"},
        {"eval",0,0,G_OPTION_ARG_FILENAME,&opt_eval,"Ejecutar JavaScript de un archivo local para pruebas","FILE"},
        {"eval-after",0,0,G_OPTION_ARG_INT,&eval_after,"Demora del JavaScript de prueba","N"},
        {"probe-interval",0,0,G_OPTION_ARG_INT,&probe_interval,"Muestrear estado del vídeo cada N segundos","N"},
        {"screenshot",0,0,G_OPTION_ARG_FILENAME,&opt_screenshot,"Guardar captura de la ventana","PNG"},
        {"snapshot-after",0,0,G_OPTION_ARG_INT,&snapshot_after,"Demora de captura","N"},{NULL}};
    GOptionContext *opts=g_option_context_new("[URL ...] — Babinium Browser 0.4.5");g_option_context_add_main_entries(opts,options,NULL);g_option_context_add_group(opts,gtk_get_option_group(TRUE));
    GError *err=NULL;if(!g_option_context_parse(opts,&argc,&argv,&err)){g_printerr("%s\n",err->message);return 2;}g_option_context_free(opts);
    if(opt_telemetry){telemetry=fopen(opt_telemetry,"w");if(!telemetry){perror("telemetry");return 2;}}
    char exe[4096];ssize_t len=readlink("/proc/self/exe",exe,sizeof(exe)-1);if(len<0)return 2;exe[len]=0;bin_dir=g_path_get_dirname(exe);char *prefix=g_path_get_dirname(bin_dir);
    data_dir=opt_data?g_canonicalize_filename(opt_data,NULL):g_build_filename(prefix,"share","babinium-browser",NULL);ext_dir=g_build_filename(prefix,"lib","babinium-browser",NULL);g_free(prefix);
    profile=opt_profile?g_canonicalize_filename(opt_profile,NULL):g_build_filename(g_get_user_data_dir(),"babinium-browser",NULL);g_mkdir_with_parents(profile,0700);
    filters_dir=g_build_filename(profile,"filters",NULL);g_mkdir_with_parents(filters_dir,0700);sites_path=g_build_filename(profile,"disabled-sites",NULL);light_path=g_build_filename(profile,"light-sites",NULL);favorites_path=g_build_filename(profile,"favorites.ini",NULL);
    disabled=g_hash_table_new_full(g_str_hash,g_str_equal,g_free,NULL);char *txt=NULL;if(g_file_get_contents(sites_path,&txt,NULL,NULL)){char **lines=g_strsplit(txt,"\n",-1);for(char **s=lines;*s;s++)if(**s)g_hash_table_add(disabled,g_strdup(*s));g_strfreev(lines);g_free(txt);}
    light_sites=g_hash_table_new_full(g_str_hash,g_str_equal,g_free,NULL);txt=NULL;if(g_file_get_contents(light_path,&txt,NULL,NULL)){char **lines=g_strsplit(txt,"\n",-1);for(char **s=lines;*s;s++)if(**s)g_hash_table_add(light_sites,g_strdup(*s));g_strfreev(lines);g_free(txt);}
    favorites=g_key_file_new();GError *fav_error=NULL;if(!g_key_file_load_from_file(favorites,favorites_path,G_KEY_FILE_NONE,&fav_error)&&!g_error_matches(fav_error,G_FILE_ERROR,G_FILE_ERROR_NOENT)){favorites_readonly=TRUE;g_printerr("No se pudo leer favoritos: %s\n",fav_error->message);}g_clear_error(&fav_error);
    index_path=g_build_filename(filters_dir,"current","engine.bin",NULL);if(!g_file_test(index_path,G_FILE_TEST_IS_REGULAR)){g_free(index_path);index_path=g_build_filename(data_dir,"engine.bin",NULL);}
    char *respath=g_build_filename(data_dir,"resources.json",NULL);
    if(!no_block&&(!g_file_test(index_path,G_FILE_TEST_IS_REGULAR)||!g_file_test(respath,G_FILE_TEST_IS_REGULAR))){g_printerr("Faltan los datos de bloqueo en %s\n",data_dir);return 2;}g_free(respath);
    g_object_set(gtk_settings_get_default(),"gtk-application-prefer-dark-theme",TRUE,NULL);
    GtkCssProvider *css=gtk_css_provider_new();gtk_css_provider_load_from_data(css,"#bb-empty-tab { background-color: #000000; color: #dddddd; } #bb-brand { padding: 0 12px; font-weight: bold; background: none; border: 0; box-shadow: none; } #bb-help, #bb-help viewport { background-color: #0d0f13; color: #eeeeee; } #bb-help-key { font-weight: bold; color: #86b7ff; }",-1,NULL);gtk_style_context_add_provider_for_screen(gdk_screen_get_default(),GTK_STYLE_PROVIDER(css),GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);g_object_unref(css);
    tabs=g_ptr_array_new();window=gtk_window_new(GTK_WINDOW_TOPLEVEL);gtk_window_set_default_size(GTK_WINDOW(window),1100,740);gtk_window_set_title(GTK_WINDOW(window),"Babinium Browser");gtk_window_set_wmclass(GTK_WINDOW(window),"babinium-browser","BabiniumBrowser");
    root=gtk_box_new(GTK_ORIENTATION_VERTICAL,0);gtk_container_add(GTK_CONTAINER(window),root);toolbar=gtk_box_new(GTK_ORIENTATION_HORIZONTAL,3);gtk_container_set_border_width(GTK_CONTAINER(toolbar),4);gtk_box_pack_start(GTK_BOX(root),toolbar,FALSE,FALSE,0);
    back=button("Atrás",G_CALLBACK(navigate),GINT_TO_POINTER(0));forward=button("Adelante",G_CALLBACK(navigate),GINT_TO_POINTER(1));reload_btn=button("Recargar",G_CALLBACK(navigate),GINT_TO_POINTER(2));
    address=gtk_entry_new();gtk_entry_set_placeholder_text(GTK_ENTRY(address),"Dirección o búsqueda");gtk_box_pack_start(GTK_BOX(toolbar),address,TRUE,TRUE,0);g_signal_connect(address,"activate",G_CALLBACK(entry_activate),NULL);
    favorite_button=button("☆",G_CALLBACK(toggle_favorite),NULL);
    GtkWidget *fm=gtk_menu_button_new();gtk_button_set_label(GTK_BUTTON(fm),"Favoritos");gtk_box_pack_start(GTK_BOX(toolbar),fm,FALSE,FALSE,0);favorites_pop=gtk_popover_new(fm);
    favorites_scroll=gtk_scrolled_window_new(NULL,NULL);gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(favorites_scroll),GTK_POLICY_NEVER,GTK_POLICY_AUTOMATIC);gtk_scrolled_window_set_max_content_height(GTK_SCROLLED_WINDOW(favorites_scroll),480);gtk_scrolled_window_set_propagate_natural_height(GTK_SCROLLED_WINDOW(favorites_scroll),TRUE);
    favorites_box=gtk_box_new(GTK_ORIENTATION_VERTICAL,3);gtk_container_set_border_width(GTK_CONTAINER(favorites_box),8);gtk_container_add(GTK_CONTAINER(favorites_scroll),favorites_box);gtk_container_add(GTK_CONTAINER(favorites_pop),favorites_scroll);gtk_widget_show_all(favorites_scroll);gtk_menu_button_set_popover(GTK_MENU_BUTTON(fm),favorites_pop);g_signal_connect(favorites_pop,"show",G_CALLBACK(favorites_show),NULL);
    shield=gtk_toggle_button_new_with_label("Bloqueo");gtk_box_pack_start(GTK_BOX(toolbar),shield,FALSE,FALSE,0);g_signal_connect(shield,"toggled",G_CALLBACK(toggle_block),NULL);
    dark_button=gtk_toggle_button_new_with_label("Oscuro");gtk_widget_set_tooltip_text(dark_button,"Activar o desactivar el modo oscuro para este sitio. Se recarga la pestaña.");gtk_box_pack_start(GTK_BOX(toolbar),dark_button,FALSE,FALSE,0);g_signal_connect(dark_button,"toggled",G_CALLBACK(toggle_dark),NULL);
    GtkWidget *dl=gtk_menu_button_new();gtk_button_set_label(GTK_BUTTON(dl),"Descargas");gtk_box_pack_start(GTK_BOX(toolbar),dl,FALSE,FALSE,0);downloads_pop=gtk_popover_new(dl);downloads_box=gtk_box_new(GTK_ORIENTATION_VERTICAL,6);gtk_container_set_border_width(GTK_CONTAINER(downloads_box),10);gtk_container_add(GTK_CONTAINER(downloads_pop),downloads_box);list_status=gtk_label_new(no_update?"Listas incluidas · actualización desactivada en esta prueba":"Listas incluidas · actualización automática cada 6 h");gtk_label_set_line_wrap(GTK_LABEL(list_status),TRUE);gtk_box_pack_start(GTK_BOX(downloads_box),list_status,FALSE,FALSE,0);GtkWidget *u=gtk_button_new_with_label("Actualizar listas");gtk_box_pack_start(GTK_BOX(downloads_box),u,FALSE,FALSE,0);g_signal_connect(u,"clicked",G_CALLBACK(manual_update),NULL);gtk_widget_show_all(downloads_box);gtk_menu_button_set_popover(GTK_MENU_BUTTON(dl),downloads_pop);
    button("+",G_CALLBACK(add_tab),NULL);notebook=gtk_notebook_new();gtk_notebook_set_scrollable(GTK_NOTEBOOK(notebook),TRUE);GtkWidget *brand=gtk_button_new_with_label("Babinium");gtk_widget_set_name(brand,"bb-brand");gtk_widget_set_tooltip_text(brand,"Abrir ayuda de Babinium");g_signal_connect(brand,"clicked",G_CALLBACK(open_help),NULL);gtk_widget_show(brand);gtk_notebook_set_action_widget(GTK_NOTEBOOK(notebook),brand,GTK_PACK_END);gtk_box_pack_start(GTK_BOX(root),notebook,TRUE,TRUE,0);
    g_signal_connect_after(notebook,"switch-page",G_CALLBACK(switch_page),NULL);g_signal_connect(window,"destroy",G_CALLBACK(gtk_main_quit),NULL);g_signal_connect(window,"key-press-event",G_CALLBACK(key_press),NULL);g_signal_connect(window,"map-event",G_CALLBACK(mapped),NULL);g_signal_connect(window,"draw",G_CALLBACK(drawn),NULL);
    if(argc<2)new_tab("about:blank",TRUE);else for(int i=1;i<argc;i++)new_tab(argv[i],TRUE);
    gtk_widget_show_all(window);refresh_controls();
    char *version=g_strdup_printf("WebKitGTK %u.%u.%u; sandbox=%d",webkit_get_major_version(),webkit_get_minor_version(),webkit_get_micro_version(),context?webkit_web_context_get_sandbox_enabled(context):TRUE);log_event("runtime",version);g_free(version);
    if(!no_update){g_timeout_add_seconds(30,update_lists,NULL);g_timeout_add_seconds(3600,update_tick,NULL);}
    if(quit_after>0)g_timeout_add_seconds(quit_after,quit_timer,NULL);
    if(opt_eval)g_timeout_add_seconds(MAX(1,eval_after),eval_timer,NULL);
    if(probe_interval>0)g_timeout_add_seconds(probe_interval,probe,NULL);
    if(opt_screenshot)g_timeout_add_seconds(MAX(1,snapshot_after),screenshot,NULL);
    gtk_main();if(telemetry)fclose(telemetry);return 0;
}
