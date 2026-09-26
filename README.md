# ConnectorDB — ASP.NET Core / Razor Pages

MIL-spec connector reference database: 419,000+ connectors, inventory tracking, mating connector lookup.

## Local Development

**Requirements:** .NET 8 SDK, Visual Studio 2022 or VS Code

```bash
# Restore packages
dotnet restore

# Run locally (uses Data/connectors.db)
dotnet run
# → https://localhost:5001
```

The `Data/connectors.db` file must be present. It's the SQLite database containing all connector data.

## Project Structure

```
ConnectorDB/
├── Program.cs                  # App startup, API endpoints, DB path logic
├── ConnectorDB.csproj
├── Dockerfile
├── railway.toml
├── Data/
│   └── connectors.db           # SQLite database (419k connectors, inventory, fixtures, tooling)
├── Models/
│   └── Connector.cs            # All model classes
├── Services/
│   └── ConnectorService.cs     # All DB queries via Dapper
├── Pages/
│   ├── Shared/_Layout.cshtml   # Master layout
│   ├── Index.cshtml            # Main search page
│   └── Index.cshtml.cs
└── wwwroot/
    ├── css/site.css            # Dark theme styles
    └── js/app.js               # Client-side search, render, inventory logic
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/summary` | Stats for header chips |
| GET | `/api/specs` | Spec/series list for dropdowns |
| GET | `/api/search?q=&spec=&series=&type=&inv_status=&limit=` | Search connectors |
| GET | `/api/connector/{partNumber}` | Full connector detail with mates, fixtures, tooling |
| POST | `/api/inventory/{partNumber}` | Update inventory status/box/notes |

## Deploying to Railway

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/connectordb.git
git push -u origin main
```

### 2. Create Railway project
- Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
- Select your repository

### 3. Add a Volume (persistent SQLite storage)
- In your Railway service → **Volumes** tab → **Add Volume**
- Mount path: `/data`
- On first boot, the app automatically copies `Data/connectors.db` from the image to `/data/connectors.db`
- All inventory changes are written to the Volume and survive restarts

### 4. Set environment variables (optional)
Railway auto-detects the port via `$PORT`. The Dockerfile sets `ASPNETCORE_URLS=http://+:8080`.
If Railway assigns a different port, add:
```
ASPNETCORE_URLS=http://+:$PORT
```

### 5. Deploy
Railway builds the Dockerfile and deploys automatically on every `git push`.

## Database Notes

- **connectors** — 419,083 MIL-spec part numbers (MIL-DTL-38999, 26482, 5015, 83513, 83723, 22992, 24308, AS95234, Molex crossref)
- **inventory** — 445 entries from CableScan_Cables.xlsx (status: Available / Not Built / Purchased / Need to Order / Needs Replacement)
- **fixtures** — 10 fixture inventory records
- **contacts_tools** — 14 contact tooling / crimping records

## The Database File

`connectors.db` is ~150 MB uncompressed. Options for Git:
- **Git LFS** — `git lfs track "*.db"` then commit normally (recommended)
- **Keep it local** — don't commit it; download separately and place in `Data/`
- **Build script** — rebuild from source Excel files using the included Python script (if you have the source files)
