from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException, InvalidSelectorException
from bs4 import BeautifulSoup
import time
import logging
import re
from api.utils import clean_text, preprocess_data, store_data
from api.models import Produit, Review, Supplier, ProduitDetails, Pricing
from sqlalchemy.orm import Session
from api.database import SessionLocal 
import sys
# Ajouter le répertoire racine au PYTHONPATH
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def setup_driver():
    """Configure et retourne le driver Chrome avec les options optimales."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Configuration pour éviter la détection
    options.add_experimental_option("prefs", {
        "translate": {"enabled": False},
        "intl.accept_languages": "en,en-US"
    })
    
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    )
    
    service = Service()
    return webdriver.Chrome(service=service, options=options)

def scroll_page(driver):
    """Scroll progressif de la page."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    logging.info("✅ Scrolling terminé.")

def get_element_text(driver, selectors):
    """Récupère le texte d'un élément en utilisant une liste de sélecteurs CSS."""
    for selector in selectors:
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
            return clean_text(element.text)
        except (NoSuchElementException, InvalidSelectorException):
            continue
    return "Non spécifié"

def extract_prices(price_text):
    """Extrait les prix en gérant plusieurs formats."""
    logging.info(f"Texte brut des prix : {price_text}")  # Vérification des valeurs capturées
    prices = re.findall(r"\$?\d{1,3}(?:[.,]\d{2})?", price_text)  # Gère plusieurs formats
    logging.info(f"Prix extraits : {prices}")  # Vérification
    
    if len(prices) >= 2:
        return prices[0], prices[1]
    elif len(prices) == 1:
        return prices[0], "Non spécifié"
    return "Non spécifié", "Non spécifié"

def scrape_product_pricing(driver):
    """Scrape les informations principales du produit (prix, réductions)."""
    product_data = {"pricing": [], "discount": "0"}

    try:
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "product-price")))
        logging.info("✅ Section prix trouvée.")

        # Vérifier s'il y a une promotion active
        discount_selectors = [
            ".product-price div.id-text-white",
            ".module_price .id-bg-[#ff4014]"
        ]
        discount_text = get_element_text(driver, discount_selectors)
        has_discount = discount_text != "Non spécifié"
        product_data["discount"] = discount_text if has_discount else "0"

        # Récupérer les prix et quantités
        try:
            price_items = driver.find_elements(By.CSS_SELECTOR, ".price-item, .price-range")
            if price_items:
                for item in price_items:
                    try:
                        quantity_selectors = [".quality", ".min-moq"]
                        quantity_range = get_element_text(item, quantity_selectors)

                        price_selectors = [".price", "span.price"]
                        price_text = get_element_text(item, price_selectors)

                        discounted_price, original_price = extract_prices(price_text)

                        if not has_discount:
                            original_price = discounted_price
                            #discounted_price = original_price

                        product_data["pricing"].append({
                            "quantity_range": quantity_range,
                            "discounted_price": discounted_price,
                            "original_price": original_price
                        })

                    except Exception as e:
                        logging.error(f"❌ Erreur lors de l'extraction des prix : {e}")

            else:
                logging.warning("⚠️ Aucun prix trouvé.")

        except NoSuchElementException:
            logging.warning("⚠️ Impossible de récupérer les prix.")

    except TimeoutException:
        logging.error("❌ Impossible de charger les détails du produit.")

    return product_data

def scrape_product_attributes(driver):
    """Récupère les attributs du produit."""
    attributes_data = {}

    try:
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "attribute-info")))
        logging.info("✅ Section des attributs trouvée.")

        show_more_button = driver.find_element(By.CSS_SELECTOR, ".more-bg a")
        driver.execute_script("arguments[0].scrollIntoView(true);", show_more_button)
        time.sleep(2)

        if show_more_button.is_displayed():
            driver.execute_script("arguments[0].click();", show_more_button)
            time.sleep(3)

        attribute_items = driver.find_elements(By.CSS_SELECTOR, ".attribute-item")
        for item in attribute_items:
            try:
                attribute_name = clean_text(item.find_element(By.CSS_SELECTOR, ".left").text)
                attribute_value = clean_text(item.find_element(By.CSS_SELECTOR, ".right").text)
                attributes_data[attribute_name] = attribute_value
            except NoSuchElementException:
                continue

    except (NoSuchElementException, TimeoutException) as e:
        logging.error(f"❌ Erreur lors de l'extraction des attributs : {e}")

    return attributes_data

def scrape_reviews(driver, product_url):
    """Extraction des avis selon votre fonction originale qui marche bien."""
    driver.get(product_url)
    review_data = []

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "review-list"))
        )
        logging.info("✅ Module des avis trouvé !")
    except TimeoutException:
        logging.error("❌ Module des avis non trouvé.")
        return []

    page_number = 1

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        reviews = soup.find_all("div", class_="review-item")
        
        review_count = len(reviews)
        logging.info(f"📄 Page {page_number} - Nombre d'avis trouvés : {review_count}")
        
        if not reviews:
            logging.warning("❌ Aucun avis trouvé sur cette page.")
            break

        for review in reviews:
            try:
                full_stars = len(review.find_all("svg", class_="fa-star"))
                half_stars = len(review.find_all("svg", class_="fa-star-half"))
                rating = min(full_stars + 0.5 * half_stars, 5.0)
                
                avatar_info = review.find_previous("div", class_="avatar-info")
                review_meta = review.find_previous("div", class_="review-meta")

                if avatar_info:
                    date_tag = avatar_info.find("span", class_="date")
                    country_img = avatar_info.find("img")
                elif review_meta:
                    date_tag = review_meta.find("span", class_="date")
                    country_img = review_meta.find("img")
                else:
                    date_tag, country_img = None, None

                date = date_tag.text.strip() if date_tag else "N/A"
                country = country_img["src"].split("/")[-1].split(".")[0].upper() if country_img else "N/A"

                comment_tag = review.find("div", class_="review-content") or review.find("div", class_="review-info")
                comment = comment_tag.text.strip() if comment_tag else "N/A"

                review_data.append({
                    "rating": rating,
                    "date": date,
                    "country": country,
                    "comment": comment
                })

            except Exception as e:
                logging.error(f"⚠️ Erreur lors de l'extraction d'un avis : {e}")
        
        try:
            next_buttons = driver.find_elements(By.CSS_SELECTOR, ".detail-pagination-list button")
            active_index = next((i for i, btn in enumerate(next_buttons) if "active" in btn.get_attribute("class")), None)

            if active_index is not None and active_index < len(next_buttons) - 1:
                next_page_button = next_buttons[active_index + 1]
                driver.execute_script("arguments[0].scrollIntoView();", next_page_button)
                time.sleep(1)
                
                try:
                    next_page_button.click()
                    logging.info(f"➡️ Passage à la page {page_number + 1}...")
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", next_page_button)
                
                time.sleep(5)
                page_number += 1
            else:
                logging.info("✅ Dernière page atteinte.")
                break
        except (NoSuchElementException, TimeoutException):
            logging.info("✅ Fin de pagination.")
            break

    return review_data

def extract_supplier_info(driver):
    """Extraction des informations fournisseur selon votre fonction originale."""
    try:
        scroll_page(driver)
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".company-name a"))
        )
        logging.info("✅ Module du fournisseur trouvé !")

        soup = BeautifulSoup(driver.page_source, "html.parser")

        def extract_text_safe(soup, selectors, default="NA"):
            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    return element.get_text(strip=True)
            return default

        def extract_experience(soup):
            for item in soup.select(".header-item span"):
                text = item.get_text(strip=True)
                match = re.search(r"(\d+)\s*(?:ans|years|yrs|mois|months|-Year)", text, re.IGNORECASE)
                if match:
                    return f"{match.group(1)} ans"
            return "NA"

        def extract_supplier_type(soup):
            selectors = [".header-item:nth-child(2) span", ".supplier-type"]
            text = extract_text_safe(soup, selectors, default="NA")
            if re.match(r"^\d+\s*(ans|years|yrs)$", text, re.IGNORECASE):
                return "NA"
            return text

        def extract_location(soup):
            location = extract_text_safe(soup, [".header-item span:last-child"], default="NA")
            location = location.replace("Pays/Région :", "").replace("Located in", "").strip()
            if re.match(r"^\d+\s*(ans|years|yrs)$", location, re.IGNORECASE):
                return "NA"
            return location

        title_map = {
            "rating": "Évaluation du magasin",
            "évaluation": "Évaluation du magasin",
            "on-time delivery": "Taux de livraison",
            "livraison": "Taux de livraison",
            "response time": "Temps de réponse",
            "temps": "Temps de réponse",
            "revenue": "Chiffre d'affaires",
            "chiffre d'affaires": "Chiffre d'affaires",
            "floorspace": "Surface au sol",
            "surface": "Surface au sol",
            "superficie": "Surface au sol",
            "personnel": "Personnel",
            "staff": "Personnel",
            "markets": "Principaux marchés",
            "marchés": "Principaux marchés",
        }

        attributes = {
            "Évaluation du magasin": "NA",
            "Taux de livraison": "NA",
            "Temps de réponse": "NA",
            "Chiffre d'affaires": "NA",
            "Surface au sol": "NA",
            "Personnel": "NA",
            "Principaux marchés": "NA",
        }

        for item in soup.select(".attr-item"):
            title_elem = item.select_one(".attr-title")
            content_elem = item.select_one(".attr-content")

            if title_elem and content_elem:
                title = re.sub(r"\s+", " ", title_elem.get_text(strip=True).lower())
                content = content_elem.get_text(strip=True)

                for key, value in title_map.items():
                    if key in title:
                        attributes[value] = content
                        break

        supplier_link = soup.select_one(".company-name a")
        supplier_url = supplier_link["href"] if supplier_link else "NA"

        data = {
            "Nom du fournisseur": extract_text_safe(soup, [".company-name a"]),
            "Profil du fournisseur": supplier_url,
            "Type de fournisseur": extract_supplier_type(soup),
            "Années d'expérience": extract_experience(soup),
            "Localisation": extract_location(soup),
        }

        data.update(attributes)
        return data

    except Exception as e:
        logging.error(f"Erreur lors de l'extraction des données fournisseur : {e}")
        return None

def scrape_product(url):
    """Fonction principale de scraping."""
    driver = setup_driver()
    product_data = {}

    try:
        logging.info(f"🌍 Accès à l'URL produit : {url}")
        driver.get(url)
        scroll_page(driver)

        # Scraping des différentes sections
        product_data["details_attributes"] = {
            "pricing": scrape_product_pricing(driver),
            "attributes": scrape_product_attributes(driver)
        }
        product_data["reviews_supplier"] = {
            "reviews": scrape_reviews(driver, url),
            "supplier": extract_supplier_info(driver)
        }

        return product_data

    except Exception as e:
        logging.error(f"❌ Erreur lors du scraping du produit : {e}")
        return None

    finally:
        driver.quit()


def spi3(url):
    """Scrape tous informations sur chaque produit et les stocke dans les tables 'review', ' `products`."""
    # scraping
    data= scrape_product(url)
    # traitement
    clean_data=preprocess_data(data)
    # stockage
    db = SessionLocal()
    store_data(db, clean_data, url)
    print("Processus terminé!")
    
    return data

# Exécution de la fonction spi3
if __name__ == "__main__":
    url = "https://www.alibaba.com/product-detail/Chili-Garlic-Roasted-Peanuts-320g-Made_1600215160678.html"
    spi3(url)

    