#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Helpers for tests on the user's visible X11 desktop."""
import subprocess
import time


def browser_window(pid, timeout=12):
    """Select the main window, not a small same-process GTK helper window."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        result = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', str(pid)],
                                capture_output=True, text=True, timeout=5)
        candidates = []
        for wid in result.stdout.splitlines():
            geometry = subprocess.run(['xdotool', 'getwindowgeometry', '--shell', wid],
                                      capture_output=True, text=True, timeout=5)
            if geometry.returncode:
                continue
            values = dict(line.split('=', 1) for line in geometry.stdout.splitlines() if '=' in line)
            try:
                width, height = int(values['WIDTH']), int(values['HEIGHT'])
            except (KeyError, ValueError):
                continue
            if width >= 500 and height >= 250:
                candidates.append((width * height, wid))
        if candidates:
            return max(candidates)[1]
        time.sleep(.1)
    raise AssertionError('No apareció la ventana principal del navegador')


def key(value):
    # The main window is focused by each test. Global XTest releases still
    # arrive if a key closes a tab/window; --window can leave modifiers stuck.
    subprocess.run(['xdotool', 'key', '--clearmodifiers', value], check=True, timeout=5)
