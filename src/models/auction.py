from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

@dataclass
class Auction:
    """Data model for an auction item"""
    
    title: str
    url: str
    auction_title: str = ""
    auction_url: str = ""
    description: str = ""
    evaluation: Optional[str] = None
    minimum_bid: Optional[str] = None
    current_bid: Optional[str] = None
    next_session: Optional[str] = None
    closing_at: Optional[str] = None
    status: Optional[str] = None
    images: List[str] = field(default_factory=list)
    source: str = ""
    location: Optional[str] = None
    relevance: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Auction':
        """Create an Auction object from a dictionary"""
        # Copy the data to avoid modifying the original
        auction_data = data.copy()
        
        # Extract any fields that don't match the constructor
        metadata = {}
        for key in list(auction_data.keys()):
            if key not in cls.__annotations__ and key != 'images':
                metadata[key] = auction_data.pop(key)
        
        # Ensure images is a list
        if 'images' in auction_data and not isinstance(auction_data['images'], list):
            if auction_data['images'] is None:
                auction_data['images'] = []
            else:
                auction_data['images'] = [auction_data['images']]
        
        # Handle image_url field
        if 'image_url' in auction_data and auction_data['image_url']:
            if 'images' not in auction_data or not auction_data['images']:
                auction_data['images'] = [auction_data['image_url']]
            else:
                auction_data['images'].append(auction_data['image_url'])
            auction_data.pop('image_url')
        
        # Set the metadata field
        auction_data['metadata'] = metadata
        
        return cls(**auction_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the auction to a dictionary"""
        result = {
            'title': self.title,
            'url': self.url,
            'auction_title': self.auction_title,
            'auction_url': self.auction_url,
            'description': self.description,
            'evaluation': self.evaluation,
            'minimum_bid': self.minimum_bid,
            'current_bid': self.current_bid,
            'next_session': self.next_session,
            'closing_at': self.closing_at,
            'status': self.status,
            'images': self.images,
            'source': self.source,
            'location': self.location,
            'relevance': self.relevance,
            'created_at': self.created_at.isoformat(),
        }
        
        # Add metadata fields
        for key, value in self.metadata.items():
            if key not in result:
                result[key] = value
                
        return result
    
    def to_json(self) -> str:
        """Convert the auction to a JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
        
    def __str__(self) -> str:
        """String representation of the auction"""
        return f"{self.title} ({self.evaluation}) - {self.url}" 