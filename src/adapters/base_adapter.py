import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from selenium import webdriver
from src.llm.deepseek_client import DeepseekClient

logger = logging.getLogger(__name__)

class BaseAuctionAdapter(ABC):
    """Base adapter for auction websites with common functionality"""
    
    def __init__(self, driver: webdriver.Chrome = None, llm_client: DeepseekClient = None):
        """
        Initialize the adapter
        
        Args:
            driver: Selenium WebDriver instance
            llm_client: DeepSeek client for LLM processing
        """
        self.driver = driver
        self.llm_client = llm_client
        self.name = self.__class__.__name__
    
    @abstractmethod
    def search(self, query: str, location: str = "Brasil") -> List[Dict[str, Any]]:
        """
        Search for auctions matching the query
        
        Args:
            query: Search term (e.g. "itapiruba")
            location: Location context
            
        Returns:
            List of auction data dictionaries
        """
        pass
    
    @abstractmethod
    def get_auction_details(self, auction_url: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific auction
        
        Args:
            auction_url: URL of the auction
            
        Returns:
            Dictionary with detailed auction information
        """
        pass
    
    def filter_relevant_auctions(self, auctions: List[Dict[str, Any]], query: str, 
                               location: str, confidence_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Use LLM to filter auctions for relevance to the query
        
        Args:
            auctions: List of auction data
            query: Original search query
            location: Location context
            confidence_threshold: Minimum confidence score for inclusion
            
        Returns:
            Filtered list of relevant auctions
        """
        if not self.llm_client:
            logger.warning("No LLM client configured, returning unfiltered auctions")
            return auctions
            
        relevant_auctions = []
        
        for auction in auctions:
            # Convert auction to string representation for LLM analysis
            auction_text = self._auction_to_text(auction)
            
            # Analyze relevance
            analysis = self.llm_client.analyze_auction_page(auction_text, query, location)
            
            is_relevant = analysis.get("is_relevant", False)
            confidence = analysis.get("confidence", 0)
            reason = analysis.get("reason", "No reason provided")
            
            # Add analysis metadata to the auction
            auction["relevance"] = {
                "is_relevant": is_relevant,
                "confidence": confidence,
                "reason": reason
            }
            
            # Filter based on relevance and confidence
            if is_relevant and confidence >= confidence_threshold:
                logger.info(f"Auction deemed relevant: {auction.get('title')} (confidence: {confidence})")
                relevant_auctions.append(auction)
            else:
                logger.info(f"Auction filtered out: {auction.get('title')} (confidence: {confidence})")
                
        return relevant_auctions
    
    def enrich_auction_data(self, auction: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Use LLM to enhance auction data with additional insights
        
        Args:
            auction: Original auction data
            query: Original search query
            
        Returns:
            Enhanced auction data
        """
        if not self.llm_client or "html_content" not in auction:
            return auction
            
        # Extract structured data from HTML using LLM
        enhanced_data = self.llm_client.extract_auction_data(auction["html_content"], query)
        
        # Merge the enhanced data with original auction data
        # Original data takes precedence over LLM extraction
        merged_auction = {**enhanced_data, **auction}
        
        return merged_auction
    
    def _auction_to_text(self, auction: Dict[str, Any]) -> str:
        """Convert auction dictionary to text for LLM analysis"""
        if "html_content" in auction:
            return auction["html_content"]
            
        # Fall back to string representation of the auction data
        text = []
        for key, value in auction.items():
            text.append(f"{key}: {value}")
            
        return "\n".join(text) 