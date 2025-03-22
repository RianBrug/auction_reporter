# Auction Crawler

An intelligent crawler for monitoring property auctions across multiple Brazilian auction websites. The system is designed to find and track real estate auctions in various locations.

## Features

- 🔍 Search for auctions in different cities and regions
- 🏙️ Support for multiple locations with intelligent variations
- 🏢 Clean architecture for easy extension to multiple auction sites
- 📊 Detailed information about each auction (price, description, etc.)
- 🤖 NEW: LLM-based auction generator for realistic auction listings

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
│   ├── llm/               # DeepSeek LLM integration and generators
│   ├── models/            # Data models
│   ├── utils/             # Utility functions
│   ├── config.py          # Configuration
│   ├── lambda_function.py # AWS Lambda handler (scraping version)
│   ├── lambda_function_llm.py # AWS Lambda handler (LLM version)
│   ├── local.py           # Local runner (scraping version)
│   └── local_llm.py       # Local runner (LLM version)
├── requirements.txt
├── run.sh                 # Run script for scraping version
├── run_llm.sh             # Run script for LLM version
├── Makefile
└── README.md
```

## Setup

1. Create a virtual environment and install dependencies:

```bash
make install
```

2. Configure your environment (required for LLM version):

```bash
cp .env.example .env
# Edit .env and add your DEEPSEEK_API_KEY
```

## Usage

### Web Scraping Version

Using the run script:

```bash
# Make the script executable (one time only)
chmod +x run.sh

# Run with default location (Itapiruba)
./run.sh

# Search in a different location
./run.sh -q florianopolis

# See all supported locations
./run.sh --list-locations
```

### LLM-Based Version (NEW)

The LLM-based version generates realistic auction listings without scraping websites:

```bash
# Make the script executable (one time only)
chmod +x run_llm.sh

# Run with default location (Itapiruba)
./run_llm.sh

# Generate auctions for a different location
./run_llm.sh -q florianopolis

# See all supported locations
./run_llm.sh --list-locations
```

### Manual Execution

You can also run either version directly:

```bash
# Web scraping version
python src/local.py -q "itapiruba" --deduplicate

# LLM-based version
python src/local_llm.py -q "itapiruba"
```

## LLM Integration

The project now has two modes of operation:

1. **Web Scraping Mode**: Scrapes auction websites directly for real-time data
2. **LLM-Based Mode**: Uses DeepSeek AI to generate realistic auction listings

The LLM mode is useful when:
- You need example data without accessing the real websites
- You want to test the application without making real web requests
- The website structure changes and scraping temporarily doesn't work
- You want to see what types of auctions would typically be available

### Configuration for LLM

To use the LLM-based version, you need a DeepSeek API key:

1. Get an API key from DeepSeek: https://platform.deepseek.com/
2. Add it to your `.env` file: `DEEPSEEK_API_KEY=your_key_here`

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
- **LLM**: Integration with DeepSeek API for auction generation and analysis

## License

MIT 