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

/* Fast 360p mode: keep Spanish audio first when available, otherwise prefer
 * the combined progressive format (e.g. itag 18 via Android client) before
 * throttled separate streams. */
#define BB_MPV_YTDL_FORMAT_FAST_TEMPLATE \
    "best[height=%u][language^=es]/" \
    "(bestvideo[height=%u][vcodec^=avc1]/bestvideo[height=%u])+bestaudio[language^=es]/" \
    "best[height=%u]/" \
    "(bestvideo[height=%u][vcodec^=avc1]/bestvideo[height=%u])+bestaudio/" \
    "best[height<%u][language^=es]/" \
    "bestvideo[height<%u]+bestaudio[language^=es]/" \
    "best[height<%u]/" \
    "bestvideo[height<%u]+bestaudio"

static inline char *bb_mpv_ytdl_format(guint height){
    const char *tmpl=height==360?BB_MPV_YTDL_FORMAT_FAST_TEMPLATE:BB_MPV_YTDL_FORMAT_TEMPLATE;
    return g_strdup_printf(tmpl,height,height,height,height,height,
                           height,height,height,height,height);
}
#define BB_MPV_AUDIO_LANGUAGE "--alang=es,es-419,es-ES"
/* GPU-only quality filters for low-resolution sources: spline36 upscaling with
 * anti-ringing, spline36 chroma upscaling and light debanding. All run as
 * shaders on the GPU and keep VA-API hardware decoding. */
#define BB_MPV_SCALE "--scale=spline36"
#define BB_MPV_SCALE_ANTIRING "--scale-antiring=0.7"
#define BB_MPV_CSCALE "--cscale=spline36"
#define BB_MPV_DEBAND "--deband=yes"
#define BB_MPV_DEBAND_ITERATIONS "--deband-iterations=2"
#define BB_MPV_DEBAND_GRAIN "--deband-grain=0"
/* Offload H.264 decoding to the Intel GPU; MPV falls back to software when a
 * stream is unsupported. */
#define BB_MPV_HWDEC "--hwdec=vaapi"
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
#define BB_MPV_YTDL_FAST_EXTRACTOR ",extractor-args=%37%youtube:player_client=android,default"

static inline char *bb_mpv_ytdl_raw_options(guint height,gboolean subtitles){
    const char *base=subtitles?"write-auto-subs=,sub-langs=^$":"sub-langs=^$";
    return g_strconcat(base,height==360?BB_MPV_YTDL_FAST_EXTRACTOR:"",NULL);
}

#endif
