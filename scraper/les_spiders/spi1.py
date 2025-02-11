from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tempfile


def create_driver():
    chrome_options = webdriver.ChromeOptions()
    
    # Temporary profile directory
    chrome_options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
    
    # Headless configuration (optional)
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
    # Shared memory configuration
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    return webdriver.Chrome(options=chrome_options)

def scrape_alibaba():

    driver = create_driver()
    results = {}

    try:
        driver.get("https://www.alibaba.com/")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "industry-row"))
        )

        # Exécuter du JavaScript pour récupérer directement les produits
        categorie = driver.execute_script("""
            let data = {};
            document.querySelectorAll('div.industry-row a').forEach(a => {
                let title = a.getAttribute('title');
                let link = a.getAttribute('href');
                if (title && link) data[title] = link;
            });
            return data;
        """)

        results.update(categorie)

    finally:
        driver.quit()

    return results

if __name__ == "__main__":
    data = scrape_alibaba()
    print("Produits récupérés :", data)
