import json
import requests
import logging
from src.config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL

logger = logging.getLogger(__name__)

class DeepseekClient:
    """Client for interacting with DeepSeek LLM API"""
    
    def __init__(self, api_key=None, model=None, api_url=None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.model = model or DEEPSEEK_MODEL
        self.api_url = api_url or DEEPSEEK_API_URL
        
        if not self.api_key:
            logger.warning("DeepSeek API key not provided. LLM functionality will be limited.")
    
    def analyze_auction_page(self, page_content, query, location):
        """
        Analyze auction page content to identify relevant properties.
        
        Args:
            page_content (str): HTML or text content from the auction page
            query (str): Search query (e.g., "itapiruba")
            location (str): Location context (e.g., "Santa Catarina, Brazil")
            
        Returns:
            dict: Processed auction data and analysis
        """
        if not self.api_key:
            logger.warning("DeepSeek API not configured. Returning content without analysis.")
            return {"error": "API not configured", "is_relevant": None}
            
        prompt = self._build_auction_analysis_prompt(page_content, query, location)
        
        try:
            response = self._call_api(prompt)
            return self._parse_llm_response(response)
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {str(e)}")
            return {"error": str(e), "is_relevant": None}
    
    def extract_auction_data(self, auction_html, query):
        """
        Extract structured auction data from HTML content
        
        Args:
            auction_html (str): HTML content of an auction listing
            query (str): Original search query
            
        Returns:
            dict: Structured auction data
        """
        if not self.api_key:
            logger.warning("DeepSeek API not configured. Returning empty extraction.")
            return {}
            
        prompt = self._build_data_extraction_prompt(auction_html, query)
        
        try:
            response = self._call_api(prompt)
            return self._parse_extracted_data(response)
        except Exception as e:
            logger.error(f"Error extracting auction data: {str(e)}")
            return {}
    
    def _build_auction_analysis_prompt(self, content, query, location):
        """Build prompt for auction relevance analysis"""
        return [
            {"role": "system", "content": 
                f"""You are an expert in real estate auctions in Brazil.
                Your task is to analyze auction listings and determine if they are relevant to a search query.
                Focus specifically on whether the property is located in or near {query} in {location}.
                The user will provide auction content, and you must determine if it's relevant."""
            },
            {"role": "user", "content": 
                f"""Analyze this auction content and determine if it relates to a property in or near {query}.
                Provide your response as JSON with these fields:
                - is_relevant: true/false
                - confidence: number from 0-1
                - reason: brief explanation of your decision
                
                Auction content:
                {content[:8000]}  # Limiting content length to avoid token limits
                """
            }
        ]
    
    def _build_data_extraction_prompt(self, auction_html, query):
        """Build prompt for auction data extraction"""
        return [
            {"role": "system", "content": 
                """You are an expert in extracting structured data from auction listings.
                Parse the provided HTML/text and extract key information about the auction property.
                Provide a clean JSON output with the extracted fields."""
            },
            {"role": "user", "content": 
                f"""Extract all relevant information from this auction listing about a property in {query}.
                Return a JSON object with these fields if found:
                - title
                - description
                - price (evaluation price)
                - minimum_bid
                - auction_date
                - auction_title
                - location
                - images
                - url
                
                HTML Content:
                {auction_html[:8000]}  # Limiting content length to avoid token limits
                """
            }
        ]
    
    def _call_api(self, messages):
        """Make a call to the DeepSeek API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"}  # Request JSON output
        }
        
        response = requests.post(self.api_url, headers=headers, json=payload)
        response.raise_for_status()
        
        return response.json()
    
    def _parse_llm_response(self, response):
        """Parse the LLM API response"""
        try:
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            return json.loads(content)
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return {"error": "Failed to parse response", "is_relevant": None}
    
    def _parse_extracted_data(self, response):
        """Parse the data extraction API response"""
        try:
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            return json.loads(content)
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.error(f"Error parsing extracted data: {str(e)}")
            return {} 