from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_alibaba():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=chrome_options)
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
