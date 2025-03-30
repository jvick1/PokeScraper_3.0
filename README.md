# Intro to PokeScraper_3.0

This repository contains two Python scripts designed to scrape Pokémon-related data from pokellector.com (English) and jp.pokellector.com (Japanese). Together, these tools enable comprehensive data collection for Pokémon trading card enthusiasts, researchers, or developers, covering both set-level metadata and individual card details across English and Japanese markets:

# 1. Data Collection
## 1.1 Pokémon Set Data Scraper (Poke_Set.py)
Extracts metadata about Pokémon card sets, including set names, descriptions, card counts, secret card counts, and release dates, from the `/sets` pages of both sites. The output is saved as pokellector_set_data.csv, which serves as a foundational dataset for further scraping or analysis. **Only run this when NEW SETS are released.**

### Usage
Run the script:
```bash
python pokemon_set_data_scraper.py
```
The script will:
- Scrape set links from both English and Japanese Pokellector "Sets" pages.

- Extract detailed data from each set page.

- Save the results to pokellector_set_data.csv in the directory specified by WD_PATH (default: E:/Code/Python/Pokemon/data/).

Output
- **Output file:** pokellector_set_data.csv
- **Columns:** URL, Category, Series, SetName, Description, Card Count, Secret Card Count, Release Date

## 1.2 Pokémon Card Scraper (Pokellector_V3.py)
This is the main code of the project. Scrapes detailed card data for specific Pokémon names, pulling information like card names, set names, card numbers, prices, image URLs, and release dates (linked from the set data CSV). Results are saved as individual CSV files per Pokémon (e.g., Pikachu.csv).

### Usage
Run the script:
```bash
python pokemon_card_scraper.py
```
Enter Pokémon names when prompted (comma-separated, e.g., Pikachu, Charizard).

The script will:
- Fetch data from both English and Japanese Pokellector sites.

- Save results as <pokemon_name>.csv in the directory specified by WD_PATH (default: E:/Code/Python/Pokemon/output/).

**Example**

```plaintext
Type Pokémon names (comma-separated): Pikachu, Bulbasaur
```
**Output files:** Pikachu.csv, Bulbasaur.csv



