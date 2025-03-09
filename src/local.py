import logging
import json
import argparse
import sys
import os

# Add the parent directory to sys.path to allow importing the package modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.lambda_function import lambda_handler
from src.config import DEFAULT_QUERY, LOCATIONS

def setup_logging(debug=False):
    """Configure logging based on debug flag"""
    level = logging.DEBUG if debug else logging.INFO
    
    # Configure logging to output to terminal
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Set specific loggers to DEBUG if requested
    if debug:
        logging.getLogger('src.adapters').setLevel(logging.DEBUG)
        logging.getLogger('src.llm').setLevel(logging.DEBUG)
        logging.getLogger('src.utils').setLevel(logging.DEBUG)
    
    return logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Auction Crawler CLI')
    parser.add_argument('-q', '--query', type=str, default=DEFAULT_QUERY,
                        help=f'Search query (default: {DEFAULT_QUERY})')
    parser.add_argument('-l', '--location', type=str, default="Santa Catarina, Brasil",
                        help='Location context (default: "Santa Catarina, Brasil")')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--no-headless', action='store_true',
                        help='Disable headless browser mode (shows browser UI)')
    parser.add_argument('--use-llm', action='store_true',
                        help='Enable LLM for filtering and analysis (requires API key)')
    parser.add_argument('--no-descriptions', action='store_true',
                        help='Disable fetching detailed descriptions')
    parser.add_argument('--deduplicate', action='store_true',
                        help='Deduplicate auction results')
    parser.add_argument('--list-locations', action='store_true',
                        help='List supported locations')
    return parser.parse_args()

def print_colored(text, color=None):
    """Print colored text in terminal"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'bold': '\033[1m',
        'underline': '\033[4m',
        'end': '\033[0m'
    }
    
    if color and color in colors:
        print(f"{colors[color]}{text}{colors['end']}")
    else:
        print(text)

if __name__ == "__main__":
    args = parse_args()
    
    # If list locations was requested, show them and exit
    if args.list_locations:
        print("\nSupported Locations:\n")
        for location_id, config in LOCATIONS.items():
            print(f"  {location_id:<18} - {config['name']}/{config['state']}")
        print("\nYou can also use other locations not in this list.\n")
        sys.exit(0)
    
    # Set up logging based on debug flag
    logger = setup_logging(args.debug)
    
    # Set environment variables based on command-line flags
    if args.no_headless:
        os.environ['HEADLESS_BROWSER'] = 'false'
    
    if args.use_llm:
        os.environ['USE_LLM'] = 'true'
    
    if args.no_descriptions:
        os.environ['FETCH_DESCRIPTIONS'] = 'false'
    
    logger.info(f"Starting auction crawler with query: {args.query} in {args.location}")
    
    if args.debug:
        logger.debug("Debug mode enabled - showing detailed logs")
    
    if args.use_llm:
        logger.info("LLM filtering enabled")
    
    # Call the lambda handler with event and context
    event = {
        'query': args.query,
        'location': args.location,
        'use_llm': args.use_llm,
        'fetch_descriptions': not args.no_descriptions,
        'deduplicate': args.deduplicate
    }
    
    result = lambda_handler(event, None)
    
    # Pretty print the results
    status_code = result.get('statusCode')
    body = json.loads(result.get('body', '{}'))
    
    if status_code == 200:
        auctions = body.get('auctions', [])
        count = body.get('count', 0)
        
        logger.info(f"Found {count} auctions for query '{args.query}'")
        
        if count > 0:
            print("\n" + "="*50)
            print_colored(f"SEARCH RESULTS FOR: {args.query}", "green")
            print("="*50)
            
            for i, auction in enumerate(auctions, 1):
                print(f"\n{i}. ", end="")
                print_colored(auction.get('title', 'Unknown Title'), "bold")
                
                if auction.get('evaluation'):
                    print_colored(f"   Evaluation: {auction.get('evaluation')}", "cyan")
                
                if auction.get('minimum_bid'):
                    print_colored(f"   Minimum Bid: {auction.get('minimum_bid')}", "yellow")
                
                if auction.get('status'):
                    print(f"   Status: {auction.get('status')}")
                
                if auction.get('description'):
                    print(f"   Description: {auction.get('description')}")
                
                print(f"   URL: {auction.get('url')}")
                
                # Display relevance if available
                relevance = auction.get('relevance', {})
                if relevance:
                    confidence = relevance.get('confidence', 0)
                    reason = relevance.get('reason', '')
                    print(f"   Relevance: {confidence:.2f} - {reason}")
                
                print("-"*50)
                
            print("\nScreenshot saved to 'search_results.png'")
        else:
            print_colored("\nNo auctions found matching your criteria.", "yellow")
            print("This could be because:")
            print("1. There are no auctions in this area currently")
            print("2. The search term may need to be adjusted")
            print("3. The website structure may have changed")
            
            if args.debug:
                print("\nCheck the screenshot at 'search_results.png' to see what was loaded.")
    else:
        error = body.get('error', 'Unknown error')
        print_colored(f"\nError: {error}", "red")
        print("Check the logs for more details.") 