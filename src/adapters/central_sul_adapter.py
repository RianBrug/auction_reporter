import logging
import time
import json
import requests
import os
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

from src.adapters.base_adapter import BaseAuctionAdapter
from src.config import SELENIUM_WAIT_TIME, get_location_config, LOCATIONS

logger = logging.getLogger(__name__)

class CentralSulAdapter(BaseAuctionAdapter):
    """Adapter for Central Sul Leiloes website"""
    
    def __init__(self, driver=None, llm_client=None):
        super().__init__(driver, llm_client)
        self.base_url = "https://www.centralsuldeleiloes.com.br/leiloes"
        self.api_url = "https://www.centralsuldeleiloes.com.br/api/v2/web/search/lot"
        self.auth_token = None
        self.io_cookie = None
    
    def search(self, query: str, location: str = "Santa Catarina, Brasil") -> List[Dict[str, Any]]:
        """
        Search for auctions matching the query using direct API first, with Selenium as fallback
        
        Args:
            query: Search term (e.g. "itapiruba")
            location: Location context
            
        Returns:
            List of auction data dictionaries
        """
        auctions = []
        
        try:
            # Try Selenium approach directly (API approach requires authentication)
            logger.info("Using Selenium approach for search...")
            raw_auctions = self._selenium_search(query)
            
            # Deduplicate auctions
            auctions = self._deduplicate_auctions(raw_auctions)
            
            # Filter auctions
            auctions = self._filter_auctions(auctions, query)
            
            # Fetch descriptions if needed
            if auctions and os.getenv("FETCH_DESCRIPTIONS", "true").lower() == "true":
                auctions = self._fetch_descriptions(auctions)
                
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
        
        return auctions
    
    def _deduplicate_auctions(self, auctions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate auctions by URL"""
        # Use a dictionary to deduplicate
        unique_auctions = {}
        for auction in auctions:
            url = auction.get('url')
            if url and url not in unique_auctions:
                unique_auctions[url] = auction
        
        # Convert back to list
        result = list(unique_auctions.values())
        logger.info(f"Deduplicated from {len(auctions)} to {len(result)} unique auctions")
        return result
    
    def _fetch_descriptions(self, auctions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fetch detailed descriptions for auctions"""
        logger.info("Fetching detailed descriptions for filtered auctions...")
        
        for auction in auctions:
            if auction.get('description') in [None, "", "Clique para ver a descrição completa do lote"]:
                try:
                    # Fetch detailed auction information
                    auction_url = auction.get('url')
                    if auction_url:
                        details = self.get_auction_details(auction_url)
                        if details and details.get('description'):
                            auction['description'] = details.get('description')
                            logger.info(f"Updated description for auction: {auction.get('title')}")
                except Exception as e:
                    logger.error(f"Error fetching detailed description: {str(e)}")
        
        return auctions
    
    def _api_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Use direct API call to search for auctions
        """
        try:
            # First need to visit the page to get tokens
            logger.info(f"Navigating to {self.base_url} to extract authentication tokens...")
            self.driver.get(self.base_url)
            time.sleep(3)
            
            # Extract auth token and cookies
            self._extract_auth_tokens()
            
            if not self.auth_token:
                logger.warning("Failed to extract authorization token, API search will likely fail")
            
            # Prepare headers
            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'en-US,en;q=0.7',
                'content-type': 'application/json',
                'origin': 'https://www.centralsuldeleiloes.com.br',
                'referer': 'https://www.centralsuldeleiloes.com.br/leiloes',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
            }
            
            # Add auth token if available
            if self.auth_token:
                headers['authorization'] = f'Bearer {self.auth_token}'
            
            # Prepare cookies
            cookies = {}
            if self.io_cookie:
                cookies['io'] = self.io_cookie
            
            # Prepare payload
            payload = {
                "query": query,
                "city_slug": None,
                "category_slug": None
            }
            
            # Make API request
            logger.info(f"Making API request with query: {query}")
            response = requests.post(
                self.api_url,
                headers=headers,
                cookies=cookies,
                json=payload
            )
            
            # Check response
            if response.status_code != 200:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return []
            
            # Parse response
            try:
                data = response.json()
                logger.info(f"API returned {len(data.get('data', []))} results")
                
                # Save the raw response for debugging
                with open("api_response.json", "w") as f:
                    json.dump(data, f, indent=2)
                
                # Convert API response to our auction format
                raw_auctions = self._api_response_to_auctions(data)
                
                # Apply filtering
                return self._filter_auctions(raw_auctions, query)
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse API response as JSON: {response.text[:100]}...")
                return []
                
        except Exception as e:
            logger.error(f"Error in API search: {str(e)}")
            return []
    
    def _extract_auth_tokens(self):
        """Extract authorization token and cookies needed for API requests"""
        # Method 1: Extract from localStorage (works for authorization token)
        try:
            # Extract the token using JavaScript
            local_storage = self.driver.execute_script("return window.localStorage;")
            
            # Look for token in localStorage
            if local_storage.get('user'):
                user_data = json.loads(local_storage.get('user'))
                if user_data.get('token'):
                    self.auth_token = user_data.get('token')
                    logger.info("Successfully extracted auth token from localStorage")
            
            # If not found in localStorage, try looking for it in network requests
            if not self.auth_token:
                # Extract from any script tags
                script_tags = self.driver.find_elements(By.TAG_NAME, "script")
                for script in script_tags:
                    script_content = script.get_attribute("innerHTML")
                    if "Bearer" in script_content:
                        import re
                        # Look for Bearer token pattern
                        token_match = re.search(r'Bearer\s+([A-Za-z0-9|]+)', script_content)
                        if token_match:
                            self.auth_token = token_match.group(1)
                            logger.info("Successfully extracted auth token from script tag")
                            break
        except Exception as e:
            logger.warning(f"Error extracting auth token: {str(e)}")
        
        # Extract cookies
        try:
            cookies = self.driver.get_cookies()
            for cookie in cookies:
                if cookie['name'] == 'io':
                    self.io_cookie = cookie['value']
                    logger.info("Successfully extracted io cookie")
                    break
        except Exception as e:
            logger.warning(f"Error extracting cookies: {str(e)}")
    
    def _api_response_to_auctions(self, api_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert API response to our auction format"""
        raw_auctions = []
        
        try:
            lots = api_data.get('data', [])
            for lot in lots:
                auction_data = {
                    'title': lot.get('title', 'Unknown Title'),
                    'url': f"https://www.centralsuldeleiloes.com.br/lote/{lot.get('slug')}",
                    'description': lot.get('description', ''),
                    'evaluation': lot.get('evaluation_formated', None),
                    'minimum_bid': lot.get('minimum_bid_formated', None),
                    'current_bid': lot.get('bid_formated', None),
                    'closing_at': lot.get('closing_at', None),
                    'status': lot.get('status', None),
                    'auction_title': lot.get('auction', {}).get('title', ''),
                    'auction_url': f"https://www.centralsuldeleiloes.com.br/leilao/{lot.get('auction', {}).get('slug')}",
                    'images': [img.get('url') for img in lot.get('images', [])],
                    'html_content': json.dumps(lot),  # Store the raw JSON for LLM analysis
                    'api_data': lot,  # Keep the original API data
                }
                raw_auctions.append(auction_data)
        except Exception as e:
            logger.error(f"Error converting API response to auctions: {str(e)}")
        
        return raw_auctions
    
    def _selenium_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Use Selenium to search for auctions with the given query
        
        Args:
            query: Search query (e.g., "itapiruba", "florianopolis")
            
        Returns:
            List of auction data dictionaries
        """
        raw_auctions = []
        
        try:
            # First navigate to the base URL
            logger.info(f"Navigating to {self.base_url}")
            self.driver.get(self.base_url)
            
            # Wait for the page to load
            logger.info("Waiting for page to load...")
            time.sleep(3)
            
            # Take a screenshot before search
            try:
                screenshot_name = f"before_search_{query.replace(' ', '_')}.png"
                self.driver.save_screenshot(screenshot_name)
                logger.info(f"Saved screenshot before search to {screenshot_name}")
            except Exception as e:
                logger.warning(f"Could not save before screenshot: {str(e)}")
            
            # Try standard search approach
            search_succeeded = False
            
            try:
                search_input = self._wait_and_find_element(
                    By.CSS_SELECTOR, 
                    "input.mat-input-element, input#mat-input-0, input[aria-label='Pesquisar'], mat-form-field input"
                )
                
                if search_input:
                    logger.info(f"Found search input, entering query: {query}")
                    search_input.click()
                    time.sleep(0.5)
                    search_input.clear()
                    time.sleep(0.5)
                    
                    # Type the search query character by character
                    for char in query:
                        search_input.send_keys(char)
                        time.sleep(0.1)
                    
                    time.sleep(1)
                    search_input.send_keys(Keys.RETURN)
                    logger.info("Submitted search with Enter key")
                    search_succeeded = True
                    time.sleep(5)
                else:
                    logger.warning("Could not find search input")
            except Exception as e:
                logger.warning(f"Standard search approach failed: {str(e)}")
                
            # If standard search failed, try JavaScript approach
            if not search_succeeded:
                try:
                    logger.info("Trying JavaScript search approach")
                    js_script = """
                    var inputField = document.querySelector('input.mat-input-element, input#mat-input-0, input[type="search"], input[placeholder*="Pesquisar"]');
                    if (inputField) {
                        inputField.value = arguments[0];
                        inputField.dispatchEvent(new Event('input', { bubbles: true }));
                        return true;
                    }
                    return false;
                    """
                    js_result = self.driver.execute_script(js_script, query)
                    
                    if js_result:
                        logger.info("JavaScript search input succeeded, pressing Enter")
                        ActionChains(self.driver).send_keys(Keys.RETURN).perform()
                        search_succeeded = True
                        time.sleep(5)
                    else:
                        logger.warning("JavaScript search approach failed to find input")
                except Exception as e:
                    logger.warning(f"JavaScript search approach failed: {str(e)}")
            
            # If both interactive searches failed, try URL approach
            if not search_succeeded:
                logger.info("Using URL approach for search")
                search_url = f"{self.base_url}?q={query}"
                self.driver.get(search_url)
                time.sleep(5)
            
            # Take screenshot after search attempt
            try:
                screenshot_name = f"after_search_{query.replace(' ', '_')}.png"
                self.driver.save_screenshot(screenshot_name)
                logger.info(f"Saved screenshot after search to {screenshot_name}")
            except Exception as e:
                logger.warning(f"Could not save after screenshot: {str(e)}")
            
            # Log the current URL
            logger.info(f"Current URL after search: {self.driver.current_url}")
            
            # Try multiple approaches to find auction elements
            all_auction_elements = self._find_auction_elements()
            logger.info(f"Found {len(all_auction_elements)} potential auction elements")
            
            # Extract auction data from each element
            for element in all_auction_elements:
                try:
                    auction_data = self._extract_auction_from_element(element)
                    if auction_data and 'url' in auction_data and auction_data['url']:
                        raw_auctions.append(auction_data)
                        logger.info(f"Added auction: {auction_data.get('title', 'Unknown')}")
                except Exception as e:
                    logger.error(f"Error extracting auction data: {str(e)}")
            
            logger.info(f"Found {len(raw_auctions)} total auctions for query: {query}")
            
            # If we didn't find any auctions and a fallback URL exists for this query, try direct navigation
            if not raw_auctions:
                fallback_auction = self._get_fallback_auction_for_query(query)
                if fallback_auction:
                    logger.info(f"No auctions found, trying direct navigation to known auction for {query}")
                    try:
                        details = self.get_auction_details(fallback_auction)
                        if details:
                            raw_auctions.append(details)
                            logger.info(f"Added known auction via direct navigation for {query}")
                    except Exception as e:
                        logger.error(f"Error getting fallback auction: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error in Selenium search: {str(e)}")
        
        return raw_auctions
        
    def _find_auction_elements(self) -> List[Any]:
        """Find auction elements using multiple selector strategies"""
        all_elements = []
        
        # Strategy 1: Standard lot items
        elements = self.driver.find_elements(By.CSS_SELECTOR, ".lot-list-item")
        if elements:
            logger.info(f"Found {len(elements)} standard lot items")
            all_elements.extend(elements)
            
        # Strategy 2: Any elements that might contain lot information
        alt_selectors = [
            "div[class*='lot-']", 
            "div[class*='auction-item']", 
            "a[href*='/lote/']",
            "div.csdl-panel"
        ]
        
        for selector in alt_selectors:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            new_elements = [e for e in elements if e not in all_elements]
            if new_elements:
                logger.info(f"Found {len(new_elements)} elements with selector: {selector}")
                all_elements.extend(new_elements)
                
        return all_elements
        
    def _extract_auction_from_element(self, element) -> Dict[str, Any]:
        """Extract auction data from an element"""
        auction_data = {
            'title': "Unknown",
            'description': "",
        }
        
        # Try to find the auction URL (most important piece)
        auction_url = None
        
        # Approach 1: Direct link on the element
        if element.tag_name == "a" and '/lote/' in element.get_attribute('href'):
            auction_url = element.get_attribute('href')
            # Get title from the link text if available
            if element.text.strip():
                auction_data['title'] = element.text.strip()
                
        # Approach 2: Find links inside the element
        if not auction_url:
            links = element.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute('href')
                if href and '/lote/' in href:
                    auction_url = href
                    # Get title from the link text if available
                    if link.text.strip():
                        auction_data['title'] = link.text.strip()
                    break
        
        # If no URL found, this is not a valid auction
        if not auction_url:
            return None
        
        auction_data['url'] = auction_url
        
        # If title is still unknown, try to find it elsewhere
        if auction_data['title'] == "Unknown":
            title_candidates = element.find_elements(By.CSS_SELECTOR, 
                "h2, h3, .title, div[class*='title'], div[class*='heading']")
            for candidate in title_candidates:
                if candidate.text.strip():
                    auction_data['title'] = candidate.text.strip()
                    break
        
        # Try to get the image URL
        try:
            img_element = element.find_element(By.CSS_SELECTOR, "img")
            if img_element:
                auction_data['image_url'] = img_element.get_attribute('src')
        except:
            pass
        
        # Try to get evaluation and minimum bid using regex on the element HTML
        try:
            element_html = element.get_attribute('outerHTML')
            import re
            
            # Look for price patterns
            price_matches = re.findall(r'R\$\s*([\d.,]+)', element_html)
            if len(price_matches) >= 2:
                auction_data['evaluation'] = f"R$ {price_matches[0]}"
                auction_data['minimum_bid'] = f"R$ {price_matches[1]}"
            elif len(price_matches) == 1:
                auction_data['minimum_bid'] = f"R$ {price_matches[0]}"
        except:
            pass
        
        return auction_data
        
    def _get_fallback_auction_for_query(self, query: str) -> Optional[str]:
        """Get a fallback auction URL for a given query if available"""
        # Get location configuration
        location_config = get_location_config(query)
        
        # If we have a fallback URL in the config, use it
        if location_config and "fallback_url" in location_config:
            logger.info(f"Using fallback URL for {location_config['name']}")
            return location_config["fallback_url"]
            
        # No specific fallback found
        return None
    
    def _filter_auctions(self, raw_auctions: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Apply filtering to raw auctions based on search query
        
        Args:
            raw_auctions: List of auction data dictionaries
            query: Search term
            
        Returns:
            Filtered list of auction data dictionaries
        """
        # Generate variations of the search query
        query_variations = self._generate_query_variations(query)
        
        # Basic keyword filtering
        logger.info(f"Applying keyword filtering for query: {query}")
        logger.debug(f"Using query variations: {query_variations}")
        
        filtered_auctions = []
        
        for auction in raw_auctions:
            # Prepare text for search by combining all text fields
            auction_text = (
                auction.get('title', '').lower() + ' ' + 
                auction.get('description', '').lower() + ' ' + 
                auction.get('auction_title', '').lower()
            )
            
            # Check if any query variations match
            matched_variation = None
            for variation in query_variations:
                if variation in auction_text:
                    matched_variation = variation
                    break
                    
            if matched_variation:
                # Add match metadata to the auction
                auction['match_reason'] = f"Matched term: {matched_variation}"
                filtered_auctions.append(auction)
        
        logger.info(f"Filtered to {len(filtered_auctions)} relevant auctions for query: {query}")
        return filtered_auctions
        
    def _generate_query_variations(self, query: str) -> List[str]:
        """
        Generate variations of the search query to improve matching
        
        Args:
            query: Original search query
            
        Returns:
            List of query variations
        """
        # Convert query to lowercase for case-insensitive matching
        query = query.lower().strip()
        
        # Start with the original query
        variations = [query]
        
        # Get location configuration if available
        location_config = get_location_config(query)
        
        if location_config:
            # Add the official name
            variations.append(location_config["name"].lower())
            
            # Add all aliases
            variations.extend([alias.lower() for alias in location_config.get("aliases", [])])
            
            # Add name with state
            if "state" in location_config:
                variations.append(f"{location_config['name'].lower()}/{location_config['state'].lower()}")
        else:
            # No specific location config found, use general approach
            
            # 1. Remove accents (replace á,é,í,ó,ú with a,e,i,o,u)
            import unicodedata
            normalized = ''.join(
                c for c in unicodedata.normalize('NFD', query)
                if unicodedata.category(c) != 'Mn'
            )
            if normalized != query:
                variations.append(normalized)
                
            # 2. Add variations with and without special characters
            if '/' in query:
                variations.append(query.replace('/', ''))
            else:
                # Check if it might be a city name and add state code
                for location_id, config in LOCATIONS.items():
                    if query in config.get("aliases", []) or query in location_id:
                        variations.append(f"{query}/{config['state'].lower()}")
                        break
        
        # Remove duplicates and ensure all are lowercase
        unique_variations = []
        for var in variations:
            var_lower = var.lower()
            if var_lower not in unique_variations:
                unique_variations.append(var_lower)
                
        logger.debug(f"Generated variations for '{query}': {unique_variations}")
        return unique_variations
    
    def get_auction_details(self, auction_url: str) -> Dict[str, Any]:
        """Get detailed information about a specific auction"""
        try:
            logger.info(f"Getting details for auction: {auction_url}")
            self.driver.get(auction_url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Take a screenshot for debugging
            try:
                screenshot_path = f"auction_details_{auction_url.split('/')[-1]}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Saved auction details screenshot to {screenshot_path}")
            except Exception as e:
                logger.warning(f"Could not save auction details screenshot: {str(e)}")
            
            # Extract detailed information
            details = {}
            
            # Get title
            try:
                details["title"] = self.driver.find_element(By.CSS_SELECTOR, "h1.lot-page-title").text.strip()
            except NoSuchElementException:
                try:
                    # Try alternative selectors
                    details["title"] = self.driver.find_element(By.CSS_SELECTOR, 
                        "h1, .lot-title, .auction-title, .csdl-panel-title").text.strip()
                except:
                    details["title"] = "Unknown"
            
            # Get description - try multiple methods
            description = ""
            
            # Method 1: Try to find dedicated description element
            try:
                desc_element = self.driver.find_element(By.CSS_SELECTOR, "div.lot-description")
                description = desc_element.text.strip()
            except NoSuchElementException:
                # Method 2: Try alternative description elements
                try:
                    description_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                        ".description, .lot-info, p.detail-text, .auction-description")
                    for elem in description_elements:
                        if elem.text and len(elem.text) > 20:  # Only use substantial text
                            description += elem.text.strip() + "\n\n"
                except:
                    pass
            
            # Method 3: If still no description, try to extract from metadata sections
            if not description:
                try:
                    # Look for labels that might indicate description sections
                    labels = self.driver.find_elements(By.XPATH, 
                        "//*[contains(text(), 'Descrição') or contains(text(), 'Detalhes') or contains(text(), 'Informações')]")
                    
                    for label in labels:
                        # Try to get parent or following sibling element that may contain the description
                        try:
                            parent = label.find_element(By.XPATH, "./..")
                            if parent and parent.text and len(parent.text) > len(label.text) + 20:
                                description += parent.text.replace(label.text, "").strip() + "\n\n"
                                continue
                        except:
                            pass
                            
                        try:
                            sibling = label.find_element(By.XPATH, "./following-sibling::*[1]")
                            if sibling and sibling.text and len(sibling.text) > 20:
                                description += sibling.text.strip() + "\n\n"
                        except:
                            pass
                except:
                    pass
            
            # Method 4: As a last resort, try to use JavaScript to extract text content
            if not description:
                try:
                    js_script = """
                    var descriptionText = "";
                    
                    // Try to find elements with description-like content
                    var elements = document.querySelectorAll('.lot-page-content p, .content p, .details p');
                    for (var i = 0; i < elements.length; i++) {
                        if (elements[i].textContent.trim().length > 50) {
                            descriptionText += elements[i].textContent.trim() + "\\n\\n";
                        }
                    }
                    
                    return descriptionText;
                    """
                    js_description = self.driver.execute_script(js_script)
                    if js_description:
                        description = js_description
                except Exception as e:
                    logger.warning(f"JavaScript description extraction failed: {str(e)}")
            
            details["description"] = description.strip() if description else "No description available"
            
            # Get images
            try:
                img_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.lot-page-gallery img, .carousel img, .auction-images img")
                details["images"] = [img.get_attribute("src") for img in img_elements if img.get_attribute("src")]
            except:
                details["images"] = []
            
            # Get price information - improved to handle different layouts
            try:
                # Try multiple approaches to get price information
                price_info = {}
                
                # Method 1: Look for standard price elements
                price_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.lot-page-value, .price-info, .auction-value")
                for element in price_elements:
                    try:
                        label_elem = element.find_element(By.CSS_SELECTOR, "div.lot-page-value-label, .value-label, .price-label")
                        value_elem = element.find_element(By.CSS_SELECTOR, "div.lot-page-value-text, .value-text, .price-value")
                        
                        label = label_elem.text.strip().lower()
                        value = value_elem.text.strip()
                        
                        if "avalia" in label:
                            price_info["evaluation"] = value
                        elif "lance" in label and "mínimo" in label:
                            price_info["minimum_bid"] = value
                        elif "lance" in label and "atual" in label:
                            price_info["current_bid"] = value
                    except:
                        continue
                
                # Method 2: If method 1 failed, try alternative approach with labels
                if not price_info:
                    label_elements = self.driver.find_elements(By.XPATH, 
                        "//*[contains(text(), 'Avaliação') or contains(text(), 'Lance Mínimo') or contains(text(), 'Lance Atual')]")
                    
                    for label in label_elements:
                        label_text = label.text.strip().lower()
                        try:
                            value_elem = label.find_element(By.XPATH, "./following-sibling::*[1]")
                            value = value_elem.text.strip()
                            
                            if "avalia" in label_text:
                                price_info["evaluation"] = value
                            elif "mínimo" in label_text:
                                price_info["minimum_bid"] = value
                            elif "atual" in label_text:
                                price_info["current_bid"] = value
                        except:
                            pass
                
                # Method 3: Extract from any text with currency symbols
                if not price_info:
                    page_source = self.driver.page_source
                    import re
                    price_matches = re.findall(r'(Avaliação|Lance Mínimo|Lance Atual|Valor)[\s:]*R\$\s*[\d.,]+', page_source)
                    
                    for match in price_matches:
                        if "avalia" in match.lower():
                            match_value = re.search(r'R\$\s*([\d.,]+)', match)
                            if match_value:
                                price_info["evaluation"] = f"R$ {match_value.group(1)}"
                        elif "mínimo" in match.lower():
                            match_value = re.search(r'R\$\s*([\d.,]+)', match)
                            if match_value:
                                price_info["minimum_bid"] = f"R$ {match_value.group(1)}"
                        elif "atual" in match.lower():
                            match_value = re.search(r'R\$\s*([\d.,]+)', match)
                            if match_value:
                                price_info["current_bid"] = f"R$ {match_value.group(1)}"
                
                # Add the price information to details
                details.update(price_info)
                
            except Exception as e:
                logger.warning(f"Error extracting price info: {str(e)}")
            
            # Get auction closing date
            try:
                date_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                    "div.lot-page-date, .auction-date, .closing-date, .end-date")
                
                for date_elem in date_elements:
                    date_text = date_elem.text.strip()
                    if date_text:
                        details["closing_at"] = date_text
                        break
            except:
                details["closing_at"] = "Unknown"
            
            # Capture HTML for LLM processing
            details["html_content"] = self.driver.page_source
            
            # Enhance with LLM if available and enabled
            use_llm = self.llm_client and self.llm_client.api_key and os.getenv("USE_LLM", "false").lower() == "true"
            if use_llm:
                logger.info("Using LLM to enhance auction details")
                details = self.enrich_auction_data(details, "")
                
            return details
            
        except Exception as e:
            logger.error(f"Error getting auction details: {str(e)}")
            return {"error": str(e)}
            
    def _wait_and_find_elements(self, by, value, timeout=None):
        """Helper method to wait for elements and find them"""
        timeout = timeout or SELENIUM_WAIT_TIME
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return self.driver.find_elements(by, value)
        except TimeoutException:
            logger.warning(f"Timeout waiting for elements: {value}")
            return []
    
    def _extract_auction_header(self, container):
        """Extract auction header information from container"""
        try:
            header = {
                'title': container.find_element(By.CSS_SELECTOR, "h2.lot-list-item-value").text.strip(),
                'url': container.find_element(By.CSS_SELECTOR, "div.auction-header a").get_attribute('href'),
            }
            
            # Get next session date
            try:
                header['next_session'] = container.find_element(
                    By.CSS_SELECTOR, "div.lot-list-item-auction-heading span.lot-list-item-value"
                ).text.strip()
            except:
                header['next_session'] = "Unknown"
                
            return header
        except Exception as e:
            logger.error(f"Error extracting auction header: {str(e)}")
            return {
                'title': 'Unknown',
                'url': '#',
                'next_session': 'Unknown'
            }
    
    def _extract_lot_data(self, lot, auction_header):
        """Extract lot data from a lot element"""
        try:
            # Find the title element
            title_element = lot.find_element(By.CSS_SELECTOR, "a.lot-list-item-value")
            title = title_element.text.strip()
            url = title_element.get_attribute('href')
            
            lot_data = {
                'auction_title': auction_header['title'],
                'auction_url': auction_header['url'],
                'next_session': auction_header['next_session'],
                'title': title,
                'url': url,
            }
        except Exception as e:
            # Try alternative selectors if the standard ones don't work
            logger.warning(f"Using alternative selectors for lot data: {str(e)}")
            try:
                # Try to find any link that might be the title
                links = lot.find_elements(By.TAG_NAME, "a")
                if links:
                    for link in links:
                        href = link.get_attribute('href')
                        if href and '/lote/' in href:
                            lot_data = {
                                'auction_title': auction_header['title'],
                                'auction_url': auction_header['url'],
                                'next_session': auction_header['next_session'],
                                'title': link.text.strip() or "Unknown Title",
                                'url': href,
                            }
                            break
                    else:
                        # If no suitable link found
                        raise Exception("No suitable link found in lot")
                else:
                    raise Exception("No links found in lot")
            except Exception as nested_e:
                logger.error(f"Failed to extract basic lot data with alternative selectors: {str(nested_e)}")
                # Create minimal data structure
                lot_data = {
                    'auction_title': auction_header['title'],
                    'auction_url': auction_header['url'],
                    'next_session': auction_header['next_session'],
                    'title': "Unknown",
                    'url': "#",
                }
        
        # Try to get the image URL
        try:
            img_element = lot.find_element(By.CSS_SELECTOR, "div.lot-list-item-photo img, img.ng-star-inserted")
            lot_data['image_url'] = img_element.get_attribute('src')
        except:
            lot_data['image_url'] = None
            logger.debug("No image found for lot")
        
        # Get evaluation and minimum bid - try different selectors
        try:
            # First try with standard selectors
            value_elements = lot.find_elements(By.CSS_SELECTOR, "div.lot-list-item-value")
            
            if len(value_elements) >= 3:
                lot_data['evaluation'] = value_elements[1].text.strip()
                lot_data['minimum_bid'] = value_elements[2].text.strip()
            elif len(value_elements) >= 2:
                lot_data['evaluation'] = value_elements[0].text.strip()
                lot_data['minimum_bid'] = value_elements[1].text.strip()
            else:
                # Try alternative selectors
                evaluation_element = lot.find_element(By.XPATH, ".//*[contains(text(), 'Avalia')]/../following-sibling::div")
                minimum_bid_element = lot.find_element(By.XPATH, ".//*[contains(text(), 'Lance')]/../following-sibling::div")
                
                lot_data['evaluation'] = evaluation_element.text.strip() if evaluation_element else None
                lot_data['minimum_bid'] = minimum_bid_element.text.strip() if minimum_bid_element else None
        except:
            logger.warning("Could not find evaluation or minimum bid with standard selectors")
            # Try to find currency values in the text
            try:
                lot_html = lot.get_attribute('outerHTML')
                import re
                # Look for R$ values
                currency_values = re.findall(r'R\$\s*[\d.,]+', lot_html)
                if len(currency_values) >= 2:
                    lot_data['evaluation'] = currency_values[0]
                    lot_data['minimum_bid'] = currency_values[1]
                elif len(currency_values) == 1:
                    lot_data['minimum_bid'] = currency_values[0]
                    lot_data['evaluation'] = None
            except:
                lot_data['evaluation'] = None
                lot_data['minimum_bid'] = None
        
        # Try to get sale status (Venda Direta, etc)
        try:
            status_elements = lot.find_elements(By.XPATH, ".//div[contains(@class, 'lot-status')]") or \
                             lot.find_elements(By.XPATH, "..//div[contains(@class, 'lot-status')]") or \
                             lot.find_elements(By.CSS_SELECTOR, "div.auction-directsale, div.auction-active, div.auction-sold")
            
            if status_elements:
                lot_data['status'] = status_elements[0].text.strip()
            else:
                lot_data['status'] = None
        except:
            lot_data['status'] = None
            
        # Get any description snippet if available
        try:
            description_elements = lot.find_elements(By.CSS_SELECTOR, "span.lot-list-item-label")
            descriptions = []
            for element in description_elements:
                text = element.text.strip()
                if text and not text.startswith("Título") and not text.startswith("Lance") and not text.startswith("Avaliação"):
                    descriptions.append(text)
            
            lot_data['description'] = " ".join(descriptions)
        except:
            lot_data['description'] = ""
        
        # Add search keywords for easier filtering
        lot_data['search_keywords'] = f"{lot_data['title']} {lot_data['description']} {lot_data['auction_title']}".lower()
            
        return lot_data

    def _wait_and_find_element(self, by, value, timeout=None):
        """Helper method to wait for a single element and find it"""
        timeout = timeout or SELENIUM_WAIT_TIME
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return self.driver.find_element(by, value)
        except TimeoutException:
            logger.warning(f"Timeout waiting for element: {value}")
            return None
        except Exception as e:
            logger.warning(f"Error finding element {value}: {str(e)}")
            return None 