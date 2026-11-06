"""pdf_find.py FILE.pdf TEXT [--pages A-B]

Find TEXT (any case) in a PDF's text layer: prints "page N: line" for each
matching line, then the list of pages. Needs pdftotext; for a scanned PDF
(no text layer) it says so and you should OCR it first (see SKILL.md).
"""
import os
import re
import subprocess
import sys


def main():
    args = sys.argv[1:]
    span = []
    if '--pages' in args:
        i = args.index('--pages')
        m = re.fullmatch(r'(\d+)(?:-(\d+))?', args[i + 1]) if i + 1 < len(args) else None
        if not m:
            sys.exit('ERROR: --pages takes a range like 3-5')
        span = ['-f', m.group(1), '-l', m.group(2) or m.group(1)]
        del args[i:i + 2]
    if len(args) != 2 or not args[1]:
        sys.exit(__doc__)
    path, needle = args
    if not os.path.isfile(path):
        sys.exit(f'ERROR: not found: {path}. A path that starts with an unexpected "/" means a shell variable was empty: every shell call starts fresh.')
    done = subprocess.run(['pdftotext', '-layout', *span, path, '-'], capture_output=True, text=True)
    if done.returncode != 0:
        sys.exit('ERROR: pdftotext could not read the file: ' + (done.stderr.strip().splitlines() or ['unknown error'])[0])
    first = int(span[1]) if span else 1
    pages = done.stdout.split('\f')
    if not any(p.strip() for p in pages):
        sys.exit('ERROR: no text layer in this PDF (scanned pages). OCR it first: see "Scanned PDFs" in SKILL.md.')
    hit_pages = []
    for n, page in enumerate(pages, first):
        found = [line.strip() for line in page.splitlines() if needle.lower() in line.lower()]
        for line in found:
            print(f'page {n}: {line[:200]}')
        if found:
            hit_pages.append(n)
    if not hit_pages:
        sys.exit(f'ERROR: {needle!r} not found in the text layer. Try a shorter or differently spelled phrase.')
    print('pages:', ', '.join(map(str, hit_pages)))


if __name__ == '__main__':
    try:
        main()
    except (SystemExit, KeyboardInterrupt):
        raise
    except FileNotFoundError as e:
        sys.exit(f'ERROR: file or program not found: {e.filename}')
    except Exception as e:
        if '--debug' in sys.argv or os.environ.get('NN_DEBUG'):
            raise
        sys.exit(f'ERROR: {type(e).__name__}: {e}')
