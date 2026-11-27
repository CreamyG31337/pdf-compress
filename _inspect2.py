# /// script
# requires-python = ">=3.9"
# dependencies = ["pikepdf>=9.0"]
# ///
import pikepdf

pdf = pikepdf.open("c:/Projects/pdf-compress/ZONE2-26-051 Earthwork Report.pdf")
print(f"Pages: {len(pdf.pages)}")

for i, page in enumerate(pdf.pages):
    # Check raw content stream size
    contents = page.get("/Contents")
    if contents is None:
        print(f"Page {i+1}: no contents")
        continue
    if isinstance(contents, pikepdf.Array):
        total = sum(len(s.read_raw_bytes()) for s in contents)
        print(f"Page {i+1}: {len(contents)} content streams, total raw={total/1024:.0f} KB")
    else:
        raw = contents.read_raw_bytes()
        decoded = contents.read_bytes()
        print(f"Page {i+1}: 1 content stream, raw={len(raw)/1024:.0f} KB, decoded={len(decoded)/1024:.0f} KB")
        # Check for inline image marker 'BI'
        if b'BI\n' in decoded[:200] or b'BI ' in decoded[:200] or b'\nBI\n' in decoded:
            print(f"  -> contains inline images (BI marker found)")

pdf.close()
