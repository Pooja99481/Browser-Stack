from selenium import webdriver
from selenium.webdriver.common.by import By
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from config import browsers
from credentials import USERNAME, ACCESS_KEY

build_name = "Cross Browser Test - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def run_test(caps):
    caps = caps.copy()
    caps['build'] = build_name
    caps['name'] = f"Test on {caps.get('browser', caps.get('device', 'Unknown'))} {caps.get('browser_version', caps.get('os_version', '')).strip()}"

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

        print("Browser:", caps['name'])

        count = 0
        for article in all_articles:
            if count == 5:
                break
            text = article.text.strip()
            if text:
                print("Article Title:", text)
                count += 1

        if count < 5:
            print(f"Only {count} articles found.")

        driver.execute_script(
            'browserstack_executor: {"action": "setSessionStatus", "arguments": {"status":"passed","reason": "Articles loaded successfully"}}'
        )

        session_id = driver.session_id
        session_link = f"https://automate.browserstack.com/sessions/{session_id}.json"
        print("Session Link:", session_link)

        with open("build_links.txt", "a") as f:
            f.write(f"{caps['name']}: {session_link}\n")

    except Exception as e:
        print("Error:", e)
        driver.execute_script(
            f'browserstack_executor: {"action": "setSessionStatus", "arguments": {{"status":"failed","reason": "Error: {str(e)}"}}}'
        )

    finally:
        driver.quit()

print("BrowserStack test execution started...\n")

with ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(run_test, browsers)

print("Done. Go to your BrowserStack builds page to find this build:")
print("https://automate.browserstack.com/builds")
print("Look for:", build_name)
