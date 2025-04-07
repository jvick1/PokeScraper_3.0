# Intro to PokeScraper_3.0

This repository contains two Python scripts designed to scrape Pokémon-related data from pokellector.com (English) and jp.pokellector.com (Japanese). Together, these tools enable comprehensive data collection for Pokémon trading card enthusiasts, researchers, or developers, covering both set-level metadata and individual card details across English and Japanese markets:

# 1. Data Collection
## 1.1 Pokémon Set Data Scraper (`0_Poke_Sets_v2.py`)

This Python script uses Selenium to scrape Pokémon set data from websites like `jp.pokellector.com/sets` and `www.pokellector.com/sets`. 

The codebase is structured into four main classes: 
- `Config` stores constants like URLs and file paths;
- `WebScraper` handles browser automation to extract links and detailed set data (e.g., breadcrumbs, card counts, release dates);
- `DataSaver` saves the scraped data into a CSV file with a predefined structure; 
- `PokemonSetScraper` orchestrates the entire process, from link extraction to data storage.

The script runs automatically, scraping multiple pages and saving results to a file in the specified directory.

Output
- **Output file:** pokellector_set_data.csv
- **Columns:** URL, Category, Series, SetName, Description, Card Count, Secret Card Count, Release Date

## 1.2 Pokémon Card Scraper (`01_Pokellector_V3.py`)

This Python script builds a Flask web application to scrape and display Pokémon card data from `www.pokellector.com` and `jp.pokellector.com`. 

It is organized into several classes: 
- `Config` stores static constants like URLs and file paths;
- `SetDataLoader` loads release dates from a CSV file;
- `DateFormatter` standardizes date strings into YYYY-MM-DD format;
- `PokellectorScraper` uses Selenium and BeautifulSoup to fetch and parse card data (e.g., names, sets, prices, images);
- `PokemonCardProcessor` coordinates scraping for multiple Pokémon across English and Japanese sites; 
- `FlaskApp` manages the web interface, rendering templates and enabling CSV downloads.

Users input Pokémon names via a form, view results in a table, and can download the data as a CSV file.

## 1.3 FlaskApp (`/templates` & `/static/css`)

### `/templates`

`index.html` serves as the landing page.

`results.html` serves as a template for displaying scraped Pokémon card data in a Flask web application. It features a styled table powered by DataTables, showing columns for card images, names, sets, card numbers, prices (with clickable links), sites, and release dates, populated dynamically using Jinja2 templating. The page includes a form to search for more Pokémon cards, a button to download the data as a CSV file, and a link to return to the search page. External resources like Google Fonts, DataTables CSS/JS, and jQuery enhance styling and interactivity, with JavaScript configuring the table for sorting, pagination, and numeric handling of card numbers.

### `/static/css`

`styles.css` styles a Pokémon card scraper web app with a modern, responsive design. It resets defaults, sets a gradient background, and uses the Poppins font. Key elements include a centered container, styled forms, a DataTable-enhanced table with hover effects, and custom image and price list formatting. Buttons and links feature transitions, and media queries adapt the layout for smaller screens.




