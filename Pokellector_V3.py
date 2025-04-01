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

WD_PATH = "E:/Code/Python/Pokemon/output/"
ENG_URL = "https://www.pokellector.com/"
JP_URL = "https://jp.pokellector.com/"
CSV_PATH = "E:/Code/Python/Pokemon/data/pokellector_set_data.csv"

# Load only SetName and Release Date from CSV into a dictionary
SET_RELEASE_DATES = {}
with open(CSV_PATH, "r", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        SET_RELEASE_DATES[row["SetName"]] = row["Release Date"]

def parse_and_format_date(date_str):
    """
    Parse a date string like 'Jan 17th 2024' and reformat to 'YYYY-MM-DD'.
    Returns 'N/A' if parsing fails.
    """
    if date_str == "N/A":
        return "N/A"
    
    try:
        # Remove suffixes like 'th', 'st', 'nd', 'rd'
        date_str = date_str.replace("th", "").replace("st", "").replace("nd", "").replace("rd", "")
        # Parse the date (e.g., "Jan 17 2024")
        date_obj = datetime.strptime(date_str, "%b %d %Y")
        # Format to YYYY-MM-DD
        return date_obj.strftime("%Y-%m-%d")
    except ValueError as e:
        print(f"Error parsing date '{date_str}': {e}")
        return "N/A"

def fetch_page_urls(driver, base_url, name):
    """
    Fetches pagination URLs for a Pokémon search from a given site.
    """
    search_url = f"{base_url}/search?criteria={name}"

    try:
        driver.get(search_url)
        time.sleep(1)
        html = driver.page_source
        soup = bs(html, "html.parser")
        page_urls = [a['href'].replace(base_url, '') for a in soup.select("div.pagination a[href]")]
        # If no pagination links, use the search page itself
        if not page_urls:
            page_urls = [search_url.replace(base_url, '')]  # Relative URL
        return page_urls
    except WebDriverException as e:
        time.sleep(2)

def fetch_card_data(driver, base_url, page_urls, site, timeout=2):
    """
    Scrapes card data from a list of page URLs for a given site.
    """
    card_data = []
    for page_url in tqdm(page_urls, desc=f"Fetching {site} cards"):
    
        try:
            full_url = base_url + page_url
            driver.get(full_url)
            
            # Wait for page to stabilize (document.readyState == 'complete') or timeout
            try:
                WebDriverWait(driver, timeout).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                print(f"{site} - {full_url}: Page loaded normally")
            except TimeoutException:
                print(f"{site} - {full_url}: Still loading after {timeout}s, stopping refresh")
                driver.execute_script("window.stop();")  # Stop the refresh/loading

            # Use whatever HTML is available
            html = driver.page_source
            soup = bs(html, "html.parser")
            cards = soup.find_all("div", attrs={"class": "cardresult"})
            print(f"{site} - {full_url}: Found {len(cards)} cards")

            for card in cards:
                # let's pull card specific info

                card_name = card.find("div", attrs={"class": "name"}).text.strip()

                set_and_card = card.find("div", attrs={"class": "set"}).text.strip()
                if "#" in set_and_card:
                    card_set, card_number =  set_and_card.split("#", 1) 
                    card_set = card_set.strip()
                else:
                    card_set = set_and_card.strip()
                    card_number = ""

                # Extract all prices as dictionary
                prices_div = card.find("div", attrs={"class": "prices"})
                prices = {}
                if prices_div:
                    price_links = prices_div.find_all("a", href=True) #find all <a> tags
                    for link in price_links:
                        href = link["href"]
                        # Extract price
                        price_text = link.get_text(strip=True).replace(link.find("img").text, "").strip()
                        prices[href] = price_text or "N/A"

                img_tag = card.find('img', class_='card ls-is-cached lazyloaded') 
                img_url = {}
                if img_tag and 'src' in img_tag.attrs: 
                    src = img_tag['src'] 
                    if src != 'https://www.pokellector.com/images/card-placeholder-small.jpg':
                        img_url["pokellector"] = src

                #pull all set data, store as csv, read that in, and provide date the card came out
                release_date = SET_RELEASE_DATES.get(card_set, "N/A")
                # Reformat the release date for sorting
                formatted_release_date = parse_and_format_date(release_date)

                card_data.append({"Name": card_name, "Images": img_url, "Set": card_set, "Card Number": card_number, "Prices": prices, "Site": site, "Release Date": formatted_release_date})
            
        except WebDriverException as e:
            time.sleep(2)
    return card_data

def save_to_csv(data, filename):
    """
    Saves a list of card data to a CSV file.
    """
    df = pd.DataFrame(data)
    df["Prices"] = df["Prices"].apply(json.dumps)
    df["Images"] = df["Images"].apply(json.dumps)
    df.to_csv(WD_PATH + filename + ".csv", index=False)
    print(f"Data saved to {WD_PATH}{filename}.csv")

if __name__ == "__main__":
    names_input = input('Type Pokémon names (comma-seprated): ').strip()
    driver = webdriver.Chrome()
    try:
        for name in names_input.split(','):
            name=name.strip()
            print(f"Processing {name}...")
            eng_page_urls = fetch_page_urls(driver, ENG_URL, name)
            jp_page_urls = fetch_page_urls(driver, JP_URL, name)
            eng_cards = fetch_card_data(driver, ENG_URL, eng_page_urls, "English")
            jp_cards = fetch_card_data(driver, JP_URL, jp_page_urls, "Japanese")
            all_cards = eng_cards + jp_cards
            save_to_csv(all_cards, name)
    finally:
        driver.quit()
