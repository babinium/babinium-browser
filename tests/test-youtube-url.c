/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "../src/youtube-url.h"
#include <glib.h>

static void valid(const char *uri){
    char *url=youtube_video_url(uri);
    g_assert_cmpstr(url,==,"https://www.youtube.com/watch?v=dQw4w9WgXcQ");g_free(url);
}
static void invalid(const char *uri){char *url=youtube_video_url(uri);g_assert_null(url);g_free(url);}
static void test_valid(void){
    valid("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=ignored");
    valid("https://m.youtube.com/watch?feature=share&v=dQw4w9WgXcQ");
    valid("https://music.youtube.com/watch?v=dQw4w9WgXcQ");
    valid("https://youtu.be/dQw4w9WgXcQ?t=40");
    valid("https://www.youtube.com/shorts/dQw4w9WgXcQ");
    valid("https://www.youtube.com/live/dQw4w9WgXcQ/");
    valid("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ");
}
static void test_invalid(void){
    invalid(NULL);invalid("https://www.youtube.com/");
    invalid("https://www.youtube.com/watch?list=example");
    invalid("https://www.youtube.com/watch?v=short");
    invalid("https://www.youtube.com/watch?v=dQw4w9WgXcQ%26x%3D1");
    invalid("https://www.youtube.com.evil.example/watch?v=dQw4w9WgXcQ");
    invalid("https://www.youtube.com@evil.example/watch?v=dQw4w9WgXcQ");
    invalid("file:///watch?v=dQw4w9WgXcQ");
    invalid("https://youtu.be/dQw4w9WgXcQ/other");
}
int main(int argc,char **argv){
    g_test_init(&argc,&argv,NULL);
    g_test_add_func("/youtube-url/valid",test_valid);
    g_test_add_func("/youtube-url/invalid",test_invalid);
    return g_test_run();
}
