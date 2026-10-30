/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef BABINIUM_MPV_OPTIONS_H
#define BABINIUM_MPV_OPTIONS_H
#include <glib.h>

/* Prefer the chosen height, H.264 and Spanish audio, then a lower height.
 * Support both separate streams and formats with video and audio together. */
#define BB_MPV_YTDL_FORMAT_TEMPLATE \
    "(bestvideo[height=%u][vcodec^=avc1]/bestvideo[height=%u])+bestaudio[language^=es]/" \
    "best[height=%u][language^=es]/" \
    "(bestvideo[height=%u][vcodec^=avc1]/bestvideo[height=%u])+bestaudio/" \
    "best[height=%u]/" \
    "bestvideo[height<%u]+bestaudio[language^=es]/" \
    "best[height<%u][language^=es]/" \
    "bestvideo[height<%u]+bestaudio/" \
    "best[height<%u]"

static inline char *bb_mpv_ytdl_format(guint height){
    return g_strdup_printf(BB_MPV_YTDL_FORMAT_TEMPLATE,height,height,height,height,height,
                           height,height,height,height,height);
}
#define BB_MPV_AUDIO_LANGUAGE "--alang=es,es-419,es-ES"
#define BB_MPV_NO_SUBTITLES "--sid=no"
#define BB_MPV_SUBTITLES "--sid=auto"
#define BB_MPV_SUBTITLE_LANGUAGE "--slang=es"
#define BB_MPV_SUBTITLE_FALLBACK "--subs-fallback=yes"
#define BB_MPV_SUBTITLE_MATCHING_AUDIO "--subs-with-matching-audio=yes"
/* MPV's yt-dlp hook always adds --write-srt after raw options. An empty-match
 * language expression prevents any subtitle tracks from being requested. */
#define BB_MPV_YTDL_NO_SUBTITLES "--ytdl-raw-options=sub-langs=^$"
/* The helper chooses one Spanish track, or one other track as a fallback. */
#define BB_MPV_YTDL_SUBTITLES "--ytdl-raw-options=write-auto-subs=,sub-langs=^$"

#endif
