/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "../src/stream-url.h"
#include <glib.h>

static void valid(const char *uri){g_assert_true(media_stream_url(uri));}
static void invalid(const char *uri){g_assert_false(media_stream_url(uri));}
static void test_valid(void){
    valid("https://cdn.example.com/live/master.m3u8");
    valid("https://cdn.example.com/live/master.m3u8?token=abc&x=1");
    valid("https://cdn.example.com/live/master.M3U8");
    valid("https://cdn.example.com/video/manifest.mpd");
    valid("https://iptv.example.org/playlist.m3u");
    valid("http://cdn.example.com/a/b.m3u8");
}
static void test_invalid(void){
    invalid(NULL);invalid("");
    invalid("https://cdn.example.com/video.mp4");
    invalid("https://cdn.example.com/master.m3u8.bak");
    invalid("https://cdn.example.com/page.m3u8x");
    invalid("https://cdn.example.com/xmpd/file.html");
    invalid("file:///tmp/stream.m3u8");
    invalid("https://cdn.example.com/?file=video.m3u8");
    invalid("notaurl.m3u8");
}
int main(int argc,char **argv){
    g_test_init(&argc,&argv,NULL);
    g_test_add_func("/stream-url/valid",test_valid);
    g_test_add_func("/stream-url/invalid",test_invalid);
    return g_test_run();
}
