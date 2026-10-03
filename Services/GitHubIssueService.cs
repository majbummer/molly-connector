using System.Text;
using System.Text.Json;

namespace ConnectorDB.Services;

public class GitHubIssueService
{
    private readonly string? _token;
    private const string Repo = "majbummer/molly-connector";
    private const string ApiUrl = "https://api.github.com/repos/" + Repo + "/issues";

    public GitHubIssueService(IConfiguration config)
    {
        _token = config["GITHUB_ISSUE_TOKEN"];
    }

    public bool IsConfigured => !string.IsNullOrWhiteSpace(_token);

    public async Task<bool> CreateCorrectionIssueAsync(
        string partNumber, string fieldName,
        string? oldValue, string correctedValue, string? notes)
    {
        if (!IsConfigured) return false;

        var title = $"[Correction] {partNumber} — {fieldName}";
        var body  = $"""
## Data Correction Report — Molly Connector

**Part Number:** `{partNumber}`
**Field:** {fieldName}
**Current Value:** {(string.IsNullOrWhiteSpace(oldValue) ? "_not provided_" : $"`{oldValue}`")}
**Corrected Value:** `{correctedValue}`
**Notes:** {(string.IsNullOrWhiteSpace(notes) ? "_none_" : notes)}

---
_Submitted via mollyconnector.com_
""";

        var payload = JsonSerializer.Serialize(new
        {
            title,
            body,
            labels = new[] { "data-correction", "needs-review" }
        });

        try
        {
            using var http = new HttpClient();
            http.DefaultRequestHeaders.UserAgent.ParseAdd("MollyConnector/1.0");
            http.DefaultRequestHeaders.Authorization =
                new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", _token);

            var response = await http.PostAsync(
                ApiUrl,
                new StringContent(payload, Encoding.UTF8, "application/json"));
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }
}
