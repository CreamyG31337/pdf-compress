# /// script
# requires-python = ">=3.9"
# dependencies = ["pikepdf>=9.0"]
# ///
import pikepdf

pdf = pikepdf.open("c:/Projects/pdf-compress/ZONE2-26-051 Earthwork Report.pdf")

# Check page annotations — likely where the images live (e.g. stamp/overlay annotations)
for i, page in enumerate(pdf.pages):
    annots = page.get("/Annots")
    if annots is None:
        continue
    annot_list = list(annots)
    print(f"Page {i+1}: {len(annot_list)} annotations")
    for j, a in enumerate(annot_list):
        asubtype = a.get("/Subtype")
        ap = a.get("/AP")  # Appearance stream
        print(f"  [{j}] Subtype={asubtype}, has AP={ap is not None}, keys={list(a.keys())}")
        if ap:
            n_stream = ap.get("/N")  # Normal appearance
            if n_stream and hasattr(n_stream, 'get'):
                print(f"       AP/N: Type={n_stream.get('/Type')}, Subtype={n_stream.get('/Subtype')}")
                inner_res = n_stream.get("/Resources")
                if inner_res:
                    inner_x = inner_res.get("/XObject", {})
                    for xname, xobj in inner_x.items():
                        xsub = xobj.get("/Subtype")
                        xfilt = xobj.get("/Filter")
                        size = len(xobj.read_raw_bytes())
                        print(f"         {xname}: subtype={xsub}, filter={xfilt}, size={size/1024:.0f} KB")

pdf.close()
