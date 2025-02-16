import json
from lambda_function import lambda_handler

def run_local():
    # Simulate Lambda event and context
    event = {}
    context = {}
    
    # Run the lambda handler
    result = lambda_handler(event, context)
    
    # Print results
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    run_local() 