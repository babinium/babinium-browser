#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the real YouTube button on the visible desktop with an isolated profile.

The first run records the launch arguments; the second runs the installed MPV
with its normal configuration and quality, muted for this test, and checks
playback after closing the browser. The real user's browser profile and existing
MPV processes are untouched.
"""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time

from features import events, wait_for
from mpv_format import selector
from ui import browser_window, key


binary = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).resolve()
output.mkdir(parents=True, exist_ok=True)
source = os.environ.get('BB_MPV_TEST_URL', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ&utm_source=babinium-test')
canonical = os.environ.get('BB_MPV_TEST_CANONICAL', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ')


def property_value(path, name):
    with socket.socket(socket.AF_UNIX) as conn:
        conn.settimeout(3)
        conn.connect(str(path))
        conn.sendall((json.dumps({'command': ['get_property', name], 'request_id': 1}) + '\n').encode())
        with conn.makefile('r') as reader:
            for line in reader:
                message = json.loads(line)
                if message.get('request_id') == 1:
                    return message.get('data')
    return None


def wait_browser(predicate, browser, timeout):
    def ready():
        if browser.poll() is not None:
            raise AssertionError(f'Babinium terminó antes de tiempo: {browser.returncode}')
        return predicate()
    wait_for(ready, timeout)


for mode in os.environ.get('BB_MPV_TEST_MODES', 'fake,real').split(','):
    with tempfile.TemporaryDirectory(prefix='bb-mpv-button-') as temp_name:
        temp = Path(temp_name)
        bindir = temp / 'bin'
        bindir.mkdir()
        record = temp / 'launch.json'
        ipc = temp / 'mpv.sock'
        wrapper = bindir / 'mpv'
        code = [
            '#!/usr/bin/python3',
            'import json,os,sys,time',
            f'open({str(record)!r},"w").write(json.dumps({{"pid":os.getpid(),"sid":os.getsid(0),"argv":sys.argv[1:]}}))',
        ]
        if mode == 'fake':
            code.append('time.sleep(120)')
        else:
            code.append(f'os.execv("/usr/bin/mpv",["/usr/bin/mpv","--mute=yes",'
                        f'{("--input-ipc-server=" + str(ipc))!r},'
                        f'{("--log-file=" + str(output / "real-mpv.log"))!r}]+sys.argv[1:])')
        wrapper.write_text('\n'.join(code) + '\n')
        wrapper.chmod(0o755)
        env = dict(os.environ)
        env['PATH'] = str(bindir) + os.pathsep + env['PATH']
        telemetry = output / (mode + '-events.jsonl')
        screen = output / (mode + '-youtube.png')
        pid = None
        with (output / (mode + '-stderr.log')).open('w') as stderr:
            browser = subprocess.Popen([str(binary), '--profile', str(temp / 'profile'), '--no-update',
                                        '--telemetry', str(telemetry), '--screenshot', str(screen),
                                        '--snapshot-after', '8', '--quit-after', '210', source],
                                       env=env, stdout=subprocess.DEVNULL, stderr=stderr)
            try:
                wait_browser(lambda: any(e['event'] == 'load_committed' for e in events(telemetry)), browser, 30)
                wid = browser_window(browser.pid)
                wait_browser(screen.exists, browser, 25)
                subprocess.run(['xdotool', 'windowfocus', '--sync', wid], check=True, timeout=5)
                for shortcut in ('ctrl+l', 'Tab', 'Return'):
                    key(shortcut)
                    time.sleep(.15)
                wait_browser(record.exists, browser, 12)
                launch = json.loads(record.read_text())
                pid = launch['pid']
                assert launch['sid'] == pid, launch
                assert launch['argv'] == ['--force-window=immediate', '--no-terminal',
                    '--ytdl-format=' + selector(), '--alang=es,es-419,es-ES',
                    '--sid=no', '--ytdl-raw-options=sub-langs=^$',
                    '--', canonical], launch
                if mode == 'real':
                    wait_for(ipc.exists, 15)
                    # YouTube extraction and CDN startup can be slow on an
                    # unreliable connection; the window remains visible.
                    end = time.monotonic() + 160
                    before = None
                    while time.monotonic() < end:
                        try:
                            before = property_value(ipc, 'time-pos')
                            if isinstance(before, (float, int)) and before > 2:
                                break
                        except (OSError, ValueError):
                            pass
                        time.sleep(1)
                    assert isinstance(before, (float, int)) and before > 2, before
                    video = property_value(ipc, 'video-params')
                    assert video and video.get('w') and video.get('h'), video
                    assert video['h'] <= 1080, video
                    expected_height = os.environ.get('BB_MPV_EXPECT_HEIGHT')
                    if expected_height:
                        assert video['h'] == int(expected_height), video
                    tracks = property_value(ipc, 'track-list') or []
                    selected = [{'type': track.get('type'), 'lang': track.get('lang')}
                                for track in tracks if track.get('selected')]
                    assert not any(track.get('type') == 'sub' for track in tracks), tracks
                    if os.environ.get('BB_MPV_EXPECT_SPANISH_AUDIO'):
                        # The container can label a dubbed stream "eng" even
                        # when yt-dlp selected its Spanish-language format.
                        result = property_value(ipc, 'user-data/mpv/ytdl/json-subprocess-result')
                        info = json.loads(result['stdout'])
                        requested = info.get('requested_formats', [])
                        assert any(str(item.get('language', '')).startswith('es') and
                                   item.get('acodec') not in (None, 'none') for item in requested), requested
                subprocess.run(['xdotool', 'windowfocus', '--sync', wid], check=True, timeout=5)
                # The window can disappear between key-down and key-up. Send
                # releases globally so Ctrl+W cannot remain stuck on the desktop.
                try:
                    subprocess.run(['xdotool', 'keydown', 'Control_L'], check=True, timeout=5)
                    subprocess.run(['xdotool', 'key', 'w'], check=True, timeout=5)
                finally:
                    subprocess.run(['xdotool', 'keyup', 'w', 'Control_L'], check=True, timeout=5)
                browser.wait(timeout=12)
                assert browser.returncode == 0, browser.returncode
                os.kill(pid, 0)
                if mode == 'real':
                    time.sleep(3)
                    after = property_value(ipc, 'time-pos')
                    assert isinstance(after, (float, int)) and after > before, (before, after)
                    print('MPV real siguió reproduciendo tras cerrar Babinium:',
                          json.dumps({'antes': before, 'despues': after, 'video': video,
                                      'pistas': selected}), flush=True)
                else:
                    print('Botón de YouTube, URL limpia y proceso independiente: correcto', flush=True)
            finally:
                if browser.poll() is None:
                    browser.terminate()
                    browser.wait(timeout=10)
                if pid:
                    try:
                        os.killpg(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
