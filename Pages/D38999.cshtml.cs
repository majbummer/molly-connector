using Microsoft.AspNetCore.Mvc.RazorPages;
using ConnectorDB.Services;

namespace ConnectorDB.Pages;

public class D38999Model : PageModel
{
    private readonly ConnectorService _svc;
    public D38999Model(ConnectorService svc) => _svc = svc;

    public List<dynamic> Contacts { get; private set; } = new();

    public void OnGet()
    {
        try { Contacts = _svc.GetContactsForSpec("38999").ToList(); }
        catch { Contacts = new(); } // page still renders if the DB is unavailable
    }
}
