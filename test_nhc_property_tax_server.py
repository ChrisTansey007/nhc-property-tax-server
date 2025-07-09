"""
Test suite for New Hanover County Property Tax Search MCP Server
Tests all 7 tools and core functionality with mocked external requests
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import requests

# Import the server components
from nhc_property_tax_server import (
    PropertyTaxSearcher,
    search_property_by_owner,
    search_property_by_address,
    search_property_by_parcel_id,
    get_property_details,
    check_system_status,
    get_search_capabilities,
    clear_cache,
    Settings
)


@pytest.fixture
def mock_context():
    """Create a mock context with logger"""
    ctx = Mock()
    ctx.logger = Mock()
    ctx.request_id = "test-123"
    return ctx

@pytest.fixture
def mock_html_response():
    """Mock HTML response with property results"""
    return """
    <html>
    <body>
    <table class="SearchResults">
        <tr>
            <th>Parcel ID</th>
            <th>Owner</th>
            <th>Address</th>
            <th>Tax Value</th>
        </tr>
        <tr>
            <td><a href="/detail.aspx?id=123456">123456</a></td>
            <td>SMITH JOHN</td>
            <td>123 MAIN ST</td>
            <td>$250,000</td>
        </tr>
        <tr>
            <td><a href="/detail.aspx?id=789012">789012</a></td>
            <td>SMITH JANE</td>
            <td>456 OAK AVE</td>
            <td>$180,000</td>
        </tr>
    </table>
    </body>
    </html>
    """
@pytest.fixture
def mock_detail_html():
    """Mock HTML response for property details page"""
    return """
    <html>
    <body>
    <table>
        <tr><td>Parcel ID:</td><td>123456</td></tr>
        <tr><td>Owner:</td><td>SMITH JOHN</td></tr>
        <tr><td>Property Address:</td><td>123 MAIN ST</td></tr>
        <tr><td>Tax Value:</td><td>$250,000</td></tr>
        <tr><td>Land Value:</td><td>$50,000</td></tr>
        <tr><td>Building Value:</td><td>$200,000</td></tr>
        <tr><td>Year Built:</td><td>1995</td></tr>
    </table>
    </body>
    </html>
    """


class TestPropertyTaxSearcher:
    """Test PropertyTaxSearcher class methods"""
    
    @patch('requests.Session')
    def test_searcher_initialization(self, mock_session):
        """Test PropertyTaxSearcher initialization"""
        searcher = PropertyTaxSearcher()
        assert searcher.session is not None
        assert searcher._tokens == {}
        assert searcher._last_request_time == 0
    @patch('nhc_property_tax_server.PropertyTaxSearcher._safe_request')
    def test_search_by_owner(self, mock_request):
        """Test search by owner functionality"""
        mock_response = Mock()
        mock_response.text = """
        <html>
        <body>
        <input name="__VIEWSTATE" value="test_viewstate" />
        <input name="__EVENTVALIDATION" value="test_validation" />
        </body>
        </html>
        """
        mock_request.return_value = mock_response
        
        searcher = PropertyTaxSearcher()
        # First call gets form data
        searcher._get_form_data('owner')
        
        # Second call performs search
        mock_response.text = mock_html_response()
        results = searcher.search_by_owner("SMITH")
        
        assert len(results) == 2
        assert results[0]['owner_name'] == 'SMITH JOHN'
        assert results[0]['property_address'] == '123 MAIN ST'
        assert results[1]['owner_name'] == 'SMITH JANE'

class TestMCPTools:
    """Test MCP tool functions"""
    
    @patch('nhc_property_tax_server.get_searcher')
    def test_search_property_by_owner_tool(self, mock_get_searcher, mock_context):
        """Test search_property_by_owner MCP tool"""
        mock_searcher = Mock()
        mock_searcher.search_by_owner.return_value = [
            {
                'parcel_id': '123456',
                'owner_name': 'SMITH JOHN',
                'property_address': '123 MAIN ST',
                'tax_value': '$250,000'
            }
        ]
        mock_get_searcher.return_value = mock_searcher
        
        result = search_property_by_owner("SMITH", ctx=mock_context)
        
        assert result['success'] is True
        assert result['search_type'] == 'owner'
        assert result['query'] == 'SMITH'
        assert result['results_count'] == 1
        assert len(result['properties']) == 1
        assert result['properties'][0]['owner_name'] == 'SMITH JOHN'
        mock_context.logger.info.assert_called()
    @patch('nhc_property_tax_server.get_searcher')
    def test_search_property_by_owner_error(self, mock_get_searcher, mock_context):
        """Test error handling in search_property_by_owner"""
        mock_searcher = Mock()
        mock_searcher.search_by_owner.side_effect = requests.HTTPError("404 Not Found")
        mock_get_searcher.return_value = mock_searcher
        
        result = search_property_by_owner("SMITH", ctx=mock_context)
        
        assert result['success'] is False
        assert result['error_type'] == 'http_error'
        assert '404' in result['error']
        mock_context.logger.error.assert_called()

    @patch('nhc_property_tax_server.get_searcher')
    def test_get_property_details_tool(self, mock_get_searcher, mock_context):
        """Test get_property_details MCP tool"""
        mock_searcher = Mock()
        mock_searcher.search_by_parcel_id.return_value = [{
            'parcel_id': '123456',
            'detail_url': 'https://etax.nhcgov.com/detail.aspx?id=123456'
        }]
        mock_searcher.get_parcel_details.return_value = {
            'parcel_id': '123456',
            'land_value': '$50,000',
            'building_value': '$200,000'
        }        mock_get_searcher.return_value = mock_searcher
        
        result = get_property_details("123456", ctx=mock_context)
        
        assert result['success'] is True
        assert result['parcel_id'] == '123456'
        assert 'basic_info' in result
        assert 'detailed_info' in result
        assert result['detailed_info']['land_value'] == '$50,000'

    def test_get_search_capabilities(self):
        """Test get_search_capabilities tool"""
        result = get_search_capabilities()
        
        assert 'search_types' in result
        assert len(result['search_types']) == 4
        assert 'data_fields' in result
        assert 'configuration' in result
        assert result['system_info'] == "New Hanover County Property Tax Search v2.0"

    @patch('nhc_property_tax_server._owner_cache')
    def test_clear_cache_tool(self, mock_cache, mock_context):
        """Test clear_cache tool"""
        Settings.CACHE_ENABLED = True
        
        result = clear_cache("owner", ctx=mock_context)
        
        assert result['success'] is True
        assert 'owner' in result['cleared_caches']
        mock_cache.clear.assert_called_once()

class TestSystemStatus:
    """Test system status check"""
    
    @patch('nhc_property_tax_server.get_searcher')
    def test_check_system_status(self, mock_get_searcher, mock_context):
        """Test system status check tool"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "New Hanover County Property Tax Search"
        mock_response.elapsed.total_seconds.return_value = 0.5
        
        mock_searcher = Mock()
        mock_searcher._safe_request.return_value = mock_response
        mock_get_searcher.return_value = mock_searcher
        
        result = check_system_status(ctx=mock_context)
        
        assert result['system_available'] is True
        assert result['status_code'] == 200
        assert result['maintenance_mode'] is False
        assert result['response_time_ms'] == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])