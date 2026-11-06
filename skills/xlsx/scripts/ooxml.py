"""Edit Office files (docx, xlsx, pptx) one XML part at a time.

  ooxml.py unpack FILE DIR                 every part of FILE into DIR
  ooxml.py replace PART OLD NEW [--all]    exact text replace in one part; OLD must occur once
  ooxml.py pack ORIGINAL DIR OUT           rebuild: untouched parts copied as they were,
                                           changed parts checked, nothing written on a problem
  ooxml.py validate [ORIGINAL] FILE        check FILE; with ORIGINAL, report only new problems

OLD/NEW starting with @ are read from that file (one final newline dropped).

Checks: every changed XML part is well formed and, with lxml and the ECMA-376
schemas present, valid against its schema (after the markup-compatibility
rules: ignorable namespaces dropped, AlternateContent resolved to Fallback);
relationships point at parts that exist; every part has a content type; every
r:id in a part names a relationship of that part. Without lxml or the schemas
only the other checks run, and it says so.

Schemas: $NN_OOXML_SCHEMAS, else /opt/nodenova/ooxml-schemas
(transitional/*.xsd from ECMA-376 Part 4, opc/*.xsd from Part 2, w3c/xml.xsd).
"""
import os
import posixpath
import re
import sys
import zipfile
from collections import Counter

try:
    from lxml import etree as LX
except ImportError:  # the checks that need it are skipped and reported
    LX = None
try:
    from defusedxml.ElementTree import fromstring as safe_parse
except ImportError:
    from xml.etree.ElementTree import fromstring as safe_parse

SCHEMAS = os.environ.get('NN_OOXML_SCHEMAS', '/opt/nodenova/ooxml-schemas')
MC = 'http://schemas.openxmlformats.org/markup-compatibility/2006'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG_RELS = 'http://schemas.openxmlformats.org/package/2006/relationships'
PKG_TYPES = 'http://schemas.openxmlformats.org/package/2006/content-types'
OX = 'http://schemas.openxmlformats.org/'
SCHEMA_FOR_NS = {
    OX + 'wordprocessingml/2006/main': 'transitional/wml.xsd',
    OX + 'spreadsheetml/2006/main': 'transitional/sml.xsd',
    OX + 'presentationml/2006/main': 'transitional/pml.xsd',
    OX + 'drawingml/2006/main': 'transitional/dml-main.xsd',
    OX + 'drawingml/2006/chart': 'transitional/dml-chart.xsd',
    OX + 'officeDocument/2006/extended-properties': 'transitional/shared-documentPropertiesExtended.xsd',
    PKG_RELS: 'opc/opc-relationships.xsd',
    PKG_TYPES: 'opc/opc-contentTypes.xsd',
}


# ---------- unpack / replace / pack ----------

def arg(s):
    if not s.startswith('@'):
        return s
    t = open(s[1:], encoding='utf-8').read()
    return t[:-1] if t.endswith('\n') else t


def unpack(src, d):
    with zipfile.ZipFile(src) as z:
        for n in z.namelist():
            if n.endswith('/') or '..' in n.split('/') or n.startswith('/'):
                continue
            os.makedirs(os.path.join(d, os.path.dirname(n)), exist_ok=True)
            with open(os.path.join(d, n), 'wb') as f:
                f.write(z.read(n))
        print('unpacked', len(z.namelist()), 'parts to', d)


def replace(part, old, new, every):
    s = open(part, encoding='utf-8').read()
    n = s.count(old)
    if n == 0 or (n > 1 and not every):
        sys.exit(f'ERROR: found {n} times in {part}; need exactly 1 (or --all). Nothing changed.')
    open(part, 'w', encoding='utf-8').write(s.replace(old, new))
    print(f'replaced {n} in {part}')


def pack(src, d, out):
    zin = zipfile.ZipFile(src)
    names = [n for n in zin.namelist() if not n.endswith('/')]
    folders = {n for n in zin.namelist() if n.endswith('/')}
    on_disk = set()
    for root, _, files in os.walk(d):
        for f in files:
            on_disk.add(os.path.relpath(os.path.join(root, f), d).replace(os.sep, '/'))
    changed = []
    tmp = out + '.part'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        # The original's entry order and entry settings, exactly (folder
        # entries too, which some producers write); new parts last.
        order = zin.namelist() + sorted(on_disk - set(names))
        for n in order:
            if n in folders:
                info = zin.getinfo(n)
                attr = info.external_attr
                zout.writestr(info, b'')
                zout.getinfo(n).external_attr = attr
                continue
            if n not in on_disk:
                print('removed', n)
                continue
            data = open(os.path.join(d, n), 'rb').read()
            if n not in names or data != zin.read(n):
                changed.append(n)
            if n in names:
                info = zin.getinfo(n)
                attr = info.external_attr
                zout.writestr(info, data)
                # writestr fills in Unix permissions when the original had none.
                zout.getinfo(n).external_attr = attr
            else:
                zout.writestr(n, data)
    problems, notes = check(tmp, src)
    for note in notes:
        print('note:', note)
    if problems:
        os.remove(tmp)
        sys.exit('ERROR: nothing written. Fix these and pack again:\n' + '\n'.join('- ' + p for p in problems))
    os.replace(tmp, out)
    print('wrote', out, '| changed:', ', '.join(changed) or 'nothing', '| checks passed')


# ---------- checks ----------

def read_parts(path):
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad:
            raise SystemExit(f'ERROR: {path}: damaged zip entry {bad}')
        return {n: z.read(n) for n in z.namelist() if not n.endswith('/')}


def is_xml(name):
    return name.endswith(('.xml', '.rels', '.vml')) or name == '[Content_Types].xml'


def rels_part_for(name):
    d, f = posixpath.split(name)
    return posixpath.join(d, '_rels', f + '.rels')


def source_of_rels(rels_name):
    d, f = posixpath.split(rels_name)
    return posixpath.join(posixpath.dirname(d), f[:-len('.rels')])


def resolve_target(rels_name, target):
    if target.startswith('/'):
        return target.lstrip('/')
    base = posixpath.dirname(source_of_rels(rels_name))
    return posixpath.normpath(posixpath.join(base, target)).lstrip('./') if base else posixpath.normpath(target)


def local(tag):
    return tag.rsplit('}', 1)[-1]


def package_problems(parts):
    """Wiring problems as plain strings (no line numbers, so two files compare)."""
    out = []
    trees = {}
    for n, data in parts.items():
        if is_xml(n):
            try:
                trees[n] = safe_parse(data)
            except Exception as e:  # noqa: BLE001 - report any parse failure
                out.append(f'{n}: not well-formed XML ({str(e).split(",")[0]})')
    ct = trees.get('[Content_Types].xml')
    if ct is None:
        out.append('[Content_Types].xml is missing')
    else:
        defaults = {e.get('Extension', '').lower() for e in ct if local(e.tag) == 'Default'}
        overrides = {e.get('PartName', '').lstrip('/') for e in ct if local(e.tag) == 'Override'}
        for o in sorted(overrides - set(parts)):
            out.append(f'[Content_Types].xml: Override for missing part /{o}')
        for n in parts:
            # Office keeps discarded data in `[trash]/` parts with no content type.
            if n == '[Content_Types].xml' or n in overrides or n.startswith('[trash]/'):
                continue
            if n.rsplit('.', 1)[-1].lower() not in defaults:
                out.append(f'{n}: no content type (add an Override or a Default for .{n.rsplit(".", 1)[-1]})')
    rel_ids = {}
    for n, t in trees.items():
        if not n.endswith('.rels'):
            continue
        ids = Counter(e.get('Id') for e in t)
        for i, c in ids.items():
            if c > 1:
                out.append(f'{n}: relationship Id {i} used {c} times')
        rel_ids[source_of_rels(n)] = set(ids)
        for e in t:
            if e.get('TargetMode') == 'External':
                continue
            tgt = resolve_target(n, e.get('Target', ''))
            if tgt not in parts:
                out.append(f'{n}: {e.get("Id")} points to missing part {tgt}')
    for n, t in trees.items():
        if n.endswith('.rels') or n == '[Content_Types].xml':
            continue
        have = rel_ids.get(n, set())
        for el in t.iter():
            for k, v in el.attrib.items():
                if k.startswith('{' + R + '}') and v and v not in have:
                    out.append(f'{n}: <{local(el.tag)} r:{local(k)}="{v}"> has no relationship in {rels_part_for(n)}')
    return out


_schema_cache = {}


def load_schema(rel, ns):
    """The ECMA files import the xml: namespace without a location, so load each
    through a wrapper that imports W3C's xml.xsd first (the ECMA files stay as published)."""
    if rel not in _schema_cache:
        loc = lambda p: 'file://' + os.path.abspath(os.path.join(SCHEMAS, p))
        wrapper = ('<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" targetNamespace="urn:nodenova:ooxml-check">'
                   f'<xsd:import namespace="http://www.w3.org/XML/1998/namespace" schemaLocation="{loc("w3c/xml.xsd")}"/>'
                   f'<xsd:import namespace="{ns}" schemaLocation="{loc(rel)}"/></xsd:schema>')
        parser = LX.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
        _schema_cache[rel] = LX.XMLSchema(LX.fromstring(wrapper.encode(), parser, base_url=loc('wrapper.xsd')))
    return _schema_cache[rel]


def apply_mce(root):
    """Markup compatibility: what a consumer that knows only the base schema sees."""
    ignorable = set()
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        for prefix in (el.get('{%s}Ignorable' % MC) or '').split():
            if el.nsmap.get(prefix):
                ignorable.add(el.nsmap[prefix])
    for ac in list(root.iter('{%s}AlternateContent' % MC)):
        parent = ac.getparent()
        if parent is None:
            continue
        fallback = ac.find('{%s}Fallback' % MC)
        at = parent.index(ac)
        parent.remove(ac)
        for i, kid in enumerate(list(fallback) if fallback is not None else []):
            parent.insert(at + i, kid)
    drop = []
    sml = OX + 'spreadsheetml/2006/main'
    for el in root.iter():
        # Excel writes xml:space on SpreadsheetML <t>, which its schema omits.
        if isinstance(el.tag, str) and LX.QName(el).namespace == sml:
            el.attrib.pop('{http://www.w3.org/XML/1998/namespace}space', None)
        if not isinstance(el.tag, str):
            drop.append(el)  # comments, processing instructions
            continue
        ns = LX.QName(el).namespace
        if ns in ignorable or ns == MC:
            drop.append(el)
            continue
        for a in list(el.attrib):
            ans = LX.QName(a).namespace
            if ans in ignorable or ans == MC:
                del el.attrib[a]
    for el in drop:
        if el.getparent() is not None:
            el.getparent().remove(el)
    return root


def schema_problems(name, data):
    parser = LX.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, remove_blank_text=False)
    root = LX.fromstring(data, parser)
    ns = LX.QName(root).namespace
    rel = SCHEMA_FOR_NS.get(ns)
    if rel is None or not os.path.exists(os.path.join(SCHEMAS, rel)):
        return None
    schema = load_schema(rel, ns)
    if schema.validate(LX.ElementTree(apply_mce(root))):
        return []
    msgs = []
    for e in schema.error_log:
        m = re.sub(r'\{[^}]*\}', '', e.message)
        msgs.append(f'{name}: {m}')
    return msgs


def check(path, original=None):
    """(problems, notes). With an original, only problems it did not have."""
    new = read_parts(path)
    old = read_parts(original) if original else {}
    notes = []
    problems = package_problems(new)
    if original:
        before = Counter(package_problems(old))
        problems = [p for p in problems if not before.get(p) or before.subtract([p])]
    targets = [n for n in new if is_xml(n) and (not original or old.get(n) != new[n])]
    if LX is None:
        notes.append('lxml is not installed: schema check skipped (well-formedness and wiring were checked)')
    elif not os.path.isdir(SCHEMAS):
        notes.append(f'no schemas at {SCHEMAS}: schema check skipped (well-formedness and wiring were checked)')
    else:
        for n in sorted(targets):
            try:
                found = schema_problems(n, new[n])
            except LX.XMLSyntaxError:
                continue  # already reported as not well-formed
            if not found:
                continue
            if n in old:
                try:
                    before = Counter(schema_problems(n, old[n]) or [])
                except LX.XMLSyntaxError:
                    before = Counter()
                found = [p for p in found if not before.get(p) or before.subtract([p])]
            problems += found
    counted = Counter(problems)
    problems = [p + (f' (x{counted[p]})' if counted[p] > 1 else '') for p in dict.fromkeys(problems)]
    if len(problems) > 30:
        problems = problems[:30] + [f'... {len(problems) - 30} more']
    return problems, notes


def validate(args):
    original, path = (args[0], args[1]) if len(args) == 2 else (None, args[0])
    problems, notes = check(path, original)
    for note in notes:
        print('note:', note)
    if problems:
        print(('New problems' if original else 'Problems') + f' in {path}:')
        print('\n'.join('- ' + p for p in problems))
        sys.exit(1)
    print(f'{path}: checks passed' + (' (no new problems)' if original else ''))


if __name__ == '__main__':
    cmd, rest = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ('', [])
    if cmd == 'unpack' and len(rest) == 2:
        unpack(*rest)
    elif cmd == 'replace' and len(rest) >= 3:
        replace(rest[0], arg(rest[1]), arg(rest[2]), '--all' in rest[3:])
    elif cmd == 'pack' and len(rest) == 3:
        pack(*rest)
    elif cmd == 'validate' and len(rest) in (1, 2):
        validate(rest)
    else:
        sys.exit(__doc__)
