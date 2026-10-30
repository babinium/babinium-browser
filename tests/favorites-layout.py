#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Show synthetic favorites on the active X11 desktop for visual inspection."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import time

binary=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
items=[
    ('https://www.youtube.com/watch?v=example123&list=sample',
     'Una guía para aprender a usar el navegador y leer cómodamente un título de favorito que ocupa varias líneas'),
    ('https://www.bbc.co.uk/news/article/example','Noticias internacionales y actualidad'),
    ('https://es.wikipedia.org/wiki/Navegador_web','Navegador web — Wikipedia'),
    ('https://www.example.com/una/direccion/muy/larga?dato=ejemplo',
     'https://www.example.com/una/direccion/muy/larga?dato=ejemplo'),
    ('https://www.example.com/con-www?dato=ejemplo','www.example.com/con-www?dato=ejemplo'),
    ('https://www.example.com/sin-www?dato=ejemplo','example.com/sin-www?dato=ejemplo'),
    ('http://127.0.0.1:1234/private/path','Sitio de prueba local'),
    ('https://mail.google.com/mail/u/0/#inbox','TituloLargoSinEspacios'*4),
]
if 'many' in sys.argv[3:]:
    items.extend((f'https://www.example.com/page/{i}',f'Favorito de prueba número {i}') for i in range(1,21))
with tempfile.TemporaryDirectory(prefix='bb-favorites-layout-') as temp:
    profile=Path(temp);config=profile/'favorites.ini'
    data=''.join(f'[{hashlib.sha256(uri.encode()).hexdigest()}]\nuri={uri}\ntitle={title}\n\n' for uri,title in items)
    config.write_text(data)
    screenshot=out/'favorites.png'
    with (out/'stderr.log').open('w') as stderr:
        p=subprocess.Popen([str(binary),'--profile',temp,'--no-update','--no-block',
            '--screenshot',str(screenshot),'--snapshot-after','4','--quit-after','8'],stdout=subprocess.DEVNULL,stderr=stderr)
        try:
            end=time.monotonic()+8;wid=None
            while time.monotonic()<end and p.poll() is None:
                result=subprocess.run(['xdotool','search','--onlyvisible','--pid',str(p.pid)],capture_output=True,text=True,timeout=5)
                if result.returncode==0 and result.stdout.splitlines():wid=result.stdout.splitlines()[0];break
                time.sleep(.1)
            if not wid:raise AssertionError('No apareció la ventana del navegador')
            widths=[arg for arg in sys.argv[3:] if arg.isdecimal()]
            if widths:
                width=int(widths[0])
                command=f'[id="{wid}"] floating enable, resize set width {width} px height 500 px'
                subprocess.run(['i3-msg',command],check=True,capture_output=True,text=True,timeout=5)
                time.sleep(.4)
            subprocess.run(['xdotool','windowfocus','--sync',wid],check=True,timeout=5)
            subprocess.run(['xdotool','key','--clearmodifiers','--window',wid,'ctrl+shift+d'],check=True,timeout=5)
            children=Path('/proc')/str(p.pid)/'task'/str(p.pid)/'children'
            if children.read_text().strip():raise AssertionError('El panel abrió un proceso adicional')
            p.wait(timeout=15)
            if p.returncode:raise AssertionError('El navegador salió con error')
            if not screenshot.is_file():raise AssertionError('No se guardó la captura de la ventana de prueba')
            if config.read_text()!=data:raise AssertionError('La apertura del panel modificó los favoritos')
            print('Panel de favoritos de prueba visible; direcciones originales conservadas:',screenshot,flush=True)
        finally:
            if p.poll() is None:p.terminate();p.wait(timeout=10)
