"""
Rebuild SAE-AS95234 part numbers.

  python gen_as95234.py           -> dry run
  python gen_as95234.py --apply   -> hide live AS95234 rows that do not match the PIN, insert rule-built rows

PIN (Spacecraft Catalog 802, "AS95234 ordering information"):
    AS95234/<sheet><finish><shell>-<insert><contact><position>        e.g. AS95234/1W18-10PW
  sheet     1 in-line rcpt, 2/3 box mount front/rear, 4/5 wall mount front/rear, 6 straight plug,
            7 jam nut, 8 jam nut w/ accessory threads, 9 plug w/ grounding spring, 13 thru-bulkhead
  finish    A B S W X XS Y YS Z ZS
  shell     10SL 14S 16 16S 18 20 22 24 28 32 36
  contact   P / S crimp (M39029/44 /45), C / D solder cup, A / B less contacts;
            (A / B are valid PINs but not rule-built, as for the other specs)
            thru-bulkhead (/13): E pin-pin, F socket-socket, G pin-socket, H socket-pin
  position  W X Y Z, omitted for normal
Arrangements: code X in the catalog table AND listed in MIL-STD-1651B (contact counts/sizes/alternates from 1651B).
The SAE AS95234 standard itself is not on file - every row says to confirm on the slash sheet or QPL.
"""
import sqlite3, sys, os, json, re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "Data", "connectors.db")
APPLY = "--apply" in sys.argv
SRC = "Rule-built: AS95234 PIN per Spacecraft Cat 802 + MIL-STD-1651B arrangement (AS95234-approved) - confirm on slash sheet or QPL"

CAT = json.load(open(os.path.join(HERE, "as95234-arrangements.json")))["arrangements"]
J1651 = json.load(open(os.path.join(HERE, "mil-std-1651b-arrangements.json")))
ACTIVE, DET = J1651["active"], J1651["details"]
SHELLS = ["10SL", "14S", "16", "16S", "18", "20", "22", "24", "28", "32", "36"]
SHEETS = {"1": ("Receptacle", "In-Line Receptacle", "Cable"),
          "2": ("Receptacle", "Box Mount Receptacle, Front Panel Mount", "Panel Box"),
          "3": ("Receptacle", "Box Mount Receptacle, Rear Panel Mount", "Panel Box"),
          "4": ("Receptacle", "Wall Mount Receptacle, Front Panel Mount", "Panel Wall"),
          "5": ("Receptacle", "Wall Mount Receptacle, Rear Panel Mount", "Panel Wall"),
          "6": ("Plug", "Straight Plug", "Cable"),
          "7": ("Receptacle", "Jam Nut Receptacle", "Panel Jam Nut"),
          "8": ("Receptacle", "Jam Nut Receptacle, Accessory Threads", "Panel Jam Nut"),
          "9": ("Plug", "Straight Plug, Grounding Spring (EMI/RFI)", "Cable"),
          "13": ("Receptacle", "Thru-Bulkhead Receptacle", "Panel Thru-Bulkhead")}
FINISH = {"A": ("Aluminum", "Black Anodize"), "B": ("Stainless Steel", "Cadmium, Black"), "S": ("Stainless Steel", "Passivate"),
          "W": ("Aluminum", "Cadmium, Olive Drab"), "X": ("Aluminum", "Nickel Fluorocarbon"), "XS": ("Stainless Steel", "Nickel Fluorocarbon"),
          "Y": ("Aluminum", "Electrodeposited Aluminum"), "YS": ("Stainless Steel", "Electrodeposited Aluminum"),
          "Z": ("Aluminum", "Zinc-Nickel"), "ZS": ("Stainless Steel", "Zinc-Nickel")}
CONTACT = {"P": ("P", "Crimp", "S"), "S": ("S", "Crimp", "P"), "C": ("P", "Solder", "D"), "D": ("S", "Solder", "C"),
           "A": ("P", "Crimp (less contacts)", "B"), "B": ("S", "Crimp (less contacts)", "A")}
CONTACT_13 = {"E": ("P", "Fixed, pin-pin"), "F": ("S", "Fixed, socket-socket"), "G": ("P", "Fixed, pin-socket"), "H": ("S", "Fixed, socket-pin")}
PLUGS, RCPTS = ["6", "9"], ["1", "2", "3", "4", "5", "7", "8"]

RE_AS = re.compile(r"^AS95234/(1|2|3|4|5|6|7|8|9|13)(XS|YS|ZS|[ABSWXYZ])(10SL|14S|16S|\d{2})-(\d{1,3})([A-H]|P|S)([WXYZ])?$")
def why_bad(pn):
    m = RE_AS.match(pn)
    if not m: return "not an AS95234 PIN: AS95234/<sheet><finish><shell>-<insert><contact>[position] (Spacecraft Cat 802)"
    sheet, fin, shell, ins, ct, pos = m.groups()
    if shell not in SHELLS: return f"shell {shell} not an AS95234 shell size"
    key = f"{shell}-{int(ins)}"
    if key not in CAT or key not in ACTIVE: return f"arrangement {key} not approved for AS95234"
    if (sheet == "13") != (ct in CONTACT_13): return f"contact {ct} not valid on AS95234/{sheet}"
    alts = (DET.get(key) or {}).get("alternates") or []
    if pos and pos not in alts: return f"position {pos} not an alternate for {key} (MIL-STD-1651B)"
    return None

rows = []
for key in CAT:
    if key not in ACTIVE: continue                       # VG-only (16A11, 20A9, 28A63) and cancelled layouts
    shell, ins = key.rsplit("-", 1)
    if shell not in SHELLS: continue
    det = DET.get(key) or {}
    sz = "; ".join(dict.fromkeys(c["size"].split(" ")[0] for c in det.get("contacts", []))) or None
    note = ("Insert arrangement inactive for new design (MIL-STD-1651B); approved for AS95234. " if ACTIVE[key] != "active" else "")
    for sheet, (ctype, style, mount) in SHEETS.items():
        cts = CONTACT_13 if sheet == "13" else {k: v for k, v in CONTACT.items() if k in "PSCD"}   # A/B (less contacts) valid but not built
        for fin, (mat, plat) in FINISH.items():
            for ct, info in cts.items():
                for pos in [""] + (det.get("alternates") or []):
                    pn = f"AS95234/{sheet}{fin}{shell}-{ins}{ct}{pos}"
                    if sheet == "13":
                        mates = []
                    else:
                        opp = CONTACT[ct][2]
                        mates = [f"AS95234/{m}{fin}{shell}-{ins}{opp}{pos}" for m in (RCPTS if sheet in PLUGS else PLUGS)][:3]
                    rows.append(dict(part_number=pn, spec="AS95234", series=None, prefix=f"AS95234/{sheet}",
                        connector_type=ctype, shell_style=style, mounting_type=mount, insert_arrangement=ins,
                        contact_size=sz, contact_type=info[0], contact_count=det.get("total"),
                        shell_size_letter=None, shell_size_numeric=shell, keying=pos or "N", **{"class": fin},
                        shell_material=mat, shell_plating=plat, termination_type=info[1],
                        environment_type="Environment Resisting", shielding="Yes" if sheet == "9" else None,
                        mating_connectors="; ".join(mates) or None, compatible_contact_sizes=sz,
                        notes=note + "Reverse bayonet coupling. Rule-built part number.", verified_source=SRC))
for r in rows: assert why_bad(r["part_number"]) is None, r["part_number"]

con = sqlite3.connect(DB); cur = con.cursor()
cols = [r[1] for r in cur.execute("pragma table_info(connectors)")]
live = cur.execute("select rowid, part_number from connectors where spec='AS95234'").fetchall()
bad = [(rid, pn, w) for rid, pn in live for w in [why_bad(pn)] if w]
wc = Counter(w for _, _, w in bad); ex = {}
for _, pn, w in bad: ex.setdefault(w, pn)
have = {pn for _, pn in live} - {pn for _, pn, _ in bad}
new = [r for r in rows if r["part_number"] not in have]
print(f"Mode: {'APPLY' if APPLY else 'DRY RUN'}\nLive AS95234: {len(live):,} -> hide {len(bad):,}")
for w, n in wc.most_common(): print(f"   {n:>7,}  {w:90} e.g. {ex[w]}")
print(f"Rule set {len(rows):,}; new {len(new):,}; arrangements {len({r['shell_size_numeric']+'-'+r['insert_arrangement'] for r in rows})}")
for pn in ("AS95234/1W18-10PW", "AS95234/6ZS24-28S", "AS95234/13A20-27E", "AS95234/4W32-17P"):
    print("  ", pn, "->", "built" if any(r["part_number"] == pn for r in rows) else "NOT BUILT", why_bad(pn) or "")
if APPLY:
    cur.execute("create index if not exists idx_unverified_pn on connectors_unverified(part_number)")
    cur.executemany(f"insert into connectors_unverified ({','.join(cols)}, hidden_reason) select {','.join(cols)}, ? from connectors where rowid=?",
                    [(w, rid) for rid, _, w in bad])
    cur.executemany("delete from connectors where rowid=?", [(rid,) for rid, _, _ in bad])
    bc = list(rows[0].keys()); q = ",".join("?" * len(bc))
    cur.executemany(f"insert or ignore into connectors ({','.join(chr(34)+k+chr(34) for k in bc)}) values ({q})",
                    [tuple(r[k] for k in bc) for r in new])
    cur.executemany("delete from connectors_unverified where part_number=?", [(r["part_number"],) for r in new])
    con.commit(); print("COMMITTED. AS95234 live:", cur.execute("select count(*) from connectors where spec='AS95234'").fetchone()[0])
else:
    print("Dry run only - nothing written.")
