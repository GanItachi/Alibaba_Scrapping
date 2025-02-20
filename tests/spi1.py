from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sqlalchemy.orm import Session
from api.database import SessionLocal
from api.models import Categorie
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

# ✅ Scraping des catégories Alibaba
def scrape_alibaba():
    """Scrape les catégories de produits Alibaba et retourne un dictionnaire {nom_catégorie: lien}."""
    driver = setup_driver()
    results = {}

    try:
        print("🔍 Accès à Alibaba...")
        driver.get("https://www.alibaba.com/")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "industry-row"))
        )

        print("✅ Extraction des catégories en cours...")
        # Extraction avec JavaScript
        categories = driver.execute_script("""
            let data = {};
            document.querySelectorAll('div.industry-row a').forEach(a => {
                let title = a.getAttribute('title');
                let link = a.getAttribute('href');
                if (title && link) data[title] = link;
            });
            return data;
        """)

        results.update(categories)

    except Exception as e:
        print(f"❌ Erreur lors du scraping : {e}")
    finally:
        driver.quit()

    print(f"✅ {len(results)} catégories récupérées.")
    return results

# ✅ Stockage des catégories dans la base PostgreSQL
def store_categories_in_db(categories):
    """Stocke les catégories scrappées dans la base de données en évitant les doublons."""
    db = SessionLocal()
    try:
        for title, link in categories.items():
            # Vérifier si la catégorie existe déjà
            existing_category = db.query(Categorie).filter(Categorie.link == link).first()
            if not existing_category:
                new_category = Categorie(title=title, link=link)
                db.add(new_category)
                print(f"🆕 Ajout : {title} ({link})")
        
        db.commit()
        print("✅ Toutes les catégories ont été enregistrées avec succès.")
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de l'insertion en base : {e}")
    finally:
        db.close()

# ✅ Fonction principale
if __name__ == "__main__":
    scraped_categories = scrape_alibaba()
    store_categories_in_db(scraped_categories)
