#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Helpers for tests on the user's visible X11 desktop."""
import ctypes
import ctypes.util
import re
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
    if value in ('braceleft', 'braceright'):
        # xdotool may select an AltGr mapping even when an unmodified physical
        # key exists; WebKit can then receive the underlying digit instead.
        mapping=subprocess.check_output(['xmodmap','-pke'],text=True,timeout=5)
        choices=[];shift=None
        for line in mapping.splitlines():
            match=re.match(r'keycode\s+(\d+)\s*=\s*(.*)',line)
            if not match:continue
            code=int(match.group(1));symbols=match.group(2).split()
            if symbols and symbols[0]=='Shift_L':shift=code
            if symbols and symbols[0]==value:choices.append((0,code))
            elif len(symbols)>1 and symbols[1]==value:choices.append((1,code))
        if choices:
            needs_shift,code=min(choices)
            if needs_shift and shift is None:raise RuntimeError('No se encontró Shift_L')
            x11=ctypes.CDLL(ctypes.util.find_library('X11'))
            xtst=ctypes.CDLL(ctypes.util.find_library('Xtst'))
            x11.XOpenDisplay.argtypes=[ctypes.c_char_p];x11.XOpenDisplay.restype=ctypes.c_void_p
            x11.XCloseDisplay.argtypes=[ctypes.c_void_p];x11.XFlush.argtypes=[ctypes.c_void_p]
            xtst.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
            display=x11.XOpenDisplay(None)
            if not display:raise RuntimeError('No se pudo abrir la pantalla visible')
            try:
                if needs_shift:xtst.XTestFakeKeyEvent(display,shift,1,0)
                xtst.XTestFakeKeyEvent(display,code,1,0);xtst.XTestFakeKeyEvent(display,code,0,0)
                if needs_shift:xtst.XTestFakeKeyEvent(display,shift,0,0)
                x11.XFlush(display)
            finally:x11.XCloseDisplay(display)
            return
    subprocess.run(['xdotool', 'key', '--clearmodifiers', value], check=True, timeout=5)
