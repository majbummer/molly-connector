"""
Verify MIL-DTL-26482, MIL-DTL-83723 and MIL-DTL-5015 rows (part-number syntax + insert arrangement).

  python verify_circular_other.py           -> dry run
  python verify_circular_other.py --apply   -> move failing rows to connectors_unverified

Sources:
  26482 (Series 1 & 2): MIL-STD-1669 layouts - Glenair "Insert arrangements per MIL-STD-1669";
        contact counts from Conesys MIL-DTL-26482 Series II catalog.
  83723 Series III: arrangements listed in both the Conesys and Amphenol 83723 Series III catalogs
        (non-MS / commercial-only layouts excluded).
  5015: part-number syntax only (catalog arrangement lists omit inactive layouts, so arrangements
        are NOT used to hide rows).
"""
import sqlite3, sys, os, re
from collections import Counter

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Data", "connectors.db")
APPLY = "--apply" in sys.argv

L1669 = set("""8-2 8-3 8-4 8-8 8-9 8-33 8-98 10-6 10-9 12-3 12-8 12-10 14-4 14-5 14-9 14-12 14-14 14-15 14-18 14-19
14-22 16-8 16-14 16-23 16-26 16-95 16-99 18-8 18-11 18-30 18-32 18-85 18-88 20-16 20-24 20-27 20-39 20-41 20-90
22-12 22-19 22-21 22-32 22-34 22-41 22-55 22-95 22-96 24-19 24-27 24-31 24-61""".split())
# (#20, #16, #12) from the Conesys Series II table
C26482 = {"8-33":(3,0,0),"8-98":(3,0,0),"10-6":(6,0,0),"12-3":(0,3,0),"12-8":(8,0,0),"12-10":(10,0,0),"14-4":(0,0,4),
 "14-5":(0,5,0),"14-9":(5,0,4),"14-12":(8,4,0),"14-15":(14,1,0),"14-18":(18,0,0),"14-19":(19,0,0),"16-8":(0,8,0),
 "16-14":(8,6,0),"16-23":(22,1,0),"16-26":(26,0,0),"18-8":(0,0,8),"18-11":(0,11,0),"18-30":(29,1,0),"18-32":(32,0,0),
 "20-16":(0,16,0),"20-24":(24,0,0),"20-39":(37,2,0),"20-41":(41,0,0),"22-12":(0,0,12),"22-21":(0,21,0),"22-41":(27,14,0),
 "22-55":(55,0,0),"22-95":(26,0,6),"24-19":(0,0,19),"24-31":(31,0,0),"24-61":(61,0,0)}
L83723 = set("""8-2 8-3 8-98 10-2 10-5 10-6 10-20 12-3 12-12 14-4 14-7 14-12 14-15 16-10 16-24 18-8 18-14 18-31
20-16 20-25 20-28 20-39 20-41 22-12 22-19 22-32 22-39 22-55 24-19 24-43 24-57 24-61""".split())

RE_26482_2 = re.compile(r"^MS34(70|71|72|74|75|76)(A|L|W|S|BN)(\d{1,2})-(\d{1,3})([PSAB])([NWXYZ])?$")
RE_26482_1 = re.compile(r"^MS31(1[0-6]|2[0-6])([A-Z])(\d{1,2})-(\d{1,3})([PSAB])([NWXYZ])?$")
RE_83723 = re.compile(r"^M83723/(7[1-8]|8[2-7]|9[1256])([AGRWKSN])(\d{2})(\d{2})([N6789Y1-5])?$")
RE_5015 = re.compile(r"^MS(310[01268]|340[01268]|345[012469])([A-Z]{1,2})(\d{1,2}(?:S|SL)?)-(\d{1,3})([PSAB])([WXYZ])?$")

def check(spec, pn):
    if spec == "MIL-DTL-26482":
        m = RE_26482_2.match(pn) or RE_26482_1.match(pn)
        if not m: return None, "part number syntax not valid"
        shell, ins = int(m.group(3)), int(m.group(4))
        if shell % 2 or not 8 <= shell <= 24: return None, "shell size not valid for 26482"
        key = f"{shell}-{ins}"
        if key not in L1669: return None, f"arrangement not in MIL-STD-1669"
        return ("MIL-STD-1669", key), None
    if spec == "MIL-DTL-83723":
        m = RE_83723.match(pn)
        if not m: return None, "part number syntax not valid (contact type is set by slash number; no P/S letter)"
        key = f"{int(m.group(3))}-{int(m.group(4))}"
        if key not in L83723: return None, "arrangement not an MS 83723 layout"
        return ("83723 catalogs", key), None
    if spec == "MIL-DTL-5015":
        m = RE_5015.match(pn)
        if not m: return None, "part number syntax not valid"
        return ("5015 syntax only", None), None

con = sqlite3.connect(DB); cur = con.cursor()
cols = [r[1] for r in cur.execute("pragma table_info(connectors)")]
rows = cur.execute("select rowid, spec, part_number, contact_count from connectors where spec in ('MIL-DTL-26482','MIL-DTL-83723','MIL-DTL-5015')").fetchall()
keep, bad = Counter(), []
reasons = Counter(); examples = {}
counts = []
for rid, spec, pn, cnt in rows:
    ok, why = check(spec, pn)
    if why:
        bad.append((rid, why)); k = (spec, why); reasons[k] += 1; examples.setdefault(k, pn)
    else:
        keep[spec] += 1
        if spec == "MIL-DTL-26482" and ok[1] in C26482:
            c20, c16, c12 = C26482[ok[1]]
            sizes = "; ".join(s for s, n in (("20", c20), ("16", c16), ("12", c12)) if n)
            counts.append((c20 + c16 + c12, sizes, sizes, ok[0] + " / Conesys 26482 Series II catalog", rid))
        else:
            counts.append((None, None, None, ok[0], rid))

print(f"Mode: {'APPLY' if APPLY else 'DRY RUN'}")
for spec in ("MIL-DTL-26482", "MIL-DTL-83723", "MIL-DTL-5015"):
    tot = sum(1 for r in rows if r[1] == spec)
    print(f"\n{spec}: {tot:,} rows -> keep {keep[spec]:,}, hide {tot - keep[spec]:,}")
    for (s, why), n in reasons.most_common():
        if s == spec: print(f"   {n:>7,}  {why:70}  e.g. {examples[(s, why)]}")

if APPLY:
    cur.execute("create table if not exists connectors_unverified as select *, '' as hidden_reason from connectors where 0")
    cur.executemany(f"insert into connectors_unverified ({','.join(cols)}, hidden_reason) select {','.join(cols)}, ? from connectors where rowid=?",
                    [(why, rid) for rid, why in bad])
    cur.executemany("delete from connectors where rowid=?", [(rid,) for rid, _ in bad])
    for total, size, csz, src, rid in counts:
        if total is not None:
            cur.execute("update connectors set contact_count=?, contact_size=?, compatible_contact_sizes=?, verified_source=? where rowid=?",
                        (total, size, csz, src, rid))
        elif src != "5015 syntax only":
            cur.execute("update connectors set verified_source=? where rowid=?", (src + " (arrangement only)", rid))
    con.commit(); print("\nCOMMITTED.")
else:
    print("\nDry run only - nothing written.")
