import json
import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
                chrome_options.binary_location = '/opt/chrome/chrome'
                return webdriver.Chrome(
                    executable_path='/opt/chromedriver',
                    options=chrome_options
                )
            elif os.getenv('DOCKER_ENV'):
                # Docker development - use remote WebDriver
                return webdriver.Remote(
                    command_executor='http://chrome:4444/wd/hub',
                    options=chrome_options
                )
            else:
                # Local development - use local Chrome
                service = Service(ChromeDriverManager().install())
                return webdriver.Chrome(
                    service=service,
                    options=chrome_options
                )
        except WebDriverException as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"Failed to connect to Chrome (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)

def scrape_auctions(driver, url):
    driver.get(url)
    auctions = []
    
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "auction-container"))
        )
        time.sleep(2)  # Small delay to ensure content loads
        
        auction_containers = driver.find_elements(By.CLASS_NAME, "auction-container")
        logger.info(f"Found {len(auction_containers)} auction containers")

        for container in auction_containers:
            try:
                auction_title = container.find_element(By.CSS_SELECTOR, 'h2.lot-list-item-value').text
                auction_date = container.find_element(By.CSS_SELECTOR, 'div.lot-list-item-auction-heading span.lot-list-item-value').text
                lots = container.find_elements(By.CLASS_NAME, 'lot-list-item')
                
                for lot in lots:
                    try:
                        lot_data = {
                            'auction_title': auction_title,
                            'auction_date': auction_date,
                            'title': lot.find_element(By.CSS_SELECTOR, 'a.lot-list-item-value').text.strip(),
                            'url': lot.find_element(By.CSS_SELECTOR, 'a.lot-list-item-value').get_attribute('href'),
                            'image_url': lot.find_element(By.CSS_SELECTOR, 'img.ng-star-inserted').get_attribute('src'),
                            'evaluation': lot.find_elements(By.CSS_SELECTOR, 'div.lot-list-item-value')[0].text.strip(),
                            'minimum_bid': lot.find_elements(By.CSS_SELECTOR, 'div.lot-list-item-value')[1].text.strip()
                        }
                        auctions.append(lot_data)
                        logger.info(f"Found lot: {lot_data['title']}")
                    except Exception as e:
                        logger.error(f"Error parsing lot: {str(e)}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error parsing auction container: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Error waiting for auctions: {str(e)}")
        
    return auctions

def lambda_handler(event, context):
    url = 'https://www.centralsuldeleiloes.com.br/leiloes?q=florianopolis'
    driver = None
    
    try:
        driver = get_chrome_driver()
        auctions = scrape_auctions(driver, url)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'auctions': auctions
            })
        }
    except Exception as e:
        logger.error(f"Error in lambda execution: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
    finally:
        if driver:
            driver.quit()