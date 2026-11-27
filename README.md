# pdf-compress

Compress images in bloated PDF files using JPEG recompression. Targets PDFs
that are large because they contain high-resolution uncompressed or lightly
compressed images (common when exporting from Bluebeam, Revit, etc.).

Default quality is **90** — visually lossless for most engineering documents,
but reduces a typical 30 MB file to ~6 MB.

## Why use this instead of Bluebeam's image compression?

Some Bluebeam compression workflows make PDF files smaller by applying
aggressive JPEG compression and chroma downsampling. On engineering drawings,
plans, and screenshots, that can make embedded or rasterized text look blurry,
soft, or develop colored edges.

This tool is designed to reduce that problem while still producing a much
smaller PDF. Its default settings use high-quality JPEG at **q90** with **4:4:4
chroma** (no color downsampling), which keeps fine text and colored annotations
crisper than the usual 4:2:0 encoding. It also leaves transparency and 1-bit
line-art images alone instead of converting them to a format that could damage
their appearance. Bluebeam annotation appearance streams are scanned as well,
so images stored there are not silently missed.

The result is not lossless: quality settings still trade file size for image
quality. For PDFs where text sharpness matters, keep the default q90 or use
`-q 95` rather than lowering the quality.

---

## Quick start

### Drag and drop on Windows

After setup, drag one or more PDF files onto **Compress PDF.bat** in File
Explorer. The batch file compresses each PDF and saves the result next to the
original as `filename_compressed.pdf`. Your original files are left untouched.

### Command line

```
uv run compress_pdf.py "my file.pdf"
```

Produces `my file_compressed.pdf` alongside the original. The original is
never touched unless you explicitly use `-s ""`.

---

## Setup (no admin required)

Everything runs in your user profile — no elevated permissions needed.

### Step 1 — Install uv

Open PowerShell and run:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

This installs `uv` to `%USERPROFILE%\.local\bin\`. Close and reopen your
terminal so the PATH update takes effect.

### Step 2 — First run

`uv` will automatically download Python and install `pikepdf`/`Pillow` the
first time you run the script. No separate install step needed:

```
uv run compress_pdf.py "your file.pdf"
```

Subsequent runs are instant — packages are cached in your user profile.

---

## Usage

```
uv run compress_pdf.py input.pdf [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `-o FILE` | — | Output file (single input only) |
| `-q N` | `90` | JPEG quality 1–95. 90 = very high quality, safe for text |
| `-s SUFFIX` | `_compressed` | Output filename suffix. Use `""` to overwrite originals |
| `-v` | off | Verbose: show per-image details |

### Examples

```bash
# Single file — creates "report_compressed.pdf"
uv run compress_pdf.py report.pdf

# Specify output name
uv run compress_pdf.py report.pdf -o report_small.pdf

# Batch compress all PDFs in current folder
uv run compress_pdf.py *.pdf

# Overwrite originals (make a backup first!)
uv run compress_pdf.py *.pdf -s ""

# Slightly more aggressive (still very good quality)
uv run compress_pdf.py report.pdf -q 85
```

---

## Notes

- **Text quality**: Quality 90 is safe. JPEG artifacts on text become
  noticeable below ~80. Don't go lower unless you're okay with soft edges
  on fine print.
- **Already-small images**: If recompressing would make an image larger, it
  is left alone. The script never inflates a file.
- **Transparency / 1-bit images**: RGBA, masks, and fax-encoded images are
  skipped — JPEG does not support transparency and would be wrong for
  black-and-white line art.
- **Shared images**: Images referenced on multiple pages are only compressed
  once.
- **Bluebeam annotation images**: Bluebeam embeds large images inside
  annotation appearance streams (not page resources), which most tools miss.
  This script scans annotation AP streams as well as page resources.

---

## Compression findings

Tested against engineering PDFs exported from Bluebeam (30 MB plan view,
22 MB earthwork report with Excel screenshots and cross-section plots).

**Typical results at q90**: ~80% size reduction (30 MB → 6 MB).

### Chroma subsampling: use 4:4:4, not 4:2:0

JPEG's default chroma subsampling (4:2:0) halves color resolution in both
directions. On photographic content this is invisible, but on engineering
documents it causes noticeable color shift on text — red annotation text
becomes brownish/orange, colored callouts lose saturation.

Using 4:4:4 (no chroma subsampling, `subsampling=0` in Pillow) fixes this
completely. File size penalty is ~5–10% at the same quality setting, which
is worth it for document legibility.

**This is the default in this script.**

### Unsharp mask

Pre-sharpening before JPEG encoding partially compensates for DCT softening
on edges. Tested at `radius=0.5, percent=150, threshold=2`. The improvement
is subtle compared to fixing chroma subsampling, and adds ~8% to file size.
Not applied by default — use if you need maximum crispness on fine line art.

### Size vs quality tradeoff (earthwork report, 22 MB original)

| Setting | Output size | Reduction |
|---|---|---|
| q90, 4:2:0 (old default) | 4.4 MB | 80% |
| q90, 4:4:4 ← **current default** | 5.3 MB | 76% |
| q90, 4:4:4, unsharp | 5.8 MB | 74% |
| q95, 4:4:4 | 7.4 MB | 66% |

## Tests

`tests/test_compress_pdf.py` builds small PDFs and checks that photo-like images are recompressed to JPEG, that an image is never replaced by a bigger one, and which image modes can be JPEG-encoded. Run with `python -m pytest` (needs pytest and pymupdf).
