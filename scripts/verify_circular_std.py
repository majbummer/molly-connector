"""
Verify MIL-DTL-26482 and MIL-DTL-5015 rows against the governing insert-arrangement standards.

  python verify_circular_std.py           -> dry run
  python verify_circular_std.py --apply   -> apply

  26482: MIL-STD-1669A w/Change 2  (scripts/mil-std-1669a-inserts.json)  - arrangement + contact counts
  5015:  MIL-STD-1651B w/Change 2  (scripts/mil-std-1651b-arrangements.json) - arrangement exists
         (active, inactive, or removed/cancelled - removed layouts are kept but flagged)

Checks both live rows and rows previously moved to connectors_unverified:
failing live rows are hidden, passing hidden rows are restored. Nothing is deleted.
"""
import sqlite3, sys, os, re, json
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "Data", "connectors.db")
APPLY = "--apply" in sys.argv

S1669 = {a["arrangement"]: a for a in json.load(open(os.path.join(HERE, "mil-std-1669a-inserts.json")))["arrangements"]}
J1651 = json.load(open(os.path.join(HERE, "mil-std-1651b-arrangements.json")))
A1651, R1651 = J1651["active"], J1651["removed"]

RE_26482_2 = re.compile(r"^MS34(70|71|72|74|75|76)([ALWKTD])(\d{1,2})-(\d{1,3})([PSAB])([WXYZ])?$")  # MIL-DTL-26482H Table I
RE_26482_1 = re.compile(r"^MS31(1[0-9]|2[0-8])([EPJFH])(\d{1,2})-(\d{1,3})([PSAB])([WXYZ])?([DTK])?$")  # MIL-DTL-26482H 1.1.1 (finish D/T/K)
RE_5015 = re.compile(r"^MS(310[01268]|340[01268]|345[012469])([A-Z]{1,2})(\d{1,2}(?:SL|S)?)-(\d{1,3})([PSAB])([WXYZ])?$")

_f = {"__file__": os.path.join(HERE, "fix_26482.py")}   # same 26482H / Supplement 1 rules as fix_26482.py
exec(compile(open(os.path.join(HERE, "fix_26482.py")).read().split("rows = []")[0], "fix_26482.py", "exec"), _f)

def check(spec, pn):
    if spec == "MIL-DTL-26482" and _f["why_bad"](pn):
        return None, _f["why_bad"](pn)
    if spec == "MIL-DTL-26482":
        m = RE_26482_2.match(pn) or RE_26482_1.match(pn)
        if not m: return None, "part number syntax not valid"
        key = f"{int(m.group(3))}-{int(m.group(4))}"
        a = S1669.get(key)
        if not a: return None, "arrangement not in MIL-STD-1669A"
        if m.re is RE_26482_2 and a.get("note") and "series 2" in a["note"]:
            return None, "arrangement not applicable to series 2 (MIL-STD-1669A)"
        return a, None
    if spec == "MIL-DTL-5015":
        m = RE_5015.match(pn)
        if not m: return None, "part number syntax not valid"
        key = f"{m.group(3)}-{int(m.group(4))}"
        if key in A1651: return {"status": A1651[key]}, None
        if key in R1651: return {"status": "removed from MIL-STD-1651: " + R1651[key]}, None
        return None, "arrangement not in MIL-STD-1651B"

con = sqlite3.connect(DB); cur = con.cursor()
cols = [r[1] for r in cur.execute("pragma table_info(connectors)")]
SPECS = ("MIL-DTL-26482", "MIL-DTL-5015")
live = cur.execute(f"select rowid, spec, part_number from connectors where spec in {SPECS}").fetchall()
hidden = cur.execute(f"select rowid, spec, part_number from connectors_unverified where spec in {SPECS}").fetchall()

hide, restore, ok_live = [], [], []
stats = Counter(); why_c = Counter(); ex = {}
for rid, spec, pn in live:
    a, why = check(spec, pn)
    if why: hide.append((rid, why)); why_c[(spec, why)] += 1; ex.setdefault((spec, why), pn)
    else: ok_live.append((rid, spec, a)); stats[(spec, "keep")] += 1
for rid, spec, pn in hidden:
    a, why = check(spec, pn)
    if a: restore.append((rid, spec, pn)); stats[(spec, "restore")] += 1
    else: stats[(spec, "stay hidden")] += 1

print(f"Mode: {'APPLY' if APPLY else 'DRY RUN'}")
for spec in SPECS:
    print(f"\n{spec}: live {sum(1 for r in live if r[1]==spec):,} -> keep {stats[(spec,'keep')]:,}, hide {sum(n for (s,_),n in why_c.items() if s==spec):,}"
          f" | hidden {sum(1 for r in hidden if r[1]==spec):,} -> restore {stats[(spec,'restore')]:,}")
    for (s, w), n in why_c.most_common():
        if s == spec: print(f"    {n:>7,}  {w:55} e.g. {ex[(s, w)]}")
    print("    restore e.g.", [pn for _, s, pn in restore if s == spec][:6])

if APPLY:
    cur.executemany(f"insert into connectors_unverified ({','.join(cols)}, hidden_reason) select {','.join(cols)}, ? from connectors where rowid=?",
                    [(w, rid) for rid, w in hide])
    cur.executemany("delete from connectors where rowid=?", [(rid,) for rid, _ in hide])
    cur.executemany(f"insert into connectors ({','.join(cols)}) select {','.join(cols)} from connectors_unverified where rowid=?",
                    [(rid,) for rid, _, _ in restore])
    cur.executemany("delete from connectors_unverified where rowid=?", [(rid,) for rid, _, _ in restore])
    for rid, spec, pn in cur.execute(f"select rowid, spec, part_number from connectors where spec in {SPECS}").fetchall():
        a, _ = check(spec, pn)
        if spec == "MIL-DTL-26482":
            sizes = []
            for c in a["contacts"]:
                s = c["size"].split(" ")[0]
                if s not in sizes: sizes.append(s)
            s = "; ".join(sizes)
            cur.execute("update connectors set contact_count=?, contact_size=?, compatible_contact_sizes=?, verified_source=? where rowid=?",
                        (a["total"], s, s, "MIL-STD-1669A w/Change 2" + (" (inactive for new design)" if a["inactive"] else ""), rid))
        else:
            cur.execute("update connectors set verified_source=? where rowid=?",
                        ("MIL-STD-1651B w/Change 2 arrangement (" + a["status"] + ")", rid))
    con.commit(); print("\nCOMMITTED.")
else:
    print("\nDry run only - nothing written.")
