"""
Rebuild MIL-DTL-83723 Series III part numbers from the PIN rules in MIL-DTL-83723G.

  python gen_83723.py           -> dry run (counts + examples)
  python gen_83723.py --apply   -> insert rows (replaces any existing live 83723 rows)

PIN (MIL-DTL-83723G 3.7.1):  M83723/<sheet><class><shell><insert 2 digits><position>
                              e.g. M83723/72W808N
Rules used (conservative):
  * Slash sheets 71-78 (bayonet) and 82-87, 91-92, 95-96 (threaded); pin/socket set by sheet.
  * Classes per MIL-DTL-83723G 1.2 / Table I, non-hermetic only:
        bayonet A G M R T W Z;  threaded adds K (firewall).
        RFI-grounding plugs (/77 /78 /91 /92) only classes with grounding fingers: M R T W Z.
    Firewall/hermetic classes N, S, H, J, L, P, Y are omitted (they depend on the spec sheet).
  * Insert arrangements and contact counts/sizes: MIL-STD-1554A w/Change 2 (scripts/mil-std-1554a-inserts.json).
    Positions: N plus alternates (shell 8: 6-9; others: 1-5, 6-9, Y; 1-5 inactive for new design).
Every row is labeled as rule-built; confirm against the spec sheet / QPL before ordering.
"""
import sqlite3, sys, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Data", "connectors.db")
APPLY = "--apply" in sys.argv
SOURCE = "Rule-built: MIL-DTL-83723G PIN format + MIL-STD-1554A arrangements - confirm class/style on spec sheet or QPL"

SHEETS = {  # sheet: (connector_type, shell_style, mounting, contact, coupling, rfi)
 "71": ("Receptacle", "Wall Mount Receptacle", "Panel Wall", "S", "Bayonet", False),
 "72": ("Receptacle", "Wall Mount Receptacle", "Panel Wall", "P", "Bayonet", False),
 "73": ("Receptacle", "Jam Nut Receptacle", "Panel Jam Nut", "S", "Bayonet", False),
 "74": ("Receptacle", "Jam Nut Receptacle", "Panel Jam Nut", "P", "Bayonet", False),
 "75": ("Plug", "Straight Plug", "Cable", "S", "Bayonet", False),
 "76": ("Plug", "Straight Plug", "Cable", "P", "Bayonet", False),
 "77": ("Plug", "Straight Plug, RFI Grounding", "Cable", "S", "Bayonet", True),
 "78": ("Plug", "Straight Plug, RFI Grounding", "Cable", "P", "Bayonet", True),
 "82": ("Receptacle", "Wall Mount Receptacle", "Panel Wall", "S", "Threaded", False),
 "83": ("Receptacle", "Wall Mount Receptacle", "Panel Wall", "P", "Threaded", False),
 "84": ("Receptacle", "Jam Nut Receptacle", "Panel Jam Nut", "S", "Threaded", False),
 "85": ("Receptacle", "Jam Nut Receptacle", "Panel Jam Nut", "P", "Threaded", False),
 "86": ("Plug", "Straight Plug", "Cable", "S", "Threaded", False),
 "87": ("Plug", "Straight Plug", "Cable", "P", "Threaded", False),
 "91": ("Plug", "Straight Plug, RFI Grounding", "Cable", "S", "Threaded", True),
 "92": ("Plug", "Straight Plug, RFI Grounding", "Cable", "P", "Threaded", True),
 "95": ("Plug", "Self-Locking Plug", "Cable", "S", "Threaded", False),
 "96": ("Plug", "Self-Locking Plug", "Cable", "P", "Threaded", False),
}
CLASSES = {  # class: (material, plating)
 "A": ("Aluminum", "Anodize (nonconductive)"), "G": ("Stainless Steel", "Passivated"),
 "K": ("Stainless Steel (firewall)", "Passivated"), "M": ("Aluminum", "Electrodeposited aluminum"),
 "R": ("Aluminum", "Electroless nickel"), "T": ("Aluminum", "Nickel fluorocarbon polymer"),
 "W": ("Aluminum", "Cadmium (olive drab)"), "Z": ("Aluminum", "Zinc-nickel"),
}
BAYONET, THREADED, RFI = "AGMRTWZ", "AGKMRTWZ", "MRTWZ"
J1554 = __import__("json").load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mil-std-1554a-inserts.json")))
INSERTS = {a["arrangement"]: a for a in J1554["arrangements"]}
POS = J1554["positions"]  # alternate insert positions per MIL-STD-1554A / MIL-DTL-83723G
# mating: receptacle sheet -> plug sheets with the opposite contact
MATES = {"71":["76","78"],"72":["75","77"],"73":["76","78"],"74":["75","77"],
         "82":["87","92","96"],"83":["86","91","95"],"84":["87","92","96"],"85":["86","91","95"]}
for r, ps in list(MATES.items()):
    for p in ps: MATES.setdefault(p, []).append(r)

def pn(sheet, cls, arr, pos="N"):
    s, i = arr.split("-")
    return f"M83723/{sheet}{cls}{int(s)}{int(i):02d}{pos}"

rows = []
for sheet, (ctype, style, mount, contact, coupling, rfi) in SHEETS.items():
    classes = RFI if rfi else (BAYONET if coupling == "Bayonet" else THREADED)
    for cls in classes:
        for arr, A in INSERTS.items():
            total = A["total"]; sizes = "; ".join(dict.fromkeys(c["size"] for c in A["contacts"]))
            s, i = arr.split("-")
            mat, plat = CLASSES[cls]
            for pos in ["N"] + (POS["8"] if arr.startswith("8-") else POS["other"]):
                mates = [pn(m, cls, arr, pos) for m in MATES.get(sheet, []) if cls in (RFI if SHEETS[m][5] else (BAYONET if SHEETS[m][4]=="Bayonet" else THREADED))]
                posnote = "" if pos == "N" else f" Alternate insert position {pos}" + (" (inactive for new design)." if pos in POS["inactive"] else ".")
                rows.append(dict(part_number=pn(sheet, cls, arr, pos), spec="MIL-DTL-83723", series="Series III",
                prefix=f"M83723/{sheet}", connector_type=ctype, shell_style=f"{style} ({coupling})", mounting_type=mount,
                insert_arrangement=f"{int(i):02d}", contact_size=sizes, contact_type=contact, contact_count=total,
                shell_size_letter=None, shell_size_numeric=s, keying=pos, **{"class": cls}, shell_material=mat,
                shell_plating=plat, termination_type="Crimp", environment_type="Environment Resisting",
                shielding="Yes" if rfi else None, mating_connectors="; ".join(mates[:3]) or None,
                compatible_contact_sizes=sizes, notes=f"Arrangement {arr}: " + ", ".join(f'{c["count"]} x #{c["size"]}' for c in A["contacts"]) + f" (MIL-STD-1554A). {coupling} coupling." + posnote,
                verified_source=SOURCE))

print(f"Mode: {'APPLY' if APPLY else 'DRY RUN'}\nRows to build: {len(rows):,}")
for r in rows[:3] + rows[-3:]: print("  ", r["part_number"], "|", r["shell_style"], "| mates:", r["mating_connectors"])
if APPLY:
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("delete from connectors where spec='MIL-DTL-83723'")
    cols = list(rows[0].keys()); q = ",".join("?" * len(cols))
    cur.executemany(f"insert or ignore into connectors ({','.join(chr(34)+c+chr(34) for c in cols)}) values ({q})",
                    [tuple(r[c] for c in cols) for r in rows])
    con.commit(); print("COMMITTED:", cur.execute("select count(*) from connectors where spec='MIL-DTL-83723'").fetchone()[0], "rows")
