from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from api.utils import format_price, parse_min_order
import tempfile
import time

def scrape_alibaba_products(keyword, max_pages=2):
    # Configuration de Selenium
    chrome_options = Options()
    #chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        # Temporary profile directory
    chrome_options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
        # Headless configuration (optional)
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
        # Shared memory configuration
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    products = []
    base_url = "https://www.alibaba.com"
    
    # Aller à la page d'accueil et lancer la recherche
    print(f"Chargement de la page d'accueil Alibaba...")
    driver.get(base_url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "search-bar-input")))
    
    search_input = driver.find_element(By.CLASS_NAME, "search-bar-input")
    search_input.clear()
    search_input.send_keys(keyword)
    search_button = driver.find_element(By.CLASS_NAME, "fy23-icbu-search-bar-inner-button")
    search_button.click()
    
    print("Attente avant recherche...")
    time.sleep(5)  # Attendre que la page charge complètement
    
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "search-card-e-title")))

    for page in range(1, max_pages + 1):
        print(f"Scraping page {page} pour '{keyword}'...")
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Trouver toutes les cartes produit (ajusté à l’HTML fourni)
        product_cards = soup.select(".fy23-search-card")
        if not product_cards:
            print("Aucun produit trouvé ou fin des résultats.")
            break

        for card in product_cards:
            try:
                # Title
                title_elem = card.select_one(".search-card-e-title a span")
                title = title_elem.text.strip() if title_elem else "N/A"

                # Price
                price_elem = card.select_one(".search-card-e-price-main")
                price = price_elem.text.strip() if price_elem else "N/A"

                # Min Order
                min_order_elem = card.select_one(".search-card-m-sale-features__item")
                min_order = min_order_elem.text.strip() if min_order_elem else "N/A"

                # Supplier Name & Link
                supplier_elem = card.select_one(".search-card-e-company")
                supplier_name = supplier_elem.text.strip() if supplier_elem else "N/A"
                supplier_link = supplier_elem.get("href", "N/A") if supplier_elem else "N/A"
                if supplier_link != "N/A" and not supplier_link.startswith("http"):
                    supplier_link = "https:" + supplier_link

                # Supplier Year & Country
                supplier_year_elem = card.select_one(".search-card-e-supplier__year span:first-child")
                if supplier_year_elem:
                    # Extraire le texte et le convertir en minuscules
                    text = supplier_year_elem.text.lower()
                    # Diviser le texte en mots et extraire uniquement le premier élément (le nombre)
                    supplier_year = text.split(" ")[0].strip() + " ans" if "ans" in text or "years" in text else "N/A"
                else:
                    supplier_year = "N/A"
                

                supplier_country_elem = card.select_one(".search-card-e-country-flag__wrapper img")
                supplier_country = supplier_country_elem["alt"].upper() if supplier_country_elem else "N/A"
                
                # Product Link (nouveau)
                product_link_elem = card.find("a", href=True)
                product_link = product_link_elem["href"] if product_link_elem else "N/A"
                if product_link != "N/A" and not product_link.startswith("http"):
                    product_link = "https:" + product_link
                
                min_order = min_order.replace("Min. order: ", "")
                # Stocker les données
                product_data = {
                    "title": title,
                    "price": price,
                    "min_order": min_order,
                    "supplier_name": supplier_name,
                    "supplier_link": supplier_link,
                    "supplier_year": supplier_year,
                    "supplier_country": supplier_country,
                    "product_link": product_link
                }
                
                product_data['price_min'], product_data['price_max'] = format_price(product_data['price'])
                product_data["min_order_qty"], product_data["min_order_unit"] = parse_min_order(product_data["min_order"])
        
                del product_data["price"], product_data["min_order"] 
                    
                products.append(product_data)

            except Exception as e:
                print(f"Erreur sur un produit : {e}")
                continue
        
        # Passer à la page suivante
        if page < max_pages:
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".next-btn.next-next"))
                )
                if next_button:
                    next_button.click()
                    WebDriverWait(driver, 10).until(EC.stale_element_reference_exception(next_button))
                else:
                    print("Plus de pages disponibles.")
                    break
            except:
                print("Fin des pages ou erreur de navigation.")
                break

    driver.quit()
    return products
