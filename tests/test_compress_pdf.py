"""Tests for compress_pdf.py on generated PDFs.  Run from the repo folder:  python -m pytest  (needs pymupdf)"""
import io
import sys
from pathlib import Path

import pikepdf
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import compress_pdf as cp  # noqa: E402

pymupdf = pytest.importorskip("pymupdf")


def photo(w=600, h=400):
    """Smooth gradient + a little noise: compresses badly as Flate/PNG, well as JPEG."""
    import random
    rnd = random.Random(1)
    img = Image.new("RGB", (w, h))
    img.putdata([((x * 255) // w, (y * 255) // h, (rnd.randrange(40) + 100)) for y in range(h) for x in range(w)])
    return img


def make_pdf(path, images):
    doc = pymupdf.open()
    for img, fmt in images:
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        page = doc.new_page()
        page.insert_image(page.rect, stream=buf.getvalue())
    doc.save(path)


def image_filters(path):
    with pikepdf.open(path) as pdf:
        out = []
        for page in pdf.pages:
            for _, x in page.Resources.XObject.items():
                if x.get("/Subtype") == "/Image":
                    out.append(str(x.get("/Filter")))
        return out


def test_png_photo_recompressed_to_jpeg(tmp_path):
    src, dst = tmp_path / "in.pdf", tmp_path / "out.pdf"
    make_pdf(src, [(photo(), "PNG")])
    before, after = cp.compress_pdf(src, dst, quality=75, verbose=False)
    assert after < before / 2
    assert image_filters(dst) == ["/DCTDecode"]
    pix = pymupdf.open(dst)[0].get_pixmap(dpi=20)          # still renders
    assert pix.width > 0


def test_image_never_replaced_by_a_bigger_one(tmp_path):
    # a low-quality JPEG re-encoded at quality 95 would grow, so the original bytes must stay
    src, dst = tmp_path / "in.pdf", tmp_path / "out.pdf"
    buf = io.BytesIO()
    photo(200, 150).save(buf, format="JPEG", quality=30)
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_image(page.rect, stream=buf.getvalue())
    doc.save(src)
    with pikepdf.open(src) as pdf:
        orig = bytes(next(iter(pdf.pages[0].Resources.XObject.values())).read_raw_bytes())
    cp.compress_pdf(src, dst, quality=95, verbose=False)
    with pikepdf.open(dst) as pdf:
        assert bytes(next(iter(pdf.pages[0].Resources.XObject.values())).read_raw_bytes()) == orig


def test_encode_jpeg_modes():
    assert cp.encode_jpeg(Image.new("RGBA", (4, 4)), 80) is None      # alpha: never JPEG
    assert cp.encode_jpeg(Image.new("P", (4, 4)), 80) is None
    for mode in ("RGB", "L", "CMYK", "I;16"):
        data = cp.encode_jpeg(Image.new(mode, (8, 8)), 80)
        assert data[:2] == b"\xff\xd8", mode
