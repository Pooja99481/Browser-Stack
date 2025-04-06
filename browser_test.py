from selenium import webdriver
from selenium.webdriver.common.by import By
from concurrent.futures import ThreadPoolExecutor
from config import browsers
from credentials import USERNAME, ACCESS_KEY

def run_test(caps):
    options = webdriver.ChromeOptions()
    for key, value in caps.items():
        options.set_capability(key, value)

    driver = webdriver.Remote(
        command_executor=f"https://{USERNAME}:{ACCESS_KEY}@hub-cloud.browserstack.com/wd/hub",
        options=options
    )

    try:
        driver.get("https://elpais.com/opinion/")
        print("Title:", driver.title)

        driver.implicitly_wait(5)

        all_articles = driver.find_elements(By.CSS_SELECTOR, "h2.c_t")

        print("Browser:", caps)

        count = 0
        for article in all_articles:
            if count == 5:
                break
            text = article.text.strip()
            if text:  # Only non-empty titles
                print("Article Title:", text)
                count += 1

        if count < 5:
            print(f"Only {count} articles found.")

        session_id = driver.session_id
        print("BrowserStack Session Link: https://automate.browserstack.com/sessions/" + session_id + ".json")

    except Exception as e:
        print("Error:", e)

    finally:
        driver.quit()


print("BrowserStack test execution started...\n")

with ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(run_test, browsers)
