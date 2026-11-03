/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef BABINIUM_STREAM_URL_H
#define BABINIUM_STREAM_URL_H
#include <glib.h>

/* Media manifest URLs the reusable MPV window can play directly. */
gboolean media_stream_url(const char *uri);

#endif
