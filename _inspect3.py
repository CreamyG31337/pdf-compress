# /// script
# requires-python = ">=3.9"
# dependencies = ["pikepdf>=9.0"]
# ///
import pikepdf

pdf = pikepdf.open("c:/Projects/pdf-compress/ZONE2-26-051 Earthwork Report.pdf")

# Check for embedded files / attachments
root = pdf.Root
print("Root keys:", list(root.keys()))

names = root.get("/Names")
if names:
    print("Names keys:", list(names.keys()))
    ef = names.get("/EmbeddedFiles")
    if ef:
        print("EmbeddedFiles:", ef)

# Walk all objects and find large ones
print("\nLargest objects:")
sizes = []
for objnum in range(1, len(pdf.objects) + 1):
    try:
        obj = pdf.get_object(objnum, 0)
        if hasattr(obj, 'read_raw_bytes'):
            raw = obj.read_raw_bytes()
            if len(raw) > 100_000:
                filt = obj.get("/Filter") if hasattr(obj, 'get') else None
                subtype = obj.get("/Subtype") if hasattr(obj, 'get') else None
                ftype = obj.get("/Type") if hasattr(obj, 'get') else None
                sizes.append((len(raw), objnum, filt, subtype, ftype))
    except Exception:
        pass

for size, num, filt, sub, ftype in sorted(sizes, reverse=True)[:15]:
    print(f"  obj {num}: {size/1024:.0f} KB, Type={ftype}, Subtype={sub}, Filter={filt}")

pdf.close()
