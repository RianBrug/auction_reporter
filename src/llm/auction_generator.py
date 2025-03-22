import json
import logging
import os
from typing import List, Dict, Any, Optional

from src.llm.deepseek_client import DeepseekClient
from src.config import get_location_config, LOCATIONS

logger = logging.getLogger(__name__)

class AuctionGenerator:
    """
    LLM-based auction generator that returns property auctions based on a query
    without scraping websites. This uses the LLM to generate realistic auction data
    that matches what the scraper would have found.
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or DeepseekClient()
    
    def generate_auctions(self, query: str, location: str) -> List[Dict[str, Any]]:
        """
        Generate auction results based on the query and location
        
        Args:
            query: Search query (e.g. "itapiruba")
            location: Location context (e.g. "Santa Catarina, Brasil")
            
        Returns:
            List of generated auction data dictionaries
        """
        logger.info(f"Generating auctions for query: {query} in {location}")
        
        # Get location configuration
        location_config = get_location_config(query)
        location_name = location_config.get("name", query)
        state = location_config.get("state", "")
        
        prompt = self._build_auction_generation_prompt(query, location_name, state)
        
        try:
            response = self.llm_client._call_api(prompt)
            generated_data = self._parse_generated_auctions(response)
            
            # Add source and other metadata
            for auction in generated_data:
                auction['source'] = 'llm_generated'
                auction['generated'] = True
                
                # Ensure required fields are present
                if 'url' not in auction:
                    auction['url'] = f"https://www.example.com/auction/{hash(auction.get('title', ''))}"
                
                if 'images' not in auction or not auction['images']:
                    auction['images'] = [
                        "https://centralsuldeleiloes.blob.core.windows.net/imagens/FOTOS_DIVERSAS/GENERICAS/generica-imovel.jpg"
                    ]
            
            logger.info(f"Generated {len(generated_data)} auctions for {query}")
            return generated_data
            
        except Exception as e:
            logger.error(f"Error generating auctions: {str(e)}")
            return []
    
    def _build_auction_generation_prompt(self, query: str, location_name: str, state: str) -> List[Dict[str, str]]:
        """Build prompt for auction generation"""
        return [
            {"role": "system", "content": 
                f"""You are an expert in Brazilian real estate auctions, especially properties in {location_name}, {state}.
                You have access to the Central Sul Leiloes database and can provide current auction listings.
                Provide realistic and accurate data about properties that would be available in auctions.
                Your results should look exactly like what would be returned from the actual website.
                """
            },
            {"role": "user", "content": 
                f"""Generate 3-5 realistic auction listings for properties in {query}.
                These should be representative of what's typically available on centralsuldeleiloes.com.br.
                
                Focus on properties in {location_name}, {state}.
                Include realistic details like:
                - Realistic property titles and descriptions (in Portuguese)
                - Evaluation prices (~R$ 100k-5M for properties)
                - Minimum bids (usually 40-60% of evaluation)
                - Auction status (e.g. "Aberto", "Encerrado")
                - Realistic auction dates
                
                Return a JSON array with these fields for each auction:
                - title: Property title
                - description: Detailed description
                - evaluation: Evaluation price (formatted as "R$ XXX.XXX,XX")
                - minimum_bid: Minimum bid price (formatted as "R$ XXX.XXX,XX")
                - status: Auction status
                - auction_title: Title of the auction event
                - url: Link to the auction (can be example.com)
                - images: Array of image URLs (can be placeholder URLs)
                """
            }
        ]
    
    def _parse_generated_auctions(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse the LLM API response to extract generated auctions"""
        try:
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "[]")
            return json.loads(content)
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.error(f"Error parsing generated auctions: {str(e)}")
            return [] 