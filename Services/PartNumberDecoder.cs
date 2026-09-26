namespace ConnectorDB.Services;

/// <summary>
/// Breaks a MIL-spec connector part number into labelled fields
/// with human-readable descriptions for each value.
/// </summary>
public static class PartNumberDecoder
{
    public record DecodedField(
        string Characters,   // the actual characters from the PN
        string FieldName,    // e.g. "Shell Style"
        string Description,  // e.g. "Straight Plug"
        string? Detail = null // extra context when helpful
    );

    public record DecodeResult(
        string PartNumber,
        string Spec,
        string SpecName,
        List<DecodedField> Fields,
        string? Warning = null
    );

    public static DecodeResult? Decode(string partNumber)
    {
        if (string.IsNullOrWhiteSpace(partNumber)) return null;
        var pn = partNumber.Trim().ToUpperInvariant();

        return pn switch
        {
            _ when pn.StartsWith("D38999/") => DecodeD38999(pn),
            _ when pn.StartsWith("MS27466") => DecodeMS274xx(pn, "MS27466"),
            _ when pn.StartsWith("MS27467") => DecodeMS274xx(pn, "MS27467"),
            _ when pn.StartsWith("MS27468") => DecodeMS274xx(pn, "MS27468"),
            _ when pn.StartsWith("MS27472") => DecodeMS274xx(pn, "MS27472"),
            _ when pn.StartsWith("MS27473") => DecodeMS274xx(pn, "MS27473"),
            _ when pn.StartsWith("MS27474") => DecodeMS274xx(pn, "MS27474"),
            _ when pn.StartsWith("MS27496") => DecodeMS274xx(pn, "MS27496"),
            _ when pn.StartsWith("MS27513") => DecodeMS274xx(pn, "MS27513"),
            _ when pn.StartsWith("MS3110")  => DecodeMS26482(pn, "MS3110"),
            _ when pn.StartsWith("MS3111")  => DecodeMS26482(pn, "MS3111"),
            _ when pn.StartsWith("MS3112")  => DecodeMS26482(pn, "MS3112"),
            _ when pn.StartsWith("MS3114")  => DecodeMS26482(pn, "MS3114"),
            _ when pn.StartsWith("MS3116")  => DecodeMS26482(pn, "MS3116"),
            _ when pn.StartsWith("MS3120")  => DecodeMS26482(pn, "MS3120"),
            _ when pn.StartsWith("MS3121")  => DecodeMS26482(pn, "MS3121"),
            _ when pn.StartsWith("MS3122")  => DecodeMS26482(pn, "MS3122"),
            _ when pn.StartsWith("MS3124")  => DecodeMS26482(pn, "MS3124"),
            _ when pn.StartsWith("MS3126")  => DecodeMS26482(pn, "MS3126"),
            _ when pn.StartsWith("MS3470")  => DecodeMS26482(pn, "MS3470"),
            _ when pn.StartsWith("MS3474")  => DecodeMS26482(pn, "MS3474"),
            _ when pn.StartsWith("MS3476")  => DecodeMS26482(pn, "MS3476"),
            _ when pn.StartsWith("MS3100")  => DecodeMS5015(pn, "MS3100"),
            _ when pn.StartsWith("MS3101")  => DecodeMS5015(pn, "MS3101"),
            _ when pn.StartsWith("MS3102")  => DecodeMS5015(pn, "MS3102"),
            _ when pn.StartsWith("MS3106")  => DecodeMS5015(pn, "MS3106"),
            _ when pn.StartsWith("MS3108")  => DecodeMS5015(pn, "MS3108"),
            _ when pn.StartsWith("MS3400")  => DecodeMS5015(pn, "MS3400"),
            _ when pn.StartsWith("MS3401")  => DecodeMS5015(pn, "MS3401"),
            _ when pn.StartsWith("MS3402")  => DecodeMS5015(pn, "MS3402"),
            _ when pn.StartsWith("MS3406")  => DecodeMS5015(pn, "MS3406"),
            _ when pn.StartsWith("MS3408")  => DecodeMS5015(pn, "MS3408"),
            _ when pn.StartsWith("MS3450")  => DecodeMS5015(pn, "MS3450"),
            _ when pn.StartsWith("MS3452")  => DecodeMS5015(pn, "MS3452"),
            _ when pn.StartsWith("MS3454")  => DecodeMS5015(pn, "MS3454"),
            _ when pn.StartsWith("MS3456")  => DecodeMS5015(pn, "MS3456"),
            _ when pn.StartsWith("M83513/") => DecodeM83513(pn),
            _ when pn.StartsWith("M83723/") => DecodeM83723(pn),
            _ when pn.StartsWith("M24308/") => DecodeM24308(pn),
            _ when pn.StartsWith("MS90555") => DecodeMS22992(pn, "MS90555"),
            _ when pn.StartsWith("MS90556") => DecodeMS22992(pn, "MS90556"),
            _ when pn.StartsWith("MS90557") => DecodeMS22992(pn, "MS90557"),
            _ when pn.StartsWith("MS90558") => DecodeMS22992(pn, "MS90558"),
            _ when pn.StartsWith("MS17344") => DecodeMS22992(pn, "MS17344"),
            _ when pn.StartsWith("AS95234/")=> DecodeAS95234(pn),
            _ => null
        };
    }

    // ── MIL-DTL-38999 Series III/IV (D38999/XX...) ───────────────────────────
    // Pattern: D38999 / SS  C  LL  NN  II  T  K
    //          prefix  dash class shell-letter shell-num insert contact-type keying
    private static DecodeResult DecodeD38999(string pn)
    {
        // e.g. D38999/26WJ35SN  or  D38999/20WA09N03P
        var fields = new List<DecodedField>();

        if (pn.Length < 10) return Unknown(pn, "MIL-DTL-38999");

        // Extract shell style code (2 digits after the slash)
        var afterSlash = pn[7..]; // everything after "D38999/"
        if (afterSlash.Length < 2) return Unknown(pn, "MIL-DTL-38999");

        var styleCode = afterSlash[..2];
        fields.Add(new DecodedField(
            $"D38999/{styleCode}",
            "Prefix / Shell Style",
            D38999ShellStyle(styleCode),
            "MIL-DTL-38999"
        ));

        var rest = afterSlash[2..];
        if (rest.Length == 0) return new DecodeResult(pn, "MIL-DTL-38999", "MIL-DTL-38999 Series III/IV", fields);

        // Class (1 letter)
        var cls = rest[0].ToString();
        fields.Add(new DecodedField(cls, "Class", D38999Class(cls)));
        rest = rest[1..];

        // Shell size letter (1 letter A-J)
        if (rest.Length > 0 && char.IsLetter(rest[0]))
        {
            var sl = rest[0].ToString();
            var impliedNumeric = D38999LetterToNumeric(sl);
            fields.Add(new DecodedField(sl, "Shell Size",
                $"{D38999ShellLetter(sl)} (implies shell size {impliedNumeric})"));
            rest = rest[1..];
        }

        // Shell size numeric (2 digits)
        if (rest.Length >= 2 && char.IsDigit(rest[0]) && char.IsDigit(rest[1]))
        {
            var sn = rest[..2];
            fields.Add(new DecodedField(sn, "Shell Size (Numeric)", $"Shell size {int.Parse(sn)}"));
            rest = rest[2..];
        }

        // Insert arrangement (2 digits)
        if (rest.Length >= 2 && char.IsDigit(rest[0]))
        {
            var ins = rest[..2];
            fields.Add(new DecodedField(ins, "Insert Arrangement",
                $"Insert code {ins} — determines pin count and contact layout"));
            rest = rest[2..];
        }

        // Contact type (P or S)
        if (rest.Length >= 1 && (rest[0] == 'P' || rest[0] == 'S'))
        {
            var ct = rest[0].ToString();
            fields.Add(new DecodedField(ct, "Contact Type",
                ct == "P" ? "Pin contacts (male)" : "Socket contacts (female)"));
            rest = rest[1..];
        }

        // Keying (N, A-E)
        if (rest.Length >= 1)
        {
            var key = rest[0].ToString();
            fields.Add(new DecodedField(key, "Keying", D38999Keying(key)));
        }

        return new DecodeResult(pn, "MIL-DTL-38999", "MIL-DTL-38999 Series III / IV", fields);
    }

    // ── MIL-DTL-38999 Series I/II (MS27466, MS27467 etc.) ───────────────────
    // Pattern: MS27466  W  9  N  03  P
    //          prefix  class shell-num keying insert contact-type
    private static DecodeResult DecodeMS274xx(string pn, string prefix)
    {
        var fields = new List<DecodedField>();
        var seriesInfo = MS27xxxSeriesInfo(prefix);

        fields.Add(new DecodedField(prefix, "Prefix / Shell Style",
            seriesInfo.shellStyle, $"MIL-DTL-38999 {seriesInfo.series}"));

        var rest = pn[prefix.Length..];

        // Class (1 letter)
        if (rest.Length > 0 && char.IsLetter(rest[0]))
        {
            var cls = rest[0].ToString();
            fields.Add(new DecodedField(cls, "Class", D38999Class(cls)));
            rest = rest[1..];
        }

        // Shell size numeric (1-2 digits)
        var snMatch = System.Text.RegularExpressions.Regex.Match(rest, @"^(\d{1,2})");
        if (snMatch.Success)
        {
            var sn = snMatch.Value;
            fields.Add(new DecodedField(sn, "Shell Size",
                $"Shell size {sn} — {D38999ShellLetter(D38999NumericToLetter(sn))} shell"));
            rest = rest[sn.Length..];
        }

        // Keying (letter before insert, if present and not N with digits following)
        if (rest.Length > 0 && char.IsLetter(rest[0]) && !(rest.Length > 1 && char.IsDigit(rest[1])))
        {
            // skip — absorbed into insert field in some series
        }
        else if (rest.Length > 0 && char.IsLetter(rest[0]))
        {
            var key = rest[0].ToString();
            fields.Add(new DecodedField(key, "Keying", D38999Keying(key)));
            rest = rest[1..];
        }

        // Insert (2 digits)
        var insMatch = System.Text.RegularExpressions.Regex.Match(rest, @"^(\d{2})");
        if (insMatch.Success)
        {
            var ins = insMatch.Value;
            fields.Add(new DecodedField(ins, "Insert Arrangement",
                $"Insert code {ins} — determines pin count and layout"));
            rest = rest[ins.Length..];
        }

        // Contact type
        if (rest.Length > 0 && (rest[0] == 'P' || rest[0] == 'S'))
        {
            var ct = rest[0].ToString();
            fields.Add(new DecodedField(ct, "Contact Type",
                ct == "P" ? "Pin contacts (male)" : "Socket contacts (female)"));
        }

        return new DecodeResult(pn, "MIL-DTL-38999", $"MIL-DTL-38999 {seriesInfo.series}", fields);
    }

    // ── MIL-DTL-26482 (MS3110, MS3112 etc.) ──────────────────────────────────
    // Pattern: MS3110  E  8-3  P  N
    //          prefix class insert contact keying
    private static DecodeResult DecodeMS26482(string pn, string prefix)
    {
        var fields = new List<DecodedField>();
        var info = MS26482PrefixInfo(prefix);
        fields.Add(new DecodedField(prefix, "Prefix / Shell Style", info, "MIL-DTL-26482"));

        var rest = pn[prefix.Length..];

        // Class (1 letter)
        if (rest.Length > 0 && char.IsLetter(rest[0]))
        {
            var cls = rest[0].ToString();
            fields.Add(new DecodedField(cls, "Class", MS26482Class(cls)));
            rest = rest[1..];
        }

        // Insert arrangement (digits-digits, e.g. 8-3 or 12-10)
        var insMatch = System.Text.RegularExpressions.Regex.Match(rest, @"^(\d+-\d+|\d+)");
        if (insMatch.Success)
        {
            var ins = insMatch.Value;
            var parts = ins.Split('-');
            var shellNum = parts[0];
            var insertNum = parts.Length > 1 ? parts[1] : "?";
            fields.Add(new DecodedField(shellNum, "Shell Size", $"Shell size {shellNum}"));
            if (parts.Length > 1)
                fields.Add(new DecodedField(insertNum, "Insert Arrangement",
                    $"Insert code {insertNum} — determines pin count and layout"));
            rest = rest[ins.Length..];
        }

        // Contact type
        if (rest.Length > 0 && (rest[0] == 'P' || rest[0] == 'S'))
        {
            var ct = rest[0].ToString();
            fields.Add(new DecodedField(ct, "Contact Type",
                ct == "P" ? "Pin contacts (male)" : "Socket contacts (female)"));
            rest = rest[1..];
        }

        // Keying
        if (rest.Length > 0)
        {
            var key = rest[0].ToString();
            fields.Add(new DecodedField(key, "Keying", MS26482Keying(key)));
        }

        return new DecodeResult(pn, "MIL-DTL-26482", "MIL-DTL-26482", fields);
    }

    // ── MIL-DTL-5015 (MS3100, MS3102 etc.) ───────────────────────────────────
    // Pattern: MS3102  A  12-10  P
    //          prefix class insert contact
    private static DecodeResult DecodeMS5015(string pn, string prefix)
    {
        var fields = new List<DecodedField>();
        var info = MS5015PrefixInfo(prefix);
        fields.Add(new DecodedField(prefix, "Prefix / Shell Style", info, "MIL-DTL-5015"));

        var rest = pn[prefix.Length..];

        // Class (1 letter)
        if (rest.Length > 0 && char.IsLetter(rest[0]))
        {
            var cls = rest[0].ToString();
            fields.Add(new DecodedField(cls, "Class", MS5015Class(cls)));
            rest = rest[1..];
        }

        // Insert: shell-insert (e.g. 12-10) or just digits
        var insMatch = System.Text.RegularExpressions.Regex.Match(rest, @"^(\d+-\d+|\d+)");
        if (insMatch.Success)
        {
            var ins = insMatch.Value;
            var parts = ins.Split('-');
            fields.Add(new DecodedField(parts[0], "Shell Size", $"Shell size {parts[0]}"));
            if (parts.Length > 1)
                fields.Add(new DecodedField(parts[1], "Insert Arrangement",
                    $"Insert code {parts[1]} — determines pin count and layout"));
            rest = rest[ins.Length..];
        }

        // Contact type
        if (rest.Length > 0 && (rest[0] == 'P' || rest[0] == 'S'))
        {
            var ct = rest[0].ToString();
            fields.Add(new DecodedField(ct, "Contact Type",
                ct == "P" ? "Pin contacts (male)" : "Socket contacts (female)"));
        }

        return new DecodeResult(pn, "MIL-DTL-5015", "MIL-DTL-5015", fields);
    }

    // ── MIL-DTL-83513 Micro-D (M83513/XX-NNT) ────────────────────────────────
    // Pattern: M83513/03  -  9  P
    //          prefix     dash contacts type
    private static DecodeResult DecodeM83513(string pn)
    {
        var fields = new List<DecodedField>();

        var slashIdx = pn.IndexOf('-');
        if (slashIdx < 0) return Unknown(pn, "MIL-DTL-83513");

        var prefix = pn[..slashIdx];
        var rest   = pn[(slashIdx + 1)..];

        fields.Add(new DecodedField(prefix, "Prefix / Slash Sheet",
            M83513SlashSheet(prefix), "MIL-DTL-83513 Micro-D"));

        // Contact count (digits)
        var cntMatch = System.Text.RegularExpressions.Regex.Match(rest, @"^(\d+)");
        if (cntMatch.Success)
        {
            var cnt = cntMatch.Value;
            fields.Add(new DecodedField(cnt, "Contact Count", $"{cnt} contacts"));
            rest = rest[cnt.Length..];
        }

        // Contact type
        if (rest.Length > 0 && (rest[0] == 'P' || rest[0] == 'S'))
        {
            var ct = rest[0].ToString();
            fields.Add(new DecodedField(ct, "Contact Type",
                ct == "P" ? "Pin contacts (male)" : "Socket contacts (female)"));
        }

        return new DecodeResult(pn, "MIL-DTL-83513", "MIL-DTL-83513 Micro-D", fields);
    }

    // ── MIL-DTL-83723 (M83723/71...) ─────────────────────────────────────────
    // Pattern: M83723/71  W  10  3  P  N
    //          prefix    class shell insert type keying
    private static DecodeResult DecodeM83723(string pn)
    {
        var fields = new List<DecodedField>();

        // Find prefix (up through /XX)
        var m = System.Text.RegularExpressions.Regex.Match(pn, @"^(M83723/\d+)(.*)");
        if (!m.Success) return Unknown(pn, "MIL-DTL-83723");

        var prefix = m.Groups[1].Value;
        var rest   = m.Groups[2].Value;

        fields.Add(new DecodedField(prefix, "Prefix / Slash Sheet",
            M83723SlashSheet(prefix), "MIL-DTL-83723 Series III"));

        // Class
        if (rest.Length > 0 && char.IsLetter(rest[0]))
        {
            var cls = rest[0].ToString();
            fields.Add(new DecodedField(cls, "Class", D38999Class(cls)));
            rest = rest[1..];
        }

        // Shell + insert (digits e.g. 103 = shell 10, insert 3)
        var snm = System.Text.RegularExpressions.Regex.Match(rest, @"^(\d{2,3})");
        if (snm.Success)
        {
            var digits = snm.Value;
            if (digits.Length >= 3)
            {
                var shell  = digits[..^1];
                var insert = digits[^1..];
                fields.Add(new DecodedField(shell, "Shell Size", $"Shell size {shell}"));
                fields.Add(new DecodedField(insert, "Insert Arrangement", $"Insert code {insert}"));
            }
            else
            {
                fields.Add(new DecodedField(digits, "Shell / Insert", digits));
            }
            rest = rest[digits.Length..];
        }

        // Contact type
        if (rest.Length > 0 && (rest[0] == 'P' || rest[0] == 'S'))
        {
            var ct = rest[0].ToString();
            fields.Add(new DecodedField(ct, "Contact Type",
                ct == "P" ? "Pin contacts (male)" : "Socket contacts (female)"));
            rest = rest[1..];
        }

        // Keying
        if (rest.Length > 0)
        {
            var key = rest[0].ToString();
            fields.Add(new DecodedField(key, "Keying", D38999Keying(key)));
        }

        return new DecodeResult(pn, "MIL-DTL-83723", "MIL-DTL-83723 Series III", fields);
    }

    // ── MIL-DTL-24308 D-Sub (M24308/X-NNT) ──────────────────────────────────
    private static DecodeResult DecodeM24308(string pn)
    {
        var fields = new List<DecodedField>();
        var m = System.Text.RegularExpressions.Regex.Match(pn, @"^(M24308/\d+)-(\d+)([PFS])$");
        if (!m.Success) return Unknown(pn, "MIL-DTL-24308");

        var prefix  = m.Groups[1].Value;
        var insert  = m.Groups[2].Value;
        var contact = m.Groups[3].Value;

        fields.Add(new DecodedField(prefix, "Prefix / Slash Sheet", M24308SlashSheet(prefix), "MIL-DTL-24308 D-Sub"));
        fields.Add(new DecodedField(insert, "Insert Arrangement", $"Insert code {insert} — contact count and arrangement"));
        fields.Add(new DecodedField(contact, "Contact Type",
            contact == "P" ? "Pin contacts (male)" : contact == "S" ? "Socket contacts (female)" : "Socket (F-style)"));

        return new DecodeResult(pn, "MIL-DTL-24308", "MIL-DTL-24308 D-Subminiature", fields);
    }

    // ── MIL-DTL-22992 (MS90555 etc.) ─────────────────────────────────────────
    private static DecodeResult DecodeMS22992(string pn, string prefix)
    {
        var fields = new List<DecodedField>();
        fields.Add(new DecodedField(prefix, "Prefix / Shell Style", MS22992PrefixInfo(prefix), "MIL-DTL-22992"));

        var rest = pn[prefix.Length..];

        if (rest.Length > 0 && char.IsLetter(rest[0]))
        {
            var cls = rest[0].ToString();
            fields.Add(new DecodedField(cls, "Class", MS22992Class(cls)));
            rest = rest[1..];
        }

        var insMatch = System.Text.RegularExpressions.Regex.Match(rest, @"^(\d+-\d+|\d+)");
        if (insMatch.Success)
        {
            var ins = insMatch.Value;
            var parts = ins.Split('-');
            fields.Add(new DecodedField(parts[0], "Shell Size", $"Shell size {parts[0]}"));
            if (parts.Length > 1)
                fields.Add(new DecodedField(parts[1], "Insert Arrangement", $"Insert code {parts[1]}"));
            rest = rest[ins.Length..];
        }

        if (rest.Length > 0 && (rest[0] == 'P' || rest[0] == 'S'))
        {
            var ct = rest[0].ToString();
            fields.Add(new DecodedField(ct, "Contact Type",
                ct == "P" ? "Pin contacts (male)" : "Socket contacts (female)"));
        }

        return new DecodeResult(pn, "MIL-DTL-22992", "MIL-DTL-22992", fields);
    }

    // ── AS95234 Reverse Bayonet ───────────────────────────────────────────────
    private static DecodeResult DecodeAS95234(string pn)
    {
        var fields = new List<DecodedField>();
        var m = System.Text.RegularExpressions.Regex.Match(pn, @"^(AS95234/\d+)-(\d+)-(\d+)([PS])$");
        if (!m.Success) return Unknown(pn, "AS95234");

        var prefix = m.Groups[1].Value;
        var shell  = m.Groups[2].Value;
        var insert = m.Groups[3].Value;
        var ct     = m.Groups[4].Value;

        fields.Add(new DecodedField(prefix, "Prefix / Shell Style", AS95234SlashSheet(prefix), "AS95234 Reverse Bayonet"));
        fields.Add(new DecodedField(shell,  "Shell Size", $"Shell size {shell}"));
        fields.Add(new DecodedField(insert, "Insert Arrangement", $"Insert code {insert}"));
        fields.Add(new DecodedField(ct,     "Contact Type",
            ct == "P" ? "Pin contacts (male)" : "Socket contacts (female)"));

        return new DecodeResult(pn, "AS95234", "AS95234 Reverse Bayonet", fields);
    }

    private static DecodeResult Unknown(string pn, string spec) =>
        new(pn, spec, spec, new List<DecodedField>(),
            "Part number structure could not be fully decoded.");

    // ── Lookup tables ─────────────────────────────────────────────────────────

    private static string D38999ShellStyle(string code) => code switch
    {
        "20" => "Wall Mount Receptacle",
        "21" => "Hermetic Box Mount Receptacle",
        "23" => "Hermetic Jam Nut Receptacle",
        "24" => "Jam Nut Receptacle",
        "25" => "Hermetic Straight Plug",
        "26" => "Straight Plug",
        "27" => "Hermetic Right Angle Plug",
        "46" => "Series IV Wall Mount Receptacle",
        "47" => "Series IV Straight Plug",
        _ => $"Shell style code {code}"
    };

    private static string D38999Class(string cls) => cls switch
    {
        "W" => "W — Aluminum alloy / Olive drab cadmium",
        "G" => "G — Aluminum alloy / Electroless nickel",
        "T" => "T — Titanium alloy",
        "Z" => "Z — Aluminum alloy / Zinc-nickel",
        "J" => "J — Aluminum alloy / Nickel-PTFE",
        "K" => "K — Aluminum alloy / Electroless nickel + PTFE",
        "M" => "M — Aluminum alloy / Black zinc-cobalt",
        "P" => "P — Aluminum alloy / Passivate",
        "R" => "R — Aluminum alloy / Bright dip",
        "Y" => "Y — Stainless steel",
        "H" => "H — Aluminum alloy / Electroless nickel (Hermetic)",
        "N" => "N — Aluminum alloy / Olive drab cadmium (Hermetic)",
        _ => $"Class {cls}"
    };

    private static string D38999ShellLetter(string letter) => letter switch
    {
        "A" => "A — Shell size 09",
        "B" => "B — Shell size 11",
        "C" => "C — Shell size 13",
        "D" => "D — Shell size 15",
        "E" => "E — Shell size 17",
        "F" => "F — Shell size 19",
        "G" => "G — Shell size 21",
        "H" => "H — Shell size 23",
        "J" => "J — Shell size 25",
        _ => $"Shell letter {letter}"
    };

    private static string D38999LetterToNumeric(string letter) => letter switch
    {
        "A" => "09", "B" => "11", "C" => "13", "D" => "15",
        "E" => "17", "F" => "19", "G" => "21", "H" => "23", "J" => "25",
        _ => "?"
    };

    private static string D38999NumericToLetter(string sn) => sn.TrimStart('0') switch
    {
        "9"  => "A", "11" => "B", "13" => "C", "15" => "D",
        "17" => "E", "19" => "F", "21" => "G", "23" => "H", "25" => "J",
        _ => "?"
    };

    private static string D38999Keying(string key) => key switch
    {
        "N" => "N — No keying (universal mating)",
        "A" => "A — Keying position A",
        "B" => "B — Keying position B",
        "C" => "C — Keying position C",
        "D" => "D — Keying position D",
        "E" => "E — Keying position E",
        _ => $"Keying {key}"
    };

    private static (string series, string shellStyle) MS27xxxSeriesInfo(string prefix) => prefix switch
    {
        "MS27466" => ("Series I", "Box Mount Receptacle (Series I)"),
        "MS27467" => ("Series I", "Straight Plug (Series I)"),
        "MS27468" => ("Series I", "Jam Nut Receptacle (Series I)"),
        "MS27472" => ("Series II", "Box Mount Receptacle (Series II)"),
        "MS27473" => ("Series II", "Straight Plug (Series II)"),
        "MS27474" => ("Series II", "Jam Nut Receptacle (Series II)"),
        "MS27496" => ("Series II", "Wall Mount Receptacle (Series II)"),
        "MS27513" => ("Series II", "Right Angle Plug (Series II)"),
        _ => ("Series I/II", prefix)
    };

    private static string MS26482PrefixInfo(string prefix) => prefix switch
    {
        "MS3110" => ("Box Mount Receptacle"),
        "MS3111" => ("Box Mount Receptacle — Solder"),
        "MS3112" => ("Straight Plug"),
        "MS3114" => ("Straight Plug — Solder"),
        "MS3116" => ("Jam Nut Receptacle"),
        "MS3120" => ("Box Mount Receptacle — ENV Resistant"),
        "MS3121" => ("Box Mount Receptacle — ENV Resistant Solder"),
        "MS3122" => ("Straight Plug — ENV Resistant"),
        "MS3124" => ("Straight Plug — ENV Resistant Solder"),
        "MS3126" => ("Jam Nut Receptacle — ENV Resistant"),
        "MS3470" => ("Wall Mount Receptacle — Series II"),
        "MS3474" => ("Straight Plug — Series II"),
        "MS3476" => ("Jam Nut Receptacle — Series II"),
        _ => prefix
    };

    private static string MS26482Class(string cls) => cls switch
    {
        "E" => "E — Aluminum alloy / Olive drab cadmium",
        "R" => "R — Aluminum alloy / Electroless nickel",
        "L" => "L — Stainless steel",
        "W" => "W — Aluminum alloy / Zinc-nickel",
        _ => $"Class {cls}"
    };

    private static string MS26482Keying(string key) => key switch
    {
        "N" => "N — No keying",
        "W" => "W — Keying position W",
        "X" => "X — Keying position X",
        "Y" => "Y — Keying position Y",
        _ => $"Keying {key}"
    };

    private static string MS5015PrefixInfo(string prefix) => prefix switch
    {
        "MS3100" => "Box Mount Receptacle",
        "MS3101" => "Box Mount Receptacle — Solder",
        "MS3102" => "Cable Receptacle",
        "MS3106" => "Straight Plug",
        "MS3108" => "Angle Plug",
        "MS3400" => "Box Mount Receptacle — ENV Resistant",
        "MS3401" => "Box Mount Receptacle — ENV Resistant Solder",
        "MS3402" => "Cable Receptacle — ENV Resistant",
        "MS3406" => "Straight Plug — ENV Resistant",
        "MS3408" => "Angle Plug — ENV Resistant",
        "MS3450" => "Wall Mount Receptacle",
        "MS3452" => "Cable Plug",
        "MS3454" => "Angle Plug",
        "MS3456" => "Jam Nut Receptacle",
        _ => prefix
    };

    private static string MS5015Class(string cls) => cls switch
    {
        "A" => "A — Aluminum alloy / Olive drab cadmium",
        "B" => "B — Aluminum alloy / Electroless nickel",
        "C" => "C — Stainless steel",
        "E" => "E — Aluminum alloy / Zinc-nickel",
        _ => $"Class {cls}"
    };

    private static string M83513SlashSheet(string prefix) => prefix switch
    {
        "M83513/01" => "/01 — PCB Right Angle Receptacle",
        "M83513/02" => "/02 — PCB Vertical Receptacle",
        "M83513/03" => "/03 — Panel Mount Receptacle (solder cup)",
        "M83513/04" => "/04 — Cable Plug (solder cup)",
        _ => $"Slash sheet {prefix}"
    };

    private static string M83723SlashSheet(string prefix) => prefix switch
    {
        "M83723/71" => "/71 — Box Mount Receptacle (Series III)",
        "M83723/75" => "/75 — Straight Plug (Series III)",
        "M83723/82" => "/82 — Jam Nut Receptacle (Series III)",
        _ => $"Slash sheet {prefix}"
    };

    private static string M24308SlashSheet(string prefix) => prefix switch
    {
        "M24308/1" => "/1 — D-Sub Solder Cup, Standard Density",
        "M24308/2" => "/2 — D-Sub PCB Right Angle, Standard Density",
        "M24308/3" => "/3 — D-Sub PCB Vertical, Standard Density",
        "M24308/4" => "/4 — D-Sub Crimp, Standard Density",
        "M24308/5" => "/5 — D-Sub Solder Cup, High Density",
        "M24308/6" => "/6 — D-Sub PCB Right Angle, High Density",
        "M24308/7" => "/7 — D-Sub Solder Cup, Double Density",
        "M24308/8" => "/8 — D-Sub PCB Vertical, High Density",
        "M24308/9" => "/9 — D-Sub Crimp, High Density",
        _ => $"Slash sheet {prefix}"
    };

    private static string MS22992PrefixInfo(string prefix) => prefix switch
    {
        "MS90555" => "Box Mount Receptacle",
        "MS90556" => "Cable Receptacle",
        "MS90557" => "Straight Plug",
        "MS90558" => "Angle Plug",
        "MS17344" => "Jam Nut Receptacle",
        _ => prefix
    };

    private static string MS22992Class(string cls) => cls switch
    {
        "L" => "L — Aluminum alloy",
        "Q" => "Q — Stainless steel",
        _ => $"Class {cls}"
    };

    private static string AS95234SlashSheet(string prefix) => prefix switch
    {
        "AS95234/1" => "/1 — Receptacle (Reverse Bayonet coupling)",
        "AS95234/2" => "/2 — Straight Plug (Reverse Bayonet coupling)",
        "AS95234/3" => "/3 — Jam Nut Receptacle (Reverse Bayonet coupling)",
        _ => $"Slash sheet {prefix}"
    };
}
