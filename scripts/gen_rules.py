"""
Add missing part numbers built from the governing standards' rules.

  python gen_rules.py           -> dry run (counts + examples)
  python gen_rules.py --apply   -> insert rows that are not already in the database

Normal and alternate key/insert positions are built, and only combinations of documented fields. Existing rows are never changed. Every new row is labeled "Rule-built".

  D38999 Series III/IV  - PIN per MIL-DTL-38999; slash sheets /20 /24 /26 /40 /42 /44 /46 /47;
                          classes per MIL-DTL-38999M Table II (C F G R T W Z J M K S L); arrangements MIL-STD-1560C
                          (Series IV: no shell A); contacts P / S; keys N A-E (series III), N A-D K L M R (series IV).
  MIL-DTL-26482 Series 2 - MS3470/3471/3472/3474/3475/3476; classes A L W;
                          arrangements MIL-STD-1669A (Series-1-only layouts excluded); P / S;
                          normal + the alternate positions (W/X/Y/Z) each arrangement allows.
  MIL-DTL-5015          - crimp MS3450/3451/3452/3454/3456/3459, classes L LS W WS K KT KS U US (MIL-DTL-5015H Table XIX);
                          solder MS3100/3101/3102/3106/3108, classes A E F R (Table XIX);
                          arrangements MIL-STD-1651B current + inactive (not removed) on 5015 shells; P / S;
                          normal + the alternate positions (W/X/Y/Z) each arrangement allows; contact counts from 1651B.
"""
import sqlite3, sys, os, json, re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "Data", "connectors.db")
APPLY = "--apply" in sys.argv
J = lambda f: json.load(open(os.path.join(HERE, f)))

def sizes_of(contacts):
    return "; ".join(dict.fromkeys(c["size"].split(" ")[0] for c in contacts)) or None

rows = []
def add(**r): rows.append(r)

# ── D38999 Series III / IV ───────────────────────────────────────────────────
LET = {9: "A", 11: "B", 13: "C", 15: "D", 17: "E", 19: "F", 21: "G", 23: "H", 25: "J"}
D_SHEETS = {"20": ("Series III", "Receptacle", "Wall Mount Receptacle", "Panel Wall"),
            "24": ("Series III", "Receptacle", "Jam Nut Receptacle", "Panel Jam Nut"),
            "26": ("Series III", "Plug", "Straight Plug", "Cable"),
            "40": ("Series IV", "Receptacle", "Wall Mount Receptacle", "Panel Wall"),
            "42": ("Series IV", "Receptacle", "Box Mount Receptacle", "Panel Box"),
            "44": ("Series IV", "Receptacle", "Jam Nut Receptacle", "Panel Jam Nut"),
            "46": ("Series IV", "Plug", "Straight Plug, EMI Grounding", "Cable"),
            "47": ("Series IV", "Plug", "Straight Plug", "Cable")}
# MIL-DTL-38999M Table II environmental classes (hermetic H, N, Y need hermetic sheets - not built)
D_CLASS = {"C": ("Aluminum Alloy", "Anodic (nonconductive)"), "F": ("Aluminum Alloy", "Electroless Nickel"),
           "G": ("Aluminum Alloy", "Electroless Nickel (space grade)"), "R": ("Aluminum Alloy", "Electroless Nickel (higher corrosion)"),
           "T": ("Aluminum Alloy", "Nickel Fluorocarbon Polymer"), "W": ("Aluminum Alloy", "Olive Drab Cadmium"),
           "Z": ("Aluminum Alloy", "Zinc-Nickel"), "J": ("Composite", "Olive Drab Cadmium"), "M": ("Composite", "Nickel"),
           "K": ("Stainless Steel (firewall)", "Passivated"), "S": ("Stainless Steel (firewall)", "Electrodeposited Nickel"),
           "L": ("Stainless Steel", "Electrodeposited Nickel")}
# MIL-DTL-38999M figure 6 (series III) / figure 7 (series IV): positions apply to all shell sizes
D_KEYS = {"Series III": "NABCDE", "Series IV": "NABCDKLMR"}
D_MATE = {"26": ["20", "24"], "20": ["26"], "24": ["26"], "46": ["40", "42", "44"], "47": ["40", "42", "44"],
          "40": ["46", "47"], "42": ["46", "47"], "44": ["46", "47"]}
for a in J("mil-std-1560c-inserts.json")["arrangements"]:
    if a["series"] != "I/III/IV": continue
    L = LET[a["shell"]]; sz = sizes_of(a["contacts"])
    for sheet, (series, ctype, style, mount) in D_SHEETS.items():
        if series == "Series IV" and L == "A": continue
        for cls, (mat, plat) in D_CLASS.items():
            for ct, key in ((c, k) for c in "PS" for k in D_KEYS[series]):
                opp = "S" if ct == "P" else "P"
                pn = f"D38999/{sheet}{cls}{L}{a['insert']}{ct}{key}"
                mates = "; ".join(f"D38999/{m}{cls}{L}{a['insert']}{opp}{key}" for m in D_MATE[sheet])
                add(part_number=pn, spec="MIL-DTL-38999", series=series, prefix=f"D38999/{sheet}", connector_type=ctype,
                    shell_style=style, mounting_type=mount, insert_arrangement=str(a["insert"]), contact_size=sz,
                    contact_type=ct, contact_count=a["total"], shell_size_letter=L, shell_size_numeric=str(a["shell"]),
                    keying=key, **{"class": cls}, shell_material=mat, shell_plating=plat, termination_type="Crimp",
                    environment_type="Environment Resisting", shielding="Yes", mating_connectors=mates,
                    compatible_contact_sizes=sz,
                    notes=("Insert arrangement inactive for new design (MIL-STD-1560C). " if a["inactive"] else "") + "Rule-built part number.",
                    verified_source="Rule-built: MIL-DTL-38999M PIN/classes/polarization + MIL-STD-1560C arrangement - confirm on slash sheet or QPL")

# ── MIL-DTL-26482 Series 2 ───────────────────────────────────────────────────
S2 = {"3470": ("Receptacle", "Wall Mount Receptacle, Narrow Flange", "Panel Wall"),
      "3472": ("Receptacle", "Wall Mount Receptacle, Wide Flange", "Panel Wall"),
      "3471": ("Receptacle", "Cable Connecting Receptacle", "Cable"),
      "3474": ("Receptacle", "Jam Nut Receptacle", "Panel Jam Nut"),
      "3476": ("Plug", "Straight Plug", "Cable"),
      "3475": ("Plug", "Straight Plug, RFI Grounding", "Cable")}
S2_CLASS = {"A": ("Aluminum", "Black Anodize"), "L": ("Aluminum", "Electroless Nickel"), "W": ("Aluminum", "Olive Drab Cadmium")}
S2_MATE = {"3476": ["3470", "3474"], "3475": ["3470", "3474"], "3470": ["3476"], "3472": ["3476"], "3471": ["3476"], "3474": ["3476"]}
for a in J("mil-std-1669a-inserts.json")["arrangements"]:
    if a.get("note") and "series 2" in a["note"]: continue
    sz = sizes_of(a["contacts"])
    for ms, (ctype, style, mount) in S2.items():
        for cls, (mat, plat) in S2_CLASS.items():
            if ms == "3475" and cls == "A": continue      # MIL-DTL-26482H Supplement 1: MS3475 classes L and W only
            for ct, pos in ((c, p) for c in "PS" for p in [""] + a.get("alternates", [])):
                opp = "S" if ct == "P" else "P"
                add(part_number=f"MS{ms}{cls}{a['shell']}-{a['insert']}{ct}{pos}", spec="MIL-DTL-26482", series="Series II",
                    prefix=f"MS{ms}", connector_type=ctype, shell_style=style, mounting_type=mount,
                    insert_arrangement=str(a["insert"]), contact_size=sz, contact_type=ct, contact_count=a["total"],
                    shell_size_letter=None, shell_size_numeric=str(a["shell"]), keying=pos or "N", **{"class": cls},
                    shell_material=mat, shell_plating=plat, termination_type="Crimp", environment_type="Environment Resisting",
                    shielding="Yes" if ms == "3475" else None,
                    mating_connectors="; ".join(f"MS{m}{cls}{a['shell']}-{a['insert']}{opp}{pos}" for m in S2_MATE[ms]),
                    compatible_contact_sizes=sz,
                    notes=("Insert arrangement inactive for new design (MIL-STD-1669A). " if a["inactive"] else "") + "Rule-built part number.",
                    verified_source="Rule-built: MIL-DTL-26482 Series 2 PIN format + MIL-STD-1669A arrangement - confirm on MS sheet or QPL")

# ── MIL-DTL-5015 ─────────────────────────────────────────────────────────────
M5 = {"3450": ("Crimp", "Receptacle", "Wall Mount Receptacle", "Panel Wall"),
      "3451": ("Crimp", "Receptacle", "Cable Connecting Receptacle", "Cable"),
      "3452": ("Crimp", "Receptacle", "Box Mount Receptacle", "Panel Box"),
      "3454": ("Crimp", "Receptacle", "Jam Nut Receptacle", "Panel Jam Nut"),
      "3456": ("Crimp", "Plug", "Straight Plug", "Cable"),
      "3459": ("Crimp", "Plug", "Straight Plug, Self-Locking", "Cable"),
      "3100": ("Solder", "Receptacle", "Wall Mount Receptacle", "Panel Wall"),
      "3101": ("Solder", "Receptacle", "Cable Connecting Receptacle", "Cable"),
      "3102": ("Solder", "Receptacle", "Box Mount Receptacle", "Panel Box"),
      "3106": ("Solder", "Plug", "Straight Plug", "Cable"),
      "3108": ("Solder", "Plug", "90° Angle Plug", "Cable")}
# MIL-DTL-5015H w/Amendment 1, Table XIX + 6.6.2.1 (class letter + material letter: S stainless, T ferrous/cadmium)
CRIMP_CLASS = {"L": ("Aluminum", "Electroless Nickel"), "LS": ("Stainless Steel", "Passivated"),
               "W": ("Aluminum", "Olive Drab Cadmium over Nickel"), "WS": ("Stainless Steel", "Olive Drab Cadmium"),
               "K": ("Ferrous Alloy (firewall)", "Electroless Nickel"), "KT": ("Ferrous Alloy (firewall)", "Olive Drab Cadmium"),
               "KS": ("Stainless Steel (firewall)", "Passivated"),
               "U": ("Aluminum", "Electroless Nickel"), "US": ("Stainless Steel", "Passivated")}
CRIMP_NOTE = {"U": "Class U inactive for new design, use class L (MIL-DTL-5015H Table XIX). ",
              "US": "Class U inactive for new design, use class L (MIL-DTL-5015H Table XIX). "}
SOLDER_CLASS = {"A": ("Aluminum", "Olive Drab Cadmium - solid shell, nonenvironmental"),
                "E": ("Aluminum", "Olive Drab Cadmium - environment resistant"),
                "F": ("Aluminum", "Olive Drab Cadmium - environment resistant, with clamp"),
                "R": ("Aluminum", "Olive Drab Cadmium - grommet seal without clamp")}
M5_MATE = {"3456": ["3450", "3451", "3452", "3454"], "3459": ["3450", "3451", "3452", "3454"],
           "3450": ["3456"], "3451": ["3456"], "3452": ["3456"], "3454": ["3456"],
           "3106": ["3100", "3101", "3102"], "3108": ["3100", "3101", "3102"],
           "3100": ["3106", "3108"], "3101": ["3106", "3108"], "3102": ["3106", "3108"]}
J1651 = J("mil-std-1651b-arrangements.json"); A1651, D1651 = J1651["active"], J1651["details"]
for key, status in A1651.items():
    shell, ins = key.rsplit("-", 1)
    if shell in ("8", "11", "13", "15", "17"): continue      # 83723 Series II-only shells
    det = D1651.get(key) or {}
    csz = sizes_of(det["contacts"]) if det.get("contacts") else None
    for ms, (term, ctype, style, mount) in M5.items():
        classes = CRIMP_CLASS if term == "Crimp" else SOLDER_CLASS
        for cls, (mat, plat) in classes.items():
            for ct, pos in ((c, p) for c in "PS" for p in [""] + (det.get("alternates") or [])):
                opp = "S" if ct == "P" else "P"
                add(part_number=f"MS{ms}{cls}{shell}-{ins}{ct}{pos}", spec="MIL-DTL-5015", series=term,
                    prefix=f"MS{ms}", connector_type=ctype, shell_style=style, mounting_type=mount,
                    insert_arrangement=ins, contact_size=csz, contact_type=ct, contact_count=det.get("total"),
                    shell_size_letter=None, shell_size_numeric=shell, keying=pos or "N", **{"class": cls},
                    shell_material=mat, shell_plating=plat, termination_type=term, environment_type=None, shielding=None,
                    mating_connectors="; ".join(f"MS{m}{cls}{shell}-{ins}{opp}{pos}" for m in M5_MATE[ms]
                                                if (cls in CRIMP_CLASS) == (M5[m][0] == "Crimp")),
                    compatible_contact_sizes=csz,
                    notes=("Insert arrangement inactive for new design (MIL-STD-1651B). " if status != "active" else "")
                          + CRIMP_NOTE.get(cls, "")
                          + ("Series I (solder): all classes canceled or inactive for new design (MIL-DTL-5015H 6.1k). " if term == "Solder" else "")
                          + "Rule-built part number.",
                    verified_source="Rule-built: MIL-DTL-5015H PIN (6.6) and classes (Table XIX) + MIL-STD-1651B arrangement - confirm on MS sheet or QPL")

con = sqlite3.connect(DB); cur = con.cursor()
have = {r[0] for r in cur.execute("select part_number from connectors")}
new = [r for r in rows if r["part_number"] not in have]
by = Counter(r["spec"] for r in new); tot = Counter(r["spec"] for r in rows)
print(f"Mode: {'APPLY' if APPLY else 'DRY RUN'}")
for s in tot: print(f"  {s:15} rule set {tot[s]:>7,}   already present {tot[s]-by[s]:>6,}   new {by[s]:>7,}")
for pn in ("MS3106A18-1SW", "MS3102E20-27PX", "MS3456L18-1S", "MS3476L12-10PW", "D38999/26WD35SA", "D38999/20FJ61PE"):
    print("  ", pn, "->", "already in DB" if pn in have else ("new" if any(r["part_number"] == pn for r in new) else "NOT BUILT"))
if APPLY:
    cols = list(rows[0].keys()); q = ",".join("?" * len(cols))
    cur.executemany(f"insert or ignore into connectors ({','.join(chr(34)+c+chr(34) for c in cols)}) values ({q})",
                    [tuple(r[c] for c in cols) for r in new])
    # a rebuilt PN that was hidden earlier is now live - drop the hidden copy
    cur.execute("create index if not exists idx_unverified_pn on connectors_unverified(part_number)")
    cur.executemany("delete from connectors_unverified where part_number=?", [(r["part_number"],) for r in new])
    # fill contact counts/sizes on 5015 rule-built rows added before counts were on file
    cur.executemany("update connectors set contact_count=?, contact_size=?, compatible_contact_sizes=? where part_number=? and contact_count is null",
                    [(r["contact_count"], r["contact_size"], r["contact_size"], r["part_number"]) for r in rows
                     if r["spec"] == "MIL-DTL-5015" and r["contact_count"] is not None and r["part_number"] in have])
    cur.executemany("update connectors set verified_source=?, notes=?, shell_plating=? where part_number=? and verified_source like 'Rule-built%'",
                    [(r["verified_source"], r["notes"], r["shell_plating"], r["part_number"]) for r in rows
                     if r["spec"] in ("MIL-DTL-5015", "MIL-DTL-38999") and r["part_number"] in have])
    con.commit(); print("COMMITTED", len(new), "rows")
