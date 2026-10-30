"""Read the exact yt-dlp format expression passed by the C application."""
import ast
from pathlib import Path
import re


def selector(height=1080):
    header = (Path(__file__).resolve().parents[1] / 'src/mpv-options.h').read_text()
    body = header.split('#define BB_MPV_YTDL_FORMAT_TEMPLATE \\\n', 1)[1].split('\n\n', 1)[0]
    template = ''.join(ast.literal_eval(s) for s in re.findall(r'"(?:\\.|[^"\\])*"', body))
    return template % ((height,) * template.count('%u'))
