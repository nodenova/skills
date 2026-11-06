"""docx_images.py list FILE.docx
docx_images.py replace IN.docx OUT.docx --image word/media/image1.jpeg --with NEW.png [--keep-size | --fit]

list: every picture in the body, headers and footers: image file and pixel
size, shown size, where it is (body paragraph N, header1 default header, ...),
name, alt text, nearby text. Use it to find a logo; docx_find.py cannot, a
picture is not text. Never print an image file to the terminal.
replace: put NEW (png, jpeg, gif, bmp, tiff) in place of one image file (as
listed). Every place showing it changes; relationship ids stay. --keep-size
(default) keeps the shown size; --fit keeps NEW's proportions inside the old
box. Written through the checked pack.
"""
import ooxml
import ooxml_images

if __name__ == '__main__':
    ooxml.cli(lambda: ooxml_images.run('docx', __doc__))
