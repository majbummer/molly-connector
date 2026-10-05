using System.Linq;
namespace ConnectorDB.Services;

/// <summary>
/// Static, source-cited reference data for the /d38999 guide page.
/// Sources: NASA NEPP Parts Selection List (MIL-DTL-38999 Series I/II and III/IV pages),
/// Glenair D38999 catalog sheets (/20, /25) and environmental overview.
/// Insert arrangements come from MIL-STD-1560C. Do not add rows without a source.
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

    // MIL-DTL-38999M w/Amendment 2, Table II and 6.1.1.d
    public static readonly Code[] ClassesEnvironmental =
    {
        new("C", "Aluminum, anodic — nonconductive (-65 to +200 °C)"),
        new("F", "Aluminum, electroless nickel — conductive (-65 to +200 °C)", "Not for Navy use; inactive for new design for Air Force"),
        new("G", "Aluminum, electroless nickel — same as F, space grade (-65 to +200 °C)", "Not for Navy or Air Force use"),
        new("R", "Aluminum, electroless nickel — same as F, higher corrosion requirement (-65 to +200 °C)"),
        new("T", "Aluminum, nickel fluorocarbon polymer — conductive (-65 to +175 °C)"),
        new("W", "Aluminum, olive drab cadmium — conductive (-65 to +175 °C)"),
        new("Z", "Aluminum, zinc-nickel — conductive (-65 to +175 °C)"),
        new("J", "Composite, olive drab cadmium — conductive (-65 to +175 °C)"),
        new("M", "Composite, nickel — conductive (-65 to +200 °C)"),
        new("K", "Corrosion-resistant steel, passivated — firewall (-65 to +200 °C)"),
        new("S", "Corrosion-resistant steel, electrodeposited nickel — firewall, more conductive than K (-65 to +200 °C)"),
        new("L", "Corrosion-resistant steel, electrodeposited nickel — conductive (-65 to +200 °C)"),
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
        new("R", "Pin, rhodium plated"),
        new("M", "Socket, rhodium plated"),
        new("G", "Pin, heavy gold plated"),
        new("U", "Socket, heavy gold plated"),
        new("A", "Pin insert, less contacts", "Contacts ordered separately"),
        new("B", "Socket insert, less contacts", "Contacts ordered separately"),
    };

    public static readonly Code[] ContactsHermetic =
    {
        new("P", "Pin, solder cup"),
        new("S", "Socket, solder cup"),
        new("X", "Pin, eyelet"),
        new("Z", "Socket, eyelet"),
        new("C", "Pin, PCB / flex feedthrough"),
        new("D", "Socket, PCB / flex feedthrough"),
    };

    // MIL-DTL-38999M figure 6 (series III) and figure 7 (series IV). Positions apply to all shell sizes.
    public static readonly Code[] Polarization =
    {
        new("N", "Normal", "Series III and IV: the N is always written in the part number"),
        new("A", "Alternate A", "Series III and IV"),
        new("B", "Alternate B", "Series III and IV"),
        new("C", "Alternate C", "Series III and IV"),
        new("D", "Alternate D", "Series III and IV"),
        new("E", "Alternate E", "Series III only"),
        new("K", "Alternate K", "Series IV only"),
        new("L", "Alternate L", "Series IV only"),
        new("M", "Alternate M", "Series IV only"),
        new("R", "Alternate R", "Series IV only"),
    };

    /// <summary>One insert arrangement (MIL-STD-1560C). Null codes = not offered in that series.</summary>
    public record Insert(string Group, string? SeriesIII, bool SeriesIV, string? SeriesI, string? SeriesII,
        int C22D, int C20, int C16, int C12, string Other = "", bool Inactive = false)
    {
        public int Total => C22D + C20 + C16 + C12 + OtherCount;
        public int OtherCount => string.IsNullOrEmpty(Other) ? 0 :
            Other.Split(',').Sum(p => int.TryParse(p.Trim().Split(' ')[0], out var n) ? n : 0);
    }

    // Generated from scripts/mil-std-1560c-inserts.json (MIL-STD-1560C, 27599-only layouts excluded).
    // Series II codes are listed beside the Series I/III/IV arrangement when the contact layout is identical.
    public static readonly Insert[] Inserts =
    {
        new("A · Shell 9", "A6", false, "9-6", "8-6", 0, 0, 0, 0, "6 \u00d7 #22M", true),
        new("A · Shell 9", "A7", false, "9-7", null, 7, 0, 0, 0, "", false),
        new("A · Shell 9", "A23", false, "9-23", null, 0, 0, 0, 0, "9 \u00d7 #23", false),
        new("A · Shell 9", "A35", false, "9-35", "8-35", 6, 0, 0, 0, "", false),
        new("A · Shell 9", "A44", false, "9-44", null, 0, 0, 0, 0, "4 \u00d7 #22", true),
        new("A · Shell 9", "A98", false, "9-98", "8-98", 0, 3, 0, 0, "", false),
        new("B · Shell 11", "B2", true, "11-2", null, 0, 0, 2, 0, "", false),
        new("B · Shell 11", "B4", true, "11-4", null, 0, 4, 0, 0, "", false),
        new("B · Shell 11", "B5", true, "11-5", "10-5", 0, 5, 0, 0, "", false),
        new("B · Shell 11", "B13", true, "11-13", "10-13", 0, 0, 0, 0, "13 \u00d7 #22M", true),
        new("B · Shell 11", "B23", true, "11-23", null, 0, 0, 0, 0, "19 \u00d7 #23", false),
        new("B · Shell 11", "B35", true, "11-35", "10-35", 13, 0, 0, 0, "", false),
        new("B · Shell 11", "B98", true, "11-98", "10-98", 0, 6, 0, 0, "", false),
        new("B · Shell 11", "B99", true, "11-99", "10-99", 0, 7, 0, 0, "", false),
        new("C · Shell 13", "C4", true, "13-4", "12-4", 0, 0, 4, 0, "", false),
        new("C · Shell 13", "C8", true, "13-8", "12-8", 0, 8, 0, 0, "", false),
        new("C · Shell 13", "C22", true, "13-22", "12-22", 0, 0, 0, 0, "22 \u00d7 #22M", false),
        new("C · Shell 13", "C23", true, "13-23", null, 0, 0, 0, 0, "32 \u00d7 #23", false),
        new("C · Shell 13", "C35", true, "13-35", "12-35", 22, 0, 0, 0, "", false),
        new("C · Shell 13", "C98", true, "13-98", "12-98", 0, 10, 0, 0, "", false),
        new("D · Shell 15", "D5", true, "15-5", "14-5", 0, 0, 5, 0, "", false),
        new("D · Shell 15", "D15", true, "15-15", "14-15", 0, 14, 1, 0, "", false),
        new("D · Shell 15", "D18", true, "15-18", "14-18", 0, 18, 0, 0, "", false),
        new("D · Shell 15", "D19", true, "15-19", null, 0, 19, 0, 0, "", false),
        new("D · Shell 15", "D21", true, "15-21", null, 17, 3, 0, 1, "", false),
        new("D · Shell 15", "D23", true, "15-23", null, 0, 0, 0, 0, "55 \u00d7 #23", false),
        new("D · Shell 15", "D35", true, "15-35", "14-35", 37, 0, 0, 0, "", false),
        new("D · Shell 15", "D37", true, "15-37", "14-37", 0, 0, 0, 0, "37 \u00d7 #22M", true),
        new("D · Shell 15", "D97", true, "15-97", "14-97", 0, 8, 4, 0, "", false),
        new("E · Shell 17", "E2", true, "17-2", null, 38, 0, 0, 0, "1 \u00d7 #8 twinax", true),
        new("E · Shell 17", "E3", true, "17-3", null, 38, 0, 0, 0, "1 \u00d7 #8 twinax", false),
        new("E · Shell 17", "E6", true, "17-6", "16-6", 0, 0, 0, 6, "", false),
        new("E · Shell 17", "E8", true, "17-8", "16-8", 0, 0, 8, 0, "", false),
        new("E · Shell 17", "E11", true, "17-11", null, 0, 8, 0, 0, "1 \u00d7 #12 coax, 2 \u00d7 #12 twinax", false),
        new("E · Shell 17", "E23", true, "17-23", null, 0, 0, 0, 0, "73 \u00d7 #23", false),
        new("E · Shell 17", "E26", true, "17-26", "16-26", 0, 26, 0, 0, "", false),
        new("E · Shell 17", "E35", true, "17-35", "16-35", 55, 0, 0, 0, "", false),
        new("E · Shell 17", "E55", true, "17-55", "16-55", 0, 0, 0, 0, "55 \u00d7 #22M", false),
        new("E · Shell 17", "E99", true, "17-99", "16-99", 0, 21, 2, 0, "", false),
        new("F · Shell 19", "F11", true, "19-11", "18-11", 0, 0, 11, 0, "", false),
        new("F · Shell 19", "F18", true, "19-18", null, 14, 0, 0, 0, "4 \u00d7 #8 twinax", true),
        new("F · Shell 19", "F19", true, "19-19", null, 14, 0, 0, 0, "4 \u00d7 #8 twinax", false),
        new("F · Shell 19", "F23", true, "19-23", null, 0, 0, 0, 0, "88 \u00d7 #23", false),
        new("F · Shell 19", "F28", true, "19-28", "18-28", 0, 26, 2, 0, "", false),
        new("F · Shell 19", "F30", true, "19-30", "18-30", 0, 29, 1, 0, "", false),
        new("F · Shell 19", "F32", true, "19-32", "18-32", 0, 32, 0, 0, "", false),
        new("F · Shell 19", "F35", true, "19-35", "18-35", 66, 0, 0, 0, "", false),
        new("F · Shell 19", "F45", true, "19-45", "18-45", 67, 0, 0, 0, "", false),
        new("F · Shell 19", "F66", true, "19-66", "18-66", 0, 0, 0, 0, "66 \u00d7 #22M", true),
        new("F · Shell 19", "F67", true, "19-67", "18-67", 0, 0, 0, 0, "67 \u00d7 #22M", true),
        new("G · Shell 21", "G1", true, "21-1", "20-1", 0, 0, 0, 0, "79 \u00d7 #22M", true),
        new("G · Shell 21", "G11", true, "21-11", null, 0, 0, 0, 11, "", false),
        new("G · Shell 21", "G16", true, "21-16", "20-16", 0, 0, 16, 0, "", false),
        new("G · Shell 21", "G23", true, "21-23", null, 0, 0, 0, 0, "121 \u00d7 #23", false),
        new("G · Shell 21", "G24", true, "21-24", "20-24", 0, 24, 0, 0, "", false),
        new("G · Shell 21", "G25", true, "21-25", "20-25", 0, 25, 0, 0, "", false),
        new("G · Shell 21", "G27", true, "21-27", "20-27", 0, 27, 0, 0, "", false),
        new("G · Shell 21", "G29", true, "21-29", null, 0, 19, 4, 4, "", false),
        new("G · Shell 21", "G35", true, "21-35", "20-35", 79, 0, 0, 0, "", false),
        new("G · Shell 21", "G39", true, "21-39", "20-39", 0, 37, 2, 0, "", false),
        new("G · Shell 21", "G41", true, "21-41", "20-41", 0, 41, 0, 0, "", false),
        new("G · Shell 21", "G75", true, "21-75", null, 0, 0, 0, 0, "4 \u00d7 #8 twinax", true),
        new("G · Shell 21", "G76", true, "21-76", null, 0, 0, 0, 0, "4 \u00d7 #8 twinax", false),
        new("H · Shell 23", "H1", true, "23-1", "22-1", 0, 0, 0, 0, "100 \u00d7 #22M", true),
        new("H · Shell 23", "H2", true, "23-2", "22-2", 0, 0, 0, 0, "85 \u00d7 #22", true),
        new("H · Shell 23", "H21", true, "23-21", "22-21", 0, 0, 21, 0, "", false),
        new("H · Shell 23", "H23", true, "23-23", null, 0, 0, 0, 0, "151 \u00d7 #23", false),
        new("H · Shell 23", "H32", true, "23-32", "22-32", 0, 32, 0, 0, "", false),
        new("H · Shell 23", "H34", true, "23-34", "22-34", 0, 34, 0, 0, "", false),
        new("H · Shell 23", "H35", true, "23-35", "22-35", 100, 0, 0, 0, "", false),
        new("H · Shell 23", "H36", true, "23-36", "22-36", 0, 36, 0, 0, "", false),
        new("H · Shell 23", "H53", true, "23-53", "22-53", 0, 53, 0, 0, "", false),
        new("H · Shell 23", "H55", true, "23-55", "22-55", 0, 55, 0, 0, "", false),
        new("H · Shell 23", "H97", true, "23-97", "22-97", 0, 0, 16, 0, "", false),
        new("H · Shell 23", "H99", true, "23-99", "22-99", 0, 0, 11, 0, "", false),
        new("J · Shell 25", "J1", true, "25-1", "24-1", 0, 0, 0, 0, "128 \u00d7 #22M", true),
        new("J · Shell 25", "J2", true, "25-2", "24-2", 0, 0, 0, 0, "100 \u00d7 #22", true),
        new("J · Shell 25", "J4", true, "25-4", "24-4", 0, 48, 8, 0, "", false),
        new("J · Shell 25", "J7", true, "25-7", null, 97, 0, 0, 0, "2 \u00d7 #8 twinax", true),
        new("J · Shell 25", "J8", true, "25-8", null, 0, 0, 0, 0, "8 \u00d7 #8 twinax", true),
        new("J · Shell 25", "J9", true, "25-9", null, 97, 0, 0, 0, "2 \u00d7 #8 twinax", false),
        new("J · Shell 25", "J10", true, "25-10", null, 0, 0, 0, 0, "8 \u00d7 #8 twinax", false),
        new("J · Shell 25", "J11", true, "25-11", null, 0, 2, 0, 0, "9 \u00d7 #10", false),
        new("J · Shell 25", "J19", true, "25-19", "24-19", 0, 0, 0, 19, "", false),
        new("J · Shell 25", "J20", true, "25-20", null, 0, 10, 13, 0, "3 \u00d7 #8 twinax, 4 \u00d7 #12 coax", false),
        new("J · Shell 25", "J21", true, "25-21", null, 0, 10, 13, 0, "3 \u00d7 #8 twinax, 4 \u00d7 #12 coax", false),
        new("J · Shell 25", "J23", true, "25-23", null, 0, 0, 0, 0, "187 \u00d7 #23", false),
        new("J · Shell 25", "J24", true, "25-24", "24-24", 0, 0, 12, 12, "", false),
        new("J · Shell 25", "J29", true, "25-29", "24-29", 0, 0, 29, 0, "", false),
        new("J · Shell 25", "J35", true, "25-35", "24-35", 128, 0, 0, 0, "", false),
        new("J · Shell 25", "J37", true, "25-37", null, 0, 0, 37, 0, "", false),
        new("J · Shell 25", "J43", true, "25-43", null, 0, 23, 20, 0, "", false),
        new("J · Shell 25", "J46", true, "25-46", null, 0, 40, 4, 0, "", true),
        new("J · Shell 25", "J47", true, "25-47", null, 0, 40, 4, 0, "", false),
        new("J · Shell 25", "J61", true, "25-61", "24-61", 0, 61, 0, 0, "", false),
        new("J · Shell 25", "J90", true, "25-90", null, 0, 40, 4, 0, "2 \u00d7 #8 twinax", true),
        new("J · Shell 25", "J91", true, "25-91", null, 0, 40, 4, 0, "2 \u00d7 #8 twinax", false),
        new("Series II only", null, false, null, "12-3", 0, 0, 3, 0, "", false),
        new("Series II only", null, false, null, "18-53", 0, 0, 0, 0, "53 \u00d7 #22", true),
        new("Series II only", null, false, null, "18-96", 0, 0, 0, 9, "", false),
        new("Series II only", null, false, null, "20-2", 0, 0, 0, 0, "65 \u00d7 #22", true),
    };

    public record Source(string Title, string Url);

    public static readonly Source[] Sources =
    {
        new("MIL-DTL-38999M w/Amendment 2 — classes (Table II), contact styles (1.4.2), polarization (figures 6 and 7); available on ASSIST",
            "https://quicksearch.dla.mil/"),
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
        new("MIL-STD-1560C — insert arrangements for MIL-DTL-38999 (insert table source); available on ASSIST",
            "https://quicksearch.dla.mil/"),
    };
}
