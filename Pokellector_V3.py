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

app = Flask(__name__)
app.jinja_env.filters['zip'] = zip  # Enable the zip filter
app.jinja_env.filters['from_json'] = json.loads  # Add this to parse JSON in template

WD_PATH = "E:/Code/Python/Pokemon/output/"
ENG_URL = "https://www.pokellector.com/"
JP_URL = "https://jp.pokellector.com/"
CSV_PATH = "E:/Code/Python/Pokemon/data/pokellector_set_data.csv"

# Load set release dates
SET_RELEASE_DATES = {}
with open(CSV_PATH, "r", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        SET_RELEASE_DATES[row["SetName"]] = row["Release Date"]

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

def fetch_page_urls(driver, base_url, name):
    search_url = f"{base_url}/search?criteria={name}"
    try:
        driver.get(search_url)
        time.sleep(1)
        html = driver.page_source
        soup = bs(html, "html.parser")
        page_urls = [a['href'].replace(base_url, '') for a in soup.select("div.pagination a[href]")]
        if not page_urls:
            page_urls = [search_url.replace(base_url, '')]
        return page_urls
    except WebDriverException:
        time.sleep(2)
        return []

def fetch_card_data(driver, base_url, page_urls, site, timeout=2):
    card_data = []
    for page_url in tqdm(page_urls, desc=f"Fetching {site} cards"):
        try:
            full_url = base_url + page_url
            driver.get(full_url)
            try:
                WebDriverWait(driver, timeout).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except TimeoutException:
                driver.execute_script("window.stop();")
            
            html = driver.page_source
            soup = bs(html, "html.parser")
            cards = soup.find_all("div", attrs={"class": "cardresult"})
            
            for card in cards:
                card_name = card.find("div", attrs={"class": "name"}).text.strip()
                set_and_card = card.find("div", attrs={"class": "set"}).text.strip()
                if "#" in set_and_card:
                    card_set, card_number = set_and_card.split("#", 1)
                    card_set = card_set.strip()
                else:
                    card_set = set_and_card.strip()
                    card_number = ""
                
                prices_div = card.find("div", attrs={"class": "prices"})
                prices = {}
                if prices_div:
                    price_links = prices_div.find_all("a", href=True)
                    for link in price_links:
                        href = link["href"]
                        price_text = link.get_text(strip=True).replace(link.find("img").text, "").strip() if link.find("img") else link.get_text(strip=True)
                        prices[href] = price_text or "N/A"
                
                img_tag = card.find('img', class_='card ls-is-cached lazyloaded')
                img_url = {}
                if img_tag and 'src' in img_tag.attrs:
                    src = img_tag['src']
                    if src != 'https://www.pokellector.com/images/card-placeholder-small.jpg':
                        img_url["pokellector"] = src
                
                release_date = SET_RELEASE_DATES.get(card_set, "N/A")
                formatted_release_date = parse_and_format_date(release_date)
                
                card_data.append({
                    "Name": card_name,
                    "Images": img_url,
                    "Set": card_set,
                    "Card Number": card_number,
                    "Prices": prices,
                    "Site": site,
                    "Release Date": formatted_release_date
                })
        except WebDriverException:
            time.sleep(2)
    return card_data

def process_pokemon_names(names):
    driver = webdriver.Chrome()
    all_cards = []
    try:
        for name in names.split(','):
            name = name.strip()
            eng_page_urls = fetch_page_urls(driver, ENG_URL, name)
            jp_page_urls = fetch_page_urls(driver, JP_URL, name)
            eng_cards = fetch_card_data(driver, ENG_URL, eng_page_urls, "English")
            jp_cards = fetch_card_data(driver, JP_URL, jp_page_urls, "Japanese")
            all_cards.extend(eng_cards + jp_cards)
    finally:
        driver.quit()
    return all_cards

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        names = request.form.get('pokemon_names', '').strip()
        if names:
            card_data = process_pokemon_names(names)
            if card_data:
                df = pd.DataFrame(card_data)
                # Convert dictionaries to JSON for CSV
                df["Prices"] = df["Prices"].apply(json.dumps)
                df["Images"] = df["Images"].apply(json.dumps)
                
                # Prepare data for template
                rows = df.to_dict('records')  # List of dictionaries
                image_urls = [json.loads(row["Images"]).get("pokellector", "") for row in rows]
                
                # Prepare CSV
                csv_buffer = BytesIO()
                df.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                
                return render_template('results.html',
                                    rows=rows,
                                    image_urls=image_urls,
                                    csv_data=csv_buffer.getvalue().decode('utf-8'),
                                    filename=f"pokemon_cards_{'_'.join(names.split(','))}.csv")
            return render_template('index.html', error="No data found")
        return render_template('index.html', error="Please enter Pokémon names")
    return render_template('index.html')

@app.route('/download/<filename>', methods=['POST'])
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

if __name__ == "__main__":
    app.run(debug=True)
