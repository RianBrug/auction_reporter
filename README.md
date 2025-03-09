# Auction Crawler

An intelligent crawler for monitoring property auctions across multiple Brazilian auction websites. The system is designed to find and track real estate auctions in various locations.

## Features

- 🔍 Search for auctions in different cities and regions
- 🏙️ Support for multiple locations with intelligent variations
- 🏢 Clean architecture for easy extension to multiple auction sites
- 📊 Detailed information about each auction (price, description, etc.)

## Supported Locations

The crawler is optimized for searching in these locations:

- **Itapiruba/SC** - Beach location in Santa Catarina
- **Florianópolis/SC** - Capital of Santa Catarina
- **Balneário Camboriú/SC** - Popular beach resort city
- **São Paulo/SP** - Brazil's largest city
- **Rio de Janeiro/RJ** - Famous beach city

You can also search for other locations, but these have specific optimizations.

## Project Structure

```
auction_crawler/
├── src/
│   ├── adapters/          # Website-specific adapters
│   ├── llm/               # DeepSeek LLM integration
│   ├── models/            # Data models
│   ├── utils/             # Utility functions
│   ├── config.py          # Configuration
│   ├── lambda_function.py # AWS Lambda handler
│   └── local.py           # Local runner
├── requirements.txt
├── Makefile
└── README.md
```

## Setup

1. Create a virtual environment and install dependencies:

```bash
make install
```

2. Configure your environment (optional):

```bash
cp .env.example .env
# Edit .env as needed
```

## Usage

### Using the Run Script

The easiest way to run the crawler is with the provided script:

```bash
# Make the script executable (one time only)
chmod +x run.sh

# Run with default location (Itapiruba)
./run.sh

# Search in a different location
./run.sh -q florianopolis

# See all supported locations
./run.sh --list-locations

# Enable debug mode
./run.sh -q "balneario-camboriu" --debug

# Show browser window during scraping
./run.sh -q "sao-paulo" --no-headless
```

### Manual Execution

You can also run the crawler directly:

```bash
# Basic run with default query
python src/local.py -q "itapiruba" --deduplicate

# Search in a specific location
python src/local.py -q "florianopolis" -l "Santa Catarina" --deduplicate

# Debug mode with browser window visible
python src/local.py -q "rio-de-janeiro" -d --no-headless --deduplicate
```

## Adding New Locations

To optimize the crawler for a new location:

1. Add the location to the `LOCATIONS` dictionary in `src/config.py`:

```python
"new-location": {
    "name": "New Location Name",
    "state": "ST",
    "aliases": ["alternative name", "nl", "new location/st"],
    "fallback_url": "https://example.com/known-auction-link-for-this-location"
}
```

## Architecture

The crawler uses a modular, adapter-based architecture:

- **Adapters**: Website-specific code for extracting auction data
- **Models**: Data structures for representing auctions
- **Config**: Centralized configuration and location-specific settings

## License

MIT 