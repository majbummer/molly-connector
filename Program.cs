using ConnectorDB.Services;

var builder = WebApplication.CreateBuilder(args);

// ── Database path ────────────────────────────────────────────────────────────
// On Railway, the Volume is mounted at /data. If /data/connectors.db doesn't
// exist yet (first boot), we copy the seed database from the app bundle.
// Locally the DB just sits next to the executable in Data/.
var volumePath = "/data";
var seedPath   = Path.Combine(AppContext.BaseDirectory, "Data", "connectors.db");
string dbPath;

if (Directory.Exists(volumePath))
{
    dbPath = Path.Combine(volumePath, "connectors.db");
    if (!File.Exists(dbPath) && File.Exists(seedPath))
    {
        Console.WriteLine("First boot: copying seed database to Railway volume...");
        File.Copy(seedPath, dbPath);
        Console.WriteLine($"Seed copied → {dbPath}");
    }
}
else
{
    // Local development — use the Data folder
    dbPath = seedPath;
}

Console.WriteLine($"Using database: {dbPath}");
builder.Configuration["DatabasePath"] = dbPath;

// ── Services ─────────────────────────────────────────────────────────────────
builder.Services.AddRazorPages();
builder.Services.ConfigureHttpJsonOptions(opts =>
    opts.SerializerOptions.PropertyNameCaseInsensitive = true);
builder.Services.AddSingleton<ConnectorService>();
builder.Services.AddSingleton<ConnectorDB.Services.GitHubIssueService>();

var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseStaticFiles();
app.UseRouting();
app.MapRazorPages();

// ── Minimal API endpoints (called by JS fetch) ───────────────────────────────
app.MapGet("/api/summary", (ConnectorService svc) => svc.GetSummary());

app.MapGet("/api/specs", (ConnectorService svc) => svc.GetSpecs());

app.MapGet("/api/search", (
    string? q, string? spec, string? series, string? type,
    int limit, ConnectorService svc) =>
    svc.Search(q, spec, series, type, Math.Min(limit == 0 ? 50 : limit, 200)));

// ── Reference API endpoints ──────────────────────────────────────────────────
app.MapGet("/api/reference/milspecs", (ConnectorService svc) => svc.GetMilSpecs());
app.MapGet("/api/reference/crimping-tools", (ConnectorService svc) => svc.GetCrimpingTools());
app.MapGet("/api/reference/positioners", (ConnectorService svc) => svc.GetPositioners());
app.MapGet("/api/reference/insertion-tools", (ConnectorService svc) => svc.GetInsertionTools());
app.MapGet("/api/reference/wire", (ConnectorService svc) => svc.GetWireReference());
app.MapGet("/api/reference/torque", (ConnectorService svc) => svc.GetTorqueSpecs());

app.MapGet("/api/contacts", (ConnectorService svc) => svc.GetAllContacts());

app.MapGet("/api/contacts/{partNumber}", (string partNumber, ConnectorService svc) =>
{
    var result = svc.GetContact(Uri.UnescapeDataString(partNumber));
    return result is null ? Results.NotFound() : Results.Ok(result);
});

app.MapGet("/api/decode/{partNumber}", (string partNumber) =>
{
    var result = PartNumberDecoder.Decode(Uri.UnescapeDataString(partNumber));
    return result is null ? Results.NotFound() : Results.Ok(result);
});

app.MapGet("/api/connector/{partNumber}", (string partNumber, ConnectorService svc) =>
{
    var result = svc.GetConnector(Uri.UnescapeDataString(partNumber));
    return result is null ? Results.NotFound() : Results.Ok(result);
});

app.MapPost("/api/correction", async (
    HttpRequest request,
    ConnectorService svc,
    ConnectorDB.Services.GitHubIssueService github) =>
{
    var body = await request.ReadFromJsonAsync<CorrectionRequest>();
    if (body is null || string.IsNullOrWhiteSpace(body.PartNumber) || string.IsNullOrWhiteSpace(body.CorrectedValue))
        return Results.BadRequest();

    // Save to local DB
    svc.SubmitCorrection(body.PartNumber, body.FieldName, body.OldValue, body.CorrectedValue, body.Notes);

    _ = github.CreateCorrectionIssueAsync(
        body.PartNumber, body.FieldName,
        body.OldValue, body.CorrectedValue, body.Notes);

    // Create GitHub Issue (if token is configured)
    _ = github.CreateCorrectionIssueAsync(
        body.partNumber, body.fieldName,
        body.oldValue, body.correctedValue, body.notes);

    return Results.Ok(new { message = "Correction submitted. Thank you!" });
});

app.Run();

record CorrectionRequest(string PartNumber, string FieldName, string? OldValue, string CorrectedValue, string? Notes);
