# PokeScraper_3.0

This repository contains two Python scripts designed to scrape Pokémon-related data from Pokellector (English) and jp.pokellector.com (Japanese):
1. Pokémon Set Data Scraper (pokemon_set_data_scraper.py): Extracts metadata about Pokémon card sets, including set names, descriptions, card counts, secret card counts, and release dates, from the "Sets" pages of both sites. The output is saved as pokellector_set_data.csv, which serves as a foundational dataset for further scraping or analysis.

2. Pokémon Card Scraper (pokemon_card_scraper.py): Scrapes detailed card data for specific Pokémon names, pulling information like card names, set names, card numbers, prices, image URLs, and release dates (linked from the set data CSV). Results are saved as individual CSV files per Pokémon (e.g., Pikachu.csv).

Together, these tools enable comprehensive data collection for Pokémon trading card enthusiasts, researchers, or developers, covering both set-level metadata and individual card details across English and Japanese markets.

