namespace ConnectorDB.Models;

public class Connector
{
    public string PartNumber { get; set; } = "";
    public string? Spec { get; set; }
    public string? Series { get; set; }
    public string? Prefix { get; set; }
    public string? ConnectorType { get; set; }
    public string? ShellStyle { get; set; }
    public string? MountingType { get; set; }
    public string? InsertArrangement { get; set; }
    public string? ContactSize { get; set; }
    public string? ContactType { get; set; }
    public int? ContactCount { get; set; }
    public string? ShellSizeLetter { get; set; }
    public string? ShellSizeNumeric { get; set; }
    public string? Keying { get; set; }
    public string? Class { get; set; }
    public string? ShellMaterial { get; set; }
    public string? ShellPlating { get; set; }
    public string? TerminationType { get; set; }
    public string? EnvironmentType { get; set; }
    public string? Shielding { get; set; }
    public string? MatingConnectors { get; set; }
    public string? CompatibleContactSizes { get; set; }
    public string? Notes { get; set; }

    // Joined from inventory table
    public string? InvStatus { get; set; }
    public string? BoxNumber { get; set; }
    public string? InvNotes { get; set; }

    // Resolved mating connectors (populated by service)
    public List<Connector> MatingConnectorDetails { get; set; } = new();
    public List<InventoryItem> Fixtures { get; set; } = new();
    public ContactTooling? ContactTooling { get; set; }
    public InventoryItem? Inventory { get; set; }
}

public class InventoryItem
{
    public string PartNumber { get; set; } = "";
    public string? BoxNumber { get; set; }
    public string Status { get; set; } = "Available";
    public string? Notes { get; set; }

    // Fixture fields (reused for fixture table)
    public string? AssemblyConnector { get; set; }
    public string? FixtureId { get; set; }
    public string? MatingConnector { get; set; }
    public string? BoxSection { get; set; }
    public string? SlotPosition { get; set; }
    public string? FixtureStatus { get; set; }
    public string? LastVerifiedDate { get; set; }
    public string? ConnectorStatus { get; set; }
}

public class ContactTooling
{
    public string? MappingKey { get; set; }
    public string? ContactPartNumber { get; set; }
    public string? ContactSize { get; set; }
    public string? ContactType { get; set; }
    public string? WireGaugeRange { get; set; }
    public double? StripLengthMin { get; set; }
    public double? StripLengthMax { get; set; }
    public double? DefaultStripLength { get; set; }
    public string? CrimperTool { get; set; }
    public string? Positioner { get; set; }
    public string? Locator { get; set; }
    public string? InserterTool { get; set; }
    public string? ExtractorTool { get; set; }
    public string? ToolFamily { get; set; }
    public string? ToolLocation { get; set; }
    public string? Notes { get; set; }
}

public class SpecGroup
{
    public string? Spec { get; set; }
    public string? Series { get; set; }
    public int Count { get; set; }
}

public class Summary
{
    public int TotalConnectors { get; set; }
    public int CrossReferences { get; set; }
    public int Specs { get; set; }
}
