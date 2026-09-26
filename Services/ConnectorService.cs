using ConnectorDB.Models;
using Dapper;
using Microsoft.Data.Sqlite;

namespace ConnectorDB.Services;

public class ConnectorService
{
    private readonly string _connectionString;

    public ConnectorService(IConfiguration config)
    {
        var path = config["DatabasePath"]
            ?? throw new InvalidOperationException("DatabasePath not configured.");
        _connectionString = $"Data Source={path};Mode=ReadWriteCreate;Cache=Shared";
    }

    private SqliteConnection Open() => new(_connectionString);

    // ── Summary ────────────────────────────────────────────────────────────
    public Summary GetSummary()
    {
        using var db = Open();
        var total  = db.ExecuteScalar<int>("SELECT COUNT(*) FROM connectors");
        var specs  = db.ExecuteScalar<int>("SELECT COUNT(DISTINCT spec) FROM connectors");
        return new Summary { TotalConnectors = total, Specs = specs };
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
                       tool_location AS ToolLocation, notes AS Notes
                FROM contacts_tools WHERE mapping_key = @key", new { key });
        }

        return row;
    }
}
