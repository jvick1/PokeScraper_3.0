# PokeScraper_3.0

Need to update -- but we have Poke_Sets.py which pulls a full history of all sets eng/jap and stores it under data. Pokellector_V3 pulls img, price, set, etc of the cards you are looking for.

There are two main py codes in this newest update. We also plan to build out a flask UI and pull better pricing data. But for now this is what we have. Set scraper and card scraper. The set results are stored in ./data NOTE this has to be ran first or atleast have the csv saved. 

## Pokémon Set Data Scraper

This Python script scrapes Pokémon set data from the "Sets" pages of Pokellector (English) and jp.pokellector.com (Japanese). It collects details such as set names, descriptions, card counts, secret card counts, and release dates, then saves the data into a CSV file for use in further analysis or projects.

## Pokémon Card Scraper

This Python script scrapes Pokémon card data from Pokellector (English) and its Japanese counterpart (jp.pokellector.com). It retrieves card details such as name, set, card number, price, image URL, and release date, then saves the data into CSV files for further analysis or use.
