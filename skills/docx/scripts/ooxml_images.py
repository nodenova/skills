"""Pictures in Word and PowerPoint files: list them, replace one picture's file.

  docx_images.py / pptx_images.py list FILE
  docx_images.py / pptx_images.py replace IN OUT --image MEDIA --with NEW [--keep-size | --fit]

list prints every picture with the image file behind it, its pixel size, the
size it is shown at, where it sits (body paragraph, header, footer, slide,
layout, master), its name and alt text, and the text next to it. Nothing
binary is ever printed.

replace swaps the bytes of one image file (MEDIA, as listed) for NEW. Every
place that shows that file changes, and each relationship id stays. If NEW
has another format, the part is renamed, relationships follow it and the
content type is added. The shown size is kept unless --fit, which keeps NEW's
proportions inside the old box (and drops any crop). The result is written by
ooxml.repack: untouched parts stay byte-identical and the usual checks run.
"""
import bisect
import os
import posixpath
import re
import struct
import sys
import zipfile
from xml.sax.saxutils import escape, unescape

import ooxml

EXT = {'png': 'png', 'jpeg': 'jpeg', 'gif': 'gif', 'bmp': 'bmp', 'tiff': 'tiff', 'emf': 'emf', 'wmf': 'wmf'}
CONTENT_TYPE = {'png': 'image/png', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'bmp': 'image/bmp',
                'tiff': 'image/tiff', 'emf': 'image/x-emf', 'wmf': 'image/x-wmf'}
LIMIT = 80


def sniff(data):
    """(format, width, height) from the first bytes; format None when unknown."""
    if data[:8] == b'\x89PNG\r\n\x1a\n' and len(data) >= 24:
        return ('png',) + struct.unpack('>II', data[16:24])
    if data[:6] in (b'GIF87a', b'GIF89a') and len(data) >= 10:
        return ('gif',) + struct.unpack('<HH', data[6:10])
    if data[:2] == b'BM' and len(data) >= 26:
        w, h = struct.unpack('<ii', data[18:26])
        return 'bmp', abs(w), abs(h)
    if data[:2] == b'\xff\xd8':
        i = 2
        while i + 4 <= len(data) and data[i] == 0xFF:
            m = data[i + 1]
            if m == 0xFF:
                i += 1
            elif m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
                i += 2
            elif 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack('>HH', data[i + 5:i + 9])
                return 'jpeg', w, h
            else:
                i += 2 + struct.unpack('>H', data[i + 2:i + 4])[0]
        return 'jpeg', None, None
    if data[:4] in (b'II*\x00', b'MM\x00*'):
        return 'tiff', None, None
    if data[40:44] == b' EMF':
        return 'emf', None, None
    if data[:4] == b'\xd7\xcd\xc6\x9a':
        return 'wmf', None, None
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp', None, None
    head = data[:2048].lstrip()
    if b'<svg' in head or (head.startswith(b'<?xml') and b'<svg' in data[:8192]):
        tag = re.search(rb'<svg\b[^>]*>', data[:8192])
        w = h = None
        if tag:
            num = lambda k: re.search(rb'\b' + k + rb'="\s*([\d.]+)', tag.group(0))
            if num(b'width') and num(b'height'):
                w, h = float(num(b'width').group(1)), float(num(b'height').group(1))
            else:
                vb = re.search(rb'viewBox="\s*[-\d.]+[ ,]+[-\d.]+[ ,]+([\d.]+)[ ,]+([\d.]+)', tag.group(0))
                if vb:
                    w, h = float(vb.group(1)), float(vb.group(2))
        return 'svg', (round(w) if w else None), (round(h) if h else None)
    return None, None, None


def attr(tag, name):
    m = re.search(rf'(?<![\w:]){name}="([^"]*)"', tag)
    return unescape(m.group(1), {'&quot;': '"', '&apos;': "'"}) if m else ''


def rels_of(z, part):
    """{rId: (resolved target, type, external)} for one part."""
    name = ooxml.rels_part_for(part)
    if name not in z.namelist():
        return {}
    out = {}
    for tag in re.findall(r'<Relationship\b[^>]*>', z.read(name).decode('utf-8')):
        ext = attr(tag, 'TargetMode') == 'External'
        out[attr(tag, 'Id')] = (attr(tag, 'Target') if ext else ooxml.resolve_target(name, attr(tag, 'Target')),
                                attr(tag, 'Type').rsplit('/', 1)[-1], ext)
    return out


def human_size(n):
    return f'{n} B' if n < 1024 else f'{n / 1024:.0f} KB' if n < 1048576 else f'{n / 1048576:.1f} MB'


def shown(cx, cy):
    if not cx or not cy:
        return 'size inherited from the layout or not given'
    return f'{cx / 914400:.2f} x {cy / 914400:.2f} in ({cx} x {cy} EMU)'


def kind_of(part):
    return 'docx' if part.startswith('word/') else 'pptx'


def content_parts(z, kind):
    """[(part, label)] in reading order."""
    names = z.namelist()
    num = lambda n: int(re.search(r'(\d+)\.xml$', n).group(1)) if re.search(r'(\d+)\.xml$', n) else 0
    out = []
    if kind == 'docx':
        used = {}
        if 'word/document.xml' in names:
            doc = z.read('word/document.xml').decode('utf-8')
            drels = rels_of(z, 'word/document.xml')
            for tag in re.findall(r'<w:(?:header|footer)Reference\b[^>]*>', doc):
                rid = re.search(r'r:id="([^"]*)"', tag)
                if rid and rid.group(1) in drels:
                    word = 'header' if 'headerReference' in tag else 'footer'
                    used.setdefault(drels[rid.group(1)][0], []).append(f'{attr(tag, "w:type") or "default"} {word}')
            out.append(('word/document.xml', 'body'))
        for pat in (r'word/header\d*\.xml', r'word/footer\d*\.xml', r'word/footnotes\.xml', r'word/endnotes\.xml'):
            for n in sorted((n for n in names if re.fullmatch(pat, n)), key=num):
                out.append((n, ', '.join(used.get(n, [])) or n.rsplit('/', 1)[-1][:-4]))
        return out
    if 'ppt/presentation.xml' in names:
        pres = z.read('ppt/presentation.xml').decode('utf-8')
        prels = rels_of(z, 'ppt/presentation.xml')
        for i, rid in enumerate(re.findall(r'<p:sldId\b[^>]*?r:id="([^"]+)"', pres), 1):
            if rid in prels:
                out.append((prels[rid][0], f'slide {i}'))
    for n in sorted((n for n in names if re.fullmatch(r'ppt/slideLayouts/slideLayout\d+\.xml', n)), key=num):
        title = re.search(r'<p:cSld\b[^>]*name="([^"]*)"', z.read(n).decode('utf-8'))
        out.append((n, f'layout {num(n)}' + (f' "{unescape(title.group(1))}"' if title else '')))
    for n in sorted((n for n in names if re.fullmatch(r'ppt/slideMasters/slideMaster\d+\.xml', n)), key=num):
        out.append((n, f'master {num(n)}'))
    return out


def snippet(s, width=60):
    s = ' '.join(s.split())
    return s if len(s) <= width else s[:width] + '...'


def scan(xml, part, rels, kind):
    """Placements of pictures in one part: dicts with rid, name, alt, cx, cy, how, near, start, end."""
    found = []
    if kind == 'docx':
        clean = re.sub(r'<mc:Fallback>.*?</mc:Fallback>', lambda m: ' ' * len(m.group(0)), xml, flags=re.S)
        spans = [(m.start(), m.end()) for m in ooxml.paragraph_matches(xml, ooxml.DOCX)]
        texts = [ooxml.paragraph_text(xml[a:b], ooxml.DOCX).strip() for a, b in spans]
        starts = [a for a, _ in spans]

        def near(pos):
            i = bisect.bisect_right(starts, pos) - 1
            if i < 0:
                return 0, ''
            if texts[i]:
                return i + 1, texts[i]
            before = next((texts[j] for j in range(i - 1, -1, -1) if texts[j]), '')
            after = next((texts[j] for j in range(i + 1, len(texts)) if texts[j]), '')
            return i + 1, ' | '.join(x for x in (f'before: {snippet(before)}' if before else '', f'after: {snippet(after)}' if after else '') if x)
        for m in re.finditer(r'<w:drawing>.*?</w:drawing>', clean, re.S):
            block = m.group(0)
            rids = re.findall(r'<a:blip\b[^>]*?r:embed="([^"]+)"', block)
            if not rids:
                continue
            ext = re.search(r'<wp:extent\s+cx="(\d+)"\s+cy="(\d+)"', block)
            doc_pr = re.search(r'<wp:docPr\b[^>]*>', block)
            n, around = near(m.start())
            for rid in rids:
                found.append({'rid': rid, 'name': attr(doc_pr.group(0), 'name') if doc_pr else '',
                              'alt': (attr(doc_pr.group(0), 'descr') or attr(doc_pr.group(0), 'title')) if doc_pr else '',
                              'cx': int(ext.group(1)) if ext else None, 'cy': int(ext.group(2)) if ext else None,
                              'how': 'floating' if '<wp:anchor' in block else 'inline', 'par': n, 'near': around,
                              'start': m.start(), 'end': m.end(), 'vml': False})
        for m in re.finditer(r'<w:pict>.*?</w:pict>', clean, re.S):
            block = m.group(0)
            n, around = near(m.start())
            for tag in re.findall(r'<v:imagedata\b[^>]*>', block):
                rid = attr(tag, 'r:id')
                if not rid:
                    continue
                style = re.search(r'<v:shape\b[^>]*style="([^"]*)"', block)
                dim = lambda k: re.search(rf'{k}:\s*([\d.]+)pt', style.group(1)) if style else None
                shape = re.search(r'<v:shape\b[^>]*>', block)
                found.append({'rid': rid, 'name': attr(tag, 'o:title') or (attr(shape.group(0), 'id') if shape else ''), 'alt': attr(shape.group(0), 'alt') if shape else '',
                              'cx': int(float(dim('width').group(1)) * 12700) if dim('width') else None,
                              'cy': int(float(dim('height').group(1)) * 12700) if dim('height') else None,
                              'how': 'legacy VML picture (watermark?)', 'par': n, 'near': around,
                              'start': m.start(), 'end': m.end(), 'vml': True})
        return sorted(found, key=lambda f: f['start'])
    first = [t for t in ooxml.paragraph_texts(xml, ooxml.PPTX) if t.strip()][:2]
    around = snippet(' / '.join(first), 80)
    taken = []
    for m in re.finditer(r'<p:pic>.*?</p:pic>', xml, re.S):
        block = m.group(0)
        taken.append((m.start(), m.end()))
        rids = re.findall(r'<a:blip\b[^>]*?r:embed="([^"]+)"', block)
        cnv = re.search(r'<p:cNvPr\b[^>]*>', block)
        ext = re.search(r'<a:ext\s+cx="(\d+)"\s+cy="(\d+)"', block)
        for rid in rids:
            found.append({'rid': rid, 'name': attr(cnv.group(0), 'name') if cnv else '', 'alt': attr(cnv.group(0), 'descr') if cnv else '',
                          'cx': int(ext.group(1)) if ext else None, 'cy': int(ext.group(2)) if ext else None,
                          'how': 'picture', 'near': around, 'start': m.start(), 'end': m.end(), 'vml': False})
    for m in re.finditer(r'<a:blip\b[^>]*?r:embed="([^"]+)"', xml):
        if any(a <= m.start() < b for a, b in taken):
            continue
        cnv = [c for c in re.finditer(r'<p:cNvPr\b[^>]*>', xml[:m.start()])]
        in_bg = xml.rfind('<p:bg>', 0, m.start()) > xml.rfind('</p:bg>', 0, m.start())
        found.append({'rid': m.group(1), 'name': 'background' if in_bg else (attr(cnv[-1].group(0), 'name') if cnv else ''), 'alt': '',
                      'cx': None, 'cy': None, 'how': 'picture fill', 'near': around, 'start': m.start(), 'end': m.end(), 'vml': False})
    return sorted(found, key=lambda f: f['start'])


def placements(z, kind):
    out = []
    for part, label in content_parts(z, kind):
        rels = rels_of(z, part)
        for f in scan(z.read(part).decode('utf-8'), part, rels, kind):
            target = rels.get(f['rid'])
            f.update(part=part, label=label, media=target[0] if target and not target[2] else None,
                     external=bool(target and target[2]))
            where = f'{label}' + (f', paragraph {f["par"]}' if f.get('par') else '')
            f['where'] = where
            out.append(f)
    return out


def describe_media(z, media):
    if not media or media not in z.namelist():
        return 'file missing from the package'
    data = z.read(media)
    fmt, w, h = sniff(data)
    return f'{fmt or "unknown format"}{f" {w}x{h} px" if w and h else ""}, {human_size(len(data))}'


def list_pictures(src, kind):
    ooxml.need_zip(src, 'FILE')
    with zipfile.ZipFile(src) as z:
        items = [p for p in placements(z, kind) if p['media'] or p['external']]
        if not items:
            print(f'No pictures in {src}. (Only images placed in the body, headers, footers'
                  f'{", slides, layouts or masters" if kind == "pptx" else " or notes"} are listed; charts and shapes drawn in Office are not images.)')
            return
        files = {p['media'] for p in items if p['media']}
        print(f'{len(items)} picture(s) using {len(files)} image file(s):')
        for n, p in enumerate(items[:LIMIT], 1):
            print(f'{n}. {p["where"]}')
            print(f'   file: {p["media"] or "(linked, not stored in the file)"}  ({describe_media(z, p["media"])})')
            print(f'   shown: {shown(p["cx"], p["cy"])}, {p["how"]}')
            print(f'   name: {p["name"] or "-"}  alt: {p["alt"] or "-"}')
            if p['near']:
                print(f'   near: {snippet(p["near"], 90)}')
        if len(items) > LIMIT:
            print(f'... {len(items) - LIMIT} more not shown.')
        script = 'docx_images.py' if kind == 'docx' else 'pptx_images.py'
        print(f'To swap one: {script} replace IN OUT --image <file above> --with NEW.png [--fit]')


def pick_media(z, wanted):
    names = [n for n in z.namelist() if re.search(r'/media/[^/]+$', n)]
    if wanted in names:
        return wanted
    same = [n for n in names if n.rsplit('/', 1)[-1] == wanted.rsplit('/', 1)[-1]]
    if len(same) == 1:
        return same[0]
    listing = ', '.join(f'{n} ({human_size(z.getinfo(n).file_size)})' for n in names) or 'none'
    sys.exit(f'ERROR: no image file {wanted!r} in the package. Image files: {listing}. Run the list command to see which picture is which.')


def fit_box(cx, cy, w, h):
    if w / h >= cx / cy:
        return cx, max(1, round(cx * h / w))
    return max(1, round(cy * w / h)), cy


def resize_block(block, kind, old, new, off_delta):
    ox, oy = old
    nx, ny = new
    pattern = rf'(<(?:wp:extent|a:ext)\s+cx="){ox}(" cy="){oy}"'
    block = re.sub(pattern, rf'\g<1>{nx}\g<2>{ny}"', block)
    if kind == 'pptx':
        dx, dy = off_delta
        block = re.sub(rf'<a:off\s+x="(-?\d+)"\s+y="(-?\d+)"(\s*/>\s*<a:ext\s+cx="{nx}")',
                       lambda m: f'<a:off x="{int(m.group(1)) + dx}" y="{int(m.group(2)) + dy}"{m.group(3)}', block)
    return re.sub(r'<a:srcRect\b[^>]*/>', '', block)


def replace_picture(src, out, kind, media_arg, new_path, fit):
    ooxml.need_zip(src, 'IN')
    ooxml.need_distinct(src, out)
    if not os.path.isfile(new_path):
        sys.exit(f'ERROR: --with file not found: {new_path}')
    new = open(new_path, 'rb').read()
    fmt, nw, nh = sniff(new)
    if fmt == 'svg':
        sys.exit('ERROR: Word and PowerPoint cannot show a plain SVG here. Convert it to PNG first (for example `convert in.svg out.png`) and use that.')
    if fmt not in EXT:
        sys.exit(f'ERROR: {new_path} is not a PNG, JPEG, GIF, BMP, TIFF, EMF or WMF image' + (f' ({fmt} is not supported)' if fmt else '') + '. Convert it to PNG first.')
    changes, notes = {}, []
    with zipfile.ZipFile(src) as z:
        media = pick_media(z, media_arg)
        old_ext = media.rsplit('.', 1)[-1].lower()
        same = old_ext == EXT[fmt] or (old_ext == 'jpg' and fmt == 'jpeg')
        target = media
        if not same:
            stem = media.rsplit('.', 1)[0]
            target = f'{stem}.{EXT[fmt]}'
            while target in z.namelist():
                stem += '-new'
                target = f'{stem}.{EXT[fmt]}'
            changes[media] = None
            refs = 0
            for rels_name in [n for n in z.namelist() if n.endswith('.rels')]:
                text = z.read(rels_name).decode('utf-8')
                base = posixpath.dirname(ooxml.source_of_rels(rels_name))

                def retarget(m):
                    nonlocal refs
                    tag = m.group(0)
                    if attr(tag, 'TargetMode') == 'External' or ooxml.resolve_target(rels_name, attr(tag, 'Target')) != media:
                        return tag
                    refs += 1
                    old_t = attr(tag, 'Target')
                    new_t = '/' + target if old_t.startswith('/') else posixpath.relpath(target, base or '.')
                    return tag.replace(f'Target="{old_t}"', f'Target="{new_t}"')
                fixed = re.sub(r'<Relationship\b[^>]*>', retarget, text)
                if fixed != text:
                    changes[rels_name] = fixed.encode('utf-8')
            if not refs:
                sys.exit(f'ERROR: no relationship points to {media}, so no picture shows it. Nothing changed.')
            types = z.read('[Content_Types].xml').decode('utf-8')
            have = {e.lower() for e in re.findall(r'<Default\b[^>]*?Extension="([^"]*)"', types)}
            if EXT[fmt] not in have:
                tag = f'<Default Extension="{EXT[fmt]}" ContentType="{CONTENT_TYPE[fmt]}"/>'
                at = types.find('<Override')
                types = types[:at] + tag + types[at:] if at >= 0 else types.replace('</Types>', tag + '</Types>')
                changes['[Content_Types].xml'] = types.encode('utf-8')
        changes[target] = new
        old_fmt, ow, oh = sniff(z.read(media))
        resized = []
        for part, _ in content_parts(z, kind):
            rels = rels_of(z, part)
            xml = z.read(part).decode('utf-8')
            mine = [p for p in scan(xml, part, rels, kind) if rels.get(p['rid'], ('',))[0] == media]
            if any('svgBlip' in xml[p['start']:p['end']] for p in mine):
                notes.append(f'{part}: the picture also has an SVG version that Office may show instead; only the main image was replaced')
            if not fit or not mine:
                continue
            edited = xml
            for p in sorted(mine, key=lambda p: -p['start']):
                if p['vml'] or not p['cx'] or not p['cy']:
                    notes.append(f'{part}: a picture without a known size or a legacy VML picture was not resized')
                    continue
                if not (nw and nh):
                    notes.append('--fit skipped: the size of the new image could not be read; the old size is kept')
                    break
                size = fit_box(p['cx'], p['cy'], nw, nh)
                delta = ((p['cx'] - size[0]) // 2, (p['cy'] - size[1]) // 2)
                block = resize_block(edited[p['start']:p['end']], kind, (p['cx'], p['cy']), size, delta)
                edited = edited[:p['start']] + block + edited[p['end']:]
                resized.append(f'{part}: {shown(p["cx"], p["cy"]).split(" (")[0]} -> {shown(*size).split(" (")[0]}')
            if edited != xml:
                changes[part] = edited.encode('utf-8')
        place = [p for p in placements(z, kind) if p['media'] == media]
    print(f'replaced {media} ({old_fmt or "?"}{f" {ow}x{oh} px" if ow and oh else ""}) with {os.path.basename(new_path)} '
          f'({fmt}{f" {nw}x{nh} px" if nw and nh else ""}), saved as {target}; shown in {len(place)} place(s): '
          + '; '.join(dict.fromkeys(p['where'] for p in place)))
    print('size:', '; '.join(resized) if resized else 'kept as it was')
    for n in dict.fromkeys(notes):
        print('note:', n)
    ooxml.repack(src, out, changes)


def run(kind, doc):
    args = sys.argv[1:]
    if args and args[0] == 'list' and len(args) == 2:
        return list_pictures(args[1], kind)
    if args and args[0] == 'replace':
        rest, opts = [], {}
        i = 1
        while i < len(args):
            if args[i] in ('--image', '--with') and i + 1 < len(args):
                opts[args[i]] = args[i + 1]
                i += 2
            elif args[i] in ('--fit', '--keep-size'):
                opts[args[i]] = True
                i += 1
            else:
                rest.append(args[i])
                i += 1
        if len(rest) == 2 and '--image' in opts and '--with' in opts and not ('--fit' in opts and '--keep-size' in opts):
            return replace_picture(rest[0], rest[1], kind, opts['--image'], opts['--with'], '--fit' in opts)
    sys.exit(doc)
