#!/usr/bin/env python3
"""Keep only one YouTube subtitle track in mpv's yt-dlp JSON response."""
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
import subprocess
import sys


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
                candidates.append((score, language, track))
    if not candidates:
        return None
    _, language, track = min(candidates, key=lambda candidate: candidate[0])
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
