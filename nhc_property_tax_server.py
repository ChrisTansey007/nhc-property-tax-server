"""
New Hanover County Property Tax Search MCP Server v2.0
-----------------------------------------------------
Enhanced FastMCP server for searching property tax records via web scraping
of the New Hanover County etax.nhcgov.com portal.

Improvements in v2.0:
- Robust retry logic with exponential backoff
- Per-mode ViewState token management
- Comprehensive caching with TTL
- Rate limiting to respect server resources
- Detail page scraping for complete property information
- Enhanced error handling with specific error types
- Thread-safe concurrent request handling
- Unicode/encoding support
- Payload size guards for large result sets
"""

from __future__ import annotations

import os
import json
import logging
import uuid
import datetime as dt
import time
import threading
from pathlib import Path
from functools import wraps
from typing import List, Dict, Any, Optional
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from dotenv import load_dotenv
from cachetools import TTLCache

from fastmcp import FastMCP, HeaderAuthMiddleware, Context

# Configuration
load_dotenv()

class Settings:
    """Environment-driven configuration"""
    
    # Data storage
    DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # New Hanover County Tax Search URLs
    BASE_URL = "https://etax.nhcgov.com"
    SEARCH_URL = f"{BASE_URL}/pt/search/commonsearch.aspx"
    
    # Search modes
    SEARCH_MODES = {
        "owner": "owner",
        "address": "address", 
        "parcel": "parid",
        "advanced": "advanced"
    }    
    # Request settings
    REQUEST_TIMEOUT = 30
    RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))
    RETRY_DELAY = float(os.getenv("RETRY_DELAY", "2.0"))
    RETRY_BACKOFF = float(os.getenv("RETRY_BACKOFF", "2.0"))
    
    # Rate limiting
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "1.0"))
    
    # Caching
    CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_DURATION_HOURS = int(os.getenv("CACHE_DURATION_HOURS", "24"))
    CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "5000"))
    
    # Result limits
    MAX_RESULTS = int(os.getenv("MAX_RESULTS", "500"))
    
    # Security
    API_KEY = os.getenv("MCP_API_KEY")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s [%(request_id)s] %(message)s"
)
logger = logging.getLogger(__name__)
# Cache instances with TTL
if Settings.CACHE_ENABLED:
    _owner_cache = TTLCache(maxsize=Settings.CACHE_MAX_SIZE, ttl=Settings.CACHE_DURATION_HOURS * 3600)
    _address_cache = TTLCache(maxsize=Settings.CACHE_MAX_SIZE, ttl=Settings.CACHE_DURATION_HOURS * 3600)
    _parcel_cache = TTLCache(maxsize=Settings.CACHE_MAX_SIZE, ttl=Settings.CACHE_DURATION_HOURS * 3600)
    _detail_cache = TTLCache(maxsize=Settings.CACHE_MAX_SIZE, ttl=Settings.CACHE_DURATION_HOURS * 3600)

def with_request_id(func):
    """Decorator for request ID correlation"""
    @wraps(func)
    def wrapper(*args, ctx: Context, **kwargs):
        rid = ctx.request_id if ctx and hasattr(ctx, "request_id") else uuid.uuid4().hex[:8]
        adapter = logging.LoggerAdapter(logger, {"request_id": rid})
        ctx.logger = adapter
        return func(*args, ctx=ctx, **kwargs)
    return wrapper

class PropertyTaxSearcher:
    """Thread-safe handler for New Hanover County property tax searches"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        # Per-mode token storage to avoid stale ViewState issues
        self._tokens = {}
        self._lock = threading.RLock()
        self._last_request_time = 0        
    def _rate_limit(self):
        """Implement rate limiting between requests"""
        if not Settings.RATE_LIMIT_ENABLED:
            return
            
        with self._lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < Settings.RATE_LIMIT_DELAY:
                sleep_time = Settings.RATE_LIMIT_DELAY - elapsed
                time.sleep(sleep_time)
            self._last_request_time = time.time()
    
    def _safe_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with retry logic and exponential backoff"""
        self._rate_limit()
        
        for attempt in range(Settings.RETRY_ATTEMPTS):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                
                # Set encoding to handle Unicode properly
                if response.encoding is None:
                    response.encoding = 'utf-8'
                
                return response                
            except (requests.RequestException, requests.HTTPError) as e:
                if attempt == Settings.RETRY_ATTEMPTS - 1:
                    raise
                
                # Exponential backoff
                delay = Settings.RETRY_DELAY * (Settings.RETRY_BACKOFF ** attempt)
                logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                time.sleep(delay)
        
        raise requests.RequestException(f"All {Settings.RETRY_ATTEMPTS} attempts failed")
        
    def _get_form_data(self, search_mode: str) -> Dict[str, str]:
        """Get ASP.NET form data including ViewState, cached per mode"""
        cache_key = f"tokens_{search_mode}"
        
        # Check if we have fresh tokens for this mode
        if cache_key in self._tokens:
            token_data, timestamp = self._tokens[cache_key]
            # Tokens are valid for ~20 minutes, refresh if older than 15 minutes
            if time.time() - timestamp < 900:  # 15 minutes
                return token_data
        
        try:
            url = f"{Settings.SEARCH_URL}?mode={search_mode}"
            response = self._safe_request('GET', url, timeout=Settings.REQUEST_TIMEOUT)            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract ASP.NET form data
            viewstate = soup.find('input', {'name': '__VIEWSTATE'})
            eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})
            
            token_data = {
                '__VIEWSTATE': viewstate['value'] if viewstate else '',
                '__EVENTVALIDATION': eventvalidation['value'] if eventvalidation else ''
            }
            
            # Cache tokens with timestamp
            self._tokens[cache_key] = (token_data, time.time())
            
            return token_data
            
        except Exception as e:
            logger.error(f"Failed to get form data for mode {search_mode}: {e}")
            return {'__VIEWSTATE': '', '__EVENTVALIDATION': ''}
    
    def _parse_property_results(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse property search results from HTML with enhanced error handling"""
        soup = BeautifulSoup(html_content, 'html.parser')
        properties = []        
        # Look for results table with multiple possible selectors
        results_table = (
            soup.find('table', class_='SearchResults') or 
            soup.find('table', id='SearchResults') or
            soup.find('table', {'class': re.compile(r'.*result.*', re.I)}) or
            soup.select_one('table[summary*="Search Results"]')
        )
        
        if not results_table:
            # Check for "no results" message
            no_results = soup.find(text=re.compile(r'no.*records.*found|no.*results', re.I))
            if no_results:
                logger.info("No results found for search")
            else:
                logger.warning("Could not locate results table in response")
            return []
        
        # Get header row to identify columns
        header_row = results_table.find('tr')
        headers = []
        if header_row:
            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]
        
        rows = results_table.find_all('tr')[1:]  # Skip header        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 2:  # Minimum viable data
                    continue
                
                # Flexible parsing based on available cells
                property_data = {
                    'search_timestamp': dt.datetime.utcnow().isoformat()
                }
                
                # Map columns based on position or header matching
                if len(cells) >= 1:
                    property_data['parcel_id'] = cells[0].get_text(strip=True)
                if len(cells) >= 2:
                    property_data['owner_name'] = cells[1].get_text(strip=True)
                if len(cells) >= 3:
                    property_data['property_address'] = cells[2].get_text(strip=True)
                if len(cells) >= 4:
                    property_data['tax_value'] = cells[3].get_text(strip=True)
                
                # Extract detail link if available
                detail_link = row.find('a', href=True)
                if detail_link:
                    href = detail_link['href']                    if href.startswith('/'):
                        property_data['detail_url'] = Settings.BASE_URL + href
                    elif not href.startswith('http'):
                        property_data['detail_url'] = Settings.BASE_URL + '/' + href
                    else:
                        property_data['detail_url'] = href
                
                properties.append(property_data)
                
            except Exception as e:
                logger.warning(f"Failed to parse result row: {e}")
                continue
        
        return properties
    
    def get_parcel_details(self, detail_url: str) -> Dict[str, Any]:
        """Scrape detailed property information from detail page"""
        try:
            response = self._safe_request('GET', detail_url, timeout=Settings.REQUEST_TIMEOUT)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            details = {
                'detail_url': detail_url,
                'scraped_timestamp': dt.datetime.utcnow().isoformat()
            }            
            # Parse property details table(s)
            for table in soup.find_all('table'):
                # Look for key-value pair tables
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) == 2:
                        key = cells[0].get_text(strip=True).rstrip(':').lower()
                        key = re.sub(r'[^a-z0-9]+', '_', key).strip('_')
                        val = cells[1].get_text(strip=True)
                        if key and val:
                            details[key] = val
            
            # Look for specific sections
            sections = ['assessment', 'ownership', 'property', 'tax', 'legal']
            for section in sections:
                section_div = soup.find('div', {'class': re.compile(f'.*{section}.*', re.I)})
                if section_div:
                    section_text = section_div.get_text(strip=True, separator=' ')
                    details[f'{section}_info'] = section_text[:500]  # Limit length
            
            return details
            
        except Exception as e:
            logger.error(f"Failed to scrape details from {detail_url}: {e}")            return {
                'detail_url': detail_url,
                'error': str(e),
                'scraped_timestamp': dt.datetime.utcnow().isoformat()
            }
    
    def search_by_owner(self, owner_name: str) -> List[Dict[str, Any]]:
        """Search properties by owner name"""
        form_data = self._get_form_data('owner')
        
        search_data = {
            **form_data,
            'ctl00$cphPage$txtOwner': owner_name,
            'ctl00$cphPage$btnSearch': 'Search'
        }
        
        response = self._safe_request(
            'POST',
            Settings.SEARCH_URL + "?mode=owner",
            data=search_data,
            timeout=Settings.REQUEST_TIMEOUT
        )
        
        return self._parse_property_results(response.text)
    
    def search_by_address(self, address: str) -> List[Dict[str, Any]]:        """Search properties by address"""
        form_data = self._get_form_data('address')
        
        search_data = {
            **form_data,
            'ctl00$cphPage$txtAddress': address,
            'ctl00$cphPage$btnSearch': 'Search'
        }
        
        response = self._safe_request(
            'POST',
            Settings.SEARCH_URL + "?mode=address",
            data=search_data,
            timeout=Settings.REQUEST_TIMEOUT
        )
        
        return self._parse_property_results(response.text)
    
    def search_by_parcel_id(self, parcel_id: str) -> List[Dict[str, Any]]:
        """Search property by parcel ID"""
        form_data = self._get_form_data('parid')
        
        search_data = {
            **form_data,
            'ctl00$cphPage$txtParID': parcel_id,
            'ctl00$cphPage$btnSearch': 'Search'
        }        
        response = self._safe_request(
            'POST',
            Settings.SEARCH_URL + "?mode=parid",
            data=search_data,
            timeout=Settings.REQUEST_TIMEOUT
        )
        
        return self._parse_property_results(response.text)

# Initialize FastMCP server
mcp = FastMCP("NHCPropertyTaxServer")

if Settings.API_KEY:
    mcp.add_middleware(HeaderAuthMiddleware, api_key=Settings.API_KEY)

# Create searcher instance per tool to avoid shared state issues
def get_searcher() -> PropertyTaxSearcher:
    """Get a fresh searcher instance for thread safety"""
    return PropertyTaxSearcher()

# MCP Tools with caching and enhanced error handling
@mcp.tool
@with_request_id
def search_property_by_owner(
    owner_name: str,
    ctx: Context | None = None
) -> Dict[str, Any]:    """Search New Hanover County properties by owner name"""
    
    # Check cache first
    if Settings.CACHE_ENABLED and owner_name in _owner_cache:
        ctx.logger.info(f"Returning cached results for owner: {owner_name}")
        return _owner_cache[owner_name]
    
    try:
        ctx.logger.info(f"Searching properties for owner: {owner_name}")
        
        searcher = get_searcher()
        results = searcher.search_by_owner(owner_name)
        
        # Apply result limit
        if len(results) > Settings.MAX_RESULTS:
            ctx.logger.warning(f"Results truncated from {len(results)} to {Settings.MAX_RESULTS}")
            results = results[:Settings.MAX_RESULTS]
        
        response = {
            "success": True,
            "search_type": "owner",
            "query": owner_name,
            "results_count": len(results),
            "properties": results,
            "truncated": len(results) == Settings.MAX_RESULTS,
            "timestamp": dt.datetime.utcnow().isoformat()
        }        
        # Cache the result
        if Settings.CACHE_ENABLED:
            _owner_cache[owner_name] = response
        
        return response
        
    except requests.HTTPError as e:
        ctx.logger.error(f"HTTP error in owner search: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "http_error",
            "status_code": getattr(e.response, 'status_code', None),
            "search_type": "owner",
            "query": owner_name
        }
    except Exception as e:
        ctx.logger.error(f"Owner search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "general_error",
            "search_type": "owner",
            "query": owner_name
        }
@mcp.tool
@with_request_id
def search_property_by_address(
    address: str,
    ctx: Context | None = None
) -> Dict[str, Any]:
    """Search New Hanover County properties by address"""
    
    # Check cache first
    if Settings.CACHE_ENABLED and address in _address_cache:
        ctx.logger.info(f"Returning cached results for address: {address}")
        return _address_cache[address]
    
    try:
        ctx.logger.info(f"Searching properties for address: {address}")
        
        searcher = get_searcher()
        results = searcher.search_by_address(address)
        
        # Apply result limit
        if len(results) > Settings.MAX_RESULTS:
            ctx.logger.warning(f"Results truncated from {len(results)} to {Settings.MAX_RESULTS}")
            results = results[:Settings.MAX_RESULTS]        
        response = {
            "success": True,
            "search_type": "address", 
            "query": address,
            "results_count": len(results),
            "properties": results,
            "truncated": len(results) == Settings.MAX_RESULTS,
            "timestamp": dt.datetime.utcnow().isoformat()
        }
        
        # Cache the result
        if Settings.CACHE_ENABLED:
            _address_cache[address] = response
        
        return response
        
    except requests.HTTPError as e:
        ctx.logger.error(f"HTTP error in address search: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "http_error",
            "status_code": getattr(e.response, 'status_code', None),
            "search_type": "address",
            "query": address
        }    except Exception as e:
        ctx.logger.error(f"Address search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "general_error",
            "search_type": "address",
            "query": address
        }

@mcp.tool
@with_request_id
def search_property_by_parcel_id(
    parcel_id: str,
    ctx: Context | None = None
) -> Dict[str, Any]:
    """Search New Hanover County property by parcel ID"""
    
    # Check cache first
    if Settings.CACHE_ENABLED and parcel_id in _parcel_cache:
        ctx.logger.info(f"Returning cached results for parcel ID: {parcel_id}")
        return _parcel_cache[parcel_id]
    
    try:
        ctx.logger.info(f"Searching property for parcel ID: {parcel_id}")
        
        searcher = get_searcher()
        results = searcher.search_by_parcel_id(parcel_id)        
        response = {
            "success": True,
            "search_type": "parcel_id",
            "query": parcel_id,
            "results_count": len(results),
            "properties": results,
            "timestamp": dt.datetime.utcnow().isoformat()
        }
        
        # Cache the result
        if Settings.CACHE_ENABLED:
            _parcel_cache[parcel_id] = response
        
        return response
        
    except requests.HTTPError as e:
        ctx.logger.error(f"HTTP error in parcel ID search: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "http_error",
            "status_code": getattr(e.response, 'status_code', None),
            "search_type": "parcel_id",
            "query": parcel_id
        }    except Exception as e:
        ctx.logger.error(f"Parcel ID search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "general_error",
            "search_type": "parcel_id",
            "query": parcel_id
        }

@mcp.tool
@with_request_id
def get_property_details(
    parcel_id: str,
    ctx: Context | None = None
) -> Dict[str, Any]:
    """Get detailed property information for a specific parcel ID"""
    
    # Check cache first
    if Settings.CACHE_ENABLED and parcel_id in _detail_cache:
        ctx.logger.info(f"Returning cached details for parcel ID: {parcel_id}")
        return _detail_cache[parcel_id]
    
    try:
        ctx.logger.info(f"Getting detailed information for parcel ID: {parcel_id}")
        
        # First search for the property to get its detail URL
        searcher = get_searcher()
        search_results = searcher.search_by_parcel_id(parcel_id)        
        if not search_results:
            return {
                "success": False,
                "error": "Property not found",
                "error_type": "not_found",
                "parcel_id": parcel_id
            }
        
        property_info = search_results[0]
        detail_url = property_info.get('detail_url')
        
        if not detail_url:
            return {
                "success": False,
                "error": "Detail URL not available",
                "error_type": "no_detail_url",
                "parcel_id": parcel_id,
                "basic_info": property_info
            }
        
        # Scrape detailed information
        details = searcher.get_parcel_details(detail_url)
        
        response = {
            "success": True,
            "parcel_id": parcel_id,
            "basic_info": property_info,            "detailed_info": details,
            "timestamp": dt.datetime.utcnow().isoformat()
        }
        
        # Cache the result
        if Settings.CACHE_ENABLED:
            _detail_cache[parcel_id] = response
        
        return response
        
    except requests.HTTPError as e:
        ctx.logger.error(f"HTTP error getting property details: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "http_error",
            "status_code": getattr(e.response, 'status_code', None),
            "parcel_id": parcel_id
        }
    except Exception as e:
        ctx.logger.error(f"Failed to get property details: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "general_error",
            "parcel_id": parcel_id
        }
@mcp.tool
@with_request_id
def check_system_status(
    ctx: Context | None = None
) -> Dict[str, Any]:
    """Check if the New Hanover County tax search system is available"""
    try:
        ctx.logger.info("Checking system status")
        
        searcher = get_searcher()
        response = searcher._safe_request(
            'GET',
            Settings.BASE_URL, 
            timeout=Settings.REQUEST_TIMEOUT
        )
        
        # Check for maintenance message and expected content
        content = response.text.lower()
        is_maintenance = "maintenance" in content
        has_property_system = "property" in content and ("tax" in content or "search" in content)
        title_check = "tax" in content or "property" in content
        
        is_available = (
            not is_maintenance and 
            response.status_code == 200 and 
            (has_property_system or title_check)
        )        
        return {
            "system_available": is_available,
            "status_code": response.status_code,
            "maintenance_mode": is_maintenance,
            "has_expected_content": has_property_system or title_check,
            "response_time_ms": response.elapsed.total_seconds() * 1000,
            "check_timestamp": dt.datetime.utcnow().isoformat()
        }
        
    except requests.HTTPError as e:
        ctx.logger.error(f"HTTP error in status check: {e}")
        return {
            "system_available": False,
            "error": str(e),
            "error_type": "http_error",
            "status_code": getattr(e.response, 'status_code', None),
            "check_timestamp": dt.datetime.utcnow().isoformat()
        }
    except Exception as e:
        ctx.logger.error(f"Status check failed: {e}")
        return {
            "system_available": False,
            "error": str(e),
            "error_type": "general_error",
            "check_timestamp": dt.datetime.utcnow().isoformat()
        }
@mcp.tool
def get_search_capabilities() -> Dict[str, Any]:
    """Get information about available search capabilities and configuration"""
    return {
        "search_types": [
            {
                "type": "owner",
                "description": "Search by property owner name",
                "parameters": ["owner_name"],
                "cached": Settings.CACHE_ENABLED
            },
            {
                "type": "address", 
                "description": "Search by property address",
                "parameters": ["address"],
                "cached": Settings.CACHE_ENABLED
            },
            {
                "type": "parcel_id",
                "description": "Search by parcel identification number", 
                "parameters": ["parcel_id"],
                "cached": Settings.CACHE_ENABLED
            },
            {
                "type": "property_details",
                "description": "Get detailed property information including assessments and ownership",
                "parameters": ["parcel_id"],
                "cached": Settings.CACHE_ENABLED
            }
        ],        "data_fields": [
            "parcel_id",
            "owner_name", 
            "property_address",
            "tax_value",
            "detail_url",
            "search_timestamp"
        ],
        "configuration": {
            "base_url": Settings.BASE_URL,
            "cache_enabled": Settings.CACHE_ENABLED,
            "cache_duration_hours": Settings.CACHE_DURATION_HOURS,
            "rate_limit_enabled": Settings.RATE_LIMIT_ENABLED,
            "rate_limit_delay": Settings.RATE_LIMIT_DELAY,
            "max_results": Settings.MAX_RESULTS,
            "retry_attempts": Settings.RETRY_ATTEMPTS
        },
        "system_info": "New Hanover County Property Tax Search v2.0"
    }

@mcp.tool
@with_request_id
def clear_cache(
    cache_type: str = "all",
    ctx: Context | None = None
) -> Dict[str, Any]:
    """Clear cached search results"""    
    if not Settings.CACHE_ENABLED:
        return {
            "success": False,
            "error": "Caching is disabled",
            "cache_enabled": False
        }
    
    try:
        ctx.logger.info(f"Clearing cache: {cache_type}")
        
        cleared_caches = []
        
        if cache_type in ["all", "owner"]:
            _owner_cache.clear()
            cleared_caches.append("owner")
        
        if cache_type in ["all", "address"]:
            _address_cache.clear()
            cleared_caches.append("address")
        
        if cache_type in ["all", "parcel"]:
            _parcel_cache.clear()
            cleared_caches.append("parcel")
        
        if cache_type in ["all", "detail"]:
            _detail_cache.clear()
            cleared_caches.append("detail")        
        return {
            "success": True,
            "cleared_caches": cleared_caches,
            "timestamp": dt.datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        ctx.logger.error(f"Failed to clear cache: {e}")
        return {
            "success": False,
            "error": str(e),
            "cache_type": cache_type
        }

if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.getenv("PORT", 8000))
    mcp.run(transport="http", host=host, port=port, path="/mcp")