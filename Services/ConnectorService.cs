using ConnectorDB.Models;
using Dapper;
using Microsoft.Data.Sqlite;

namespace ConnectorDB.Services;

public class ConnectorService
{
    private readonly string _connectionString;
    private readonly string _correctionsConnectionString;

    public ConnectorService(IConfiguration config)
    {
        var path = config["DatabasePath"]
            ?? throw new InvalidOperationException("DatabasePath not configured.");
        _connectionString = $"Data Source={path};Mode=ReadOnly;Cache=Shared";

        var corrPath = config["CorrectionsPath"]
            ?? Path.Combine(Path.GetDirectoryName(path)!, "corrections.db");
        Directory.CreateDirectory(Path.GetDirectoryName(corrPath)!);
        _correctionsConnectionString = $"Data Source={corrPath};Mode=ReadWriteCreate";
        try
        {
            using var cdb = new SqliteConnection(_correctionsConnectionString);
            cdb.Execute("""
                CREATE TABLE IF NOT EXISTS corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    connector_part_number TEXT, field_name TEXT,
                    old_value TEXT, corrected_value TEXT, correction_notes TEXT,
                    submitted_at TEXT DEFAULT (datetime('now')), status TEXT DEFAULT 'pending')
                """);
        }
        catch (Exception ex) { Console.WriteLine($"Corrections DB unavailable: {ex.Message}"); }
    }

    private SqliteConnection Open() => new(_connectionString);
    private SqliteConnection OpenCorrections() => new(_correctionsConnectionString);

    // ── Summary ────────────────────────────────────────────────────────────
    public Summary GetSummary()
    {
        using var db = Open();
        var total  = db.ExecuteScalar<int>(
            "SELECT COUNT(*) FROM connectors WHERE spec NOT LIKE '%Cross Reference%'");
        var crossref = db.ExecuteScalar<int>(
            "SELECT COUNT(*) FROM connectors WHERE spec LIKE '%Cross Reference%'");
        var specs  = db.ExecuteScalar<int>(
            "SELECT COUNT(DISTINCT spec) FROM connectors WHERE spec NOT LIKE '%Cross Reference%'");
        return new Summary { TotalConnectors = total, CrossReferences = crossref, Specs = specs };
    }

    // ── Specs for filter dropdowns ─────────────────────────────────────────
    public IEnumerable<SpecGroup> GetSpecs()
    {
        using var db = Open();
        return db.Query<SpecGroup>(
            "SELECT spec AS Spec, series AS Series, COUNT(*) AS Count " +
            "FROM connectors GROUP BY spec, series ORDER BY spec, series");
    }

    // ── Search ─────────────────────────────────────────────────────────────
    public IEnumerable<Connector> Search(
        string? q, string? spec, string? series, string? type, int limit)
    {
        using var db = Open();
        var where = new List<string>();
        var parms = new DynamicParameters();

        if (!string.IsNullOrWhiteSpace(q))
        {
            var uq = q.Trim().ToUpperInvariant();
            where.Add("(UPPER(part_number) LIKE @q OR UPPER(insert_arrangement) = @exact OR UPPER(prefix) LIKE @q)");
            parms.Add("q", $"%{uq}%");
            parms.Add("exact", uq);
        }
        if (!string.IsNullOrWhiteSpace(spec))   { where.Add("spec = @spec");             parms.Add("spec", spec); }
        if (!string.IsNullOrWhiteSpace(series))  { where.Add("series = @series");         parms.Add("series", series); }
        if (!string.IsNullOrWhiteSpace(type))    { where.Add("connector_type = @type");   parms.Add("type", type); }

        var sql = $@"
            SELECT part_number AS PartNumber, spec AS Spec, series AS Series,
                   prefix AS Prefix, connector_type AS ConnectorType,
                   shell_style AS ShellStyle, insert_arrangement AS InsertArrangement,
                   contact_count AS ContactCount, contact_size AS ContactSize,
                   contact_type AS ContactType
            FROM connectors
            {(where.Count > 0 ? "WHERE " + string.Join(" AND ", where) : "")}
            LIMIT {limit}";

        return db.Query<Connector>(sql, parms);
    }

    // ── Single connector detail ────────────────────────────────────────────
    public Connector? GetConnector(string partNumber)
    {
        using var db = Open();

        var row = db.QueryFirstOrDefault<Connector>(@"
            SELECT part_number AS PartNumber, spec AS Spec, series AS Series,
                   prefix AS Prefix, connector_type AS ConnectorType,
                   shell_style AS ShellStyle, mounting_type AS MountingType,
                   insert_arrangement AS InsertArrangement,
                   contact_size AS ContactSize, contact_type AS ContactType,
                   contact_count AS ContactCount, shell_size_letter AS ShellSizeLetter,
                   shell_size_numeric AS ShellSizeNumeric, keying AS Keying,
                   class AS Class, shell_material AS ShellMaterial,
                   shell_plating AS ShellPlating, termination_type AS TerminationType,
                   environment_type AS EnvironmentType, shielding AS Shielding,
                   mating_connectors AS MatingConnectors,
                   compatible_contact_sizes AS CompatibleContactSizes,
                   notes AS Notes
            FROM connectors WHERE part_number = @pn", new { pn = partNumber });

        if (row is null) return null;

        // Mating connectors — split on ; or ,
        if (!string.IsNullOrWhiteSpace(row.MatingConnectors))
        {
            var matePNs = row.MatingConnectors
                .Split(new[] { ',', ';' }, StringSplitOptions.RemoveEmptyEntries)
                .Select(s => s.Trim()).Where(s => s.Length > 0);

            foreach (var mpn in matePNs)
            {
                var mate = db.QueryFirstOrDefault<Connector>(@"
                    SELECT part_number AS PartNumber, spec AS Spec,
                           connector_type AS ConnectorType, shell_style AS ShellStyle,
                           contact_count AS ContactCount
                    FROM connectors WHERE part_number = @mpn", new { mpn });

                row.MatingConnectorDetails.Add(
                    mate ?? new Connector { PartNumber = mpn, Notes = "not_found" });
            }
        }

        // Fixtures
        row.Fixtures = db.Query<InventoryItem>(@"
            SELECT assembly_connector AS AssemblyConnector, fixture_id AS FixtureId,
                   mating_connector AS MatingConnector, box_number AS BoxNumber,
                   box_section AS BoxSection, slot_position AS SlotPosition,
                   fixture_status AS FixtureStatus, last_verified_date AS LastVerifiedDate
            FROM fixtures WHERE assembly_connector = @pn OR mating_connector = @pn",
            new { pn = partNumber }).ToList();

        // Contact tooling
        if (!string.IsNullOrWhiteSpace(row.ContactSize) && !string.IsNullOrWhiteSpace(row.ContactType))
        {
            var key = $"{row.ContactSize}|{row.ContactType}";
            row.ContactTooling = db.QueryFirstOrDefault<ContactTooling>(@"
                SELECT mapping_key AS MappingKey, contact_part_number AS ContactPartNumber,
                       contact_size AS ContactSize, contact_type AS ContactType,
                       wire_gauge_range AS WireGaugeRange,
                       strip_length_min AS StripLengthMin, strip_length_max AS StripLengthMax,
                       default_strip_length AS DefaultStripLength,
                       crimper_tool AS CrimperTool, positioner AS Positioner,
                       locator AS Locator, inserter_tool AS InserterTool,
                       extractor_tool AS ExtractorTool, tool_family AS ToolFamily,
                       notes AS Notes
                FROM contacts_tools WHERE mapping_key = @key", new { key });
        }

        return row;
    }

    // ── Reference data ───────────────────────────────────────────────────────────
    public IEnumerable<dynamic> GetMilSpecs()
    {
        using var db = Open();
        return db.Query(@"SELECT spec AS spec, common_name AS commonName,
            supersedes AS supersedes, superseded_by AS supersededBy,
            description AS description, connector_types AS connectorTypes,
            contact_sizes AS contactSizes, shell_styles AS shellStyles,
            environment AS environment, typical_use AS typicalUse, notes AS notes
            FROM milspec_reference ORDER BY spec");
    }

    public IEnumerable<dynamic> GetCrimpingTools()
    {
        using var db = Open();
        return db.Query(@"SELECT part_number AS partNumber, slash_sheet AS slashSheet,
            tool_family AS toolFamily, description AS description,
            manufacturer AS manufacturer, contact_sizes AS contactSizes,
            compatible_contacts AS compatibleContacts,
            positioner_series AS positionerSeries,
            calibration_interval AS calibrationInterval, notes AS notes
            FROM crimping_tools ORDER BY tool_family, part_number");
    }

    public IEnumerable<dynamic> GetPositioners()
    {
        using var db = Open();
        return db.Query(@"SELECT part_number AS partNumber, tool_family AS toolFamily,
            for_crimper AS forCrimper, contact_size AS contactSize,
            contact_type AS contactType, contact_pn AS contactPn,
            locator AS locator, notes AS notes
            FROM positioners ORDER BY contact_size, contact_type, part_number");
    }

    public IEnumerable<dynamic> GetInsertionTools()
    {
        using var db = Open();
        return db.Query(@"SELECT part_number AS partNumber, tool_type AS toolType,
            contact_size AS contactSize, connector_specs AS connectorSpecs,
            description AS description, notes AS notes
            FROM insertion_tools ORDER BY tool_type, contact_size, part_number");
    }

    public IEnumerable<dynamic> GetWireReference()
    {
        using var db = Open();
        return db.Query(@"SELECT spec AS spec, spec_dash AS specDash, awg AS awg,
            conductor_strands AS conductorStrands,
            conductor_od_mm AS conductorOdMm, insulation_od_mm AS insulationOdMm,
            max_voltage AS maxVoltage, temp_rating AS tempRating,
            current_rating_a AS currentRatingA,
            resistance_ohm_per_ft AS resistanceOhmPerFt,
            weight_lb_per_ft AS weightLbPerFt,
            insulation_material AS insulationMaterial,
            color_available AS colorAvailable, notes AS notes
            FROM wire_reference ORDER BY spec, spec_dash, awg");
    }

    public IEnumerable<dynamic> GetTorqueSpecs()
    {
        using var db = Open();
        return db.Query(@"SELECT spec AS spec, shell_size AS shellSize,
            shell_class AS shellClass, coupling_type AS couplingType,
            torque_min_inlb AS torqueMinInlb, torque_max_inlb AS torqueMaxInlb,
            torque_min_nm AS torqueMinNm, torque_max_nm AS torqueMaxNm,
            notes AS notes
            FROM torque_specs ORDER BY spec, CAST(shell_size AS INTEGER)");
    }

    // ── Extended reference data ───────────────────────────────────────────────────
    public IEnumerable<dynamic> GetGlossary()
    {
        using var db = Open();
        return db.Query("SELECT term AS term, category AS category, definition AS definition, related_terms AS relatedTerms, notes AS notes FROM glossary ORDER BY term");
    }

    public IEnumerable<dynamic> GetWireContactChart()
    {
        using var db = Open();
        return db.Query("SELECT contact_size AS contactSize, awg_range AS awgRange, crimper AS crimper, positioner AS positioner, locator AS locator, contact_pin AS contactPin, contact_socket AS contactSocket, notes AS notes FROM wire_contact_chart ORDER BY awg_min");
    }

    public IEnumerable<dynamic> GetFinishCodes()
    {
        using var db = Open();
        return db.Query("SELECT spec AS spec, code AS code, material AS material, finish AS finish, temp_rating AS tempRating, environment AS environment, notes AS notes FROM finish_codes ORDER BY spec, code");
    }

    public IEnumerable<dynamic> GetBackshells()
    {
        using var db = Open();
        return db.Query("SELECT part_number AS partNumber, slash_sheet AS slashSheet, style AS style, angle AS angle, connector_spec AS connectorSpec, shell_size AS shellSize, material AS material, plating AS plating, shielding AS shielding, notes AS notes FROM backshells ORDER BY slash_sheet");
    }

    public IEnumerable<dynamic> GetWireColors()
    {
        using var db = Open();
        return db.Query("SELECT color AS color, color_code AS colorCode, mil_std AS milStd, hex_display AS hexDisplay, typical_use AS typicalUse, notes AS notes FROM wire_colors ORDER BY color_code");
    }

    public IEnumerable<dynamic> GetHeatShrink()
    {
        using var db = Open();
        return db.Query("SELECT awg_min AS awgMin, awg_max AS awgMax, wire_od_min AS wireOdMin, wire_od_max AS wireOdMax, shrink_size AS shrinkSize, recovered_id AS recoveredId, supplied_id AS suppliedId, shrink_ratio AS shrinkRatio, notes AS notes FROM heat_shrink ORDER BY awg_max DESC");
    }

    public IEnumerable<dynamic> GetCrimpInspection()
    {
        using var db = Open();
        return db.Query("SELECT category AS category, criterion AS criterion, accept AS accept, reject AS reject, reference AS reference, notes AS notes FROM crimp_inspection ORDER BY category, criterion");
    }

    public IEnumerable<dynamic> GetSolderStandards()
    {
        using var db = Open();
        return db.Query("SELECT category AS category, standard AS standard, class AS class, requirement AS requirement, accept AS accept, reject AS reject, notes AS notes FROM solder_standards ORDER BY category, standard");
    }

    public IEnumerable<dynamic> GetEsdReference()
    {
        using var db = Open();
        return db.Query("SELECT category AS category, item AS item, requirement AS requirement, class AS class, notes AS notes FROM esd_reference ORDER BY category, item");
    }

    public IEnumerable<dynamic> GetHarnessStandards()
    {
        using var db = Open();
        return db.Query("SELECT category AS category, topic AS topic, requirement AS requirement, reference AS reference, notes AS notes FROM harness_standards ORDER BY category, topic");
    }

    // ── Sitemap helpers ───────────────────────────────────────────────────────────
    public int GetConnectorCount()
    {
        using var db = Open();
        return db.ExecuteScalar<int>(
            "SELECT COUNT(*) FROM connectors WHERE spec NOT LIKE '%Cross Reference%'");
    }

    public IEnumerable<string> GetPartNumbersForSitemap(int offset, int limit)
    {
        using var db = Open();
        return db.Query<string>(
            "SELECT part_number FROM connectors WHERE spec NOT LIKE '%Cross Reference%' ORDER BY part_number LIMIT @limit OFFSET @offset",
            new { limit, offset });
    }

    // ── Server-rendered connector page ───────────────────────────────────────────
    public dynamic? GetConnectorDetail(string partNumber)
    {
        using var db = Open();
        var connector = db.QueryFirstOrDefault(@"
            SELECT part_number AS partNumber, spec AS spec, series AS series,
                   prefix AS prefix, connector_type AS connectorType,
                   shell_style AS shellStyle, mounting_type AS mountingType,
                   insert_arrangement AS insertArrangement,
                   contact_size AS contactSize, contact_type AS contactType,
                   contact_count AS contactCount,
                   shell_size_letter AS shellSizeLetter,
                   shell_size_numeric AS shellSizeNumeric,
                   keying AS keying, class AS class,
                   shell_material AS shellMaterial, shell_plating AS shellPlating,
                   termination_type AS terminationType,
                   environment_type AS environmentType,
                   shielding AS shielding,
                   mating_connectors AS matingConnectors,
                   compatible_contact_sizes AS compatibleContactSizes,
                   notes AS notes
            FROM connectors
            WHERE UPPER(part_number) = UPPER(@pn)",
            new { pn = partNumber });

        if (connector is null) return null;

        // Get mating connectors
        var matingPNs = ((string?)connector.matingConnectors ?? "")
            .Split(new[] { ';', ',' }, StringSplitOptions.RemoveEmptyEntries)
            .Select(s => s.Trim())
            .Where(s => !string.IsNullOrEmpty(s))
            .Take(10)
            .ToList();

        List<dynamic> mates;
        if (matingPNs.Count > 0)
        {
            var inClause = string.Join(",", matingPNs.Select((_, i) => $"@p{i}"));
            var parms = new System.Dynamic.ExpandoObject() as IDictionary<string, object>;
            for (int i = 0; i < matingPNs.Count; i++)
                parms[$"p{i}"] = matingPNs[i].ToUpper();
            mates = db.Query<dynamic>($@"SELECT part_number AS partNumber, spec AS spec,
                         connector_type AS connectorType, shell_style AS shellStyle
                         FROM connectors
                         WHERE UPPER(part_number) IN ({inClause})
                         LIMIT 10", parms).ToList();
        }
        else
        {
            mates = new List<dynamic>();
        }

        // Get contact tooling
        var tooling = connector.contactSize != null && connector.contactType != null
            ? db.QueryFirstOrDefault(@"
                SELECT * FROM contacts_tools
                WHERE mapping_key = @key",
                new { key = $"{connector.contactSize}|{connector.contactType}" })
            : null;

        return new { connector, mates, tooling };
    }

    // ── Contacts ─────────────────────────────────────────────────────────────────
    public IEnumerable<dynamic> GetAllContacts()
    {
        using var db = Open();
        return db.Query(@"
            SELECT c.*,
                   (SELECT COUNT(*) FROM connectors cn
                    WHERE cn.contact_size = c.contact_size
                    AND cn.contact_type = c.contact_type) AS connector_count
            FROM contacts c
            ORDER BY c.contact_size, c.gender");
    }

    public IEnumerable<dynamic> GetContactsForSpec(string specFragment)
    {
        using var db = Open();
        return db.Query(@"
            SELECT * FROM contacts
            WHERE compatible_specs LIKE '%' || @spec || '%'
            ORDER BY CASE contact_size WHEN '8' THEN 1 WHEN '10' THEN 2 WHEN '12' THEN 3
                     WHEN '16' THEN 4 WHEN '20' THEN 5 ELSE 6 END,
                     contact_size, gender, part_number",
            new { spec = specFragment }).ToList();
    }

    public dynamic? GetContact(string partNumber)
    {
        using var db = Open();
        var contact = db.QueryFirstOrDefault(@"
            SELECT * FROM contacts WHERE part_number = @pn",
            new { pn = partNumber });
        if (contact is null) return null;

        // Find all connectors that use this contact
        var connectors = db.Query(@"
            SELECT part_number AS PartNumber, spec AS Spec, series AS Series,
                   connector_type AS ConnectorType, shell_style AS ShellStyle,
                   contact_count AS ContactCount, insert_arrangement AS InsertArrangement
            FROM connectors
            WHERE contact_size = @size AND contact_type = @type
            ORDER BY spec, series, part_number
            LIMIT 100",
            new { size = (string)contact.contact_size, type = (string)contact.contact_type });

        return new { contact, connectors };
    }

    // ── Corrections ───────────────────────────────────────────────────────────
    public void SubmitCorrection(string partNumber, string fieldName, string? oldValue, string correctedValue, string? notes)
    {
        using var db = OpenCorrections();
        db.Execute("""
            INSERT INTO corrections (connector_part_number, field_name, old_value, corrected_value, correction_notes)
            VALUES (@pn, @field, @old, @corrected, @notes)
            """,
            new { pn = partNumber, field = fieldName, old = oldValue, corrected = correctedValue, notes });
    }

    public IEnumerable<dynamic> GetCorrections(string? status = null)
    {
        using var db = OpenCorrections();
        var sql = status != null
            ? "SELECT * FROM corrections WHERE status = @status ORDER BY submitted_at DESC"
            : "SELECT * FROM corrections ORDER BY submitted_at DESC";
        return db.Query(sql, new { status });
    }
}