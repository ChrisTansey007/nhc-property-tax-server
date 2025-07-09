"""
FastMCP-compatible Swagger Documentation Server
Runs alongside the main MCP server to provide API documentation
"""

from flask import Flask, jsonify, Response
from swagger_docs import get_openapi_spec, get_swagger_ui_html, get_redoc_html
import os
from datetime import datetime

app = Flask(__name__)

# Server start time
SERVER_START_TIME = datetime.utcnow()

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": (datetime.utcnow() - SERVER_START_TIME).total_seconds(),
        "version": "2.0.0",
        "service": "nhc-property-tax-docs"
    })

@app.route('/openapi.json')
def openapi_spec():
    """Serve OpenAPI specification"""
    return jsonify(get_openapi_spec())

@app.route('/docs')
def swagger_ui():
    """Serve Swagger UI documentation"""
    return Response(get_swagger_ui_html("/openapi.json"), mimetype='text/html')
@app.route('/redoc')
def redoc_ui():
    """Serve ReDoc documentation"""
    return Response(get_redoc_html("/openapi.json"), mimetype='text/html')

@app.route('/')
def index():
    """Index page with links to documentation"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>NHC Property Tax Search API</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
            }
            h1 { color: #333; }
            .links { margin-top: 30px; }
            .link-card {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                margin: 10px 0;
                text-decoration: none;
                display: block;
                color: #333;
                transition: all 0.3s;
            }
            .link-card:hover {
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                transform: translateY(-2px);
            }
        </style>
    </head>
    <body>
        <h1>New Hanover County Property Tax Search API</h1>
        <p>FastMCP server for searching property tax records</p>
        
        <div class="links">
            <a href="/docs" class="link-card">
                <h3>📚 Swagger UI Documentation</h3>
                <p>Interactive API documentation with try-it-out functionality</p>
            </a>
            
            <a href="/redoc" class="link-card">
                <h3>📖 ReDoc Documentation</h3>
                <p>Clean, responsive API reference documentation</p>
            </a>
            
            <a href="/openapi.json" class="link-card">
                <h3>📄 OpenAPI Specification</h3>
                <p>Raw OpenAPI 3.0 specification in JSON format</p>
            </a>
            
            <a href="/health" class="link-card">
                <h3>❤️ Health Check</h3>
                <p>Check documentation server status</p>
            </a>
        </div>
        
        <div style="margin-top: 50px; color: #666;">
            <p>Main MCP server endpoint: <code>http://localhost:8000/mcp</code></p>
            <p>Documentation server: <code>http://localhost:8001</code></p>
        </div>
    </body>
    </html>
    """
    return Response(html, mimetype='text/html')

if __name__ == '__main__':
    docs_port = int(os.getenv('DOCS_PORT', 8001))
    app.run(host='0.0.0.0', port=docs_port, debug=False)