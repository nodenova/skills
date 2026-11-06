"""pptx_images.py list FILE.pptx
pptx_images.py replace IN.pptx OUT.pptx --image ppt/media/image1.jpeg --with NEW.png [--keep-size | --fit]

list: every picture on slides, layouts and masters: image file and pixel
size, shown size, where it is (slide N, layout, master), name, alt text,
nearby text. A logo is a picture, not text, so pptx_outline.py does not show
it. Never print an image file to the terminal.
replace: put NEW (png, jpeg, gif, bmp, tiff) in place of one image file (as
listed). Every place showing it changes; relationship ids stay. --keep-size
(default) keeps the shown size; --fit keeps NEW's proportions inside the old
box, centred. Written through the checked pack.
"""
import ooxml
import ooxml_images

if __name__ == '__main__':
    ooxml.cli(lambda: ooxml_images.run('pptx', __doc__))
