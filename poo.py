import os
import csv
import html
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account
from collections import Counter

SERVICE_ACCOUNT_JSON = "C:/Users/priya/Downloads/festive-zoo-456004-j6-7b6a9ec64457.json"  # <--- Change only this
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_JSON)
translate_client = translate.Client(credentials=credentials)


# -------------------- Setup --------------------
if not os.path.exists("article_images"):
    os.makedirs("article_images")

csv_filename = "translated_articles.csv"
csv_fields = ["Title (ES)", "Title (EN)", "Content Preview", "Image Filename"]
with open(csv_filename, "w", newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(csv_fields)

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-extensions")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
prefs = {"profile.managed_default_content_settings.images": 2}
options.add_experimental_option("prefs", prefs)
options.page_load_strategy = 'eager'

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.set_page_load_timeout(60)

try:
    driver.get("https://elpais.com")

    try:
        cookie_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept')] | //button[contains(., 'ACEPTAR')]"))
        )
        cookie_button.click()
    except:
        pass

    opinion_link = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/opinion/') and contains(text(), 'Opinión')]"))
    )
    opinion_link.click()

    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "article")))
    time.sleep(2)

    articles = driver.find_elements(By.XPATH, "//article//a[contains(@href, '/opinion/')]")
    links, seen_links = [], set()
    for a in articles:
        href = a.get_attribute("href")
        if href and href not in seen_links:
            seen_links.add(href)
            links.append(href)
        if len(links) >= 10:
            break

    
    translated_titles = []
    all_translated_words = []
    seen_titles = set()
    downloaded_imgs = set()

    valid_articles = 0
    i = 0

    while valid_articles < 5 and i < len(links):
        url = links[i]
        i += 1
        driver.get(url)

        try:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "article")))
        except:
            continue

        try:
            title = driver.find_element(By.TAG_NAME, "h1").text.strip()
        except:
            title = ""

        if not title or title.lower() == "opinión" or title in seen_titles:
            continue
        seen_titles.add(title)

        try:
            paragraphs = driver.find_elements(By.TAG_NAME, "p")
            content = "\n".join([p.text for p in paragraphs if p.text.strip()])
        except StaleElementReferenceException:
            time.sleep(1)
            paragraphs = driver.find_elements(By.TAG_NAME, "p")
            content = "\n".join([p.text for p in paragraphs if p.text.strip()])

        preview = content.strip() if content.strip() else "Content not available."

        # --- Image Download ---
        img_filename = "none"
        try:
            img = driver.find_element(By.XPATH, "//article//img")
            img_url = img.get_attribute("src")

            if img_url:
                img_filename = f"article_images/article_{valid_articles+1}.jpg"

                if not os.path.exists(img_filename):
                    img_data = requests.get(img_url).content
                    with open(img_filename, "wb") as f:
                        f.write(img_data)
                    downloaded_imgs.add(img_url)
                    print(f"Saved image for article {valid_articles+1}")
                else:
                    print(f"Image for article {valid_articles+1} already exists, skipped.")
        except:
            print(f"No image found for article {valid_articles+1}")
            img_filename = "none"

        # --- Translation ---
        translated_title = translate_client.translate(title, source_language='es', target_language='en')['translatedText']

        translated_titles.append(translated_title)
        translated_title = translate_client.translate(title, source_language='es', target_language='en')['translatedText']
        translated_title = html.unescape(translated_title)


        # Word cleanup for better frequency
        clean_words = re.findall(r'\b\w+\b', translated_title.lower())
        all_translated_words.extend(clean_words)

        print(f"\nArticle {valid_articles + 1} (Original):")
        print(f"Title: {title}")
        print(f"Content : {preview}")
        print(f"Translated Title: {translated_title}")

        with open(csv_filename, "a", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([title, translated_title, preview, os.path.basename(img_filename)])

        valid_articles += 1

    # --- Word Frequency ---
    stopwords = {
        "the", "and", "to", "in", "of", "a", "on", "for", "with", "at", "by", "an",
        "is", "this", "that", "it", "as", "from", "be", "are", "was", "or", "but"
    }
    filtered_words = [word for word in all_translated_words if word not in stopwords]
    word_counts = Counter(filtered_words)

    print("\nMost Frequent Words in Translated Titles:")
    printed_any = False
    for word, count in word_counts.most_common():
        if count > 2:
            print(f"Word '{word}' appears {count} times.")
            printed_any = True

    if not printed_any:
        print("No repeated words found more than twice in translated titles.")

finally:
    driver.quit()
    print("Browser session ended.")
