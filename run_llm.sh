#!/bin/bash

# Script to run the LLM-based auction generator with common options

# Activate virtual environment if it exists
if [ -d "auctions_venv" ]; then
    source auctions_venv/bin/activate
fi

# Set default query
QUERY="itapiruba"
LOCATION="Santa Catarina"

# Parse command line arguments
while [ "$1" != "" ]; do
    case $1 in
        -q | --query )          shift
                                QUERY=$1
                                ;;
        -l | --location )       shift
                                LOCATION=$1
                                ;;
        -h | --help )           echo "Usage: ./run_llm.sh [-q QUERY] [-l LOCATION] [--debug] [--list-locations]"
                                echo "  -q, --query        Search query (default: itapiruba)"
                                echo "  -l, --location     Location context (default: Santa Catarina)"
                                echo "  --debug            Enable debug logging"
                                echo "  --list-locations   Show supported locations"
                                echo "  -h, --help         Show this help message"
                                exit
                                ;;
        --debug )               DEBUG="--debug"
                                ;;
        --list-locations )      python src/local_llm.py --list-locations
                                exit
                                ;;
    esac
    shift
done

# Run the generator with options
echo "Running LLM-based auction generator with query: $QUERY in $LOCATION"
python src/local_llm.py -q "$QUERY" -l "$LOCATION" $DEBUG

# Deactivate virtual environment if activated
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi 