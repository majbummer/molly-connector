"""
Rebuild MIL-DTL-26482 from MIL-DTL-26482H w/Amendment 2 + MIL-STD-1669A w/Change 2.

  python fix_26482.py           -> dry run
  python fix_26482.py --apply   -> hide invalid live rows, add rule-built rows

MIL-DTL-26482H rules used:
  1.1.1  Series 1 PIN: MS<sheet><class><shell>-<insert><contact><position><finish>   e.g. MS3114E12-10PYT
         Series 2 PIN: MS<sheet><class><shell>-<insert><contact><position>          e.g. MS3470L12-10PY
  1.2.6  Normal insert position has NO letter; alternates W/X/Y/Z per MIL-STD-1669.
  3.3.9.4 Series 1 finish: W (cadmium, default - no letter), D, T, K.
  Table I Series 1 classes: solder E, P, J, F (H hermetic); crimp E, P, F.
          Series 2 classes: A, L (200 C); W, K, T, D (175 C) (H, N hermetic - separate MS sheets).
  Supplement 1 (MS sheet list) titles give classes for MS3111 (E F J P), MS3114 (E F H P), MS3120 / MS3121 / MS3124 /
          MS3128 (E F P), and MS3475 (L W - no A). Where a title gives no classes:
          3.4.5.1 box-mount receptacles (MS3112 / MS3122 / MS3127) have no grommet/gland nut -> E and P (inferred);
          J (jacketed-cable gland) is solder-only and also built on plug MS3116 (3.6.15.1 "class J plugs").
  Not built: MS3113 / MS3114H hermetic (class H, termination letter), MS3119 thru-bulkhead (classes not given).
Failing live rows are moved to connectors_unverified (nothing deleted).
"""
import sqlite3, sys, os, json, re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "Data", "connectors.db")
APPLY = "--apply" in sys.argv
ARR = json.load(open(os.path.join(HERE, "mil-std-1669a-inserts.json")))["arrangements"]
SRC1 = "Rule-built: MIL-DTL-26482H Series 1 PIN/classes (Table I, Supplement 1) + MIL-STD-1669A arrangement - confirm on MS sheet or QPL"
SRC2 = "Rule-built: MIL-DTL-26482H Series 2 PIN/classes (Table I) + MIL-STD-1669A arrangement - confirm on MS sheet or QPL"

def sizes_of(contacts):
    return "; ".join(dict.fromkeys(c["size"].split(" ")[0] for c in contacts)) or None

# ── validity rules (used to hide bad live rows) ─────────────────────────────
S1_SOLDER, S1_CRIMP = "3110 3111 3112 3113 3114 3116 3119".split(), "3120 3121 3122 3124 3126 3127 3128".split()
RE_S1 = re.compile(r"^MS(31[12][0-9])([A-Z])(\d{1,2})-(\d{1,3})([PSAB])([WXYZ])?([DTK])?$")
RE_S2 = re.compile(r"^MS(347[0-6])([A-Z])(\d{1,2})-(\d{1,3})([PSAB])([WXYZ])?$")
S2_OK = set("ALWKTD")
A1669 = {a["arrangement"]: a for a in ARR}

def why_bad(pn):
    m = RE_S1.match(pn)
    if m:
        ms, cls = m.group(1), m.group(2)
        ok = "EPJFH" if ms in S1_SOLDER else ("EPF" if ms in S1_CRIMP else "")
        if cls not in ok: return f"class {cls} not a Series 1 {'solder' if ms in S1_SOLDER else 'crimp'} class (MIL-DTL-26482H Table I)"
        if ms in S1 and cls not in S1[ms][4] + S1_EXTRA.get(ms, ""):
            return f"class {cls} not offered on MS{ms} " + ("(MIL-DTL-26482H Supplement 1 sheet title)" if ms in S1_EXPLICIT
                   else "(inferred: box mount has no grommet/gland nut, MIL-DTL-26482H 3.4.5.1)" if ms in ("3112", "3122", "3127")
                   else "(inferred from MIL-DTL-26482H Table I / 3.6.15.1)")
        if f"{int(m.group(3))}-{int(m.group(4))}" not in A1669: return "arrangement not in MIL-STD-1669A"
        return None
    m = RE_S2.match(pn)
    if m:
        if m.group(2) not in S2_OK: return f"class {m.group(2)} not a Series 2 class (MIL-DTL-26482H Table I)"
        if m.group(1) == "3475" and m.group(2) == "A": return "MS3475 is classes L and W only - no class A (MIL-DTL-26482H Supplement 1)"
        a = A1669.get(f"{int(m.group(3))}-{int(m.group(4))}")
        if not a: return "arrangement not in MIL-STD-1669A"
        if a.get("note") and "series 2" in a["note"]: return "arrangement not applicable to series 2 (MIL-STD-1669A)"
        return None
    if re.match(r"^MS3[14]\d\d[A-Z]\d{1,2}-\d{1,3}[PSAB]N$", pn):
        return why_bad(pn[:-1]) or "normal insert position is written with no letter (MIL-DTL-26482H 1.2.6)"
    return "part number syntax not valid (MIL-DTL-26482H 1.1.1)"

# ── Series 1 build ───────────────────────────────────────────────────────────
S1 = {  # sheet: (termination, type, style, mounting, classes)
 "3110": ("Solder", "Receptacle", "Wall Mount Receptacle", "Panel Wall", "EPF"),
 "3111": ("Solder", "Receptacle", "Cable Connecting (MS title: plug, cable connecting)", "Cable", "EPFJ"),
 "3112": ("Solder", "Receptacle", "Box Mount Receptacle", "Panel Box", "EP"),
 "3114": ("Solder", "Receptacle", "Jam Nut Receptacle", "Panel Jam Nut", "EPF"),
 "3116": ("Solder", "Plug", "Straight Plug", "Cable", "EPFJ"),
 "3120": ("Crimp", "Receptacle", "Wall Mount Receptacle", "Panel Wall", "EPF"),
 "3121": ("Crimp", "Receptacle", "Cable Connecting (MS title: plug, cable connecting)", "Cable", "EPF"),
 "3122": ("Crimp", "Receptacle", "Box Mount Receptacle", "Panel Box", "EP"),
 "3124": ("Crimp", "Receptacle", "Jam Nut Receptacle", "Panel Jam Nut", "EPF"),
 "3126": ("Crimp", "Plug", "Straight Plug", "Cable", "EPF"),
 "3127": ("Crimp", "Receptacle", "Box Mount Receptacle, 4/6 Hole Flange", "Panel Box", "EP"),
 "3128": ("Crimp", "Receptacle", "Wall Mount Receptacle, 4/6 Hole Flange", "Panel Wall", "EPF"),
}
S1_EXTRA = {"3114": "H"}
S1_EXPLICIT = {"3111", "3114", "3120", "3121", "3124", "3128"}   # classes named in the Supplement 1 sheet title   # class H exists on MS3114 (hermetic) - valid, not rule-built
S1_MATE = {"3116": ["3110", "3112", "3114"], "3126": ["3120", "3122", "3124", "3127", "3128"]}
for p, rs in list(S1_MATE.items()):
    for r in rs: S1_MATE[r] = [p]
S1_MATE["3111"], S1_MATE["3121"] = ["3116"], ["3126"]
S1_CLASS = {"E": "Grommet seal", "P": "Potted seal", "J": "Insert seal with gland seal for jacketed cable", "F": "Grommet seal with strain relief clamp"}
FINISH = {"": "Cadmium, olive drab (finish W, default)", "D": "Pure dense electrodeposited aluminum (finish D)",
          "T": "Nickel fluorocarbon polymer (finish T)", "K": "Zinc-nickel, black (finish K)"}

rows = []
def add(**r): rows.append(r)

for a in ARR:
    sz = sizes_of(a["contacts"])
    for ms, (term, ctype, style, mount, classes) in S1.items():
        for cls in classes:
            for fin, plat in FINISH.items():
                for ct in "PS":
                    opp = "S" if ct == "P" else "P"
                    for pos in [""] + a.get("alternates", []):
                        mates = [f"MS{m}{cls}{a['shell']}-{a['insert']}{opp}{pos}{fin}" for m in S1_MATE[ms] if cls in S1[m][4]]
                        add(part_number=f"MS{ms}{cls}{a['shell']}-{a['insert']}{ct}{pos}{fin}", spec="MIL-DTL-26482", series="Series I",
                            prefix=f"MS{ms}", connector_type=ctype, shell_style=style, mounting_type=mount,
                            insert_arrangement=str(a["insert"]), contact_size=sz, contact_type=ct, contact_count=a["total"],
                            shell_size_letter=None, shell_size_numeric=str(a["shell"]), keying=pos or "N", **{"class": cls},
                            shell_material="Aluminum", shell_plating=plat, termination_type=term,
                            environment_type="Environment Resisting", shielding=None,
                            mating_connectors="; ".join(mates) or None, compatible_contact_sizes=sz,
                            notes=f"Series 1 (125 C), class {cls}: {S1_CLASS[cls]}. "
                                  + ("Insert arrangement inactive for new design (MIL-STD-1669A). " if a["inactive"] else "")
                                  + (a["note"] + ". " if a.get("note") else "") + "Rule-built part number.",
                            verified_source=SRC1)

# ── Series 2: classes K, T, D (175 C) added; A, L, W already built by gen_rules.py ──
S2 = {"3470": ("Receptacle", "Wall Mount Receptacle, Narrow Flange", "Panel Wall"),
      "3472": ("Receptacle", "Wall Mount Receptacle, Wide Flange", "Panel Wall"),
      "3471": ("Receptacle", "Cable Connecting Receptacle", "Cable"),
      "3474": ("Receptacle", "Jam Nut Receptacle", "Panel Jam Nut"),
      "3476": ("Plug", "Straight Plug", "Cable"),
      "3475": ("Plug", "Straight Plug, RFI Grounding", "Cable")}
S2_MATE = {"3476": ["3470", "3474"], "3475": ["3470", "3474"], "3470": ["3476"], "3472": ["3476"], "3471": ["3476"], "3474": ["3476"]}
S2_NEW = {"K": "Zinc-nickel, black (175 C)", "T": "Nickel fluorocarbon polymer (175 C)", "D": "Pure electrodeposited aluminum (175 C)"}
for a in ARR:
    if a.get("note") and "series 2" in a["note"]: continue
    sz = sizes_of(a["contacts"])
    for ms, (ctype, style, mount) in S2.items():
        for cls, plat in S2_NEW.items():
            for ct in "PS":
                opp = "S" if ct == "P" else "P"
                for pos in [""] + a.get("alternates", []):
                    add(part_number=f"MS{ms}{cls}{a['shell']}-{a['insert']}{ct}{pos}", spec="MIL-DTL-26482", series="Series II",
                        prefix=f"MS{ms}", connector_type=ctype, shell_style=style, mounting_type=mount,
                        insert_arrangement=str(a["insert"]), contact_size=sz, contact_type=ct, contact_count=a["total"],
                        shell_size_letter=None, shell_size_numeric=str(a["shell"]), keying=pos or "N", **{"class": cls},
                        shell_material="Aluminum", shell_plating=plat, termination_type="Crimp",
                        environment_type="Environment Resisting", shielding="Yes" if ms == "3475" else None,
                        mating_connectors="; ".join(f"MS{m}{cls}{a['shell']}-{a['insert']}{opp}{pos}" for m in S2_MATE[ms]),
                        compatible_contact_sizes=sz,
                        notes=("Insert arrangement inactive for new design (MIL-STD-1669A). " if a["inactive"] else "") + "Rule-built part number.",
                        verified_source=SRC2)

for r in rows:  # every built PN must pass the validity rules
    assert why_bad(r["part_number"]) is None, r["part_number"]

con = sqlite3.connect(DB); cur = con.cursor()
cols = [r[1] for r in cur.execute("pragma table_info(connectors)")]
live = cur.execute("select rowid, part_number from connectors where spec='MIL-DTL-26482'").fetchall()
bad = [(rid, pn, w) for rid, pn in live for w in [why_bad(pn)] if w]
hide = [(rid, w) for rid, _, w in bad]
wc = Counter(w for _, _, w in bad); ex = {}
for _, pn, w in bad: ex.setdefault(w, pn)
have = {pn for _, pn in live if not why_bad(pn)}
new = [r for r in rows if r["part_number"] not in have]

print(f"Mode: {'APPLY' if APPLY else 'DRY RUN'}")
print(f"Live 26482 rows: {len(live):,}  -> hide {len(hide):,}")
for w, n in wc.most_common(): print(f"   {n:>7,}  {w:75} e.g. {ex[w]}")
c = Counter(r["series"] for r in new)
print(f"Rule set {len(rows):,}; new rows: Series I {c['Series I']:,}, Series II (K/T/D) {c['Series II']:,}")
for pn in ("MS3116E12-10P", "MS3114E12-10PYT", "MS3126F14-19SW", "MS3116J8-33PK", "MS3128F14-19S", "MS3127E12-10P", "MS3475A12-10P", "MS3475W12-10P"):
    print("  ", pn, "->", "built" if any(r["part_number"] == pn for r in rows) else "NOT BUILT")

if APPLY:
    cur.execute("create index if not exists idx_unverified_pn on connectors_unverified(part_number)")
    cur.executemany(f"insert into connectors_unverified ({','.join(cols)}, hidden_reason) select {','.join(cols)}, ? from connectors where rowid=?",
                    [(w, rid) for rid, w in hide])
    cur.executemany("delete from connectors where rowid=?", [(rid,) for rid, _ in hide])
    bc = list(rows[0].keys()); q = ",".join("?" * len(bc))
    cur.executemany(f"insert or ignore into connectors ({','.join(chr(34)+k+chr(34) for k in bc)}) values ({q})",
                    [tuple(r[k] for k in bc) for r in new])
    cur.executemany("delete from connectors_unverified where part_number=?", [(r["part_number"],) for r in new])
    con.commit()
    print("COMMITTED. 26482 live rows now:", cur.execute("select count(*) from connectors where spec='MIL-DTL-26482'").fetchone()[0])
else:
    print("Dry run only - nothing written.")
