import logging
from lambda_function import lambda_handler

# Configure logging to output to terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # This will output to terminal
    ]
)

if __name__ == "__main__":
    # Call the lambda handler with empty event and context
    result = lambda_handler({}, None)
    print("\nResult:", result) 