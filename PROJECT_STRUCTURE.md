# Project Structure

## Architecture Overview

The New Hanover County Property Tax Search MCP Server is built with a modular architecture designed for reliability, performance, and maintainability.

```
nhc-property-tax-server/
├── nhc_property_tax_server.py      # Main server implementation
├── test_nhc_property_tax_server.py # Comprehensive test suite
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment configuration template
├── Dockerfile                      # Container definition
├── docker-compose.yml              # Orchestration configuration
├── README.md                       # User documentation
├── PROJECT_STRUCTURE.md            # This file
├── LICENSE                         # MIT License
├── .gitignore                      # Git ignore rules
└── data/                          # Cache and temporary data directory
```

## Core Components

### 1. PropertyTaxSearcher Class
The main scraping engine with:
- Thread-safe session management
- Per-mode ViewState token caching
- Retry logic with exponential backoff
- Rate limiting implementation
- HTML parsing with BeautifulSoup
### 2. MCP Tools (7 total)
- **Search Tools** (3): By owner, address, and parcel ID
- **Detail Tool** (1): Comprehensive property information retrieval
- **Status Tool** (1): System availability checking
- **Capability Tool** (1): Configuration and feature discovery
- **Cache Tool** (1): Cache management

### 3. Caching Layer
- TTL-based caching using `cachetools`
- Separate caches for each search type
- Configurable duration and size limits
- Thread-safe access

### 4. Configuration Management
- Environment-based configuration via `python-dotenv`
- Comprehensive settings class
- Sensible defaults with override capability

## Data Flow

1. **Request Reception**: FastMCP server receives tool invocation
2. **Cache Check**: Query cache for existing results
3. **Token Management**: Obtain/refresh ASP.NET ViewState tokens
4. **Request Execution**: Perform HTTP request with retry logic
5. **Response Parsing**: Extract data from HTML response
6. **Result Caching**: Store results for future queries
7. **Response Delivery**: Return structured JSON response
## Key Design Decisions

### Thread Safety
- Fresh searcher instance per tool invocation
- Thread locks for shared state (tokens, rate limiting)
- Immutable configuration

### Error Handling
- Specific error types for different failure modes
- Graceful degradation with meaningful error messages
- Comprehensive logging with request correlation

### Performance Optimization
- Aggressive caching with TTL
- Connection pooling via requests.Session
- Rate limiting to prevent server overload
- Result truncation for large datasets

### Reliability Features
- Automatic retry with exponential backoff
- ViewState token refresh on expiry
- Health check endpoint for monitoring
- Docker deployment for consistency

## Extension Points

1. **Additional Search Modes**: Add new search methods by extending PropertyTaxSearcher
2. **Custom Parsers**: Implement specialized parsing for different page types
3. **Export Formats**: Add tools for different output formats (CSV, Excel)
4. **Notification System**: Implement alerts for property changes
5. **Batch Operations**: Add bulk search capabilities

## Testing Strategy

- Unit tests for individual components
- Mocked external dependencies
- Integration tests for tool workflows
- Performance benchmarks for optimization