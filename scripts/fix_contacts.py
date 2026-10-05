"""
Rebuild contact and tooling tables from sourced data.

  python fix_contacts.py           -> dry run (prints every change)
  python fix_contacts.py --apply   -> back up the six tables, then rewrite them

Sources (scripts/contacts-sourced.json):
  glenair - Glenair "AS39029 QPL and Commercial High-Performance Connector Contacts" catalog, tool
            compatibility tables read from the page images: size, wire range, crimp tool + positioner,
            insertion and extraction tools, connector series.
  milnec  - Milnec M39029 cross-reference (milnec.com): size, wire range, color bands, connector series.
            No tooling.
  aiconics- Aiconics mil-spec contact chart (saved PDF): mating end / wire barrel / shielded cavity size,
            color bands, connector families. Adds contacts not in the other two; no tooling or wire range.
  daniels - Daniels (DMC) Tooling Guide TG-BK Rev C.1: crimp tool + positioner (AF8/AFM8/MH860/WA23...), insertion /
            removal tools, wire range, mating end / barrel size per contact, plus Daniels' own M22520 positioner and
            AS81969 cross-reference tables. Tools are stored by military number with the Daniels name alongside.
  Color bands are the AS39029 BIN code (dash number digits in resistor colors).

Kept from your records: the three strip lengths from your internal contact spec records (22D socket /56-348,
size 20 pin /58-363, size 20 socket /56-351). Earlier AI-generated strip lengths, locators and tool locations
are not kept; the locator column holds the Daniels name of the sourced positioner.
Contacts not found in either source move to contacts_unverified (nothing deleted). Every original table is
copied to <table>_bak_20261004 first.
"""
import sqlite3, sys, os, json, re

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "Data", "connectors.db")
APPLY = "--apply" in sys.argv
SRC = json.load(open(os.path.join(HERE, "contacts-sourced.json")))
SOURCED = {r["part_number"]: r for r in SRC["glenair"] + SRC["milnec"]}
# Aiconics mil-spec contact chart (saved 2026-10-04): mating end / wire barrel / shielded cavity size, colors, families
AIC_SRC = "Aiconics mil-spec pin and socket contact chart (aiconics.com, saved 4 Oct 2026)"
AIC = {r["part_number"]: r for r in SRC.get("aiconics", [])}
_fam = {}
for r in AIC.values():
    if r["families"]: _fam.setdefault(r["part_number"].split("/")[0], r["families"])
def aic_text(a):
    size = (f"shielded contact, cavity size {a['shielded']}" if a["shielded"] else f"mating end size {a['mating']}, wire barrel size {a['barrel']}")
    return f"Aiconics: {size}; listed for {a['families'] or _fam.get(a['part_number'].split('/')[0], 'n/a')}. "
for pn, a in AIC.items():
    if pn in SOURCED:
        cb = SOURCED[pn]["color_bands"]
        if not cb or cb.count("/") < 2: cb = a["color_bands"]          # Milnec shows one band for /4, /5; Aiconics gives all three
        SOURCED[pn] = dict(SOURCED[pn], note=SOURCED[pn]["note"] + aic_text(a), color_bands=cb)
        continue
    size = a["shielded"] or ("22D" if a["barrel"] == "22D" else a["mating"])
    SOURCED[pn] = dict(part_number=pn, slash_sheet="/" + pn.split("/")[1].split("-")[0], contact_size=size, contact_type=a["contact_type"],
        gender=a["gender"], wire_gauge_range=None, crimp_options=[], inserter=[], extractor=[],
        compatible_specs=a["families"] or _fam.get(pn.split("/")[0]), color_bands=a["color_bands"], source=AIC_SRC,
        note=aic_text(a) + "Wire range not listed in the sources on file. ")
# ── Daniels (DMC) Tooling Guide ─────────────────────────────────────────────
DX = SRC.get("daniels_xref", {}); DAN = SRC.get("daniels", {})
POS_MIL = DX.get("positioner_dmc_to_mil", {}); INS_MIL = DX.get("insertion_dmc_to_mil", {}); TOOL_MIL = DX.get("tool_dmc_to_mil", {})
DMC = {v: k for k, v in POS_MIL.items()}; DMC.update({v: k for k, v in INS_MIL.items()}); DMC.update({v: k for k, v in TOOL_MIL.items()})
DMC_SRC = "Daniels (DMC) Tooling Guide TG-BK Rev C.1, M39029 tool selection guide"
BIN = "Black Brown Red Orange Yellow Green Blue Violet Grey White".split()
def base(p): return p.split(" (")[0]
def disp(mil):                      # "M22520/2-09 (Daniels K42)"
    d = DMC.get(base(mil)); return f"{mil} (Daniels {d})" if d and d not in mil else mil
def awg_norm(a):
    m = re.match(r"^(\d+)-(\d+)$", a or "")
    return f"{min(int(m[1]), int(m[2]))}-{max(int(m[1]), int(m[2]))}" if m else (a or None)
def dan_series(d):
    out = []
    for t in d["series"]:
        for m in re.finditer(r"(MIL-DTL-\d+|SAE-AS\d+|MIL-STD-\d+)(?:\s*\(?(SERIES \d(?:[\d,& -]*\d)?|CLASS L)\)?)?", t):
            x = m[1] + (" " + m[2].title().replace(" ", " ", 1) if m[2] else "")
            if x not in out: out.append(x)
    return "; ".join(out) or None
def dan_opts(d):
    opts = []
    for tool, pos in d["opts"]:
        t = TOOL_MIL.get(tool, f"Daniels {tool}")
        if pos.upper() == "AFFIXED TO HEAD": p = t
        elif tool == "WA23":
            parts = re.findall(r"(WA23-\d+)\s*\((DIE|LOCATOR)\)", pos)
            p = " + ".join(f"{POS_MIL.get(x, 'Daniels ' + x)} {k.lower()}" for x, k in parts) or f"Daniels {pos}"
        else: p = POS_MIL.get(pos, f"Daniels {pos}")
        opts.append((t, p))
    return opts
def dan_tools(d, key):
    return [INS_MIL.get(x, x if x.startswith("M81969") else f"Daniels {x}") for x in d[key]]
def dan_coax(d):
    if not d.get("coax"): return ""
    c = d["coax"][0]
    bits = [f"{k.lower()}: {v}" for k, v in c.items() if any(w in k for w in ("INNER", "MIDDLE", "OUTER", "CABLE"))]
    return "Coax/shielded tooling (Daniels): " + "; ".join(bits) + ". "
for pn, d in DAN.items():
    opts = dan_opts(d); ins = dan_tools(d, "ins"); ext = dan_tools(d, "rem")
    awg_d = awg_norm(next((a for a in d["awg"] if a), None))
    mat = next((m for m in d["mating"] if m), None); bar = next((b for b in d["barrel"] if b), None)
    dnote = (f"Daniels: {'mating end ' + mat + ', wire barrel ' + bar + ', ' if mat and bar else ''}listed under {dan_series(d) or 'n/a'} (guide pp. {', '.join(map(str, d['pages']))}). " + dan_coax(d))
    if pn in SOURCED:
        r = SOURCED[pn]
        have = {(c, base(p)) for c, p in r["crimp_options"]}
        merged = r["crimp_options"] + [(c, p) for c, p in opts if (c, base(p)) not in have]
        SOURCED[pn] = dict(r, crimp_options=merged,
            inserter=r["inserter"] + [x for x in ins if x not in r["inserter"]],
            extractor=r["extractor"] + [x for x in ext if x not in r["extractor"]],
            wire_gauge_range=r["wire_gauge_range"] or awg_d, note=r["note"] + dnote,
            source=r["source"] + "; " + DMC_SRC, coax=bool(d.get("coax")))
        continue
    ps = next((x for x in d["ps"] if x in ("P", "S")), None)
    if not ps: continue
    dash = pn.split("-")[1]
    size = (bar if bar in ("22D", "22M") else (mat or next((c.get("CONTACT SIZE") or c.get("MATING END") for c in d.get("coax", []) if c.get("CONTACT SIZE") or c.get("MATING END")), None)))
    m = re.match(r"^#?(\d+[A-Z]?)\b", size or ""); size = m[1] if m else size
    SOURCED[pn] = dict(part_number=pn, slash_sheet="/" + pn.split("/")[1].split("-")[0], contact_size=size, contact_type=ps,
        gender="Pin" if ps == "P" else "Socket", wire_gauge_range=awg_d, crimp_options=opts, inserter=ins, extractor=ext,
        compatible_specs=dan_series(d), color_bands=" / ".join(BIN[int(x)] for x in dash) if len(dash) == 3 else None,
        source=DMC_SRC, note=dnote, coax=bool(d.get("coax")))

# Strip lengths you supplied ("verified from internal contact spec records"); all other strip values were AI-generated and are dropped
KEEP_STRIP = {"M39029/56-348", "M39029/58-363", "M39029/56-351"}
FAMILY = {"M22520/1-01": "AF8", "M22520/2-01": "AFM8", "M22520/7-01": "MH860", "M22520/23-01": "WA23", "M22520/34-01": "M22520/34",
          "Daniels 1716P-1": "Daniels 1716", "Daniels 39-000": "Daniels 39"}
TABLES = ("contacts", "contacts_tools", "crimping_tools", "positioners", "insertion_tools", "wire_contact_chart")

def awg(rng):
    if not rng: return None, None
    a = rng.split("-")
    try: return int(a[0]), int(a[-1])
    except ValueError: return None, None

def pick(opts, prefer=None):
    """primary (crimper, positioner): the shop's crimper if the catalog lists it, else the first listed."""
    for c, p in opts:
        if c == prefer: return c, p
    return opts[0] if opts else (None, None)

def tools_text(r):
    if not r["crimp_options"]: return "" if r.get("coax") else "Tooling: not listed in the sources on file. "
    return ("Crimp: " + "; ".join(f"{disp(c)} with " + (f"positioner {disp(p)}" if p != c else "integral positioner") for c, p in r["crimp_options"]) + ". "
            + ("Insertion: " + " or ".join(map(disp, r["inserter"])) + ". " if r["inserter"] else "")
            + ("Extraction: " + " or ".join(map(disp, r["extractor"])) + ". " if r["extractor"] else ""))
def loc_check(loc, pos):
    """compare a shop locator (Daniels K-name) with the Daniels name of the catalog positioner"""
    want = DMC.get(base(pos or ""))
    if not loc: return ""
    if want and loc == want: return f"Locator {loc} matches positioner {base(pos)} (Daniels {want}). "
    if want:
        other = POS_MIL.get(loc)
        return (f"CHECK: your records show locator {loc}" + (f" (= {other})" if other else "")
                + f", but the Daniels guide lists {want} (= {base(pos)}) for this contact. ")
    return f"Locator {loc} is from your shop records - confirm it matches positioner {pos}. "

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
old = {t: [dict(x) for x in cur.execute(f"select * from {t}")] for t in TABLES}
oc = {r["part_number"]: r for r in old["contacts"]}

# ── contacts ─────────────────────────────────────────────────────────────────
hide = [(pn, "not found in the Glenair AS39029 catalog, Milnec, Aiconics or the Daniels Tooling Guide") for pn in oc if pn not in SOURCED]
try:
    restore = [r[0] for r in cur.execute("select part_number from contacts_unverified") if r[0] in SOURCED]
except sqlite3.OperationalError:
    restore = []
contacts = []
for pn, r in SOURCED.items():
    o = oc.get(pn, {})
    lo, hi = awg(r["wire_gauge_range"])
    crimp, pos = pick(r["crimp_options"], o.get("crimper_tool"))
    keep_loc = DMC.get(base(pos or "")) if pos and pos != crimp else None      # Daniels name of the sourced positioner
    keep = pn in KEEP_STRIP and o.get("default_strip_length") is not None
    note = (f"Size {r['contact_size']} {r['gender'].lower()}. " + r["note"] + tools_text(r)
            + (f"Color bands: {r['color_bands']}. " if r["color_bands"] else "")
            + (f"Locator / die: Daniels {keep_loc} (= {base(pos)}). " if keep_loc else "")
            + ("Strip length from your internal contact spec records. " if keep
               else "Strip length not in the sources on file - use the approved work instruction. ")
            + f"Source: {r['source']}.")
    contacts.append(dict(part_number=pn, slash_sheet=r["slash_sheet"], contact_size=r["contact_size"], contact_type=r["contact_type"],
        gender=r["gender"], wire_gauge_min=lo, wire_gauge_max=hi, wire_gauge_range=r["wire_gauge_range"],
        strip_length_min=o.get("strip_length_min") if keep else None, strip_length_max=o.get("strip_length_max") if keep else None,
        default_strip_length=o.get("default_strip_length") if keep else None,
        contact_material=o.get("contact_material") or ("Copper alloy" if r["crimp_options"] else None),
        plating=o.get("plating") or ("Gold" if r["crimp_options"] else None), termination="Crimp",
        compatible_specs=r["compatible_specs"], crimper_tool=crimp, positioner=pos, locator=keep_loc,
        inserter_tool=" or ".join(r["inserter"]) or None, extractor_tool=" or ".join(r["extractor"]) or None,
        tool_family=FAMILY.get(crimp), notes=note))

# ── crimping tools / positioners / insertion tools (catalog) ────────────────
uses = {}   # tool -> [(contact, size)]
for r in SOURCED.values():
    for c, p in r["crimp_options"]:
        uses.setdefault(c, []).append((r["part_number"], r["contact_size"])); uses.setdefault(p, []).append((r["part_number"], r["contact_size"], c))
    for t in r["inserter"] + r["extractor"]:
        uses.setdefault(t, []).append((r["part_number"], r["contact_size"], r["contact_type"],
                                       "ins" if t in r["inserter"] else "", "ext" if t in r["extractor"] else ""))
def sizes(lst): return ", ".join(sorted({u[1] for u in lst if u[1]}, key=lambda s: (len(s), s)))
def slashes(lst): return ", ".join(sorted({u[0].split("-")[0] for u in lst}))
CAT = "Glenair AS39029 catalog and Daniels Tooling Guide tool tables"
DESC = {"M22520/1-01": "Hand crimp tool (Daniels AF8), 8-indent; TH/TP/UH series positioners",
        "M22520/2-01": "Hand crimp tool (Daniels AFM8), miniature 8-indent; K series positioners",
        "M22520/7-01": "Hand crimp tool (Daniels MH860), 4-indent; 86 series positioners",
        "M22520/23-01": "Pneumatic crimp tool (Daniels WA23), large gauge; WA23 dies and locators",
        "M22520/34-01": "Hand crimp tool for MIL-DTL-28840 contacts (positioner M22520/34-02)",
        "Daniels 1716P-1": "Crimp tool with integral positioner (size 10)", "Daniels 39-000": "Daniels 39-000 crimp tool (39 series positioners)"}
crimpers = []
for tool in sorted({c for r in SOURCED.values() for c, _ in r["crimp_options"]}):
    u = uses[tool]
    crimpers.append(dict(part_number=tool, slash_sheet=tool.split("-")[0].replace("M22520", "") if tool.startswith("M22520") else None,
        tool_family=FAMILY.get(tool), description=DESC.get(tool, tool), manufacturer="Daniels / equivalents" if tool in DMC or tool.startswith("Daniels") else None,
        contact_sizes=sizes(u), compatible_contacts=slashes(u),
        positioner_series=", ".join(sorted({base(p) for p in uses if any(len(x) == 3 and x[2] == tool for x in uses[p]) and p != tool})) or None,
        calibration_interval="Per calibration schedule", notes=f"Source: {CAT}."))
positioners = {}
for p, u in uses.items():
    if not (u and len(u[0]) == 3): continue
    crimper = u[0][2]
    if p == crimper: continue                                         # Daniels 1716P-1 is both tool and positioner
    pbase, _, color = p.partition(" (")
    e = positioners.setdefault(pbase, dict(part_number=pbase, tool_family=FAMILY.get(crimper), for_crimper=crimper, contacts=set(), sizes=set(), colors=[]))
    if color and color.rstrip(")") not in ("red", "blue", "yellow"): color = ""
    e["contacts"] |= {x[0] for x in u}; e["sizes"] |= {x[1] for x in u}
    if color: e["colors"].append(f"{color.rstrip(')')} = size {sizes(u)}")
positioners = [dict(part_number=e["part_number"], tool_family=e["tool_family"], for_crimper=e["for_crimper"],
                    contact_size=", ".join(sorted(e["sizes"], key=lambda s: (len(s), s))), contact_type=None,
                    contact_pn=", ".join(sorted(e["contacts"])[:6]) + (" ..." if len(e["contacts"]) > 6 else ""), locator=DMC.get(e["part_number"]),
                    notes=(f"Daniels equivalent: {DMC[e['part_number']]}. " if e["part_number"] in DMC else "")
                          + ("Turret positions: " + "; ".join(sorted(set(e["colors"]))) + ". " if e["colors"] else "")
                          + f"Used with {', '.join(sorted(e['contacts']))}. Source: {CAT}.")
               for e in positioners.values()]
inserts = []
for t, u in uses.items():
    if not (u and len(u[0]) == 5): continue
    ins, ext = any(x[3] for x in u), any(x[4] for x in u)
    specs = sorted({(SOURCED[x[0]]["compatible_specs"] or "").split(" (")[0].split(" Series")[0].split(";")[0] for x in u} - {""})
    inserts.append(dict(part_number=t, tool_type="Insertion/Extraction" if ins and ext else ("Insertion" if ins else "Extraction"),
        contact_size=sizes(u), connector_specs=", ".join(specs),
        description=f"{'Insertion and extraction' if ins and ext else ('Insertion' if ins else 'Extraction')} tool, size {sizes(u)} "
                    f"({'pins and sockets' if len({x[2] for x in u}) == 2 else ('pins' if u[0][2] == 'P' else 'sockets')})",
        notes=(f"Daniels equivalent: {DMC[t]}. " if t in DMC else "") + f"Used with {slashes(u)}. Source: {CAT}."))

# ── shop tool map (contacts_tools) and wire chart: default 38999 contacts ────
DEFAULT = {"22D|P": "M39029/58-360", "22D|S": "M39029/56-348", "20|P": "M39029/58-363", "20|S": "M39029/56-351",
           "16|P": "M39029/58-364", "16|S": "M39029/56-352", "12|P": "M39029/58-365", "12|S": "M39029/56-353",
           "22M|P": "M39029/58-361", "22M|S": "M39029/56-349", "10|P": "M39029/58-528", "10|S": "M39029/56-527"}
cnew = {c["part_number"]: c for c in contacts}
shop = []
have_keys = {o["mapping_key"] for o in old["contacts_tools"]}
for k in ("10|P", "10|S"):
    if k not in have_keys:
        old["contacts_tools"].append(dict(mapping_key=k, contact_part_number=None, contact_size="10", contact_type=k[-1], wire_gauge_range=None,
            strip_length_min=None, strip_length_max=None, default_strip_length=None, crimper_tool=None, positioner=None, locator=None,
            inserter_tool=None, extractor_tool=None, tool_family=None, tool_location=None, notes=None))
for o in old["contacts_tools"]:
    k = o["mapping_key"]; pn = DEFAULT.get(k)
    if not pn:
        shop.append(dict(o, tool_location=None, contact_part_number=None, wire_gauge_range=None, crimper_tool=None, positioner=None, locator=None,
                         inserter_tool=None, extractor_tool=None, tool_family=None, strip_length_min=None, strip_length_max=None,
                         default_strip_length=None,
                         notes=f"No size {o['contact_size']} {'pin' if o['contact_type'] == 'P' else 'socket'} contact for these connectors in the sources on file "
                               f"(previous P/N {o['contact_part_number']} not confirmed)."))
        continue
    r, c = SOURCED[pn], cnew[pn]
    crimp, pos = pick(r["crimp_options"], o["crimper_tool"])
    loc = DMC.get(base(pos or "")) if pos and pos != crimp else None
    keep_strip = o["default_strip_length"] is not None and pn in KEEP_STRIP
    shop.append(dict(o, tool_location=None, contact_part_number=pn, wire_gauge_range=r["wire_gauge_range"], crimper_tool=crimp, positioner=pos, locator=loc,
        inserter_tool=c["inserter_tool"], extractor_tool=c["extractor_tool"], tool_family=FAMILY.get(crimp),
        strip_length_min=o["strip_length_min"] if keep_strip else None, strip_length_max=o["strip_length_max"] if keep_strip else None,
        default_strip_length=o["default_strip_length"] if keep_strip else None,
        notes=f"Default P/N is MIL-DTL-38999 ({r['compatible_specs']}). " + tools_text(r)
              + (f"Locator / die: Daniels {loc} (= {base(pos)}). " if loc else "")
              + ("Strip length from your internal records. " if keep_strip else "Strip length: use the approved work instruction. ")
              + f"Source: {r['source'].split(',')[0]}."))
chart = []
for i, (sz, pin, sock) in enumerate((("22D", "M39029/58-360", "M39029/56-348"), ("22M", "M39029/58-361", "M39029/56-349"),
                                      ("20", "M39029/58-363", "M39029/56-351"), ("16", "M39029/58-364", "M39029/56-352"),
                                      ("12", "M39029/58-365", "M39029/56-353"), ("10", "M39029/58-528", "M39029/56-527")), 1):
    p, s = cnew[pin], cnew[sock]; lo, hi = awg(p["wire_gauge_range"])
    pos = p["positioner"] if p["positioner"] == s["positioner"] else (f"{p['positioner']} (pin) / {s['positioner']} (socket)" if p["positioner"] else None)
    chart.append(dict(id=i, contact_size=sz, awg_min=lo, awg_max=hi, awg_range=f"{p['wire_gauge_range']} AWG", crimper=p["crimper_tool"],
        positioner=pos, locator=" / ".join(dict.fromkeys(x for x in (DMC.get(base(p["positioner"] or "")), DMC.get(base(s["positioner"] or ""))) if x)) or None,
        contact_pin=pin, contact_socket=sock,
        notes=("MIL-DTL-38999 contacts. " + (tools_text(SOURCED[pin]) if SOURCED[pin]["crimp_options"] else "Tooling not in the sources on file. ")
               + "Source: " + SOURCED[pin]["source"].split(",")[0] + ".")))

# ── report ───────────────────────────────────────────────────────────────────
print(f"Mode: {'APPLY' if APPLY else 'DRY RUN'}")
print(f"restore from contacts_unverified (now sourced, rebuilt with corrected data): {restore}")
print(f"contacts: {len(oc)} -> {len(contacts)} sourced ({sum(1 for c in contacts if c['crimper_tool'])} with tooling); hide {len(hide)}")
for pn, w in hide: print("   hide", pn, "-", oc[pn]["contact_size"], oc[pn]["contact_type"])
for c in contacts:
    o = oc.get(c["part_number"])
    if o:
        ch = [f"{k}: {o[k]!r} -> {c[k]!r}" for k in ("contact_size", "contact_type", "wire_gauge_range", "crimper_tool", "positioner",
              "inserter_tool", "extractor_tool", "default_strip_length", "compatible_specs") if str(o[k]) != str(c[k])]
        if ch: print("   fix", c["part_number"], "|", "; ".join(ch))
print(f"crimping_tools {len(old['crimping_tools'])} -> {len(crimpers)}; positioners {len(old['positioners'])} -> {len(positioners)}; "
      f"insertion_tools {len(old['insertion_tools'])} -> {len(inserts)}; wire_contact_chart {len(old['wire_contact_chart'])} -> {len(chart)}; "
      f"contacts_tools {len(shop)} rows (tool locations cleared)")
for s in shop: print("   shop", s["mapping_key"], s["contact_part_number"], s["crimper_tool"], s["positioner"], s["locator"], s["default_strip_length"])

if APPLY:
    for t in TABLES:
        cur.execute(f"create table if not exists {t}_bak_20261004 as select * from {t}")
    cur.execute("create table if not exists contacts_unverified as select *, '' as hidden_reason from contacts where 0")
    cur.executemany("delete from contacts_unverified where part_number=?", [(pn,) for pn in restore])
    for pn, w in hide:
        cols = list(oc[pn].keys())
        cur.execute(f"insert into contacts_unverified ({','.join(cols)}, hidden_reason) values ({','.join('?' * (len(cols) + 1))})",
                    [oc[pn][c] for c in cols] + [w])
    def rewrite(t, rows):
        cur.execute(f"delete from {t}")
        cols = list(rows[0].keys())
        cur.executemany(f"insert into {t} ({','.join(cols)}) values ({','.join('?' * len(cols))})", [[r[c] for c in cols] for r in rows])
    rewrite("contacts", contacts); rewrite("crimping_tools", crimpers); rewrite("positioners", positioners)
    rewrite("insertion_tools", inserts); rewrite("wire_contact_chart", chart); rewrite("contacts_tools", shop)
    cur.execute("create index if not exists idx_connectors_size_type on connectors(contact_size, contact_type)")   # contacts page counts
    con.commit(); print("COMMITTED. Backups: <table>_bak_20261004")
else:
    print("Dry run only - nothing written.")
