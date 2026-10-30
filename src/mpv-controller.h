/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <gtk/gtk.h>

/* Open or replace a YouTube video in Babinium's independent MPV process. */
void mpv_controller_play(GtkWindow *parent,const char *url,guint resolution,gboolean subtitles,const char *lib_dir);
