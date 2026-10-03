using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using ConnectorDB.Services;

namespace ConnectorDB.Pages;

public class ConnectorPageModel : PageModel
{
    private readonly ConnectorService _svc;

    public ConnectorPageModel(ConnectorService svc) => _svc = svc;

    public dynamic? Connector { get; private set; }
    public IEnumerable<dynamic>? Mates { get; private set; }
    public dynamic? Tooling { get; private set; }
    public string RequestedPN { get; private set; } = "";

    public IActionResult OnGet(string partNumber)
    {
        // Decode URL-encoded slashes
        RequestedPN = Uri.UnescapeDataString(partNumber ?? "");

        var result = _svc.GetConnectorDetail(RequestedPN);
        if (result is null)
        {
            Response.StatusCode = 404;
            return Page();
        }

        Connector = result.connector;
        Mates     = result.mates as IEnumerable<dynamic>;
        Tooling   = result.tooling;
        return Page();
    }
}
