/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef BABINIUM_MPV_OPTIONS_H
#define BABINIUM_MPV_OPTIONS_H

/* Keep resolution below 4K, prefer H.264 and Spanish audio when offered.
 * Each resolution tier also supports streams with combined video and audio. */
#define BB_MPV_YTDL_FORMAT \
    "(bestvideo[height=1080][vcodec^=avc1]/bestvideo[height=1080])+bestaudio[language^=es]/" \
    "best[height=1080][language^=es]/" \
    "(bestvideo[height=1080][vcodec^=avc1]/bestvideo[height=1080])+bestaudio/" \
    "best[height=1080]/" \
    "(bestvideo[height=720][vcodec^=avc1]/bestvideo[height=720])+bestaudio[language^=es]/" \
    "best[height=720][language^=es]/" \
    "(bestvideo[height=720][vcodec^=avc1]/bestvideo[height=720])+bestaudio/" \
    "best[height=720]/" \
    "(bestvideo[height<=720][vcodec^=avc1]/bestvideo[height<=720])+bestaudio[language^=es]/" \
    "best[height<=720][language^=es]/" \
    "(bestvideo[height<=720][vcodec^=avc1]/bestvideo[height<=720])+bestaudio/" \
    "best[height<=720]"

#define BB_MPV_YTDL_ARGUMENT "--ytdl-format=" BB_MPV_YTDL_FORMAT
#define BB_MPV_AUDIO_LANGUAGE "--alang=es,es-419,es-ES"
#define BB_MPV_NO_SUBTITLES "--sid=no"
/* MPV's yt-dlp hook always adds --write-srt after raw options. An empty-match
 * language expression prevents any subtitle tracks from being requested. */
#define BB_MPV_YTDL_NO_SUBTITLES "--ytdl-raw-options=sub-langs=^$"

#endif
