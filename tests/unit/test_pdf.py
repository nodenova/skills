"""Unit tests for the pdf skill's pdf_find.py (needs pdftotext; skipped without it)."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')), 'skills', 'pdf', 'scripts', 'pdf_find.py')


def make_pdf(path, pages):
    objs = ['<< /Type /Catalog /Pages 2 0 R >>', f'<< /Type /Pages /Kids [{" ".join(f"{3 + 2 * i} 0 R" for i in range(len(pages)))}] /Count {len(pages)} >>']
    for i, text in enumerate(pages):
        objs.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {4 + 2 * i} 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>')
        stream = f'BT /F1 12 Tf 72 700 Td ({text}) Tj ET'
        objs.append(f'<< /Length {len(stream)} >>\nstream\n{stream}\nendstream')
    out, offsets = b'%PDF-1.4\n', []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f'{i} 0 obj\n{o}\nendobj\n'.encode()
    x = len(out)
    out += f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'.encode() + b''.join(f'{o:010d} 00000 n \n'.encode() for o in offsets)
    out += f'trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n'.encode()
    with open(path, 'wb') as f:
        f.write(out)


def run(*args):
    r = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return r.returncode, r.stdout + r.stderr


@unittest.skipUnless(shutil.which('pdftotext'), 'pdftotext not installed')
class PdfFind(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pdf = os.path.join(self.tmp.name, 'a.pdf')
        make_pdf(self.pdf, ['First page', 'Termination clause here', 'Another Termination note'])

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_pages(self):
        code, out = run(self.pdf, 'termination')
        self.assertEqual(code, 0, out)
        self.assertIn('page 2: Termination clause here', out)
        self.assertIn('pages: 2, 3', out)
        code, out = run(self.pdf, 'termination', '--pages', '3')
        self.assertIn('pages: 3', out)

    def test_errors_are_one_line(self):
        for args in ([self.pdf, 'absent phrase'], [os.path.join(self.tmp.name, 'none.pdf'), 'x'], [self.tmp.name, 'x'], [__file__, 'x']):
            code, out = run(*args)
            self.assertEqual(code, 1, args)
            self.assertTrue(out.startswith('ERROR:'), out)
            self.assertNotIn('Traceback', out)


if __name__ == '__main__':
    unittest.main()
