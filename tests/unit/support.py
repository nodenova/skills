"""Shared helpers for the picture, header and date tests."""
import os
import struct
import subprocess
import sys
import zipfile
import zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SKILLS = os.path.join(ROOT, 'skills')
P = 'http://schemas.openxmlformats.org/'


def run(skill, script, *args):
    r = subprocess.run([sys.executable, os.path.join(SKILLS, skill, 'scripts', script), *args], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return r.returncode, r.stdout + r.stderr


def png(w, h):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    rows = b''.join(b'\x00' + b'\xff\x00\x00' * w for _ in range(h))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')


def jpeg(w, h):
    return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xc0\x00\x0b\x08' + struct.pack('>HH', h, w) + b'\x01\x01\x11\x00\xff\xd9'


def write_zip(path, parts):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, t in parts.items():
            z.writestr(n, t)


def read_zip(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


def text_of(parts, name):
    return parts[name].decode('utf-8')


def put(path, data):
    with open(path, 'wb' if isinstance(data, bytes) else 'w') as f:
        f.write(data)
    return path


def get(path):
    with open(path, 'rb') as f:
        return f.read()
