#!/usr/bin/env python3
"""Keep only one YouTube subtitle track in mpv's yt-dlp JSON response."""
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
import re
import subprocess
import sys
from http.client import HTTPException
from html import unescape
from urllib.request import Request, urlopen


MAX_SUBTITLE_BYTES = 4 * 1024 * 1024
TIMING = re.compile(
    r"^(\d+):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
    r"(\d+):(\d{2}):(\d{2})[,.](\d{3})(?:\s+.*)?$"
)
TAGS = re.compile(r"<[^>]*>")


def milliseconds(parts):
    hours, minutes, seconds, millis = map(int, parts)
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def timestamp(value):
    seconds, millis = divmod(value, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{millis:03}"


def normalized_line(line):
    return " ".join(unescape(TAGS.sub("", line)).split())


def clean_automatic_srt(text):
    """Remove rolling repeats and end older cues when a new cue starts."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    cues = []
    previous_lines = []
    for block in re.split(r"\n[ \t]*\n", text.strip()):
        lines = block.split("\n")
        if lines and lines[0].strip().isdigit():
            lines = lines[1:]
        timing = TIMING.fullmatch(lines[0].strip()) if lines else None
        if not timing:
            return None
        start = milliseconds(timing.groups()[:4])
        end = milliseconds(timing.groups()[4:])
        content = [line for line in lines[1:] if line.strip()]
        if end <= start or not content or (cues and start < cues[-1][0]):
            return None
        plain = [normalized_line(line) for line in content]
        if len(content) > 1 and previous_lines:
            # YouTube's rolling captions repeat an old line next to the new one.
            # Preserve a fully repeated cue and only remove a repeated edge if
            # at least one new line remains.
            while len(content) > 1 and plain[0] and plain[0] in previous_lines:
                content.pop(0); plain.pop(0)
            while len(content) > 1 and plain[-1] and plain[-1] in previous_lines:
                content.pop(); plain.pop()
        previous_lines = [normalized_line(line) for line in lines[1:] if line.strip()]
        if cues and cues[-1][0] < start < cues[-1][1]:
            cues[-1][1] = start
        cues.append([start, end, content])
    if not cues:
        return None
    return "WEBVTT\n\n" + "\n\n".join(
        f"{timestamp(start)} --> {timestamp(end)}\n" + "\n".join(content)
        for start, end, content in cues
    ) + "\n"


def clean_automatic_track(track, headers):
    """Fetch only the selected SRT; fall back to the original on any error."""
    if track.get("ext") != "srt":
        return track
    try:
        data = track.get("data")
        if not isinstance(data, str):
            url = track.get("url", "")
            if not isinstance(url, str) or not url.startswith("https://"):
                return track
            allowed = ("User-Agent", "Accept", "Accept-Language", "Referer")
            safe_headers = {key: headers[key] for key in allowed
                            if isinstance(headers.get(key), str)}
            with urlopen(Request(url, headers=safe_headers), timeout=3) as response:
                raw = response.read(MAX_SUBTITLE_BYTES + 1)
            if len(raw) > MAX_SUBTITLE_BYTES:
                return track
            data = raw.decode("utf-8-sig")
        cleaned = clean_automatic_srt(data)
        if not cleaned:
            return track
        result = dict(track)
        result.pop("url", None)
        result["ext"] = "vtt"
        result["data"] = cleaned
        return result
    except (OSError, HTTPException, UnicodeError, ValueError, TypeError):
        return track


def usable_track(formats):
    if not isinstance(formats, list):
        return None
    choices = [item for item in formats if isinstance(item, dict)
               and (item.get("url") or item.get("data"))]
    for extension in ("ass", "srt"):
        for item in reversed(choices):
            if item.get("ext") == extension:
                return item
    return choices[-1] if choices else None


def select_subtitle(info):
    manual = info.get("subtitles") or {}
    automatic = info.get("automatic_captions") or {}
    candidates = []
    for is_automatic, tracks in ((False, manual), (True, automatic)):
        if not isinstance(tracks, dict):
            continue
        for language, formats in tracks.items():
            if not isinstance(language, str) or language.lower() == "live_chat":
                continue
            track = usable_track(formats)
            if track:
                name = language.lower().replace("_", "-")
                spanish = name == "es" or name == "spa" or name.startswith("es-")
                # Spanish always wins, including automatic over non-Spanish manual.
                # Within the same priority, prefer manually authored captions.
                score = (not spanish, is_automatic, name != "es",
                         not name.endswith("-orig"), name != "en", name)
                candidates.append((score, language, track, is_automatic))
    if not candidates:
        return None
    _, language, track, is_automatic = min(candidates, key=lambda candidate: candidate[0])
    if is_automatic and not info.get("is_live") and info.get("live_status") != "is_live":
        headers = info.get("http_headers")
        track = clean_automatic_track(track, headers if isinstance(headers, dict) else {})
    return {language: track}


def main():
    args = ["yt-dlp", *sys.argv[1:]]
    if "--write-auto-subs" not in args or "-J" not in args:
        os.execvp(args[0], args)
    result = subprocess.run(args, stdout=subprocess.PIPE, check=False)
    if result.returncode:
        sys.stdout.buffer.write(result.stdout)
        return result.returncode
    try:
        info = json.loads(result.stdout)
        if not isinstance(info, dict):
            raise ValueError("expected a video object")
        info["requested_subtitles"] = select_subtitle(info)
        # The MPV hook needs only the selected track, not the full track catalog.
        info.pop("subtitles", None)
        info.pop("automatic_captions", None)
        sys.stdout.write(json.dumps(info, ensure_ascii=True) + "\n")
    except (UnicodeDecodeError, ValueError, TypeError):
        # Preserve yt-dlp's output if its response changes unexpectedly.
        sys.stdout.buffer.write(result.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
