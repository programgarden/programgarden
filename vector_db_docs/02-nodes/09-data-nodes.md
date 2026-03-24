---
category: node_reference
tags: [data, sqlite, http, field_mapping, file_reader]
priority: medium
---

# Data Nodes: SQLite, HTTP, FieldMapping, FileReader

## SQLiteNode

Stores and queries data in a local SQLite database.

### Mode 1: execute_query (Direct SQL)

```json
{
  "id": "sqlite",
  "type": "SQLiteNode",
  "db_name": "trading.db",
  "operation": "execute_query",
  "query": "SELECT * FROM trade_history WHERE symbol = :symbol",
  "parameters": {"symbol": "AAPL"}
}
```

### Mode 2: simple (CRUD without SQL)

```json
{
  "id": "sqlite",
  "type": "SQLiteNode",
  "db_name": "trading.db",
  "operation": "simple",
  "table": "peak_tracker",
  "action": "upsert",
  "columns": ["symbol", "peak_price"],
  "values": {"symbol": "AAPL", "peak_price": 195.50},
  "on_conflict": "symbol"
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `db_name` | string | O | DB filename (auto-created) |
| `operation` | string | O | `execute_query` or `simple` |
| `query` | string | Conditional | SQL query (execute_query) |
| `parameters` | object | - | Query parameters (`:name` format) |
| `table` | string | Conditional | Table name (simple) |
| `action` | string | Conditional | `select`/`insert`/`update`/`delete`/`upsert` |
| `values` | object | Conditional | Values to store |
| `on_conflict` | string | Conditional | Conflict key for upsert |

**Output**: `rows` (query results), `affected_count` (affected row count)

**upsert**: "Update if exists, insert if not". Useful for tracking peak prices, etc.

## HTTPRequestNode

Calls external HTTP APIs.

```json
{
  "id": "http",
  "type": "HTTPRequestNode",
  "method": "GET",
  "url": "https://api.example.com/news",
  "query_params": {"symbol": "AAPL", "limit": "5"},
  "timeout_seconds": 30
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `method` | string | `"GET"` | HTTP method (GET, POST, PUT, PATCH, DELETE) |
| `url` | string | - | Request URL |
| `query_params` | object | - | URL query parameters |
| `body` | object | - | Request body (POST/PUT/PATCH) |
| `headers` | object | - | Additional headers |
| `credential_id` | string | - | API authentication |
| `timeout_seconds` | number | `30` | Timeout (seconds, 1~300) |

**Output**: `response` (response), `status_code` (HTTP status), `success` (success), `error` (error)

APIs requiring authentication reference HTTP credentials via `credential_id` (Bearer Token, Basic Auth, etc.).

## FieldMappingNode

Transforms data field names. Maps field names from external API responses to ProgramGarden format.

```json
{
  "id": "mapping",
  "type": "FieldMappingNode",
  "data": "{{ nodes.http.response }}",
  "mappings": [
    {"from": "ticker", "to": "symbol"},
    {"from": "last_price", "to": "price"},
    {"from": "vol", "to": "volume"}
  ],
  "preserve_unmapped": true
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `data` | expression | - | Data to transform |
| `mappings` | array | - | Mapping rules `[{from, to}]` |
| `preserve_unmapped` | boolean | `true` | Keep fields not in mapping rules |

**Output**: `mapped_data` (transformed data)

**Before transformation**: `{"ticker": "AAPL", "last_price": 192.30, "vol": 45000000}`
**After transformation**: `{"symbol": "AAPL", "price": 192.30, "volume": 45000000}`

ConditionNode plugins use standard field names like `symbol`, `open`, `high`, `low`, `close`, `volume`. Use FieldMappingNode to align external API data field names.

## FileReaderNode

Reads and parses files into text/data. Supports PDF, TXT, CSV, JSON, MD, DOCX, XLSX formats. Can be used as an AIAgentNode tool (`is_tool_enabled`).

```json
{
  "id": "reader",
  "type": "FileReaderNode",
  "file_paths": ["/app/data/report.pdf", "/app/data/prices.csv"],
  "format": "auto"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `file_paths` | array | - | File path array |
| `file_data_list` | array | - | Base64 encoded file data array |
| `file_names` | array | - | Filenames for file_data_list (format detection) |
| `format` | string | `"auto"` | Format (`auto`, `pdf`, `txt`, `csv`, `json`, `md`, `docx`, `xlsx`) |
| `pages` | string | - | PDF page range (e.g., `"1-5"`, `"1,3,5"`) |
| `encoding` | string | `"utf-8"` | Text encoding |
| `extract_tables` | boolean | `false` | Extract tables from PDF (pdfplumber) |
| `sheet_name` | string | - | XLSX sheet name |
| `max_file_size_mb` | number | `10` | Max file size per file (MB) |

**Output**: `texts` (text array), `data_list` (parsed data array), `metadata` (file metadata array)

**Security**: File paths are restricted to `/app/data/` directory. Path traversal attacks are automatically blocked. Max 20 files per execution.

**Batch processing**: Multiple files are processed together, outputting arrays compatible with auto-iterate for per-file AI analysis.

**Community node**: Requires `programgarden-community` package. Optional extras: `pip install programgarden-community[docx,xlsx,pdf-tables]`.
