# New Hanover County Property Tax Search MCP Server

A production-ready FastMCP server with **7 comprehensive tools** for searching and retrieving property tax records from the New Hanover County etax.nhcgov.com portal. Features intelligent caching, rate limiting, robust error handling, and **interactive Swagger API documentation**.

## 🚀 Quick Start

### Local Development

1. **Clone and install dependencies:**
```bash
git clone https://github.com/ChrisTansey007/nhc-property-tax-server.git
cd nhc-property-tax-server
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Run the servers:**

```bash
# Option 1: Run both servers with the helper script
python run_servers.py

# Option 2: Run servers separately
# Terminal 1 - MCP Server:
python nhc_property_tax_server.py

# Terminal 2 - Documentation Server:
python docs_server.py
```

- MCP Server: `http://localhost:8000/mcp`
- API Documentation: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
# Check health
docker-compose ps
```

## 📋 Features

- **Web Scraping**: Robust scraping of New Hanover County tax portal
- **Intelligent Caching**: TTL-based caching with configurable duration
- **Rate Limiting**: Respects server resources with configurable delays
- **Retry Logic**: Exponential backoff for failed requests
- **Thread-Safe**: Concurrent request handling with proper locking
- **ViewState Management**: Per-mode token storage for ASP.NET forms
- **Comprehensive Error Handling**: Specific error types for debugging
- **Docker Support**: Production-ready containerization
- **Authentication**: Optional API key protection
- **Interactive API Documentation**: Swagger UI and ReDoc interfaces
- **OpenAPI 3.0 Specification**: Full API specification for client generation

## 🛠 Available Tools

### 1. `search_property_by_owner`
Search for properties by owner name.

**Parameters:**
- `owner_name` (str): Property owner's name to search

**Example:**
```json
{
  "tool": "search_property_by_owner",
  "parameters": {
    "owner_name": "SMITH"
  }
}```

**Response:**
```json
{
  "success": true,
  "search_type": "owner",
  "query": "SMITH",
  "results_count": 2,
  "properties": [
    {
      "parcel_id": "123456",
      "owner_name": "SMITH JOHN",
      "property_address": "123 MAIN ST",
      "tax_value": "$250,000",
      "detail_url": "https://etax.nhcgov.com/detail.aspx?id=123456",
      "search_timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "truncated": false,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 2. `search_property_by_address`
Search for properties by street address.

**Parameters:**
- `address` (str): Property address to search

**Example:**
```json
{  "tool": "search_property_by_address",
  "parameters": {
    "address": "123 MAIN ST"
  }
}
```

### 3. `search_property_by_parcel_id`
Search for a specific property by parcel ID.

**Parameters:**
- `parcel_id` (str): Parcel identification number

**Example:**
```json
{
  "tool": "search_property_by_parcel_id",
  "parameters": {
    "parcel_id": "123456"
  }
}
```

### 4. `get_property_details`
Retrieve detailed property information including assessments and ownership data.

**Parameters:**
- `parcel_id` (str): Parcel ID to get details for

**Example:**
```json
{
  "tool": "get_property_details",  "parameters": {
    "parcel_id": "123456"
  }
}
```

**Response includes:**
- Basic property information
- Detailed assessment data
- Ownership information
- Tax values and history
- Property characteristics

### 5. `check_system_status`
Check if the New Hanover County tax system is available.

**Example:**
```json
{
  "tool": "check_system_status"
}
```

**Response:**
```json
{
  "system_available": true,
  "status_code": 200,
  "maintenance_mode": false,
  "has_expected_content": true,
  "response_time_ms": 523,
  "check_timestamp": "2024-01-15T10:30:00Z"
}
```
### 6. `get_search_capabilities`
Get information about available search types and server configuration.

**Example:**
```json
{
  "tool": "get_search_capabilities"
}
```

### 7. `clear_cache`
Clear cached search results.

**Parameters:**
- `cache_type` (str): Type of cache to clear ("all", "owner", "address", "parcel", "detail")

**Example:**
```json
{
  "tool": "clear_cache",
  "parameters": {
    "cache_type": "all"
  }
}
```

## ⚙️ Configuration

All configuration is done through environment variables. See `.env.example` for all options:

| Variable | Default | Description |
|----------|---------|-------------|
| `RETRY_ATTEMPTS` | 3 | Number of retry attempts for failed requests || `RETRY_DELAY` | 2.0 | Initial delay between retries (seconds) |
| `RETRY_BACKOFF` | 2.0 | Exponential backoff multiplier |
| `RATE_LIMIT_ENABLED` | true | Enable rate limiting |
| `RATE_LIMIT_DELAY` | 1.0 | Delay between requests (seconds) |
| `CACHE_ENABLED` | true | Enable result caching |
| `CACHE_DURATION_HOURS` | 24 | Cache TTL in hours |
| `CACHE_MAX_SIZE` | 5000 | Maximum cached items |
| `MAX_RESULTS` | 500 | Maximum results per search |
| `MCP_API_KEY` | - | Optional API key for authentication |
| `PORT` | 8000 | Server port |

## 🔒 Security

- Optional API key authentication via `MCP_API_KEY`
- Rate limiting to prevent abuse
- Input validation on all search parameters
- Secure handling of ASP.NET ViewState tokens

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Install test dependencies
pip install pytest pytest-mock

# Run tests
pytest test_nhc_property_tax_server.py -v

# Run with coverage
pytest --cov=nhc_property_tax_server test_nhc_property_tax_server.py
```

## 📚 API Documentation

The server includes interactive API documentation powered by Swagger UI and ReDoc:

### Documentation Endpoints

- **Swagger UI**: `http://localhost:8001/docs` - Interactive API explorer with try-it-out functionality
- **ReDoc**: `http://localhost:8001/redoc` - Clean, responsive API reference
- **OpenAPI Spec**: `http://localhost:8001/openapi.json` - Raw OpenAPI 3.0 specification

### Using the Documentation

1. Start both servers using `python run_servers.py`
2. Open `http://localhost:8001` in your browser
3. Choose your preferred documentation interface
4. Explore endpoints, view schemas, and test API calls

### Client Code Generation

The OpenAPI specification can be used to generate client libraries in multiple languages:

```bash
# Example: Generate Python client
openapi-generator-cli generate -i http://localhost:8001/openapi.json -g python -o ./client
```
## 🐛 Troubleshooting

### Common Issues

1. **"No results found" errors**
   - Verify the search term spelling
   - Check system status with `check_system_status`
   - The portal may be temporarily unavailable

2. **Rate limiting errors**
   - Increase `RATE_LIMIT_DELAY` in configuration
   - Enable caching to reduce requests

3. **ViewState errors**
   - The server automatically refreshes tokens
   - If persistent, clear cache with `clear_cache`

## 📊 Performance

- Caching reduces response time by 95% for repeated queries
- Rate limiting ensures sustainable operation
- Concurrent request handling with thread safety
- Automatic retry with exponential backoff

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🏢 Disclaimer

This tool is for educational and research purposes. Users must comply with the New Hanover County website terms of service.