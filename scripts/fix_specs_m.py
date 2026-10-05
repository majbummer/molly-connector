"""
Hide rows that the current base specifications rule out.

  python fix_specs_m.py           -> dry run
  python fix_specs_m.py --apply   -> move failing rows to connectors_unverified (nothing deleted)

  MIL-DTL-38999M w/Amendment 2 (series III / IV slash sheets /2x and /4x):
     class must be in Table II: C F G H J K L M N R S T W Y Z
     polarization: series III N A B C D E (figure 6); series IV N A B C D K L M R (figure 7)
  MIL-DTL-22992H, 1.1.1 PIN formats:
     classes C, J, R:  MS<sheet><class C|J|R><shell><finish C|N|P|T|Z><insert><P|S>[alternate]   e.g. MS17343R20C27PW
     class L:          MS9055<5-8><finish C|N><shell 28|32|44|52><key N|1|4|5|6><insert 2 digits><P|S>[alt]
                       MS90555 / MS90557 socket only, MS90556 / MS90558 pin only   e.g. MS90555N32N08SW
"""
import sqlite3, sys, os, re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "Data", "connectors.db")
APPLY = "--apply" in sys.argv

RE_D = re.compile(r"^D38999/([24]\d)([A-Z])([A-J])(\d{1,3})([A-Z])([A-Z])$")
D_CLASSES = set("CFGHJKLMNRSTWYZ")
D_KEYS = {"2": set("NABCDE"), "4": set("NABCDKLMR")}

RE_22992_CJR = re.compile(r"^MS\d{5}([CJR])(\d{1,2})([CNPTZ])(\d{1,3})([PS])([A-Z])?$")
RE_22992_L = re.compile(r"^MS9055([5-8])([CN])(28|32|44|52)([N1456])(\d{2})([PS])([A-Z])?$")

def why(spec, pn):
    if spec == "MIL-DTL-38999":
        m = RE_D.match(pn)
        if not m: return None                      # other formats are handled by verify_38999_1560.py
        sheet, cls, key = m.group(1), m.group(2), m.group(6)
        if cls not in D_CLASSES: return f"class {cls} not in MIL-DTL-38999M Table II"
        if key not in D_KEYS[sheet[0]]:
            return f"polarization {key} not a series {'III' if sheet[0] == '2' else 'IV'} position (MIL-DTL-38999M figure {'6' if sheet[0] == '2' else '7'})"
        return None
    if spec == "MIL-DTL-22992":
        m = RE_22992_L.match(pn)
        if m:
            sock = m.group(1) in "57"
            if (m.group(6) == "S") != sock:
                return f"MS9055{m.group(1)} is {'socket' if sock else 'pin'} only (MIL-DTL-22992H 1.1.1b)"
            return None
        if pn.startswith("MS9055"):
            return "not a class L PIN: MS9055x + finish C/N + shell 28/32/44/52 + key + 2-digit insert (MIL-DTL-22992H 1.1.1b)"
        if RE_22992_CJR.match(pn): return None
        return "not a 22992H PIN: MS no. + class C/J/R + shell + finish C/N/P/T/Z + insert + P/S (MIL-DTL-22992H 1.1.1a)"
    return None

con = sqlite3.connect(DB); cur = con.cursor()
cols = [r[1] for r in cur.execute("pragma table_info(connectors)")]
live = cur.execute("select rowid, spec, part_number from connectors where spec in ('MIL-DTL-38999','MIL-DTL-22992')").fetchall()
bad = [(rid, spec, pn, w) for rid, spec, pn in live for w in [why(spec, pn)] if w]
wc = Counter((s, w) for _, s, _, w in bad); ex = {}
for _, s, pn, w in bad: ex.setdefault((s, w), pn)
print(f"Mode: {'APPLY' if APPLY else 'DRY RUN'}")
for spec in ("MIL-DTL-38999", "MIL-DTL-22992"):
    n = sum(1 for r in live if r[1] == spec)
    print(f"\n{spec}: live {n:,} -> hide {sum(v for (s, _), v in wc.items() if s == spec):,}")
    for (s, w), v in wc.most_common():
        if s == spec: print(f"   {v:>7,}  {w:95} e.g. {ex[(s, w)]}")
if APPLY:
    cur.execute("create index if not exists idx_unverified_pn on connectors_unverified(part_number)")
    cur.executemany(f"insert into connectors_unverified ({','.join(cols)}, hidden_reason) select {','.join(cols)}, ? from connectors where rowid=?",
                    [(w, rid) for rid, _, _, w in bad])
    cur.executemany("delete from connectors where rowid=?", [(rid,) for rid, _, _, _ in bad])
    con.commit(); print("\nCOMMITTED.")
else:
    print("\nDry run only - nothing written.")
