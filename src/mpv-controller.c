/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "mpv-controller.h"
#include "mpv-options.h"
#include <gio/gio.h>
#include <gio/gunixsocketaddress.h>
#include <json-glib/json-glib.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>
#include <string.h>

typedef struct { char *path,*url; } Attempt;
static char *socket_path,*lock_path,*pending;
static GSubprocess *player;
static GWeakRef parent_ref;
static gboolean have_parent,busy,rechecking;
static int lock_fd=-1;
static guint retry_source;
static gint64 deadline;

static void try_connection(void);
static void player_child_setup(gpointer unused){(void)unused;setsid();}
static void unlock_start(void){if(lock_fd>=0){flock(lock_fd,LOCK_UN);close(lock_fd);lock_fd=-1;}rechecking=FALSE;}

static void show_error(const char *message){
    GtkWindow *parent=have_parent?g_weak_ref_get(&parent_ref):NULL;
    if(parent&&!gtk_widget_in_destruction(GTK_WIDGET(parent))){
        GtkWidget *dialog=gtk_message_dialog_new(parent,GTK_DIALOG_MODAL,GTK_MESSAGE_ERROR,GTK_BUTTONS_CLOSE,"%s",message);
        gtk_dialog_run(GTK_DIALOG(dialog));gtk_widget_destroy(dialog);
    }
    if(parent)g_object_unref(parent);
}

static gboolean prepare_ipc(void){
    if(socket_path)return TRUE;
    char *dir=g_build_filename(g_get_user_runtime_dir(),"babinium-browser",NULL);
    struct stat st;
    if(g_mkdir_with_parents(dir,0700)<0||lstat(dir,&st)<0||!S_ISDIR(st.st_mode)||
       st.st_uid!=geteuid()||(st.st_mode&077)!=0){g_free(dir);return FALSE;}
    char *sock=g_build_filename(dir,"mpv.sock",NULL);
    if(strlen(sock)>=sizeof(((struct sockaddr_un*)0)->sun_path)-1){g_free(sock);g_free(dir);return FALSE;}
    socket_path=sock;lock_path=g_build_filename(dir,"mpv.lock",NULL);g_free(dir);return TRUE;
}

/* Return 1 with the startup lock, 0 if another launcher is starting MPV, and
 * -1 for an actual file error. The lock is held only until the socket is ready. */
static int lock_start(void){
    int fd=open(lock_path,O_CREAT|O_RDWR|O_CLOEXEC|O_NOFOLLOW,0600);
    if(fd<0)return -1;
    struct stat st;
    if(fstat(fd,&st)<0||!S_ISREG(st.st_mode)||st.st_uid!=geteuid()){close(fd);return -1;}
    if(flock(fd,LOCK_EX|LOCK_NB)<0){int e=errno;close(fd);return e==EWOULDBLOCK||e==EAGAIN?0:-1;}
    lock_fd=fd;return 1;
}

static void free_attempt(gpointer data){Attempt *a=data;g_free(a->path);g_free(a->url);g_free(a);}
/* Run the local IPC exchange off the GTK thread. A reply is required before
 * closing: MPV can send events before it consumes the requested command. */
static void exchange(GTask *task,gpointer source,gpointer data,GCancellable *cancel){
    (void)source;(void)cancel;Attempt *a=data;GError *error=NULL;int result=0;
    GSocketClient *client=g_socket_client_new();g_socket_client_set_timeout(client,2);
    GSocketConnectable *address=G_SOCKET_CONNECTABLE(g_unix_socket_address_new(a->path));
    GSocketConnection *connection=g_socket_client_connect(client,address,NULL,&error);
    g_object_unref(address);g_object_unref(client);
    if(!connection){g_clear_error(&error);g_task_return_int(task,0);return;}
    if(!a->url){g_object_unref(connection);g_task_return_int(task,1);return;}
    JsonBuilder *b=json_builder_new();json_builder_begin_object(b);
    json_builder_set_member_name(b,"command");json_builder_begin_array(b);
    json_builder_add_string_value(b,"loadfile");json_builder_add_string_value(b,a->url);
    json_builder_add_string_value(b,"replace");json_builder_end_array(b);
    json_builder_set_member_name(b,"request_id");json_builder_add_int_value(b,1);json_builder_end_object(b);
    JsonNode *node=json_builder_get_root(b);JsonGenerator *gen=json_generator_new();json_generator_set_root(gen,node);
    char *json=json_generator_to_data(gen,NULL),*line=g_strconcat(json,"\n",NULL);gsize written=0;
    gboolean sent=g_output_stream_write_all(g_io_stream_get_output_stream(G_IO_STREAM(connection)),line,strlen(line),&written,NULL,&error);
    if(sent){
        GDataInputStream *in=g_data_input_stream_new(g_io_stream_get_input_stream(G_IO_STREAM(connection)));
        for(guint i=0;i<64;i++){
            gsize length=0;char *reply=g_data_input_stream_read_line(in,&length,NULL,&error);
            if(!reply)break;
            JsonParser *parser=json_parser_new();
            if(json_parser_load_from_data(parser,reply,(gssize)length,NULL)){
                JsonNode *root=json_parser_get_root(parser);
                if(JSON_NODE_HOLDS_OBJECT(root)){
                    JsonObject *obj=json_node_get_object(root);
                    if(json_object_has_member(obj,"request_id")&&json_object_get_int_member(obj,"request_id")==1){
                        const char *status=json_object_get_string_member_with_default(obj,"error","");
                        result=!g_strcmp0(status,"success")?1:2;
                    }
                }
            }
            g_object_unref(parser);g_free(reply);if(result)break;
        }
        g_object_unref(in);
    }
    g_clear_error(&error);g_free(line);g_free(json);g_object_unref(gen);json_node_free(node);g_object_unref(b);
    g_object_unref(connection);g_task_return_int(task,result);
}

static gboolean retry_cb(gpointer unused){(void)unused;retry_source=0;try_connection();return G_SOURCE_REMOVE;}
static void retry(void){
    if(g_get_monotonic_time()>=deadline){
        unlock_start();g_clear_pointer(&pending,g_free);deadline=0;
        show_error("No se pudo conectar con MPV para cambiar el video. Cerrá MPV y usá «Abrir MPV» otra vez.");return;
    }
    if(!retry_source)retry_source=g_timeout_add(100,retry_cb,NULL);
}

static void player_finished(GObject *object,GAsyncResult *result,gpointer unused){
    (void)unused;GError *error=NULL;gboolean ok=g_subprocess_wait_check_finish(G_SUBPROCESS(object),result,&error);
    if(player==G_SUBPROCESS(object))g_clear_object(&player);
    unlock_start();
    if(pending){if(!busy&&!retry_source)retry_source=g_timeout_add(100,retry_cb,NULL);}
    else if(!ok&&g_subprocess_get_if_exited(G_SUBPROCESS(object)))
        show_error("MPV no pudo reproducir el video. Revisá tu conexión, si el video requiere iniciar sesión y que yt-dlp esté actualizado. En Debian 13, podés actualizar yt-dlp desde trixie-backports.");
    g_clear_error(&error);
}

static gboolean start_player(void){
    if(!pending)return FALSE;
    char *ipc=g_strconcat("--input-ipc-server=",socket_path,NULL);
    const char *argv[]={"mpv","--force-window=immediate","--no-terminal",ipc,BB_MPV_YTDL_ARGUMENT,
                        BB_MPV_AUDIO_LANGUAGE,BB_MPV_NO_SUBTITLES,BB_MPV_YTDL_NO_SUBTITLES,"--",pending,NULL};
    GSubprocessLauncher *launcher=g_subprocess_launcher_new(G_SUBPROCESS_FLAGS_STDOUT_SILENCE|G_SUBPROCESS_FLAGS_STDERR_SILENCE);
    g_subprocess_launcher_set_child_setup(launcher,player_child_setup,NULL,NULL);
    GError *error=NULL;player=g_subprocess_launcher_spawnv(launcher,argv,&error);g_object_unref(launcher);g_free(ipc);
    if(!player){
        char *message=g_strdup_printf("No se pudo iniciar MPV; verificá que esté instalado: %s",error?error->message:"error desconocido");
        g_clear_error(&error);g_clear_pointer(&pending,g_free);unlock_start();show_error(message);g_free(message);return FALSE;
    }
    g_clear_pointer(&pending,g_free);g_subprocess_wait_check_async(player,NULL,player_finished,NULL);return TRUE;
}

static void exchange_done(GObject *source,GAsyncResult *result,gpointer unused){
    (void)source;(void)unused;GTask *task=G_TASK(result);Attempt *a=g_task_get_task_data(task);
    int status=g_task_propagate_int(task,NULL);busy=FALSE;
    if(status==1){
        if(a->url&&!g_strcmp0(a->url,pending))g_clear_pointer(&pending,g_free);
        unlock_start();deadline=0;
        if(pending){deadline=g_get_monotonic_time()+10*G_USEC_PER_SEC;try_connection();}
        return;
    }
    if(status==2){
        if(a->url&&!g_strcmp0(a->url,pending))g_clear_pointer(&pending,g_free);
        unlock_start();show_error("MPV no pudo cambiar al video solicitado. Probá con «Abrir MPV» otra vez.");
        if(pending){deadline=g_get_monotonic_time()+10*G_USEC_PER_SEC;try_connection();}
        return;
    }
    if(player){retry();return;}
    if(lock_fd>=0&&rechecking){
        rechecking=FALSE;
        if(start_player())retry();
        return;
    }
    int locked=lock_start();
    if(locked<0){g_clear_pointer(&pending,g_free);show_error("No se pudo preparar la comunicación privada con MPV.");return;}
    if(!locked){retry();return;}
    rechecking=TRUE;try_connection();
}

static void try_connection(void){
    if(busy)return;
    if(!pending&&lock_fd<0)return;
    busy=TRUE;Attempt *a=g_new0(Attempt,1);a->path=g_strdup(socket_path);a->url=g_strdup(pending);
    GTask *task=g_task_new(NULL,NULL,exchange_done,NULL);g_task_set_task_data(task,a,free_attempt);
    g_task_run_in_thread(task,exchange);g_object_unref(task);
}

void mpv_controller_play(GtkWindow *parent,const char *url){
    if(!url||!*url)return;
    if(!have_parent){g_weak_ref_init(&parent_ref,G_OBJECT(parent));have_parent=TRUE;}
    else g_weak_ref_set(&parent_ref,G_OBJECT(parent));
    if(!prepare_ipc()){show_error("No se pudo preparar la comunicación privada con MPV.");return;}
    g_free(pending);pending=g_strdup(url);deadline=g_get_monotonic_time()+10*G_USEC_PER_SEC;
    if(!busy&&!retry_source)try_connection();
}
