"""
Fix and extend contact data using the Amphenol MIL-DTL-38999 Series III
"Standard 500 cycle contacts for TV and CTV" chart (2026-10-04).

  python fix_38999_contacts.py            -> dry run, prints a diff, changes nothing
  python fix_38999_contacts.py --apply    -> writes the changes

Tooling/strip values are assigned BY CONTACT SIZE + GENDER (per Matt: the
internal contact spec records were keyed by size, not by M39029 P/N).
"""
import sqlite3, sys, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Data", "connectors.db")
APPLY = "--apply" in sys.argv
SRC = "Amphenol 38999 Series III TV/CTV contact chart"
PLATING = "Gold over suitable underplate per SAE AS39029 (500 cycle)"

# Tooling by size|gender, taken from the existing rows (internal records are size-based)
T = {
 "16|P": dict(sl=(0.08, 0.11, 0.09),    crimper="M22520/2-01", pos="TH4A",  loc="K41",  ins="M81969/1-01", ext="M81969/14-01", fam="AF8"),
 "16|S": dict(sl=(0.175, 0.2, 0.188),   crimper="M22520/1-01", pos="TH163", loc=None,   ins="M81969/1-02", ext="M81969/14-02", fam="AF8"),
 "20|P": dict(sl=(0.15, 0.175, 0.163),  crimper="M22520/2-01", pos="TH163", loc="K13-1",ins="M81969/1-01", ext="M81969/14-01", fam="AF8"),
 "20|S": dict(sl=(0.143, 0.169, 0.156), crimper="M22520/2-01", pos="TH163", loc="K42",  ins="M81969/1-02", ext="M81969/14-02", fam="AF8"),
 "22D|P":dict(sl=(0.05, 0.065, 0.06),   crimper="M22520/2-01", pos="TH4A",  loc="K41",  ins="M81969/1-01", ext="M81969/14-01", fam="AFM8"),
 "22D|S":dict(sl=(0.112, 0.137, 0.125), crimper="M22520/2-01", pos="TH163", loc="K42",  ins="M81969/1-02", ext="M81969/14-02", fam="AFM8"),
 "12|P": dict(sl=(0.12, 0.16, 0.14),    crimper="M22520/5-01", pos="Varies",loc="Varies",ins="M81969 insertion tool", ext="M81969 extraction tool", fam="Heavy Duty"),
 "12|S": dict(sl=(0.12, 0.16, 0.14),    crimper="M22520/5-01", pos="Varies",loc="Varies",ins="M81969 insertion tool", ext="M81969 extraction tool", fam="Heavy Duty"),
}
NONE_T = dict(sl=(None, None, None), crimper=None, pos=None, loc=None, ins=None, ext=None, fam=None)
AWG = {"12": (12, 14), "16": (16, 20), "20": (20, 24), "22D": (22, 28)}

# part, size, P/S, supersedes, extra note, tooling key (None = no tooling data)
CHART = [
 ("M39029/58-365", "12",  "P", "MS27493-12",  "", "12|P"),
 ("M39029/58-364", "16",  "P", "MS27493-16",  "", "16|P"),
 ("M39029/58-363", "20",  "P", "MS27493-20",  "", "20|P"),
 ("M39029/58-360", "22D", "P", "MS27493-22D", "", "22D|P"),
 ("M39029/58-528", "10",  "P", None, "Size 10 power contact.", None),
 ("M39029/60-367", "8",   "P", "MS27536", "Size 8 coax, for RG180B/U and RG195A/U cable.", None),
 ("M39029/90-529", "8",   "P", None, "Size 8 twinax.", None),
 ("M39029/56-353", "12",  "S", "MS27490-12",  "", "12|S"),
 ("M39029/56-352", "16",  "S", "MS27490-16",  "", "16|S"),
 ("M39029/56-351", "20",  "S", "MS27490-20",  "", "20|S"),
 ("M39029/56-348", "22D", "S", "MS27490-22D", "", "22D|S"),
 ("M39029/56-527", "10",  "S", None, "Size 10 power contact.", None),
 ("M39029/59-366", "8",   "S", "MS27535", "Size 8 coax, for RG180B/U and RG195A/U cable.", None),
 ("M39029/91-530", "8",   "S", None, "Size 8 twinax.", None),
]

NOTE_ONLY = {
 "M39029/55-352": "Size 16 pin. NOT on the Amphenol 38999 Series III TV/CTV chart - the 38999 Series III size 16 pin is M39029/58-364. Verify before using with MIL-DTL-38999.",
 "M39029/57-354": "Size 22D pin. NOT on the Amphenol 38999 Series III TV/CTV chart - the 38999 Series III size 22D pin is M39029/58-360. Verify before using with MIL-DTL-38999.",
 "M39029/58-361": "Listed as size 22E socket, but /58 is the 38999 PIN slash sheet. Not on the Amphenol chart - verify size and gender.",
}
NOTE_REPLACE = {
 "M39029/33-261": ("M39029/55-352", "M39029/58-364"),
 "M39029/34-264": ("M39029/56-351", "M39029/56-352"),
}

TOOLS_DEFAULT = {  # contacts_tools mapping_key -> new default contact P/N
 "16|P": "M39029/58-364", "16|S": "M39029/56-352",
 "20|P": "M39029/58-363", "20|S": "M39029/56-351",
 "22D|P": "M39029/58-360", "22D|S": "M39029/56-348",
 "23|P": "M39029/92-540", "23|S": "M39029/93-541",
}
CHART_ROWS = {  # wire_contact_chart contact_size -> (pin, socket)
 "16": ("M39029/58-364", "M39029/56-352"),
 "20": ("M39029/58-363", "M39029/56-351"),
 "22D": ("M39029/58-360", "M39029/56-348"),
}

def contact_row(pn, size, ct, sup, extra, tkey):
    t = T[tkey] if tkey else NONE_T
    g = AWG.get(size)
    gender = "Pin" if ct == "P" else "Socket"
    note = f"Size {size} {gender.lower()}, MIL-DTL-38999 Series III ({SRC})."
    if sup: note += f" Supersedes {sup}."
    if extra: note += " " + extra
    if tkey: note += f" Tooling/strip from internal size {size} {gender.lower()} records - confirm per approved work instruction."
    else: note += " Tooling not on file - consult manufacturer."
    return dict(part_number=pn, slash_sheet="/" + pn.split("/")[1].split("-")[0], contact_size=size,
        contact_type=ct, gender=gender, wire_gauge_min=g[0] if g else None, wire_gauge_max=g[1] if g else None,
        wire_gauge_range=f"{g[0]}-{g[1]}" if g else None,
        strip_length_min=t["sl"][0], strip_length_max=t["sl"][1], default_strip_length=t["sl"][2],
        contact_material="Copper Alloy", plating=PLATING, termination="Crimp",
        compatible_specs="MIL-DTL-38999 Series III", crimper_tool=t["crimper"], positioner=t["pos"],
        locator=t["loc"], inserter_tool=t["ins"], extractor_tool=t["ext"], tool_family=t["fam"], notes=note)

def show(label, before, after):
    if before is None:
        print(f"  + NEW {label}"); [print(f"      {k}: {v}") for k, v in after.items() if v is not None]; return
    diffs = [(k, before[k], after[k]) for k in after if before[k] != after[k]]
    if diffs:
        print(f"  ~ {label}")
        for k, a, b in diffs: print(f"      {k}: {a!r}  ->  {b!r}")

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
cur = con.cursor()
get = lambda t, k, v: (lambda r: dict(r) if r else None)(cur.execute(f"select * from {t} where {k}=?", (v,)).fetchone())

print(f"DB: {os.path.abspath(DB)}\nMode: {'APPLY' if APPLY else 'DRY RUN'}\n\n== contacts")
for spec in CHART:
    new = contact_row(*spec); old = get("contacts", "part_number", new["part_number"])
    show(new["part_number"], old, new)
    cols = ",".join(new); qs = ",".join("?" * len(new))
    cur.execute(f"insert or replace into contacts ({cols}) values ({qs})", list(new.values()))
for pn, note in NOTE_ONLY.items():
    old = get("contacts", "part_number", pn)
    if not old or note in (old["notes"] or ""): continue
    if pn != "M39029/55-352":  # keep existing tooling notes, append the warning
        note = (old["notes"] or "").rstrip() + " " + note
    show(pn, old, {**old, "notes": note}); cur.execute("update contacts set notes=? where part_number=?", (note, pn))
for pn, (a, b) in NOTE_REPLACE.items():
    old = get("contacts", "part_number", pn)
    if old and a in (old["notes"] or ""):
        n = old["notes"].replace(a, b); show(pn, old, {**old, "notes": n})
        cur.execute("update contacts set notes=? where part_number=?", (n, pn))

print("\n== contacts_tools")
for key, pn in TOOLS_DEFAULT.items():
    old = get("contacts_tools", "mapping_key", key)
    if not old or old["contact_part_number"] == pn: continue
    tag = " Default P/N is MIL-DTL-38999 Series III (Amphenol chart); 5015/26482 use other slash sheets - see Contacts page."
    n = (old["notes"] or "") + ("" if tag.strip() in (old["notes"] or "") or key.startswith("23") else tag)
    show(key, old, {**old, "contact_part_number": pn, "notes": n})
    cur.execute("update contacts_tools set contact_part_number=?, notes=? where mapping_key=?", (pn, n, key))

print("\n== wire_contact_chart")
for size, (p, s) in CHART_ROWS.items():
    old = get("wire_contact_chart", "contact_size", size)
    if not old: continue
    new = {**old, "contact_pin": p, "contact_socket": s}
    if "38999" not in (old["notes"] or ""): new["notes"] = (old["notes"] or "") + " P/Ns shown are MIL-DTL-38999 Series III."
    show(f"size {size}", old, new)
    cur.execute("update wire_contact_chart set contact_pin=?, contact_socket=?, notes=? where id=?", (p, s, new["notes"], old["id"]))

if APPLY:
    con.commit(); print("\nCOMMITTED.")
else:
    con.rollback(); print("\nDry run only - nothing written. Re-run with --apply.")
print("contacts rows:", cur.execute("select count(*) from contacts").fetchone()[0])
