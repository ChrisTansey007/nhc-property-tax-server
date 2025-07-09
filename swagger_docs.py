"""
Swagger API Documentation for New Hanover County Property Tax Search MCP Server
Provides OpenAPI specification and interactive documentation
"""

from typing import Dict, Any, List
import json
from datetime import datetime

# OpenAPI 3.0 Specification
def get_openapi_spec() -> Dict[str, Any]:
    """Generate OpenAPI specification for the MCP server"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "New Hanover County Property Tax Search API",
            "description": """
## Overview

A FastMCP server providing comprehensive property tax search capabilities for New Hanover County, NC.

### Features
- Search properties by owner name, address, or parcel ID
- Retrieve detailed property information
- Intelligent caching with TTL
- Rate limiting for sustainable operation
- System health monitoring

### Authentication

Optional API key authentication via `X-API-Key` header when `MCP_API_KEY` is configured.
            """,
            "version": "2.0.0",
            "contact": {
                "name": "API Support",
                "url": "https://github.com/ChrisTansey007/nhc-property-tax-server"
            }
        },        "servers": [
            {
                "url": "http://localhost:8000",
                "description": "Local development server"
            }
        ],
        "paths": get_api_paths(),
        "components": {
            "schemas": get_schemas(),
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                }
            }
        },
        "tags": [
            {
                "name": "Property Search",
                "description": "Search operations for property records"
            },
            {
                "name": "Property Details",
                "description": "Detailed property information retrieval"
            },
            {
                "name": "System",
                "description": "System status and configuration"
            }
        ]
    }


def get_api_paths() -> Dict[str, Any]:
    """Define all API endpoints"""
    return {
        "/mcp": {
            "post": {                "summary": "Execute MCP Tool",
                "description": "Main endpoint for all MCP tool executions",
                "operationId": "executeTool",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ToolRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Successful operation",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ToolResponse"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/health": {
            "get": {
                "summary": "Health Check",
                "description": "Check server health status",
                "operationId": "healthCheck",
                "tags": ["System"],
                "responses": {
                    "200": {
                        "description": "Server is healthy",                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HealthResponse"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/docs": {
            "get": {
                "summary": "API Documentation",
                "description": "Interactive Swagger UI documentation",
                "operationId": "getDocumentation",
                "tags": ["System"],
                "responses": {
                    "200": {
                        "description": "HTML documentation page"
                    }
                }
            }
        }
    }


def get_schemas() -> Dict[str, Any]:
    """Define all request/response schemas"""
    return {
        "ToolRequest": {
            "type": "object",
            "required": ["tool", "parameters"],
            "properties": {
                "tool": {                    "type": "string",
                    "enum": [
                        "search_property_by_owner",
                        "search_property_by_address",
                        "search_property_by_parcel_id",
                        "get_property_details",
                        "check_system_status",
                        "get_search_capabilities",
                        "clear_cache"
                    ],
                    "description": "The MCP tool to execute"
                },
                "parameters": {
                    "type": "object",
                    "description": "Tool-specific parameters"
                }
            }
        },
        "ToolResponse": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {"type": "object"},
                "error": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"}
            }
        },
        "SearchResponse": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "search_type": {"type": "string"},
                "query": {"type": "string"},
                "results_count": {"type": "integer"},
                "properties": {                    "type": "array",
                    "items": {
                        "$ref": "#/components/schemas/Property"
                    }
                },
                "truncated": {"type": "boolean"},
                "timestamp": {"type": "string", "format": "date-time"}
            }
        },
        "Property": {
            "type": "object",
            "properties": {
                "parcel_id": {"type": "string"},
                "owner_name": {"type": "string"},
                "property_address": {"type": "string"},
                "tax_value": {"type": "string"},
                "detail_url": {"type": "string"},
                "search_timestamp": {"type": "string", "format": "date-time"}
            }
        },
        "HealthResponse": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
                "uptime": {"type": "number"},
                "version": {"type": "string"}
            }
        }
    }


def get_swagger_ui_html(spec_url: str = "/openapi.json") -> str:
    """Generate Swagger UI HTML page"""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>NHC Property Tax Search API Documentation</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css">
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
        .swagger-ui .topbar {{
            display: none;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            window.ui = SwaggerUIBundle({{
                url: '{spec_url}',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            }});
        }};
    </script>
</body>
</html>
"""


def get_redoc_html(spec_url: str = "/openapi.json") -> str:
    """Generate ReDoc HTML page for alternative documentation view"""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>NHC Property Tax Search API Reference</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    <redoc spec-url='{spec_url}'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"></script>
</body>
</html>
"""