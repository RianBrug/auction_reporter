import json
import logging
import os
from typing import Dict, Any, List

from src.llm.deepseek_client import DeepseekClient
from src.llm.auction_generator import AuctionGenerator
from src.models.auction import Auction
from src.config import DEFAULT_QUERY, LOG_LEVEL

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_auctions(query: str, location: str = "Brasil") -> List[Dict[str, Any]]:
    """
    Generate auction listings using LLM instead of web scraping
    
    Args:
        query: Search query
        location: Location context
        
    Returns:
        List of auction data
    """
    all_auctions = []
    
    try:
        # Initialize LLM client
        llm_client = DeepseekClient()
        
        # Create auction generator
        logger.info(f"Generating auction listings for '{query}' in {location}")
        generator = AuctionGenerator(llm_client=llm_client)
        auctions = generator.generate_auctions(query=query, location=location)
        
        # Convert to Auction objects and set source
        for auction_data in auctions:
            auction = Auction.from_dict(auction_data)
            all_auctions.append(auction.to_dict())
            
        logger.info(f"Generated {len(auctions)} auction listings for '{query}'")
        
    except Exception as e:
        logger.error(f"Error generating auctions: {str(e)}")
    
    return all_auctions

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function (LLM version)
    
    Args:
        event: Lambda event data
        context: Lambda context
        
    Returns:
        API Gateway compatible response
    """
    logger.info("Starting LLM-based auction generator")
    
    try:
        # Get search query from event or use default
        query = event.get('query', DEFAULT_QUERY)
        location = event.get('location', "Santa Catarina, Brasil")
        
        # Always enable LLM for this version
        os.environ['USE_LLM'] = 'true'
        
        logger.info(f"Generating auctions with query: {query} in {location}")
        
        auctions = generate_auctions(query, location)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'auctions': auctions,
                'count': len(auctions),
                'query': query,
                'location': location,
                'llm_generated': True
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