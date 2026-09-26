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
builder.Services.AddSingleton<ConnectorService>();

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

app.Run();

