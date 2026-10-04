"""
Verify MIL-DTL-38999 connector rows against the NASA NEPP insert arrangement list
and basic part-number syntax.

  python verify_38999.py            -> dry run (report only, nothing written)
  python verify_38999.py --apply    -> apply

Rows that pass:  contact_count / contact_size / compatible_contact_sizes are set from
                 the NASA table, verified_source is filled in.
Rows that fail:  MOVED (not deleted) to table connectors_unverified with a hidden_reason.
                 Restore any row with:  python verify_38999.py --restore <PART_NUMBER|ALL>
"""
import sqlite3, sys, os, re
from collections import Counter

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Data", "connectors.db")
APPLY = "--apply" in sys.argv
SOURCE = "NASA NEPP NPSL MIL-DTL-38999 insert table (2026-10-04)"

# (shell letter, arrangement) -> (c22D, c20, c16, c12, seriesIV_available)
III = {
 ("A",35):(6,0,0,0,False), ("A",98):(0,3,0,0,False),
 ("B",4):(0,4,0,0,False), ("B",5):(0,5,0,0,True), ("B",35):(13,0,0,0,True), ("B",98):(0,6,0,0,False), ("B",99):(0,7,0,0,True),
 ("C",4):(0,0,4,0,True), ("C",8):(0,8,0,0,False), ("C",35):(22,0,0,0,True), ("C",98):(0,10,0,0,True),
 ("D",5):(0,0,5,0,True), ("D",15):(0,14,1,0,False), ("D",18):(0,18,0,0,True), ("D",19):(0,19,0,0,True), ("D",35):(37,0,0,0,True), ("D",97):(0,8,4,0,True),
 ("E",6):(0,0,0,6,True), ("E",8):(0,0,8,0,True), ("E",26):(0,26,0,0,True), ("E",35):(55,0,0,0,True), ("E",99):(0,21,2,0,True),
 ("F",11):(0,0,11,0,True), ("F",32):(0,32,0,0,True), ("F",35):(66,0,0,0,True),
 ("G",11):(0,0,0,11,True), ("G",16):(0,0,16,0,True), ("G",35):(79,0,0,0,True), ("G",39):(0,37,2,0,False), ("G",41):(0,41,0,0,True),
 ("H",21):(0,0,21,0,True), ("H",35):(100,0,0,0,True), ("H",53):(0,53,0,0,False), ("H",55):(0,55,0,0,True),
 ("J",4):(0,48,8,0,True), ("J",19):(0,0,0,19,True), ("J",24):(0,0,12,12,True), ("J",29):(0,0,29,0,True),
 ("J",35):(128,0,0,0,True), ("J",43):(0,23,20,0,False), ("J",61):(0,61,0,0,True),
}
ENV_SHEETS = {"20","24","26","40","42","44","46","47"}
HERM_SHEETS = {"21","23","25","27","41","43","45","48"}
ENV_CLASSES, HERM_CLASSES = set("FGTVWZJMKS"), set("NYH")
ENV_CONTACTS, HERM_CONTACTS = set("PSABHJ"), set("PSXZCDY")
PN_RE = re.compile(r"^D38999/(\d\d)([A-Z])([A-J])(\d{1,3})([A-Z])([A-EN])?$")

def check(pn, series):
    if not pn.startswith("D38999/"):
        return None, "Series I/II MS part number syntax not valid (class/finish fields)"
    m = PN_RE.match(pn)
    if not m: return None, "part number syntax not valid"
    sheet, cls, shell, ins, ct, key = m.groups()
    herm = sheet in HERM_SHEETS
    if sheet not in ENV_SHEETS | HERM_SHEETS: return None, f"unknown slash sheet /{sheet}"
    if cls not in (HERM_CLASSES if herm else ENV_CLASSES): return None, f"class {cls} not valid for /{sheet}"
    if ct not in (HERM_CONTACTS if herm else ENV_CONTACTS): return None, f"contact code {ct} not valid for /{sheet}"
    arr = III.get((shell, int(ins)))
    if not arr: return None, f"arrangement {shell}{int(ins)} not in NASA list"
    if sheet.startswith("4") and not arr[4]: return None, f"arrangement {shell}{int(ins)} not offered in Series IV"
    return arr, None

def sizes(a):
    parts = [s for s, n in zip(("22D","20","16","12"), a[:4]) if n]
    return "; ".join(parts), sum(a[:4])

con = sqlite3.connect(DB); cur = con.cursor()
cols = [r[1] for r in cur.execute("pragma table_info(connectors)")]

if "--restore" in sys.argv:
    target = sys.argv[sys.argv.index("--restore") + 1]
    w, p = ("", ()) if target == "ALL" else ("where part_number=?", (target,))
    n = cur.execute(f"insert or ignore into connectors ({','.join(cols)}) select {','.join(cols)} from connectors_unverified {w}", p).rowcount
    cur.execute(f"delete from connectors_unverified {w}", p); con.commit(); print("restored", n); sys.exit()

rows = cur.execute("select rowid, part_number, series, contact_count, contact_size from connectors where spec='MIL-DTL-38999'").fetchall()
fixtures = {r[0] for r in cur.execute("select assembly_connector from fixtures union select mating_connector from fixtures")}
good, bad, reasons, changed = [], [], Counter(), Counter()
for rid, pn, series, cnt, csz in rows:
    arr, why = check(pn, series)
    if why: bad.append((rid, pn, why)); reasons[why.split(" ")[0] + " " + " ".join(why.split(" ")[1:3])] += 1
    else:
        s, total = sizes(arr)
        if cnt != total: changed["contact_count"] += 1
        if csz != s: changed["contact_size"] += 1
        good.append((rid, s, total))

print(f"DB: {os.path.abspath(DB)}\nMode: {'APPLY' if APPLY else 'DRY RUN'}\n")
print(f"MIL-DTL-38999 rows: {len(rows):,}\n  keep (verified): {len(good):,}\n  hide:            {len(bad):,}")
print("\nHide reasons:"); [print(f"  {n:>8,}  {r}") for r, n in reasons.most_common()]
print("\nCorrections on kept rows:"); [print(f"  {n:>8,}  {k}") for k, n in changed.items()]
print("\nExamples hidden:"); seen=set()
for _, pn, why in bad:
    k = re.sub(r"[A-J]?\d+", "#", why)
    if k not in seen or ("syntax" in why and sum(1 for s in seen if s.startswith(pn[:9])) < 1):
        seen.add(k); seen.add(pn[:9]); print(f"  {pn:24} {why}")
hit = [b for b in bad if b[1] in fixtures]
print(f"\nYour fixtures table references {len(hit)} rows that would be hidden:", [h[1] for h in hit])

if APPLY:
    if "verified_source" not in cols:
        cur.execute("alter table connectors add column verified_source TEXT"); cols.append("verified_source")
    cur.execute(f"create table if not exists connectors_unverified as select *, '' as hidden_reason from connectors where 0")
    cur.executemany("update connectors set contact_size=?, compatible_contact_sizes=?, contact_count=?, verified_source=? where rowid=?",
                    [(s, s, t, SOURCE, rid) for rid, s, t in good])
    cur.executemany(f"insert into connectors_unverified ({','.join(cols)}, hidden_reason) select {','.join(cols)}, ? from connectors where rowid=?",
                    [(why, rid) for rid, _, why in bad])
    cur.executemany("delete from connectors where rowid=?", [(rid,) for rid, _, _ in bad])
    con.commit()
    print("\nCOMMITTED. Run VACUUM separately to shrink the file.")
else:
    print("\nDry run only - nothing written.")
