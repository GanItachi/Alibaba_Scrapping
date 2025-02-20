from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from sqlalchemy.orm import Session
from api.database import SessionLocal 
from api.models import Categorie, Produit
import time
import sys
from pathlib import Path
# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ✅ Configuration de Selenium
def setup_driver():
    """Configure et retourne le driver Chrome."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Mode sans interface
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=chrome_options)

# ✅ Défilement pour charger les produits
def wait_for_scroll(driver, last_height, timeout=5):
    """Fait défiler la page et attend le chargement du contenu."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.body.scrollHeight") > last_height
        )
        return True
    except TimeoutException:
        return False

# ✅ Scraping des produits d'une catégorie
def scrape_category_products(category_url):
    """Scrape les produits d'une catégorie sur Alibaba et retourne un dictionnaire {nom: lien}."""
    driver = setup_driver()
    products = {}

    try:
        print(f"🔍 Chargement de la catégorie : {category_url}")
        driver.get(category_url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "alimod-industry-products-waterfall"))
        )

        last_height = driver.execute_script("return document.body.scrollHeight")
        attempts, max_attempts = 0, 3

        # 🔹 Faire défiler la page pour charger les produits
        while attempts < max_attempts:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Ajout d'un délai pour éviter le chargement incomplet
            
            if wait_for_scroll(driver, last_height, timeout=5):
                last_height = driver.execute_script("return document.body.scrollHeight")
                attempts = 0  # Réinitialisation
            else:
                attempts += 1  # Incrémentation si aucun nouveau contenu n'est chargé

        print(f"✅ Défilement terminé pour {category_url}")

        # 🔹 Extraire les informations des produits
        product_elements = driver.find_elements(By.CSS_SELECTOR, ".alimod-industry-products-waterfall .hugo4-pc-grid-item")

        for product in product_elements:
            try:
                title_span = product.find_element(By.CSS_SELECTOR, "span[title]")
                title = title_span.get_attribute("title").strip()

                link_element = product.find_element(By.CSS_SELECTOR, "a")
                product_url = link_element.get_attribute("href")

                if title and product_url:
                    products[title] = product_url
            except NoSuchElementException:
                continue

    except Exception as e:
        print(f"⚠️ Erreur dans le scraping de la catégorie : {e}")
    finally:
        driver.quit()

    return products

# ✅ Récupérer les catégories depuis la base de données
def get_all_categories(db: Session):
    """Récupère toutes les catégories enregistrées dans la base de données."""
    return db.query(Categorie).all()

# ✅ Scraper et stocker les produits de toutes les catégories
def spi2():
    """Scrape les produits pour chaque catégorie en base et les stocke dans la table `products`."""
    db = SessionLocal()
    categories = get_all_categories(db)

    if not categories:
        print("⚠️ Aucune catégorie trouvée en base.")
        db.close()
        return {}

    for category in categories:
        print(f"\n🔍 Scraping des produits pour la catégorie : {category.title}")
        products_data = scrape_category_products(category.link)

        new_products_count = 0
        for title, link in products_data.items():
            # Vérifier si le produit existe déjà en base
            existing_product = db.query(Produit).filter(Produit.link == link).first()
            if not existing_product:
                new_product = Produit(title=title, link=link, categorie_id=category.id)
                db.add(new_product)
                new_products_count += 1

        db.commit()
        print(f"✅ {new_products_count} nouveaux produits ajoutés pour la catégorie : {category.title}")

    db.close()
    print("\n🎉 Scraping des produits terminé !")
    return "Scraping terminé avec succès !"

# ✅ Test du script
if __name__ == "__main__":
    spi2()
