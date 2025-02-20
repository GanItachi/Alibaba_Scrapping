from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException
from api.database import SessionLocal  # Assure-toi d'avoir la session SQLAlchemy
from sqlalchemy.orm import Session
from sqlalchemy import or_
from api.models import Categorie
import time
import random
from tqdm import tqdm



def wait_for_scroll(driver, last_height, timeout=5):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.body.scrollHeight") > last_height
        )
        return True
    except TimeoutException:
        return False

def lien_recup(lien):
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Mode sans interface graphique
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-data-dir=/tmp/chrome-user-data")
    chrome_options.add_argument("--remote-debugging-port=9222")

    
    driver= webdriver.Chrome(options=chrome_options)
    try:
        driver.get(lien)
        
        # Attendre que le contenu principal soit chargé
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'alimod-industry-products-waterfall'))
        )
        
        # Initialisation
        last_height = driver.execute_script("return document.body.scrollHeight")
        attempts = 0
        max_attempts = 3
        
        print(lien)
        
        while attempts < max_attempts:
            # Scroll instantané jusqu'en bas
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Attente active jusqu'à ce que le scroll soit effectif
            if wait_for_scroll(driver, last_height, timeout=5):
                # Le contenu a chargé, on réinitialise le compteur d'essais
                last_height = driver.execute_script("return document.body.scrollHeight")
                attempts = 0
            else:
                # Si après 5 secondes, la hauteur ne change pas, on incrémente le compteur
                attempts += 1
        
        print("Défilement terminé")
        
        results=[]
        
        # Exécution d'un script pour récupérer les données en une seule passe
        produits = driver.execute_script("""
            var results = [];
            var elements = document.querySelectorAll('.alimod-industry-products-waterfall .hugo4-pc-grid-item');
            elements.forEach(element => {
                var titleSpan = element.querySelector('span[title]');
                var title = titleSpan ? titleSpan.getAttribute('title') : 'No title';
                var links = element.querySelectorAll('a');
                var hrefs = Array.from(links).map(a => a.href);
                hrefs.forEach(href => {
                    results.push({ url: href, title: title });  // Ajoute un objet avec l'URL et le titre au tableau
                });
            });
            return results;

        """)
        
        results.extend(produits)
        
                
    except Exception as e:
        print(f"Erreur dans lien_recup: {e}")
        return {}
    finally :
        driver.quit()
        
    return results
    
def get_categories_by_title(db: Session, keyword: str):
    return db.query(Categorie).filter(Categorie.title.ilike(f"%{keyword}%")).all()
    
    
def spi2(title):
    db = SessionLocal()
    categories = get_categories_by_title(db=db, keyword=title)  # Remplace par le mot-clé que tu cherches
    db.close()
    print(f"Categories récupérées: {categories}")
    results = []

    for cat in categories:
        results.extend(lien_recup(cat.link))  # Utilise extend pour ajouter les résultats de chaque catégorie


        
    return results

