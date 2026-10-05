"""
Verify SAE-AS95234 and MIL-DTL-22992 rows.

  python verify_as95234_22992.py           -> dry run
  python verify_as95234_22992.py --apply   -> apply

  AS95234: PIN, shell size, AS95234-approved arrangement and alternate position (same rules as gen_as95234.py).
  22992:   PIN formats per MIL-DTL-22992H 1.1.1 (same rules as fix_specs_m.py). Insert arrangements are not checked:
           classes C/J/R follow MIL-STD-1651 but the MS sheet list (22992H Supplement 1) is not on file.
Failing rows move to connectors_unverified (nothing deleted).
"""
import sqlite3, sys, os, re, json
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "Data", "connectors.db")
APPLY = "--apply" in sys.argv
J = json.load(open(os.path.join(HERE, "mil-std-1651b-arrangements.json")))
OK1651 = set(J["active"]) | set(J["removed"])

RE_AS = re.compile(r"^AS95234/\d+[A-Z]?-(\d{1,2})-(\d{1,3})[PS][A-Z]?$")
sys.path.insert(0, HERE)
_argv, sys.argv = sys.argv, [sys.argv[0]]          # import fix_specs_m's rules without running its apply step
from importlib import util as _u
_spec = _u.spec_from_file_location("_r", os.path.join(HERE, "fix_specs_m.py")); _r = _u.module_from_spec(_spec)
_src = open(os.path.join(HERE, "fix_specs_m.py")).read().split("con = sqlite3.connect")[0]
exec(compile(_src, "fix_specs_m.py", "exec"), _r.__dict__)
_a = {"__file__": os.path.join(HERE, "gen_as95234.py")}
exec(compile(open(os.path.join(HERE, "gen_as95234.py")).read().split("rows = []")[0], "gen_as95234.py", "exec"), _a)
sys.argv = _argv

def check(spec, pn):
    if spec == "AS95234":
        return _a["why_bad"](pn)
    if spec == "MIL-DTL-22992":
        return _r.why("MIL-DTL-22992", pn)

con = sqlite3.connect(DB); cur = con.cursor()
cols = [r[1] for r in cur.execute("pragma table_info(connectors)")]
rows = cur.execute("select rowid, spec, part_number from connectors where spec in ('AS95234','MIL-DTL-22992')").fetchall()
bad, why_c, ex, keep = [], Counter(), {}, Counter()
for rid, spec, pn in rows:
    w = check(spec, pn)
    if w: bad.append((rid, w)); why_c[(spec, w)] += 1; ex.setdefault((spec, w), pn)
    else: keep[spec] += 1
print(f"Mode: {'APPLY' if APPLY else 'DRY RUN'}")
for spec in ("AS95234", "MIL-DTL-22992"):
    print(f"\n{spec}: {sum(1 for r in rows if r[1]==spec):,} -> keep {keep[spec]:,}")
    for (s, w), n in why_c.most_common():
        if s == spec: print(f"   {n:>6,}  {w:50} e.g. {ex[(s, w)]}")
if APPLY:
    cur.executemany(f"insert into connectors_unverified ({','.join(cols)}, hidden_reason) select {','.join(cols)}, ? from connectors where rowid=?",
                    [(w, rid) for rid, w in bad])
    cur.executemany("delete from connectors where rowid=?", [(rid,) for rid, _ in bad])
    cur.execute("update connectors set verified_source='MIL-DTL-22992H PIN format (arrangement not checked)' where spec='MIL-DTL-22992'")
    con.commit(); print("\nCOMMITTED.")
else:
    print("\nDry run only - nothing written.")
