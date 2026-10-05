"""
Re-verify MIL-DTL-38999 Series III/IV part numbers against the full MIL-STD-1560C
insert arrangement table (scripts/mil-std-1560c-inserts.json) instead of the NASA subset.

  python verify_38999_1560.py           -> dry run
  python verify_38999_1560.py --apply   -> apply

- Rows in connectors_unverified that now pass are moved back into connectors.
- All passing rows get contact_count / contact_size / verified_source from MIL-STD-1560C.
- Rows still failing stay hidden (nothing is deleted).
"""
import sqlite3, sys, os, re, json
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "Data", "connectors.db")
APPLY = "--apply" in sys.argv
SOURCE = "MIL-STD-1560C insert table (verified 2026-10-04)"

STD = json.load(open(os.path.join(HERE, "mil-std-1560c-inserts.json")))["arrangements"]
LETTER = {"A": 9, "B": 11, "C": 13, "D": 15, "E": 17, "F": 19, "G": 21, "H": 23, "J": 25}
TABLE = {(a["shell"], a["insert"]): a for a in STD if a["series"] == "I/III/IV"}

ENV_SHEETS = {"20", "24", "26", "40", "42", "44", "46", "47"}
HERM_SHEETS = {"21", "23", "25", "27", "41", "43", "45", "48"}
# MIL-DTL-38999M w/Amendment 2: classes Table II, contact styles 1.4.2, polarization figures 6 (III) and 7 (IV)
ENV_CLASSES, HERM_CLASSES = set("CFGRTWZJMKSL"), set("NYH")
ENV_CONTACTS, HERM_CONTACTS = set("PSABHJRMGU"), set("PSXZCD")
KEYS = {"2": set("NABCDE"), "4": set("NABCDKLMR")}
PN_RE = re.compile(r"^D38999/(\d\d)([A-Z])([A-J])(\d{1,3})([A-Z])([A-Z])?$")

def check(pn):
    m = PN_RE.match(pn or "")
    if not m: return None, "part number syntax not valid"
    sheet, cls, shell, ins, ct, key = m.groups()
    herm = sheet in HERM_SHEETS
    if sheet not in ENV_SHEETS | HERM_SHEETS: return None, f"unknown slash sheet /{sheet}"
    if cls not in (HERM_CLASSES if herm else ENV_CLASSES): return None, f"class {cls} not valid for /{sheet}"
    if ct not in (HERM_CONTACTS if herm else ENV_CONTACTS): return None, f"contact code {ct} not valid for /{sheet}"
    if sheet.startswith("4") and shell == "A": return None, "Series IV has no shell size A"
    if key and key not in KEYS[sheet[0]]: return None, f"polarization {key} not valid for series {'III' if sheet[0] == '2' else 'IV'} (MIL-DTL-38999M)"
    a = TABLE.get((LETTER[shell], int(ins)))
    if not a: return None, f"arrangement {shell}{int(ins)} not in MIL-STD-1560C"
    return a, None

def describe(a):
    sizes = []
    for c in a["contacts"]:
        s = c["size"].split(" ")[0]
        if s not in sizes: sizes.append(s)
    return "; ".join(sizes), a["total"]

con = sqlite3.connect(DB); cur = con.cursor()
cols = [r[1] for r in cur.execute("pragma table_info(connectors)")]
live = cur.execute("select rowid, part_number from connectors where spec='MIL-DTL-38999'").fetchall()
hidden = cur.execute("select rowid, part_number, hidden_reason from connectors_unverified where spec='MIL-DTL-38999'").fetchall()

restore, still, newly_bad, reasons = [], Counter(), [], Counter()
for rid, pn, old in hidden:
    a, why = check(pn)
    if a: restore.append((rid, pn, a))
    else: still[re.sub(r"[A-J]?\d+", "#", why)] += 1
for rid, pn in live:
    a, why = check(pn)
    if not a: newly_bad.append((rid, pn, why))

inactive = sum(1 for _, _, a in restore if a["inactive"])
print(f"DB: {os.path.abspath(DB)}\nMode: {'APPLY' if APPLY else 'DRY RUN'}\n")
print(f"Live D38999 rows:            {len(live):,}  (would fail now: {len(newly_bad)})")
print(f"Hidden D38999 rows:          {len(hidden):,}")
print(f"  restore (in MIL-STD-1560C): {len(restore):,}  (of which inactive-for-new-design: {inactive:,})")
print(f"  stay hidden:                {len(hidden) - len(restore):,}")
for r, n in still.most_common(): print(f"     {n:>8,}  {r}")
print("\nRestored arrangements:", ", ".join(sorted({f"{PN_RE.match(pn).group(3)}{a['insert']}" for _, pn, a in restore})))
print("Examples:", [pn for _, pn, _ in restore[:8]])

if APPLY:
    cur.executemany(f"insert into connectors ({','.join(cols)}) select {','.join(cols)} from connectors_unverified where rowid=?",
                    [(rid,) for rid, _, _ in restore])
    cur.executemany("delete from connectors_unverified where rowid=?", [(rid,) for rid, _, _ in restore])
    for rid, pn in cur.execute("select rowid, part_number from connectors where spec='MIL-DTL-38999'").fetchall():
        a, _ = check(pn)
        if not a: continue
        s, total = describe(a)
        note = "Insert arrangement inactive for new design (MIL-STD-1560C)." if a["inactive"] else None
        cur.execute("""update connectors set contact_size=?, compatible_contact_sizes=?, contact_count=?, verified_source=?,
                       notes = case when ? is null then notes else ? end where rowid=?""",
                    (s, s, total, SOURCE, note, note, rid))
    con.commit()
    print("\nCOMMITTED.")
else:
    print("\nDry run only - nothing written.")
