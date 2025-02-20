from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
from sqlalchemy.orm import Session
from api.database import SessionLocal
from api.models import ProduitDetails, Supplier, Review
from api.utils import clean_text, clean_json, clean_price, clean_integer, extract_country_from_url

# 🛠️ Configuration de Selenium
def setup_driver():
    """Configure et retourne le driver Chrome."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Exécuter en mode sans interface
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=chrome_options)

# ✅ Fonction de scrolling pour charger toute la page
def scroll_page(driver):
    """Fait défiler la page pour charger tous les éléments."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Pause pour laisser le temps au contenu de charger
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# ✅ Scraping des détails du produit
def scrape_product_details(driver):
    """Scrape les informations principales du produit (prix, variations)."""
    product_data = {"pricing": [], "variations": {}, "discount": "Aucune réduction"}

    try:
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "product-price")))

        # 🔹 Vérifier s'il y a une promotion active
        try:
            discount_elem = driver.find_element(By.CSS_SELECTOR, ".product-price div.id-text-white")
            product_data["discount"] = clean_text(discount_elem.text)
        except NoSuchElementException:
            pass

        # 🔹 Récupérer les prix et quantités
        try:
            price_items = driver.find_elements(By.CSS_SELECTOR, ".price-item")
            for item in price_items:
                quantity_range = clean_text(item.find_element(By.CLASS_NAME, "quality").text)
                prices = item.find_elements(By.CSS_SELECTOR, ".price span")

                new_price = clean_price(prices[0].text) if len(prices) > 0 else "Non spécifié"
                old_price = clean_price(prices[1].text) if len(prices) > 1 else "Non spécifié"

                product_data["pricing"].append({
                    "quantity_range": quantity_range,
                    "new_price": new_price,
                    "old_price": old_price
                })
        except NoSuchElementException:
            print("⚠️ Aucun prix trouvé.")

    except TimeoutException:
        print("❌ Impossible de charger les détails du produit.")

    return product_data

# ✅ Scraping des attributs du produit
def scrape_product_attributes(driver):
    """Récupère les attributs du produit et gère le bouton 'Afficher plus'."""
    attributes_data = {}

    try:
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "attribute-info")))

        # 📌 Vérifier et cliquer sur "Afficher plus" si disponible
        try:
            show_more_button = driver.find_element(By.CSS_SELECTOR, ".more-bg a")
            if show_more_button.is_displayed():
                driver.execute_script("arguments[0].click();", show_more_button)
                time.sleep(2)
        except NoSuchElementException:
            pass

        # 🔹 Extraire les attributs
        attribute_items = driver.find_elements(By.CLASS_NAME, "attribute-item")
        for item in attribute_items:
            try:
                attribute_name = clean_text(item.find_element(By.CLASS_NAME, "left").text)
                attribute_value = clean_text(item.find_element(By.CLASS_NAME, "right").text)
                attributes_data[attribute_name] = attribute_value
            except NoSuchElementException:
                continue

    except TimeoutException:
        print("❌ Impossible de charger la section des attributs.")

    return attributes_data

# ✅ Scraping des avis avec gestion correcte de la pagination
def scrape_reviews(driver):
    """Scrape tous les avis d’un produit Alibaba en parcourant toutes les pages."""
    reviews_data = []

    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "module_review")))

        while True:
            reviews = driver.find_elements(By.CSS_SELECTOR, ".review-item")
            for review in reviews:
                try:
                    stars = len(review.find_elements(By.CSS_SELECTOR, ".star-rating-list svg"))
                    comment_elem = review.find_element(By.CSS_SELECTOR, ".review-info")
                    date_elem = review.find_element(By.CSS_SELECTOR, ".date")
                    country_img = review.find_element(By.CSS_SELECTOR, ".avatar-info img")

                    reviews_data.append({
                        "rating": stars,
                        "comment": clean_text(comment_elem.text),
                        "date": clean_text(date_elem.text),
                        "reviewer_country": extract_country_from_url(country_img.get_attribute("src"))
                    })
                except NoSuchElementException:
                    continue

            # 🔹 Vérifier la pagination
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, ".review-pagination .detail-pagination-list button:not(.active)")
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(2)
            except NoSuchElementException:
                break

    except TimeoutException:
        print("❌ Impossible de charger les avis.")

    return reviews_data

# ✅ Scraping des informations du fournisseur (version complète)
def scrape_supplier_info(driver):
    """Récupère toutes les informations du fournisseur Alibaba."""
    info = {
        "company_name": "Non spécifié",
        "company_profile_link": "Non spécifié",
        "years_in_business": "Non spécifié",
        "location": "Non spécifié",
        "store_rating": "Non spécifié",
        "on_time_delivery": "Non spécifié",
        "response_time": "Non spécifié",
        "online_revenue": "Non spécifié",
        "main_markets": "Non spécifié",
        "staff": "Non spécifié",
        "services_offered": [],
        "quality_control": []
    }

    try:
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "company-layout")))

        try:
            company_element = driver.find_element(By.CSS_SELECTOR, ".company-name a")
            info["company_name"] = clean_text(company_element.text)
            info["company_profile_link"] = company_element.get_attribute("href")
        except NoSuchElementException:
            print("⚠️ Nom du fournisseur introuvable.")

    except TimeoutException:
        print("❌ Impossible de charger les informations du fournisseur.")

    return info

# ✅ Stockage des données en base PostgreSQL
def store_product_data(db: Session, product_data, url):
    """Stocke les détails scrappés d'un produit en base de données."""
    produit = ProduitDetails(
        url=url,
        discount=product_data["details"]["discount"],
        pricing=clean_json(product_data["details"]["pricing"]),
        variations=clean_json(product_data["details"]["variations"]),
        attributes=clean_json(product_data["attributes"])
    )
    db.add(produit)
    db.commit()

# ✅ Scraping du produit complet
def scrape_product(url):
    driver = setup_driver()
    product_data = {}

    try:
        driver.get(url)
        scroll_page(driver)  # 📌 Ajout du scroll pour charger toutes les sections
        product_data["details"] = scrape_product_details(driver)
        product_data["attributes"] = scrape_product_attributes(driver)
        product_data["supplier_info"] = scrape_supplier_info(driver)
        product_data["reviews"] = scrape_reviews(driver)

        with SessionLocal() as db:
            store_product_data(db, product_data, url)

    finally:
        driver.quit()

# ✅ Test
if __name__ == "__main__":
    url = "https://www.alibaba.com/product-detail/J-M8-Game-Stick-4K-Video_1600224308009.html"
    scrape_product(url)
