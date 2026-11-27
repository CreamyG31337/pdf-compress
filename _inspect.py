# /// script
# requires-python = ">=3.9"
# dependencies = ["pikepdf>=9.0"]
# ///
import pikepdf

pdf = pikepdf.open("c:/Projects/pdf-compress/ZONE2-26-051 Earthwork Report.pdf")
print(f"Pages: {len(pdf.pages)}")

def scan_resources(res, depth=0, page_label=""):
    indent = "  " * depth
    xobjs = res.get("/XObject", {})
    for name, xobj in xobjs.items():
        subtype = xobj.get("/Subtype")
        filt = xobj.get("/Filter")
        size = len(xobj.read_raw_bytes()) if hasattr(xobj, 'read_raw_bytes') else "?"
        print(f"{indent}{page_label}{name}: subtype={subtype}, filter={filt}, size={size}")
        if subtype == "/Form":
            inner_res = xobj.get("/Resources")
            if inner_res:
                scan_resources(inner_res, depth+1, "")

for i, page in enumerate(pdf.pages[:10]):
    res = page.get("/Resources")
    if res:
        print(f"\nPage {i+1}:")
        scan_resources(res, 1, f"p{i+1}/")

pdf.close()
