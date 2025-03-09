import json
import logging
import os
from typing import Dict, Any, List

from src.utils.driver_factory import get_chrome_driver, close_driver
from src.adapters.central_sul_adapter import CentralSulAdapter
from src.llm.deepseek_client import DeepseekClient
from src.models.auction import Auction
from src.config import DEFAULT_QUERY, LOG_LEVEL

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def search_all_sources(query: str, location: str = "Brasil") -> List[Dict[str, Any]]:
    """
    Search for auctions across all configured sources
    
    Args:
        query: Search query
        location: Location context
        
    Returns:
        List of auction data
    """
    driver = None
    all_auctions = []
    
    try:
        driver = get_chrome_driver()
        
        # Initialize LLM client if API key is available
        llm_client = DeepseekClient()
        
        # CentralSul search
        try:
            logger.info(f"Searching CentralSul Leiloes for '{query}'")
            adapter = CentralSulAdapter(driver=driver, llm_client=llm_client)
            auctions = adapter.search(query=query, location=location)
            
            # Convert to Auction objects and set source
            for auction_data in auctions:
                auction_data['source'] = 'central_sul'
                auction = Auction.from_dict(auction_data)
                all_auctions.append(auction.to_dict())
                
            logger.info(f"Found {len(auctions)} relevant auctions from CentralSul")
        except Exception as e:
            logger.error(f"Error searching CentralSul: {str(e)}")
        
        # Add more sources here as needed
        # Example:
        # try:
        #     logger.info(f"Searching Another Source for '{query}'")
        #     adapter = AnotherSourceAdapter(driver=driver, llm_client=llm_client)
        #     auctions = adapter.search(query=query, location=location) 
        #     ...
        # except Exception as e:
        #     logger.error(f"Error searching Another Source: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error during auction search: {str(e)}")
    finally:
        close_driver(driver)
    
    return all_auctions

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function
    
    Args:
        event: Lambda event data
        context: Lambda context
        
    Returns:
        API Gateway compatible response
    """
    logger.info("Starting auction crawler")
    
    try:
        # Get search query from event or use default
        query = event.get('query', DEFAULT_QUERY)
        location = event.get('location', "Santa Catarina, Brasil")
        
        # Set environment variables from config or event
        # Default to disabled LLM to avoid API errors
        os.environ['USE_LLM'] = str(event.get('use_llm', False)).lower()
        os.environ['FETCH_DESCRIPTIONS'] = str(event.get('fetch_descriptions', True)).lower()
        
        # Always enable deduplication
        os.environ['DEDUPLICATE'] = 'true'
        
        logger.info(f"Searching for auctions with query: {query} in {location}")
        logger.info(f"LLM enabled: {os.environ['USE_LLM']}, Descriptions enabled: {os.environ['FETCH_DESCRIPTIONS']}")
        
        auctions = search_all_sources(query, location)
        
        # Apply deduplication at the top level to ensure no duplicates
        unique_auctions = {}
        for auction in auctions:
            url = auction.get('url')
            if url and url not in unique_auctions:
                unique_auctions[url] = auction
        
        # Convert back to list
        deduplicated_auctions = list(unique_auctions.values())
        if len(deduplicated_auctions) != len(auctions):
            logger.info(f"Final deduplication: {len(auctions)} -> {len(deduplicated_auctions)}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'auctions': deduplicated_auctions,
                'count': len(deduplicated_auctions),
                'query': query,
                'location': location
            }, ensure_ascii=False)
        }
    except Exception as e:
        logger.error(f"Error in lambda execution: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e)
            })
        }
