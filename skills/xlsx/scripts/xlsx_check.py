"""xlsx_check.py FILE.xlsx -- recalculate a scratch copy with LibreOffice and list
every formula with its fresh value, flagging errors. Never touches FILE."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

import ooxml


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ooxml.need_zip(sys.argv[1], 'FILE')
    if not shutil.which('soffice'):
        sys.exit('ERROR: `soffice` (LibreOffice) is not installed here, so formulas cannot be recalculated. '
                 'Skip this step; check the changed cells with xlsx_dump.py and tell the user the results were not recalculated.')
    src = sys.argv[1]
    work = tempfile.mkdtemp(dir=os.environ.get('TMPDIR') or None)
    nov = os.path.join(work, 'novalues.xlsx')
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(nov, 'w', zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data = zin.read(info)
            if re.match(r'xl/worksheets/sheet\d+\.xml$', info.filename):
                data = re.sub(rb'(<f[^>]*/>|<f[^>]*>[^<]*</f>)<v>[^<]*</v>', rb'\1', data)
            zout.writestr(info, data)
    os.mkdir(os.path.join(work, 'out'))
    done = subprocess.run(['soffice', '--headless', '--convert-to', 'xlsx', '--outdir', os.path.join(work, 'out'), nov],
                          capture_output=True, text=True, timeout=180)
    if done.returncode != 0 or not os.path.exists(os.path.join(work, 'out', 'novalues.xlsx')):
        sys.exit('ERROR: LibreOffice could not recalculate the file: ' + (done.stderr or done.stdout).strip()[:300])
    dump = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xlsx_dump.py'),
                           os.path.join(work, 'out', 'novalues.xlsx')], capture_output=True, text=True, check=True).stdout
    bad = [l for l in dump.splitlines() if '\t=' in l and re.search(r'-> (#\w+[!?/0]*|Err:\d+|#N/A)', l)]
    print(dump if '--all' in sys.argv else '\n'.join(l for l in dump.splitlines() if l.startswith('==') or '\t=' in l))
    print(f'\n{len(bad)} formula error(s)' + (':\n' + '\n'.join(bad) if bad else ''))
    shutil.rmtree(work)


if __name__ == '__main__':
    ooxml.cli(main)
