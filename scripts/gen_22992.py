"""
Build MIL-DTL-22992 class L part numbers.

  python gen_22992.py           -> dry run
  python gen_22992.py --apply   -> insert rows (old invalid 22992 rows stay hidden in connectors_unverified)

Sources:
  MIL-DTL-22992H 1.1.1b + MS90555G / MS90558G: PIN = MS<sheet><finish C|N><shell><key><insert 2 digits><P|S>[rotation]
      e.g. MS90555C32412SY.  MS90555 / MS90557 socket only, MS90556 / MS90558 pin only.
      MS90555 mates with MS90556; MS90558 mates with MS90557.
  Amphenol "Heavy Duty MIL-DTL-22992, Class L" catalog pp. 464-467 and Milnec LM series catalog p. 8 (identical):
      insert arrangements, contacts, master key per voltage, 400 Hz insert rotations, sheet restrictions.
      Finish C (conductive, grounding) for AC; finish N (non-conductive) for 28 V DC.
Not built: arrangements on the MS insert sheets that neither catalog shows (e.g. 32-08, shell 48 / MS90567).
Classes C, J, R (MS17343-MS17348) are not built: their MS sheets are not on file.
"""
import sqlite3, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "Data", "connectors.db")
APPLY = "--apply" in sys.argv
SRC = "Rule-built: MIL-DTL-22992H class L PIN (MS90555G/MS90558G) + Amphenol and Milnec class L catalogs - confirm on MS sheet or QPL"

SHEETS = {  # sheet: (type, style, mounting, contact)
    "90555": ("Receptacle", "Wall Mount Receptacle (power source)", "Panel Wall", "S"),
    "90556": ("Plug", "Straight Plug", "Cable", "P"),
    "90557": ("Receptacle", "Cable Connecting Receptacle, no coupling ring", "Cable", "S"),
    "90558": ("Plug", "Wall Mount Plug with Coupling Ring (equipment)", "Panel Wall", "P")}
MATE = {"90555": "90556", "90556": "90555", "90557": "90558", "90558": "90557"}
KEYS_3PH4W = [("4", "120/208 VAC (also 120/240 VAC 1-phase 3-wire)"), ("5", "240/416 VAC"), ("6", "277/480 VAC")]
# arrangement: (circuit, contacts, finish, keys, rotations, sheets)
ARR = {
 "28-12": ("Three phase AC, 4 wire, grounding", "A,B,C #6; N #6N; G #6N", "C", KEYS_3PH4W, ["Y"], None),
 "28-13": ("Three phase AC, 4 wire, grounding", "A,B,C #6; N #6N; G #6N", "C", KEYS_3PH4W, ["Y"], None),
 "32-04": ("Single phase AC, 2 wire, grounding", "A #4; N #4N; G1,G2 #6N", "C", [("4", "120 VAC"), ("5", "240 VAC")], ["X"], None),
 "32-05": ("Single phase AC, 2 wire, grounding", "A #4; N #4N; G1,G2 #6N", "C", [("4", "120 VAC"), ("5", "240 VAC")], ["X"], None),
 "32-12": ("Three phase AC, 4 wire, grounding", "A,B,C #4; N #4N; G #6N", "C", KEYS_3PH4W, ["Y"], None),
 "32-13": ("Three phase AC, 4 wire, grounding", "A,B,C #4; N #4N; G #6N", "C", KEYS_3PH4W, ["Y"], None),
 "44-02": ("28 VDC, 2 wire", "A #1/0; N #1/0N", "N", [("N", "28 VDC")], [], None),
 "44-03": ("28 VDC, 2 wire", "A #1/0; N #1/0N", "N", [("N", "28 VDC")], [], None),
 "44-12": ("Three phase AC, 4 wire, grounding", "A,B,C #1/0; N #1/0N; G1-G4 #6G", "C", KEYS_3PH4W, ["Z"], None),
 "44-13": ("Three phase AC, 4 wire, grounding", "A,B,C #1/0; N #1/0N; G1-G4 #6G", "C", KEYS_3PH4W, ["Z"], None),
 "44-50": ("Three phase AC, 3 wire, grounding (Navy ground support)", "A,B,C #1/0; G #1/0N", "C", [("1", "450/480 VAC")], [], {"90555", "90558"}),
 "44-51": ("Three phase AC, 3 wire, grounding (Navy ground support)", "A,B,C #1/0; G #1/0N", "C", [("1", "450/480 VAC")], [], {"90556", "90557"}),
 "44-52": ("Three phase AC, 3 wire, grounding (Navy ground support)", "A,B,C #1/0; G #1/0N", "C", [("1", "450/480 VAC")], [], {"90556"}),
 "44-56": ("Three phase AC, 3 wire, grounding (Navy ground support)", "A,B,C #1/0; G #1/0N", "C", [("1", "450/480 VAC")], [], {"90556"}),
 "52-12": ("Three phase AC, 4 wire, grounding", "A,B,C #4/0; N #4/0N; G1-G4 #4G", "C", KEYS_3PH4W, ["W"], None),
 "52-13": ("Three phase AC, 4 wire, grounding", "A,B,C #4/0; N #4/0N; G1-G4 #4G", "C", KEYS_3PH4W, ["W"], None),
}
AMPS = {"28": 40, "32": 60, "44": 100, "52": 200}
FINISH = {"C": ("Aluminum", "Conductive (cadmium, olive drab per MIL-DTL-22992 finish C)"), "N": ("Aluminum", "Non-conductive (hard oxide)")}

rows = []
for arr, (circuit, contacts, fin, keys, rots, only) in ARR.items():
    shell, ins = arr.split("-")
    count = sum(len(g.split(" #")[0].replace("G1-G4", "G1,G2,G3,G4").split(",")) for g in contacts.split("; "))
    sizes = "; ".join(dict.fromkeys(g.split(" #")[1] for g in contacts.split("; ")))
    for sheet, (ctype, style, mount, ct) in SHEETS.items():
        if only and sheet not in only: continue
        for key, volts in keys:
            for rot in [""] + rots:
                pn = f"MS{sheet}{fin}{shell}{key}{ins}{ct}{rot}"
                mate = MATE[sheet]
                mates = f"MS{mate}{fin}{shell}{key}{ins}{'P' if ct == 'S' else 'S'}{rot}" if not only or mate in only else None
                rows.append(dict(part_number=pn, spec="MIL-DTL-22992", series="Class L", prefix=f"MS{sheet}",
                    connector_type=ctype, shell_style=style, mounting_type=mount, insert_arrangement=ins,
                    contact_size=sizes, contact_type=ct, contact_count=count, shell_size_letter=None, shell_size_numeric=shell,
                    keying=key, **{"class": "L"}, shell_material=FINISH[fin][0], shell_plating=FINISH[fin][1],
                    termination_type="Crimp", environment_type="Waterproof", shielding=None, mating_connectors=mates,
                    compatible_contact_sizes=sizes,
                    notes=(f"Arrangement {arr}: {circuit}, {AMPS[shell]} A. Contacts {contacts} (M39029/48 pins, /49 sockets). "
                           f"Master key {key}: {volts}. " + (f"Insert rotation {rot} (400 Hz). " if rot else "Normal insert position (DC or 60 Hz). ")
                           + "Rule-built part number."),
                    verified_source=SRC))

con = sqlite3.connect(DB); cur = con.cursor()
have = {r[0] for r in cur.execute("select part_number from connectors where spec='MIL-DTL-22992'")}
new = [r for r in rows if r["part_number"] not in have]
print(f"Mode: {'APPLY' if APPLY else 'DRY RUN'}\nRule set {len(rows)}; new {len(new)}")
for pn in ("MS90555C32412SY", "MS90556N44N02P", "MS90558C52612PW", "MS90556C44152P", "MS90555C44150S"):
    print("  ", pn, "->", "built" if any(r["part_number"] == pn for r in rows) else "NOT BUILT")
if APPLY:
    cols = list(rows[0].keys()); q = ",".join("?" * len(cols))
    cur.executemany(f"insert or ignore into connectors ({','.join(chr(34)+c+chr(34) for c in cols)}) values ({q})",
                    [tuple(r[c] for c in cols) for r in new])
    cur.executemany("delete from connectors_unverified where part_number=?", [(r["part_number"],) for r in new])
    con.commit(); print("COMMITTED. 22992 live:", cur.execute("select count(*) from connectors where spec='MIL-DTL-22992'").fetchone()[0])
else:
    print("Dry run only - nothing written.")
