# ── Build stage ───────────────────────────────────────────────────────────────
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY ConnectorDB.csproj .
RUN dotnet restore

COPY . .
RUN dotnet publish -c Release -o /app/publish

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime
WORKDIR /app

# Copy published app
COPY --from=build /app/publish .

# Download the real database from GitHub Releases at build time
# (bypasses Git LFS pointer issue)
RUN mkdir -p /app/Data && \
    apt-get update && apt-get install -y curl && \
    curl -L -o /app/Data/connectors.db \
    "https://github.com/majbummer/molly-connector/releases/download/v1.0/connectors.db?v=10" && \
    apt-get remove -y curl && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080
ENV ASPNETCORE_ENVIRONMENT=Production

ENTRYPOINT ["dotnet", "ConnectorDB.dll"]
