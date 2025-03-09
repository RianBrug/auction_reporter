#!/bin/bash

# Simple script to run the auction crawler with common options

# Activate virtual environment if it exists
if [ -d "auctions_venv" ]; then
    source auctions_venv/bin/activate
fi

# Set default query
QUERY="itapiruba"
LOCATION="Santa Catarina"

# List of supported locations
function show_locations() {
    echo "Supported locations (use with -q or --query):"
    echo "  itapiruba         - Itapiruba/SC"
    echo "  florianopolis     - Florianópolis/SC"
    echo "  balneario-camboriu - Balneário Camboriú/SC"
    echo "  sao-paulo         - São Paulo/SP"
    echo "  rio-de-janeiro    - Rio de Janeiro/RJ"
    echo "You can also use other locations not in this list."
}

# Parse command line arguments
while [ "$1" != "" ]; do
    case $1 in
        -q | --query )          shift
                                QUERY=$1
                                ;;
        -l | --location )       shift
                                LOCATION=$1
                                ;;
        -h | --help )           echo "Usage: ./run.sh [-q QUERY] [-l LOCATION] [--debug] [--no-headless] [--use-llm] [--list-locations]"
                                echo "  -q, --query        Search query (default: itapiruba)"
                                echo "  -l, --location     Location context (default: Santa Catarina)"
                                echo "  --debug            Enable debug logging"
                                echo "  --no-headless      Show browser window"
                                echo "  --use-llm          Use LLM for filtering (requires API key)"
                                echo "  --list-locations   Show supported locations"
                                echo "  -h, --help         Show this help message"
                                exit
                                ;;
        --debug )               DEBUG="--debug"
                                ;;
        --no-headless )         NO_HEADLESS="--no-headless"
                                ;;
        --use-llm )             USE_LLM="--use-llm"
                                ;;
        --list-locations )      show_locations
                                exit
                                ;;
    esac
    shift
done

# Run the crawler with options
echo "Running auction crawler with query: $QUERY in $LOCATION"
python src/local.py -q "$QUERY" -l "$LOCATION" --deduplicate $DEBUG $NO_HEADLESS $USE_LLM

# Deactivate virtual environment if activated
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi 