/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <glib.h>

/* Return a canonical URL only for a specific YouTube video. */
char *youtube_video_url(const char *uri);
/* These helpers match only YouTube pages and known video delivery URLs. */
gboolean youtube_site_url(const char *uri);
gboolean youtube_media_url(const char *uri);
