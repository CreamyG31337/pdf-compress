# /// script
# requires-python = ">=3.9"
# dependencies = ["pikepdf>=9.0", "pillow>=10.0"]
# ///
"""
Produce comparison variants of a PDF to test JPEG encoding options.
Output files are named to describe what was applied.
"""

import io
from pathlib import Path
import pikepdf
from pikepdf import PdfImage
from PIL import Image, ImageFilter


INPUT = Path("c:/Projects/pdf-compress/ZONE2-26-051 Earthwork Report.pdf")

VARIANTS = [
    # (label,  quality, subsampling,  unsharp)
    ("q90-420",         90,  2,  False),   # current default (4:2:0 chroma)
    ("q90-444",         90,  0,  False),   # 4:4:4 chroma only
    ("q90-420-sharp",   90,  2,  True),    # unsharp mask only
    ("q90-444-sharp",   90,  0,  True),    # both combined
    ("q95-444",         95,  0,  False),   # higher quality + 4:4:4
]


def pil_from_xobj(xobj):
    try:
        return PdfImage(xobj).as_pil_image()
    except Exception:
        pass
    try:
        return Image.open(io.BytesIO(xobj.read_raw_bytes()))
    except Exception:
        return None


def encode_jpeg(img, quality, subsampling, unsharp):
    if img.mode in ("RGBA", "LA", "P"):
        return None
    if img.mode not in ("RGB", "L", "CMYK"):
        img = img.convert("RGB")
    if unsharp:
        img = img.filter(ImageFilter.UnsharpMask(radius=0.5, percent=150, threshold=2))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=quality, subsampling=subsampling,
             optimize=True)
    return out.getvalue()


def process(input_path, output_path, quality, subsampling, unsharp):
    seen = set()
    with pikepdf.open(input_path) as pdf:
        for page in pdf.pages:
            # Page resources
            res = page.get("/Resources")
            if res:
                for name, xobj in res.get("/XObject", {}).items():
                    _compress_xobj(xobj, seen, quality, subsampling, unsharp)

            # Annotation appearance streams
            annots = page.get("/Annots")
            if annots is None:
                continue
            for annot in annots:
                ap = annot.get("/AP")
                if ap is None:
                    continue
                for key in ("/N", "/R", "/D"):
                    ap_stream = ap.get(key)
                    if ap_stream and ap_stream.get("/Subtype") == "/Form":
                        inner_res = ap_stream.get("/Resources")
                        if inner_res:
                            for name, xobj in inner_res.get("/XObject", {}).items():
                                _compress_xobj(xobj, seen, quality, subsampling, unsharp)

        pdf.save(output_path, compress_streams=True)

    orig = input_path.stat().st_size
    new  = output_path.stat().st_size
    return orig, new


def _compress_xobj(xobj, seen, quality, subsampling, unsharp):
    if xobj.get("/Subtype") != "/Image":
        return
    filters = xobj.get("/Filter")
    if filters:
        f = str(filters)
        if "JBIG2" in f or "CCITTFaxDecode" in f:
            return
    objgen = xobj.objgen
    if objgen in seen:
        return
    seen.add(objgen)

    orig_len = len(xobj.read_raw_bytes())
    img = pil_from_xobj(xobj)
    if img is None:
        return
    compressed = encode_jpeg(img, quality, subsampling, unsharp)
    if compressed is None or len(compressed) >= orig_len:
        return
    xobj.write(compressed, filter=pikepdf.Name("/DCTDecode"))
    if "/DecodeParms" in xobj.stream_dict:
        del xobj.stream_dict["/DecodeParms"]


print(f"Input: {INPUT.name} ({INPUT.stat().st_size/1024/1024:.1f} MB)\n")
print(f"{'Variant':<22} {'Size':>8}  {'Saved':>10}")
print("-" * 44)

for label, quality, subsampling, unsharp in VARIANTS:
    out = INPUT.with_stem(INPUT.stem + f"_{label}")
    orig, new = process(INPUT, out, quality, subsampling, unsharp)
    saved_pct = (orig - new) / orig * 100
    print(f"{label:<22} {new/1024/1024:>6.1f} MB  -{saved_pct:>5.1f}%")

print("\nDone. Open the output PDFs and compare the Excel table and cross-section areas.")
