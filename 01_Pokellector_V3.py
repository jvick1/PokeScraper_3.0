from flask import Flask, render_template, request, send_file
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
import time
import pandas as pd
from tqdm import tqdm
import csv
from datetime import datetime
import json
from io import BytesIO
import os

"""
This codebase is organized into several classes, each with specific responsibilities:

Config:
    Holds configuration constants such as file paths and URLs used throughout the application.
    Contains static values like working directory path, English/Japanese site URLs, and CSV path.

SetDataLoader:
    Manages the loading and accessing of Pokémon set release dates from a CSV file.
    Provides methods to retrieve release dates for specific sets.

DateFormatter:
    Handles the parsing and formatting of date strings.
    Converts various date formats into a standardized YYYY-MM-DD format.

PokellectorScraper:
    Manages web scraping operations using Selenium and BeautifulSoup.
    Responsible for fetching page URLs and parsing card data from websites.

PokemonCardProcessor:
    Coordinates the processing of Pokémon names and collection of card data.
    Orchestrates the scraping process for multiple Pokémon across English and Japanese sites.

FlaskApp:
    Handles the Flask web application setup and routing.
    Manages HTTP requests, template rendering, and file downloads.
"""

class Config:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    ENG_URL = "https://www.pokellector.com/"
    JP_URL = "https://jp.pokellector.com/"
    PRICECHARTING_URL = "https://www.pricecharting.com/search-products?type=prices&q="
    CSV_PATH = os.path.join(SCRIPT_DIR, "data", "pokellector_set_data.csv")

class SetDataLoader:
    def __init__(self, csv_path):
        self.release_dates = self._load_release_dates(csv_path)

    def _load_release_dates(self, csv_path):
        release_dates = {}
        with open(csv_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                release_dates[row["SetName"]] = row["Release Date"]
        return release_dates

    def get_release_date(self, set_name):
        return self.release_dates.get(set_name, "N/A")

class DateFormatter:
    @staticmethod
    def parse_and_format_date(date_str):
        if date_str == "N/A":
            return "N/A"
        try:
            date_str = date_str.replace("th", "").replace("st", "").replace("nd", "").replace("rd", "")
            date_obj = datetime.strptime(date_str, "%b %d %Y")
            return date_obj.strftime("%Y-%m-%d")
        except ValueError as e:
            print(f"Error parsing date '{date_str}': {e}")
            return "N/A"

class PokellectorScraper:
    def __init__(self):
        self.driver = webdriver.Chrome()

    def __del__(self):
        self.driver.quit()

    def fetch_page_urls(self, base_url, name):
        search_url = f"{base_url}/search?criteria={name}"
        try:
            self.driver.get(search_url)
            time.sleep(1)
            html = self.driver.page_source
            soup = bs(html, "html.parser")
            page_urls = [a['href'].replace(base_url, '') for a in soup.select("div.pagination a[href]")]
            return page_urls if page_urls else [search_url.replace(base_url, '')]
        except WebDriverException:
            time.sleep(2)
            return []

    def fetch_card_data(self, base_url, page_urls, site, set_loader, timeout=2):
        card_data = []
        for page_url in tqdm(page_urls, desc=f"Fetching {site} cards"):
            try:
                full_url = base_url + page_url
                self.driver.get(full_url)
                try:
                    WebDriverWait(self.driver, timeout).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                except TimeoutException:
                    self.driver.execute_script("window.stop();")
                
                html = self.driver.page_source
                soup = bs(html, "html.parser")
                cards = soup.find_all("div", attrs={"class": "cardresult"})
                
                for card in cards:
                    card_data.append(self._parse_card(card, site, set_loader))
            except WebDriverException:
                time.sleep(2)
        return card_data

    def _parse_card(self, card, site, set_loader):
        card_name = card.find("div", attrs={"class": "name"}).text.strip()
        set_and_card = card.find("div", attrs={"class": "set"}).text.strip()
        card_set, card_number = self._split_set_and_number(set_and_card)
        
        prices = self._parse_prices(card.find("div", attrs={"class": "prices"}))
        img_url = self._parse_image(card.find('img', class_='card ls-is-cached lazyloaded'))
        
        release_date = DateFormatter.parse_and_format_date(set_loader.get_release_date(card_set))
        
        return {
            "Name": card_name,
            "Images": img_url,
            "Set": card_set,
            "Card Number": card_number,
            "Prices": prices,
            "Site": site,
            "Release Date": release_date
        }

    def _split_set_and_number(self, set_and_card):
        if "#" in set_and_card:
            card_set, card_number = set_and_card.split("#", 1)
            return card_set.strip(), card_number
        return set_and_card.strip(), ""

    def _parse_prices(self, prices_div):
        prices = {}
        valid_domains = ["ebay.com", "tcgplayer.com", "trollandtoad.com"]

        if prices_div:
            for link in prices_div.find_all("a", href=True):
                href = link["href"]
                if any(domain in href for domain in valid_domains):
                    price_text = (
                        link.get_text(strip=True).replace(link.find("img").text, "").strip() 
                        if link.find("img") 
                        else link.get_text(strip=True)
                        )
                    prices[href] = price_text or "N/A"
        return prices

    def _parse_image(self, img_tag):
        img_url = {}
        if img_tag and 'src' in img_tag.attrs:
            src = img_tag['src']
            if src != 'https://www.pokellector.com/images/card-placeholder-small.jpg':
                img_url["pokellector"] = src
        return img_url

#class PriceChartingScraper:
#    def __init__(self):
#        self.driver = webdriver.Chrome()

#    def __del__(self):
#        self.driver.quit()

class PokemonCardProcessor:
    def __init__(self, config):
        self.config = config
        self.set_loader = SetDataLoader(config.CSV_PATH)

    def process_pokemon_names(self, names):
        scraper = PokellectorScraper()
        #----pricecharting_scraper = PriceChartingScraper()
        all_cards = []
        for name in names.split(','):
            name = name.strip()
            eng_urls = scraper.fetch_page_urls(self.config.ENG_URL, name)
            jp_urls = scraper.fetch_page_urls(self.config.JP_URL, name)
            all_cards.extend(scraper.fetch_card_data(self.config.ENG_URL, eng_urls, "English", self.set_loader))
            all_cards.extend(scraper.fetch_card_data(self.config.JP_URL, jp_urls, "Japanese", self.set_loader))
        return all_cards

class FlaskApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.jinja_env.filters['zip'] = zip
        self.app.jinja_env.filters['from_json'] = json.loads
        self.config = Config()
        self.processor = PokemonCardProcessor(self.config)
        self._register_routes()

    def _register_routes(self):
        @self.app.route('/', methods=['GET', 'POST'])
        def index():
            if request.method == 'POST':
                names = request.form.get('pokemon_names', '').strip()
                if not names:
                    return render_template('index.html', error="Please enter Pokémon names")
                
                card_data = self.processor.process_pokemon_names(names) 
                if not card_data:
                    return render_template('index.html', error="No data found")
                
                df = pd.DataFrame(card_data)
                df["Prices"] = df["Prices"].apply(json.dumps)
                df["Images"] = df["Images"].apply(json.dumps)
                
                rows = df.to_dict('records')
                image_urls = [json.loads(row["Images"]).get("pokellector", "") for row in rows]
                
                csv_buffer = BytesIO()
                df.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                
                return render_template('results.html',
                                    rows=rows,
                                    image_urls=image_urls,
                                    csv_data=csv_buffer.getvalue().decode('utf-8'),
                                    filename=f"pokemon_cards_{'_'.join(names.split(','))}.csv")
            return render_template('index.html')

        @self.app.route('/download/<filename>', methods=['POST'])
        def download(filename):
            csv_data = request.form.get('csv_data')
            buffer = BytesIO()
            buffer.write(csv_data.encode('utf-8'))
            buffer.seek(0)
            return send_file(
                buffer,
                as_attachment=True,
                download_name=filename,
                mimetype='text/csv'
            )

    def run(self):
        self.app.run(debug=True)

if __name__ == "__main__":
    app = FlaskApp()
    app.run()