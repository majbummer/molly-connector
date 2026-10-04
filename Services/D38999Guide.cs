namespace ConnectorDB.Services;

/// <summary>
/// Static, source-cited reference data for the /d38999 guide page.
/// Sources: NASA NEPP Parts Selection List (MIL-DTL-38999 Series I/II and III/IV pages),
/// Glenair D38999 catalog sheets (/20, /25) and environmental overview.
/// Insert arrangements here are the common set from the NASA NEPP list; MIL-STD-1560
/// defines the complete set. Do not add rows without a source.
/// </summary>
public static class D38999Guide
{
    public record SeriesInfo(string Series, string Coupling, string ToMate, string ScoopProof,
        string Emi, string ShellCodes, string Prefixes);

    public static readonly SeriesInfo[] Series =
    {
        new("Series I",   "3-point bayonet",                         "120° (1/3 turn)", "Yes",
            "40 dB min @ 10 GHz", "9 – 25 (odd numbers)",  "MS27466, MS27467, MS27468, MS27656 …"),
        new("Series II",  "3-point bayonet, low silhouette",          "120° (1/3 turn)", "No",
            "40 dB min @ 10 GHz", "8 – 24 (even numbers)", "MS27472, MS27473, MS27474, MS27484, MS27497, MS27508 …"),
        new("Series III", "Triple-start threaded, self-locking",      "360° (1 turn)",   "Yes",
            "65 dB min @ 10 GHz", "A – J (letters)",       "D38999/20, /21, /23, /24, /25, /26, /27"),
        new("Series IV",  "Breech lock, self-locking",                "90° (1/4 turn)",  "Yes",
            "65 dB min @ 10 GHz", "B – J (no size A)",     "D38999/40 – /48"),
    };

    public record SlashSheet(string SeriesIII, string SeriesIV, string Style);

    public static readonly SlashSheet[] SlashSheets =
    {
        new("D38999/20", "D38999/40", "Receptacle, wall mount flange"),
        new("D38999/24", "D38999/44", "Receptacle, jam nut mount"),
        new("—",         "D38999/42", "Receptacle, box mount"),
        new("—",         "D38999/47", "Plug"),
        new("D38999/26", "D38999/46", "Plug, EMI grounding fingers"),
        new("D38999/21", "D38999/41", "Receptacle, box mount, hermetic"),
        new("D38999/23", "D38999/43", "Receptacle, jam nut mount, hermetic"),
        new("D38999/25", "D38999/45", "Receptacle, solder mount, hermetic"),
        new("D38999/27", "D38999/48", "Receptacle, weld mount, hermetic"),
    };

    public record MsSheet(string SeriesI, string SeriesII, string Style);

    public static readonly MsSheet[] MsSheets =
    {
        new("MS27466", "MS27472", "Receptacle, wall mount flange"),
        new("MS27468", "MS27474", "Receptacle, jam nut mount"),
        new("MS27656", "MS27497", "Receptacle, wall mount, back panel mount"),
        new("—",       "MS27508", "Receptacle, box mount, back panel mount"),
        new("—",       "MS27473", "Plug"),
        new("MS27467", "MS27484", "Plug with RFI grounding fingers"),
        new("MS27470", "MS27477", "Receptacle, jam nut mount, hermetic"),
        new("MS27471", "MS27478", "Receptacle, solder mount, hermetic"),
    };

    public record Code(string C, string Meaning, string? Note = null);

    public static readonly Code[] ClassesEnvironmental =
    {
        new("F", "Aluminum, electroless nickel (conductive)"),
        new("G", "Aluminum, electroless nickel", "Check the spec for how G differs from F on your application"),
        new("T", "Aluminum, nickel-PTFE"),
        new("V", "Aluminum, tin-zinc over electroless nickel"),
        new("W", "Aluminum, olive drab cadmium over electroless nickel"),
        new("Z", "Aluminum, black zinc-nickel"),
        new("J", "Composite, olive drab cadmium"),
        new("M", "Composite, electroless nickel"),
        new("K", "Stainless steel, passivated"),
        new("S", "Stainless steel, electrodeposited nickel"),
    };

    public static readonly Code[] ClassesHermetic =
    {
        new("N", "Hermetic, corrosion-resistant steel, electrodeposited nickel (conductive)"),
        new("Y", "Hermetic, corrosion-resistant steel, passivated (conductive)"),
        new("H", "Hermetic, corrosion-resistant steel, passivated — space grade"),
    };

    public static readonly (string Letter, int Size, string SeriesII)[] ShellSizes =
    {
        ("A", 9, "8"), ("B", 11, "10"), ("C", 13, "12"), ("D", 15, "14"), ("E", 17, "16"),
        ("F", 19, "18"), ("G", 21, "20"), ("H", 23, "22"), ("J", 25, "24"),
    };

    public static readonly Code[] ContactsEnvironmental =
    {
        new("P", "Pin, 500 mating cycles"),
        new("S", "Socket, 500 mating cycles"),
        new("H", "Pin, 1500 mating cycles"),
        new("J", "Socket, 1500 mating cycles"),
        new("A", "Pin insert, less contacts", "Contacts ordered separately"),
        new("B", "Socket insert, less contacts", "Contacts ordered separately"),
    };

    public static readonly Code[] ContactsHermetic =
    {
        new("P", "Pin, solder cup"),
        new("S", "Socket, solder cup"),
        new("X", "Pin, eyelet", "NASA's list shows Y for eyelet pins; confirm on the drawing"),
        new("Z", "Socket, eyelet"),
        new("C", "Pin, PCB / flex feedthrough"),
        new("D", "Socket, PCB / flex feedthrough"),
    };

    public static readonly Code[] Polarization =
    {
        new("N", "Normal (standard key position)"),
        new("A", "Alternate position A"),
        new("B", "Alternate position B"),
        new("C", "Alternate position C"),
        new("D", "Alternate position D"),
        new("E", "Alternate position E", "Not listed for every shell size — check the drawing"),
    };

    /// <summary>One insert arrangement. Null codes = not offered in that series.</summary>
    public record Insert(string Group, string? SeriesIII, bool SeriesIV, string? SeriesI, string? SeriesII,
        int C22D, int C20, int C16, int C12)
    {
        public int Total => C22D + C20 + C16 + C12;
    }

    public static readonly Insert[] Inserts =
    {
        new("A · Shell 9",  "A35", false, "9-35",  "8-35",  6, 0, 0, 0),
        new("A · Shell 9",  "A98", false, "9-98",  "8-98",  0, 3, 0, 0),
        new("B · Shell 11", "B4",  false, "11-4",  null,    0, 4, 0, 0),
        new("B · Shell 11", "B5",  true,  "11-5",  "10-5",  0, 5, 0, 0),
        new("B · Shell 11", "B35", true,  "11-35", "10-35", 13, 0, 0, 0),
        new("B · Shell 11", "B98", false, "11-98", "10-98", 0, 6, 0, 0),
        new("B · Shell 11", "B99", true,  "11-99", "10-99", 0, 7, 0, 0),
        new("C · Shell 13", "C4",  true,  "13-4",  "12-4",  0, 0, 4, 0),
        new("C · Shell 13", "C8",  false, "13-8",  "12-8",  0, 8, 0, 0),
        new("C · Shell 13", "C35", true,  "13-35", "12-35", 22, 0, 0, 0),
        new("C · Shell 13", "C98", true,  "13-98", "12-98", 0, 10, 0, 0),
        new("D · Shell 15", "D5",  true,  "15-5",  "14-5",  0, 0, 5, 0),
        new("D · Shell 15", "D15", false, "15-15", "14-15", 0, 14, 1, 0),
        new("D · Shell 15", "D18", true,  "15-18", "14-18", 0, 18, 0, 0),
        new("D · Shell 15", "D19", true,  "15-19", null,    0, 19, 0, 0),
        new("D · Shell 15", "D35", true,  "15-35", "14-35", 37, 0, 0, 0),
        new("D · Shell 15", "D97", true,  "15-97", "14-97", 0, 8, 4, 0),
        new("E · Shell 17", "E6",  true,  "17-6",  "16-6",  0, 0, 0, 6),
        new("E · Shell 17", "E8",  true,  "17-8",  "16-8",  0, 0, 8, 0),
        new("E · Shell 17", "E26", true,  "17-26", "16-26", 0, 26, 0, 0),
        new("E · Shell 17", "E35", true,  "17-35", "16-35", 55, 0, 0, 0),
        new("E · Shell 17", "E99", true,  "17-99", "16-99", 0, 21, 2, 0),
        new("F · Shell 19", "F11", true,  "19-11", "18-11", 0, 0, 11, 0),
        new("F · Shell 19", "F32", true,  "19-32", "18-32", 0, 32, 0, 0),
        new("F · Shell 19", "F35", true,  "19-35", "18-35", 66, 0, 0, 0),
        new("G · Shell 21", "G11", true,  "21-11", null,    0, 0, 0, 11),
        new("G · Shell 21", "G16", true,  "21-16", "20-16", 0, 0, 16, 0),
        new("G · Shell 21", "G35", true,  "21-35", "20-35", 79, 0, 0, 0),
        new("G · Shell 21", "G39", false, "21-39", "20-39", 0, 37, 2, 0),
        new("G · Shell 21", "G41", true,  "21-41", "20-41", 0, 41, 0, 0),
        new("H · Shell 23", "H21", true,  "23-21", "22-21", 0, 0, 21, 0),
        new("H · Shell 23", "H35", true,  "23-35", "22-35", 100, 0, 0, 0),
        new("H · Shell 23", "H53", false, "23-53", null,    0, 53, 0, 0),
        new("H · Shell 23", "H55", true,  "23-55", "22-55", 0, 55, 0, 0),
        new("J · Shell 25", "J4",  true,  "25-4",  "24-4",  0, 48, 8, 0),
        new("J · Shell 25", "J19", true,  "25-19", "24-19", 0, 0, 0, 19),
        new("J · Shell 25", "J24", true,  "25-24", "24-24", 0, 0, 12, 12),
        new("J · Shell 25", "J29", true,  "25-29", "24-29", 0, 0, 29, 0),
        new("J · Shell 25", "J35", true,  "25-35", "24-35", 128, 0, 0, 0),
        new("J · Shell 25", "J43", false, "25-43", null,    0, 23, 20, 0),
        new("J · Shell 25", "J61", true,  "25-61", "24-61", 0, 61, 0, 0),
        new("Series II only", null, false, null, "12-3",  0, 0, 3, 0),
        new("Series II only", null, false, null, "18-28", 0, 26, 2, 0),
        new("Series II only", null, false, null, "18-30", 0, 29, 1, 0),
        new("Series II only", null, false, null, "18-96", 0, 0, 0, 9),
        new("Series II only", null, false, null, "22-32", 0, 32, 0, 0),
    };

    public record Source(string Title, string Url);

    public static readonly Source[] Sources =
    {
        new("NASA NEPP Parts Selection List — MIL-DTL-38999 Series III & IV",
            "https://nepp.nasa.gov/npsl/connectors/m38999/38999_s3.htm"),
        new("NASA NEPP Parts Selection List — MIL-DTL-38999 Series I & II",
            "https://nepp.nasa.gov/npsl/Connectors/m38999/38999_s1.htm"),
        new("Glenair — D38999/20 Series III environmental (how-to-order, Table I finishes)",
            "https://www.glenair.com/mil-dtl-38999-series-iii-and-iv/pdf/mil-dtl-38999-series-iii-environmental/d38999-20.pdf"),
        new("Glenair — D38999/25 Series III hermetic",
            "https://ww.glenair.com/mil-dtl-38999-connector-series-iii/pdf/mil-dtl-38999-series-iii-hermetic/d38999-25.pdf"),
        new("Glenair — MIL-DTL-38999 environmental overview (series comparison)",
            "https://www.glenair.com/mil-dtl-38999/pdf/overview-environmental.pdf"),
        new("ASSIST (DLA) — MIL-DTL-38999 and MIL-STD-1560, the governing documents",
            "https://quicksearch.dla.mil/"),
    };
}
