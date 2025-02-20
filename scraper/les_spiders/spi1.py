from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tempfile
import requests
import time
from selenium.common.exceptions import TimeoutException, WebDriverException


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

def scrape_alibaba(max_retries=3, delay=3):
    """Scrape Alibaba avec gestion des erreurs et retries"""

    results = {}
    status_code = None

    for attempt in range(max_retries):
        driver = create_driver()  # Créer un nouveau driver à chaque tentative

        try:
            print(f"Tentative {attempt + 1}...")
            driver.get("https://www.alibaba.com/")
            
            # Attente jusqu'à 10 secondes pour que l'élément apparaisse
            WebDriverWait(driver, 5).until(
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

            # Vérifier le statut HTTP de la page
            try:
                response = requests.get("https://www.alibaba.com/", timeout=5)
                status_code = response.status_code
            except requests.exceptions.RequestException as e:
                print(f"Erreur réseau : {e}")
                status_code = None

            break  # Si tout fonctionne, on sort de la boucle

        except TimeoutException:
            print(f"⚠️ Timeout lors du chargement de la page (tentative {attempt + 1}/{max_retries})")
        except WebDriverException as e:
            print(f"🚨 Erreur WebDriver : {e} (tentative {attempt + 1}/{max_retries})")
        finally:
            driver.quit()

        # Attendre avant une nouvelle tentative
        time.sleep(delay)

    return results, status_code, len(results)


if __name__ == "__main__":
    data = scrape_alibaba()
    print("Produits récupérés :", data)
