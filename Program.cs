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

app.MapPost("/api/correction", (
    System.Text.Json.JsonElement body,
    ConnectorService svc,
    ConnectorDB.Services.GitHubIssueService github) =>
{
    string? GetProp(string a, string b) {
        if (body.TryGetProperty(a, out var v) && v.ValueKind == System.Text.Json.JsonValueKind.String) return v.GetString();
        if (body.TryGetProperty(b, out var v2) && v2.ValueKind == System.Text.Json.JsonValueKind.String) return v2.GetString();
        return null;
    }

    var partNumber     = GetProp("PartNumber",     "partNumber");
    var fieldName      = GetProp("FieldName",      "fieldName") ?? "";
    var oldValue       = GetProp("OldValue",       "oldValue");
    var correctedValue = GetProp("CorrectedValue", "correctedValue");
    var notes          = GetProp("Notes",          "notes");

    if (string.IsNullOrWhiteSpace(partNumber) || string.IsNullOrWhiteSpace(correctedValue))
        return Results.BadRequest();

    svc.SubmitCorrection(partNumber, fieldName, oldValue, correctedValue, notes);
    _ = github.CreateCorrectionIssueAsync(partNumber, fieldName, oldValue, correctedValue, notes);

    return Results.Ok(new { message = "Correction submitted. Thank you!" });
});

// ── Sitemap Index ─────────────────────────────────────────────────────────────
app.MapGet("/sitemap.xml", (ConnectorService svc) =>
{
    var baseUrl = "https://mollyconnector.com";
    var today = DateTime.UtcNow.ToString("yyyy-MM-dd");
    var count = svc.GetConnectorCount();
    var chunks = (int)Math.Ceiling(count / 50000.0);

    var sb = new System.Text.StringBuilder();
    sb.Append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>");
    sb.Append("<sitemapindex xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">");
    sb.Append("<sitemap><loc>" + baseUrl + "/sitemap-pages.xml</loc><lastmod>" + today + "</lastmod></sitemap>");
    for (int i = 0; i < chunks; i++)
        sb.Append("<sitemap><loc>" + baseUrl + "/sitemap-connectors-" + i + ".xml</loc><lastmod>" + today + "</lastmod></sitemap>");
    sb.Append("</sitemapindex>");
    return Results.Content(sb.ToString(), "application/xml");
});

// Static pages sitemap
app.MapGet("/sitemap-pages.xml", () =>
{
    var baseUrl = "https://mollyconnector.com";
    var today = DateTime.UtcNow.ToString("yyyy-MM-dd");
    var sb = new System.Text.StringBuilder();
    sb.Append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>");
    sb.Append("<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">");
    string[] paths = { "/", "/decoder", "/builder", "/contacts", "/reference", "/donate" };
    string[] priorities = { "1.0", "0.9", "0.9", "0.8", "0.8", "0.5" };
    for (int i = 0; i < paths.Length; i++)
    {
        sb.Append("<url>");
        sb.Append($"<loc>{baseUrl}{paths[i]}</loc>");
        sb.Append($"<lastmod>{today}</lastmod>");
        sb.Append($"<priority>{ priorities[i]}</priority>");
        sb.Append("</url>");
    }
    sb.Append("</urlset>");
    return Results.Content(sb.ToString(), "application/xml");
});

// Connector pages sitemap (chunked, 50k per file)
app.MapGet("/sitemap-connectors-{chunk:int}.xml", (int chunk, ConnectorService svc) =>
{
    var baseUrl = "https://mollyconnector.com";
    var today = DateTime.UtcNow.ToString("yyyy-MM-dd");
    var pns = svc.GetPartNumbersForSitemap(chunk * 50000, 50000);

    var sb = new System.Text.StringBuilder();
    sb.Append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>");
    sb.Append("<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">");
    foreach (var pn in pns)
    {
        var encoded = Uri.EscapeDataString(pn).Replace("%2F", "/");
        sb.Append("<url>");
        sb.Append($"<loc>{baseUrl}/connector/{encoded}</loc>");
        sb.Append($"<lastmod>{today}</lastmod>");
        sb.Append("<priority>0.6</priority>");
        sb.Append("</url>");
    }
    sb.Append("</urlset>");
    return Results.Content(sb.ToString(), "application/xml");
});

app.Run();

