#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "pikepdf>=9.0",
#   "pillow>=10.0",
# ]
# ///
"""
Compress images in a PDF using JPEG compression.

Usage:
  uv run compress_pdf.py input.pdf
  uv run compress_pdf.py input.pdf -o output.pdf
  uv run compress_pdf.py input.pdf -q 90
  uv run compress_pdf.py *.pdf          (batch mode)
"""

import argparse
import io
import sys
from pathlib import Path

import pikepdf
from pikepdf import PdfImage
from PIL import Image


def pil_from_xobj(xobj) -> Image.Image | None:
    """Extract a PIL Image from a PDF image XObject, handling any encoding."""
    try:
        pdf_image = PdfImage(xobj)
        return pdf_image.as_pil_image()
    except Exception:
        pass
    # Fallback: try reading raw bytes directly (works for bare DCT/uncompressed)
    try:
        raw = xobj.read_raw_bytes()
        return Image.open(io.BytesIO(raw))
    except Exception:
        return None


def encode_jpeg(img: Image.Image, quality: int) -> bytes | None:
    """Convert a PIL image to JPEG bytes. Returns None if the mode can't be JPEG-encoded."""
    if img.mode in ("RGBA", "LA", "P"):
        return None  # JPEG has no alpha support
    if img.mode not in ("RGB", "L", "CMYK"):
        try:
            img = img.convert("RGB")
        except Exception:
            return None
    out = io.BytesIO()
    # subsampling=0 → 4:4:4 chroma (no chroma downsampling).
    # The default 4:2:0 halves color resolution, causing color fringing on text
    # (e.g. red text shifts toward brown/orange). 4:4:4 fixes this at minimal
    # size cost (~5-10% larger than 4:2:0 at the same quality setting).
    img.save(out, format="JPEG", quality=quality, subsampling=0, optimize=True)
    return out.getvalue()


def compress_pdf(input_path: Path, output_path: Path, quality: int, verbose: bool) -> tuple[int, int]:
    """
    Compress all images in a PDF.
    Returns (original_size, new_size) in bytes.
    """
    original_size = input_path.stat().st_size

    # Track object IDs we've already processed to avoid double-compressing
    # shared XObjects (same image referenced on multiple pages)
    seen_objgens: set[tuple] = set()

    with pikepdf.open(input_path) as pdf:
        replaced = 0
        skipped = 0

        def process_xobj(xobj, label: str):
            nonlocal replaced, skipped
            try:
                if xobj.get("/Subtype") != "/Image":
                    return

                filters = xobj.get("/Filter")
                if filters is not None:
                    filter_name = str(filters)
                    if "JBIG2" in filter_name or "CCITTFaxDecode" in filter_name:
                        skipped += 1
                        return

                objgen = xobj.objgen
                if objgen in seen_objgens:
                    return
                seen_objgens.add(objgen)

                orig_len = len(xobj.read_raw_bytes())

                img = pil_from_xobj(xobj)
                if img is None:
                    if verbose:
                        print(f"  {label}: could not decode, skipping")
                    skipped += 1
                    return

                compressed = encode_jpeg(img, quality)
                if compressed is None:
                    skipped += 1
                    return

                if len(compressed) >= orig_len:
                    if verbose:
                        print(f"  {label}: already smaller, skipping")
                    skipped += 1
                    return

                xobj.write(compressed, filter=pikepdf.Name("/DCTDecode"))
                if "/DecodeParms" in xobj.stream_dict:
                    del xobj.stream_dict["/DecodeParms"]
                replaced += 1

            except Exception as e:
                if verbose:
                    print(f"  {label}: error — {e}")
                skipped += 1

        def scan_resources(res, label: str):
            xobjects = res.get("/XObject")
            if xobjects is None:
                return
            for name, xobj in xobjects.items():
                process_xobj(xobj, f"{label}/{name}")
                # Recurse into Form XObjects
                if xobj.get("/Subtype") == "/Form":
                    inner_res = xobj.get("/Resources")
                    if inner_res:
                        scan_resources(inner_res, f"{label}/{name}")

        for page_num, page in enumerate(pdf.pages, 1):
            # 1. Page-level resources
            resources = page.get("/Resources")
            if resources:
                scan_resources(resources, f"p{page_num}")

            # 2. Annotation appearance streams (AP/N) — Bluebeam embeds images here
            annots = page.get("/Annots")
            if annots is None:
                continue
            for j, annot in enumerate(annots):
                try:
                    ap = annot.get("/AP")
                    if ap is None:
                        continue
                    for ap_key in ("/N", "/R", "/D"):
                        ap_stream = ap.get(ap_key)
                        if ap_stream is None:
                            continue
                        if ap_stream.get("/Subtype") == "/Form":
                            inner_res = ap_stream.get("/Resources")
                            if inner_res:
                                scan_resources(inner_res, f"p{page_num}/annot{j}{ap_key}")
                except Exception as e:
                    if verbose:
                        print(f"  p{page_num}/annot{j}: error — {e}")

        if verbose:
            print(f"  Images: {replaced} recompressed, {skipped} skipped")

        pdf.save(output_path, compress_streams=True)

    new_size = output_path.stat().st_size
    return original_size, new_size


def main():
    parser = argparse.ArgumentParser(
        description="Compress images in PDF files using JPEG compression."
    )
    parser.add_argument("inputs", nargs="+", metavar="PDF", help="Input PDF file(s)")
    parser.add_argument(
        "-o", "--output", metavar="FILE",
        help="Output file (only valid with a single input; default: overwrite input)"
    )
    parser.add_argument(
        "-q", "--quality", type=int, default=90, metavar="N",
        help="JPEG quality 1-95 (default: 90 — very high quality)"
    )
    parser.add_argument(
        "-s", "--suffix", default="_compressed", metavar="SUFFIX",
        help="Suffix for output files in batch mode (default: _compressed). "
             "Use '' to overwrite originals."
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if not 1 <= args.quality <= 95:
        print("Error: quality must be between 1 and 95", file=sys.stderr)
        sys.exit(1)

    inputs = [Path(p) for p in args.inputs]

    if args.output and len(inputs) > 1:
        print("Error: -o/--output can only be used with a single input file", file=sys.stderr)
        sys.exit(1)

    for input_path in inputs:
        if not input_path.exists():
            print(f"Error: {input_path} not found", file=sys.stderr)
            continue
        if input_path.suffix.lower() != ".pdf":
            print(f"Warning: {input_path} doesn't look like a PDF, skipping")
            continue

        if args.output:
            output_path = Path(args.output)
        elif args.suffix == "":
            output_path = input_path
        else:
            output_path = input_path.with_stem(input_path.stem + args.suffix)

        print(f"{input_path.name} -> {output_path.name} (quality={args.quality})")
        try:
            orig, new = compress_pdf(input_path, output_path, args.quality, args.verbose)
            saved = orig - new
            pct = (saved / orig * 100) if orig else 0
            sign = "-" if saved >= 0 else "+"
            print(f"  {orig/1024/1024:.1f} MB -> {new/1024/1024:.1f} MB  "
                  f"({sign}{abs(saved)/1024:.0f} KB, {sign}{abs(pct):.1f}%)")
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
