using ConnectorDB.Services;

var builder = WebApplication.CreateBuilder(args);

// ── Database paths ───────────────────────────────────────────────────────────
// connectors.db is read-only reference data. It always comes from the app
// bundle (the Dockerfile downloads it from GitHub Releases), so every deploy
// serves the newest release — never a stale copy left on the volume.
// User-submitted corrections go to a small separate writable database: on the
// Railway volume (/data) when present so they survive redeploys, otherwise in Data/.
var volumePath      = "/data";
var dbPath          = Path.Combine(AppContext.BaseDirectory, "Data", "connectors.db");
var correctionsPath = Directory.Exists(volumePath)
    ? Path.Combine(volumePath, "corrections.db")
    : Path.Combine(AppContext.BaseDirectory, "Data", "corrections.db");

Console.WriteLine($"Using database: {dbPath}");
Console.WriteLine($"Corrections database: {correctionsPath}");
builder.Configuration["DatabasePath"] = dbPath;
builder.Configuration["CorrectionsPath"] = correctionsPath;

// ── Services ─────────────────────────────────────────────────────────────────
builder.Services.AddRazorPages();
builder.Services.ConfigureHttpJsonOptions(opts =>
    opts.SerializerOptions.PropertyNameCaseInsensitive = true);
builder.Services.AddSingleton<ConnectorService>();
builder.Services.AddSingleton<ConnectorDB.Services.GitHubIssueService>();
// gzip/brotli for HTML, JSON and the multi-MB sitemap files (application/xml is in the defaults)
builder.Services.AddResponseCompression(o => o.EnableForHttps = true);

var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseResponseCompression();
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

    // Save locally and open a GitHub issue; one failing must not block the other.
    try { svc.SubmitCorrection(partNumber, fieldName, oldValue, correctedValue, notes); }
    catch (Exception ex) { Console.WriteLine($"Correction save failed: {ex.Message}"); }
    _ = github.CreateCorrectionIssueAsync(partNumber, fieldName, oldValue, correctedValue, notes);

    return Results.Ok(new { message = "Correction submitted. Thank you!" });
});

// ── Extended reference API endpoints ──────────────────────────────────────────
app.MapGet("/api/reference/glossary",         (ConnectorService svc) => svc.GetGlossary());
app.MapGet("/api/reference/wire-contact",     (ConnectorService svc) => svc.GetWireContactChart());
app.MapGet("/api/reference/finish-codes",     (ConnectorService svc) => svc.GetFinishCodes());
app.MapGet("/api/reference/backshells",       (ConnectorService svc) => svc.GetBackshells());
app.MapGet("/api/reference/wire-colors",      (ConnectorService svc) => svc.GetWireColors());
app.MapGet("/api/reference/heat-shrink",      (ConnectorService svc) => svc.GetHeatShrink());
app.MapGet("/api/reference/crimp-inspection", (ConnectorService svc) => svc.GetCrimpInspection());
app.MapGet("/api/reference/solder",          (ConnectorService svc) => svc.GetSolderStandards());
app.MapGet("/api/reference/esd",             (ConnectorService svc) => svc.GetEsdReference());
app.MapGet("/api/reference/harness",         (ConnectorService svc) => svc.GetHarnessStandards());

// ── Sitemaps ──────────────────────────────────────────────────────────────────
// Built once per deploy and cached in memory (the data is read-only), answer GET and HEAD,
// gzip via UseResponseCompression. lastmod = database file date, so it only moves when data changes.
const string SiteUrl = "https://mollyconnector.com";
const int SitemapChunk = 45000;                        // under Google's 50,000-URL / 50 MB limits
var sitemapDate  = File.GetLastWriteTimeUtc(dbPath).ToString("yyyy-MM-dd");
var sitemapCache = new System.Collections.Concurrent.ConcurrentDictionary<string, Lazy<string>>();
string[] getHead = { "GET", "HEAD" };
IResult Xml(string key, Func<string> build) =>
    Results.Content(sitemapCache.GetOrAdd(key, _ => new Lazy<string>(build)).Value, "application/xml; charset=utf-8");
const string Head = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>";
const string Ns   = "xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\"";

app.MapMethods("/sitemap.xml", getHead, (ConnectorService svc) => Xml("index", () =>
{
    var chunks = (int)Math.Ceiling(svc.GetConnectorCount() / (double)SitemapChunk);
    var sb = new System.Text.StringBuilder(Head).Append($"<sitemapindex {Ns}>");
    sb.Append($"<sitemap><loc>{SiteUrl}/sitemap-pages.xml</loc><lastmod>{sitemapDate}</lastmod></sitemap>");
    for (int i = 0; i < chunks; i++)
        sb.Append($"<sitemap><loc>{SiteUrl}/sitemap-connectors-{i}.xml</loc><lastmod>{sitemapDate}</lastmod></sitemap>");
    return sb.Append("</sitemapindex>").ToString();
}));

app.MapMethods("/sitemap-pages.xml", getHead, () => Xml("pages", () =>
{
    string[] paths = { "/", "/decode", "/d38999", "/builder", "/contacts", "/reference", "/donate" };
    string[] priorities = { "1.0", "0.9", "0.9", "0.9", "0.8", "0.8", "0.5" };
    var sb = new System.Text.StringBuilder(Head).Append($"<urlset {Ns}>");
    for (int i = 0; i < paths.Length; i++)
        sb.Append($"<url><loc>{SiteUrl}{paths[i]}</loc><lastmod>{sitemapDate}</lastmod><priority>{priorities[i]}</priority></url>");
    return sb.Append("</urlset>").ToString();
}));

app.MapMethods("/sitemap-connectors-{chunk:int}.xml", getHead, (int chunk, ConnectorService svc) =>
{
    if (chunk < 0 || chunk * SitemapChunk >= svc.GetConnectorCount()) return Results.NotFound();
    return Xml($"c{chunk}", () =>
    {
        var sb = new System.Text.StringBuilder(Head).Append($"<urlset {Ns}>");
        foreach (var pn in svc.GetPartNumbersForSitemap(chunk * SitemapChunk, SitemapChunk))
            sb.Append($"<url><loc>{SiteUrl}/connector/{Uri.EscapeDataString(pn).Replace("%2F", "/")}</loc><lastmod>{sitemapDate}</lastmod></url>");
        return sb.Append("</urlset>").ToString();
    });
});

app.Run();
