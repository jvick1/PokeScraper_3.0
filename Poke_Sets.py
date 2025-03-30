from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import csv
import os

WD_PATH = "E:/Code/Python/Pokemon/data/"
# URLs to scrape
URLS = [
    "https://jp.pokellector.com/sets",
    "https://www.pokellector.com/sets"
]

def extract_hrefs(url, driver):
    """Extract all hrefs from <a> tags within <div id='columnLeft'>."""
    try:
        driver.get(url)
        # Wait for the div to load (timeout after 2 seconds)
        WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.ID, "columnLeft"))
        )
        
        # Find the div and all <a> tags inside it
        column_left = driver.find_element(By.ID, "columnLeft")
        links = column_left.find_elements(By.TAG_NAME, "a")
        
        # Extract hrefs
        hrefs = [link.get_attribute("href") for link in links if link.get_attribute("href")]
        return hrefs
    
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

def extract_set_data(url, driver):
    """Extract breadcrumb and set info data from a set page."""
    try:
        driver.get(url)
        WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.CLASS_NAME, "breadcrumbs"))
        )
        
        # Extract breadcrumbs
        breadcrumbs_div = driver.find_element(By.CLASS_NAME, "breadcrumbs")
        breadcrumb_texts = [a.text.strip() for a in breadcrumbs_div.find_elements(By.TAG_NAME, "a")]
        # Last part might not be in an <a> tag (e.g., "Terastal Festival ex")
        last_text = breadcrumbs_div.text.split("»")[-1].strip()
        if last_text and last_text not in breadcrumb_texts:
            breadcrumb_texts.append(last_text)
        
        # Extract set info (handle both "setinfo" and "content setinfo")
        try:
            # Try finding "setinfo" first
            setinfo_div = driver.find_element(By.CLASS_NAME, "setinfo")
        except:
            # If not found, try finding "content setinfo" using XPath
            setinfo_div = driver.find_element(By.XPATH, "//div[contains(@class, 'setinfo')]")        
            
        description = setinfo_div.find_element(By.CLASS_NAME, "description").text.strip() or "N/A"
        
        cards_div = setinfo_div.find_element(By.CLASS_NAME, "cards")
        card_count = cards_div.find_elements(By.TAG_NAME, "span")[1].text.strip()

        secret_count = "N/A"
        try:
            secret_count_elem = cards_div.find_element(By.TAG_NAME, "cite")
            secret_count = secret_count_elem.text.replace("+", "").replace("Secret", "").strip() if secret_count_elem else "N/A"
        except:
            pass #leave as na

        release_div = setinfo_div.find_elements(By.TAG_NAME, "div")[-1]
        release_spans = release_div.find_elements(By.TAG_NAME, "span")
        release_date = release_spans[1].text.strip() if len(release_spans) > 1 else "N/A"
        release_year = release_div.find_element(By.TAG_NAME, "cite").text.strip() if release_div.find_elements(By.TAG_NAME, "cite") else "N/A"
        full_release_date = f"{release_date} {release_year}".strip() if release_date != "N/A" and release_year != "N/A" else "N/A"
        
        data = {
            "URL": url,
            "Category": breadcrumb_texts[0] if len(breadcrumb_texts) > 0 else "N/A",
            "Series": breadcrumb_texts[1] if len(breadcrumb_texts) > 1 else "N/A",
            "SetName": breadcrumb_texts[2] if len(breadcrumb_texts) > 2 else "N/A",
            "Description": description,
            "Card Count": card_count,
            "Secret Card Count": secret_count,
            "Release Date": full_release_date
        }
        print(f"Debug: Scraped data from {url}: {data}")
        return data
    
    except Exception as e:
        print(f"Error scraping set page {url}: {e}")
        return {
            "URL": url,
            "Category": "N/A",
            "Series": "N/A",
            "SetName": "N/A",
            "Description": "N/A",
            "Card Count": "N/A",
            "Secret Card Count": "N/A",
            "Release Date": "N/A"
        }
    
def main():
    driver = webdriver.Chrome()

    # Store all results
    all_data = []

    # Get initial hrefs from both sites
    for url in URLS:
        print(f"Scraping {url} for links...")
        hrefs = extract_hrefs(url, driver)
        print(f"Found {len(hrefs)} links at {url}")
        
        # Scrape each set page
        for href in hrefs:
            print(f"Scraping set page: {href}")
            set_data = extract_set_data(href, driver)
            all_data.append(set_data)

    # Clean up
    driver.quit()

    # Save to CSV
    csv_file = WD_PATH + "pokellector_set_data.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "URL", "Category", "Series", "SetName",
            "Description", "Card Count", "Secret Card Count", "Release Date"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)
    
    # Verify file exists and has content
    if os.path.exists(csv_file):
        file_size = os.path.getsize(csv_file)
        print(f"Saved {len(all_data)} sets to {csv_file} (Size: {file_size} bytes)")
    else:
        print(f"Error: {csv_file} was not created!")

if __name__ == "__main__":
    main()
