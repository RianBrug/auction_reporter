import os
import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from src.config import HEADLESS_BROWSER

logger = logging.getLogger(__name__)

def get_chrome_driver(max_retries=3, retry_delay=2):
    """
    Get a Chrome webdriver based on the environment (Lambda, Docker, or local)
    
    Args:
        max_retries: Maximum number of connection retries
        retry_delay: Delay between retries in seconds
        
    Returns:
        A configured Chrome webdriver
    """
    chrome_options = Options()
    
    if HEADLESS_BROWSER:
        chrome_options.add_argument('--headless')
        
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')  # Set a standard resolution
    
    # Add more browser-like characteristics to avoid detection
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    for attempt in range(max_retries):
        try:
            if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
                # AWS Lambda environment
                logger.info("Running in AWS Lambda environment")
                chrome_options.binary_location = '/opt/chrome/chrome'
                return webdriver.Chrome(
                    executable_path='/opt/chromedriver',
                    options=chrome_options
                )
            elif os.getenv('DOCKER_ENV'):
                # Docker development environment - use remote WebDriver
                logger.info("Running in Docker environment")
                return webdriver.Remote(
                    command_executor='http://chrome:4444/wd/hub',
                    options=chrome_options
                )
            else:
                # Local development environment - use local Chrome
                logger.info("Running in local environment")
                service = Service(ChromeDriverManager().install())
                return webdriver.Chrome(
                    service=service,
                    options=chrome_options
                )
        except WebDriverException as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to create Chrome driver after {max_retries} attempts: {str(e)}")
                raise
            logger.warning(f"Failed to connect to Chrome (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            
def close_driver(driver):
    """Safely close a webdriver"""
    if driver:
        try:
            driver.quit()
            logger.info("WebDriver closed successfully")
        except Exception as e:
            logger.warning(f"Error closing WebDriver: {str(e)}") 