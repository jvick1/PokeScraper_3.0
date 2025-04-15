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
from io import BytesIO, StringIO
import os
import logging

"""
This codebase is organized into several classes, each with specific responsibilities:

Config:
    Holds configuration constants such as file paths and URLs used throughout the application.

SetDataLoader:
    Manages the loading and accessing of Pokémon set release dates from a CSV file.

DateFormatter:
    Handles the parsing and formatting of date strings.
    Converts various date formats into a standardized YYYY-MM-DD format.

PokellectorScraper:
    Manages web scraping operations using Selenium and BeautifulSoup.
    Responsible for fetching page URLs and parsing card data from websites.

PriceChartingScraper:
    Manages web scraping operations for PriceCharting.com to fetch additional price data.    

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
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        self.driver = webdriver.Chrome(options=options)

    def close(self):
        try:
            self.driver.quit()
        except:
            pass

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
            time.sleep(1)
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
                time.sleep(1)
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

class PriceChartingScraper:
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        self.driver = webdriver.Chrome(options=options)

    def close(self):
        try:
            self.driver.quit()
        except:
            pass

    def fetch_price_data(self, base_url, name, timeout=2):
        """Fetch price data from PriceCharting for a given Pokémon name."""
        search_url = f"{base_url}{name}"
        card_data = []
        try:
            self.driver.get(search_url)
            try:
                WebDriverWait(self.driver, timeout).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except TimeoutException:
                self.driver.execute_script("window.stop();")

            html = self.driver.page_source
            soup = bs(html, "html.parser")

            results = soup.find_all("tr", id=lambda x: x and x.startswith("product-"))
            for result in results:
                card_data.append(self._parse_card(result, "PriceCharting"))

        except WebDriverException as e:
            print(f"Error scraping PriceCharting for {name}: {e}")
            time.sleep(2)

        return card_data

    def _parse_card(self, result, site):
        """Parse a single card's data from a PriceCharting result row."""
        title_cell = result.find("td", class_="title")
        title_text = title_cell.find("a").text.strip() if title_cell and title_cell.find("a") else "N/A"
        card_name, card_number = self._split_name_and_number(title_text)

        set_cell = result.find("td", class_="console phone-landscape-hidden")
        card_set = set_cell.text.strip() if set_cell else "N/A"

        prices = self._parse_prices(result)
        img_url = {}

        # Fetch release date from the linked page
        release_date = "N/A"
        try:
            if title_cell and title_cell.find("a"):
                details_url = title_cell.find("a")["href"] #+ "#itemdetails"
                self.driver.get(details_url)
                WebDriverWait(self.driver, 2).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                details_html = self.driver.page_source
                details_soup = bs(details_html, "html.parser")
                
                # Find release date in the #itemdetails table
                details_table = details_soup.find("table", id="attribute")
                if details_table:
                    rows = details_table.find_all("tr")
                    for row in rows:
                        title = row.find("td", class_="title")
                        if title and title.text.strip() == "Release Date:":
                            date_cell = row.find("td", class_="details", itemprop="datePublished")
                            release_date = date_cell.text.strip() if date_cell else "none"
                            if release_date != "none":
                                # Convert "October 19, 2018" to "2018-10-19"
                                release_date = datetime.strptime(release_date, "%B %d, %Y").strftime("%Y-%m-%d")
                            break
                    
                cover_div = details_soup.find("div", class_="cover")
                if cover_div:
                    details_img = cover_div.find("img", itemprop="image")
                    if details_img and "src" in details_img.attrs:
                        img_url["pricecharting"] = details_img["src"]

                # fetch additional data (e.g., prices) in the future
                # in price col add grade to cell??
                
        except Exception as e:
            print(f"Error fetching details page: {e}")

        return {
            "Name": card_name,
            "Images": img_url,
            "Set": card_set,
            "Card Number": card_number,
            "Prices": prices,
            "Site": site,
            "Release Date": release_date
        }

    def _split_name_and_number(self, title_text):
        """Split title text into card name and number."""
        if "#" in title_text:
            card_name, card_number = title_text.split("#", 1)
            return card_name.strip(), card_number.strip()
        return title_text.strip(), ""

    def _parse_prices(self, result):
        """Parse prices from a PriceCharting result row."""
        prices = {}
        price_types = [
            ("used_price", "Ungraded"),
            ("cib_price", "Grade 7"),
            ("new_price", "Grade 8")
        ]

        for class_name, label in price_types:
            price_cell = result.find("td", class_=f"price numeric {class_name}")
            price_value = (
                price_cell.find("span", class_="js-price").text.strip().replace("$", "")
                if price_cell and price_cell.find("span", class_="js-price")
                else "N/A"
            )
            prices[f"pricecharting.com/{label.lower().replace(' ', '-')}"] = price_value

        return prices


class PokemonCardProcessor:
    def __init__(self, config):
        self.config = config
        self.set_loader = SetDataLoader(config.CSV_PATH)
        self._setup_logging()

    def _setup_logging(self):
        """Set up logging to a file in SCRIPT_DIR."""
        # Use SCRIPT_DIR from config for log file path
        log_file = os.path.join(self.config.SCRIPT_DIR, 'pokemon_processor.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, mode='a'),
                logging.StreamHandler()  # Optional: Remove if no console output needed
            ]
        )
        self.logger = logging.getLogger(__name__)   

    def process_pokemon_names(self, names):
        start_time = time.time()
        self.logger.info(f"Starting process_pokemon_names for names: {names}")
        self.pricecharting_scraper = PriceChartingScraper()
        self.scraper = PokellectorScraper()
        all_cards = []
        try:
            for name in names.split(','):
                name = name.strip()
                pokemon_start_time = time.time()

                # Fetch Pokellector English data
                eng_start = time.time()
                eng_urls = self.scraper.fetch_page_urls(self.config.ENG_URL, name)
                all_cards.extend(self.scraper.fetch_card_data(self.config.ENG_URL, eng_urls, "Pokellector English", self.set_loader))
                self.logger.info(f"Fetched Pokellector English data for {name} in {time.time() - eng_start:.2f} seconds")
                
                # Fetch Pokellector Japanese data
                jp_start = time.time()
                jp_urls = self.scraper.fetch_page_urls(self.config.JP_URL, name)
                all_cards.extend(self.scraper.fetch_card_data(self.config.JP_URL, jp_urls, "Pokellector Japanese", self.set_loader))
                self.logger.info(f"Fetched Pokellector Japanese data for {name} in {time.time() - jp_start:.2f} seconds")

                # Fetch PriceCharting data
                price_start = time.time()
                price_cards = self.pricecharting_scraper.fetch_price_data(self.config.PRICECHARTING_URL, name)
                all_cards.extend(price_cards)
                self.logger.info(f"Fetched PriceCharting data for {name} in {time.time() - price_start:.2f} seconds")

                pokemon_duration = time.time() - pokemon_start_time
                self.logger.info(f"Completed processing {name} in {pokemon_duration:.2f} seconds")
        
        finally:
            # Close scrapers to shut down browser windows after data pull
            self.pricecharting_scraper.close()
            self.scraper.close()

        total_duration = time.time() - start_time
        self.logger.info(f"Finished process_pokemon_names in {total_duration:.2f} seconds with {len(all_cards)} cards collected")
        
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
                image_urls = []
                for row in rows:
                    try:
                        images = json.loads(row["Images"])
                        url = images.get("pokellector") or images.get("pricecharting") or ""
                        if url and not url.startswith("http"):
                            url = ""
                        image_urls.append(url)
                    except json.JSONDecodeError:
                        print(f"JSON decode error for Images: {row['Images']}")
                        image_urls.append("")
                
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
            if not csv_data:
                return "No CSV data provided", 400

            # Parse the CSV data into a DataFrame
            csv_buffer = StringIO(csv_data)
            df = pd.read_csv(csv_buffer)

            # Add "Owned" column based on checkbox states
            owned_values = []
            for i in range(len(df)):
                # Checkbox name format is "owned_{index}", default to False if not checked
                owned = request.form.get(f'owned_{i}', 'False') == 'True'
                owned_values.append(owned)
            df['Owned'] = owned_values

            # Convert DataFrame back to CSV
            output_buffer = BytesIO()
            df.to_csv(output_buffer, index=False)
            output_buffer.seek(0)

            return send_file(
                output_buffer,
                as_attachment=True,
                download_name=filename,
                mimetype='text/csv'
            )

    def run(self):
        self.app.run(debug=True)

if __name__ == "__main__":
    app = FlaskApp()
    app.run()
