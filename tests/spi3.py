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
import sys
from pathlib import Path
import tempfile
import os
import json
from datetime import datetime
from api.utils import preprocess_data

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def setup_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("prefs", {"translate": {"enabled": False}, "intl.accept_languages": "en,en-US"})
    service = Service()
    return webdriver.Chrome(service=service, options=chrome_options)

def scroll_page(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    logging.info("✅ Scrolling terminé.")

def set_currency(driver, currency="XOF"):
    """Change la devise sur la page Alibaba en cliquant sur 'Save' après sélection."""
    try:
        # Localiser l'élément de sélection de devise
        currency_selector = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".current"))
        )
        current_currency = currency_selector.text.strip()
        logging.info(f"Devise actuelle : {current_currency}")
        if f"English-{currency}" in current_currency or currency in current_currency:
            logging.info(f"✅ Devise déjà réglée sur {currency}.")
            return
        
        currency_selector.click()
        logging.info("✅ Menu de devise ouvert.")

        # Attendre que le popup ou la modale s'ouvre
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "popup-root"))
        )

        # Trouver l'option de devise dans la modale
        currency_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//li[contains(text(), '{currency}')] | //*[contains(@class, 'currency-item') and contains(text(), '{currency}') or contains(text(), '{currency} - CFA Franc BCEAO')] | //option[contains(text(), '{currency}')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", currency_option)
        currency_option.click()
        logging.info(f"✅ Option de devise {currency} sélectionnée.")

        # Cliquer sur le bouton "Save" (hypothèse générique, ajuste selon l'HTML)
        save_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Save')] | //button[contains(@class, 'save-button')] | //*[contains(text(), 'Apply') or contains(text(), 'Confirmer')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", save_button)
        save_button.click()
        logging.info("✅ Bouton 'Save' cliqué.")

        # Vérifier que la devise a bien été changée
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element((By.CSS_SELECTOR, ".hide-item[data-tnhkey='Language-Text']"), f"English-{currency}")
        )
        logging.info(f"✅ Confirmation : Devise changée en {currency}.")
        time.sleep(3)  # Attendre que la page se recharge complètement
    except TimeoutException:
        logging.warning(f"⚠️ Impossible de changer la devise en {currency}, utilisation de la devise par défaut.")
    except Exception as e:
        logging.error(f"❌ Erreur lors du changement de devise : {e}")

def get_element_text(driver, selectors):
    for selector in selectors:
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
            return clean_text(element.text)
        except (NoSuchElementException, InvalidSelectorException):
            continue
    return "Non spécifié"

def clean_text(text):
    return text.strip() if text else "Non spécifié"

def extract_prices(price_text):
    logging.info(f"Texte brut des prix : {price_text}")
    # Accepter les devises avec symbole ou sans, suivi d'un nombre avec décimaux
    prices = re.findall(r"(?:[A-Z]{3}\s*)?\d+(?:[.,]\d{1,3})?", price_text)
    logging.info(f"Prix extraits : {prices}")
    if len(prices) >= 2:
        return prices[0], prices[1]
    elif len(prices) == 1:
        return prices[0], "Non spécifié"
    return "Non spécifié", "Non spécifié"

def scrape_product_pricing(driver, currency="XOF"):
    product_data = {"pricing": [], "discount": "0"}
    try:
        set_currency(driver, currency)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "product-price")))
        logging.info("✅ Section prix trouvée.")
        discount_selectors = [".product-price div.id-text-white", ".module_price .id-bg-[#ff4014]"]
        discount_text = get_element_text(driver, discount_selectors)
        has_discount = discount_text != "Non spécifié"
        product_data["discount"] = discount_text if has_discount else "0"

        price_items = driver.find_elements(By.CSS_SELECTOR, ".price-item, .price-range")
        if price_items:
            for item in price_items:
                try:
                    quantity_range = get_element_text(item, [".quality", ".min-moq"])
                    price_text = get_element_text(item, [".price", "span.price"])
                    discounted_price, original_price = extract_prices(price_text)
                    if not has_discount:
                        original_price = discounted_price
                    product_data["pricing"].append({
                        "quantity_range": quantity_range,
                        "discounted_price": discounted_price,
                        "original_price": original_price
                    })
                except Exception as e:
                    logging.error(f"❌ Erreur lors de l'extraction des prix : {e}")
        else:
            logging.warning("⚠️ Aucun prix trouvé.")
    except TimeoutException:
        logging.error("❌ Impossible de charger les détails du produit.")
    return product_data

def scrape_product_attributes(driver):
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
    driver.get(product_url)
    review_data = []
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "review-list")))
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
                date_tag = avatar_info.find("span", class_="date") if avatar_info else (review_meta.find("span", class_="date") if review_meta else None)
                country_img = avatar_info.find("img") if avatar_info else (review_meta.find("img") if review_meta else None)

                date = date_tag.text.strip() if date_tag else "N/A"
                country = country_img["src"].split("/")[-1].split(".")[0].upper() if country_img else "N/A"
                comment = review.find("div", class_="review-content") or review.find("div", class_="review-info")
                comment = comment.text.strip() if comment else "N/A"

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
    try:
        scroll_page(driver)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".id-relative.id-overflow-hidden.id-rounded-lg"))
        )
        logging.info("✅ Module du fournisseur trouvé !")

        soup = BeautifulSoup(driver.page_source, "html.parser")

        def extract_text_safe(soup, selectors, default="NA"):
            for selector in selectors:
                try:
                    element = soup.select_one(selector)
                    if element:
                        return element.get_text(strip=True)
                except Exception as e:
                    logging.warning(f"⚠️ Erreur avec le sélecteur {selector} : {e}")
            return default

        def extract_experience(soup):
            text = extract_text_safe(soup, [".id-flex.id-items-center.id-text-xs"])
            match = re.search(r"(\d+)\s*(?:ans|years|yrs)", text, re.IGNORECASE)
            return f"{match.group(1)} ans" if match else "NA"

        def extract_supplier_type(soup):
            text = extract_text_safe(soup, [".id-flex.id-items-center.id-text-xs"])
            if "Manufacturer" in text or "Trading Company" in text or "Custom manufacturer" in text:
                parts = text.split("on Alibaba.com")
                return parts[0].strip() if "on Alibaba.com" in text else text
            return "NA"

        def extract_location(soup):
            # Recherche basée sur le texte "Located in" avec BeautifulSoup
            try:
                location_elements = soup.find_all("span", text=lambda text: text and "Located in" in text)
                for element in location_elements:
                    if "Located in" in element.get_text(strip=True):
                        location = element.get_text(strip=True)
                        return location.replace("Located in", "").strip()
                # Fallback avec sélecteurs CSS si texte non trouvé
                location = extract_text_safe(soup, [
                    ".id-mt-1.id-flex.id-items-center.id-gap-0.5.id-text-xs span",
                    ".id-text-xs span"
                ])
                return location.replace("Located in", "").strip() if location and "Located in" in location else "NA"
            except Exception as e:
                logging.error(f"⚠️ Erreur lors de l'extraction de la localisation : {e}")
                return "NA"
            
        title_map = {
            "rating": "Évaluation du magasin",
            "store rating": "Évaluation du magasin",
            "on-time delivery": "Taux de livraison",
            "response time": "Temps de réponse",
            "revenue": "Chiffre d'affaires",
            "online revenue": "Chiffre d'affaires",
            "floorspace": "Surface au sol",
            "staff": "Personnel",
            "markets": "Principaux marchés",
            "main markets": "Principaux marchés"
        }

        attributes = {
            "Évaluation du magasin": "NA",
            "Taux de livraison": "NA",
            "Temps de réponse": "NA",
            "Chiffre d'affaires": "NA",
            "Surface au sol": "NA",
            "Personnel": "NA",
            "Principaux marchés": "NA"
        }

        performance_section = soup.select_one(".id-z-10.id-mt-5.id-rounded-lg.id-bg-white")
        if performance_section:
            for button in performance_section.select("button"):
                title_elem = button.select_one(".company_card_online_performance_value")
                content_elem = button.select_one(".id-text-xl.id-font-semibold")
                if title_elem and content_elem:
                    title = re.sub(r"\s+", " ", title_elem.get_text(strip=True).lower())
                    content = content_elem.get_text(strip=True)
                    for key, value in title_map.items():
                        if key in title:
                            attributes[value] = content
                            break

        markets = []
        markets_section = soup.select(".id-mt-3.id-flex.id-flex-wrap.id-items-center .id-flex.id-items-center span.id-ms-1.id-text-xs")
        if markets_section:
            markets = [market.text.strip() for market in markets_section]
        attributes["Principaux marchés"] = ", ".join(markets) if markets else "NA"

        overview_section = soup.select_one(".id-mt-4.id-grid.id-w-full.id-grid-flow-row.id-grid-cols-2")
        if overview_section:
            for item in overview_section.select("div.id-truncate"):
                text = item.get("title", "NA")
                if "Floorspace" in text:
                    attributes["Surface au sol"] = text.replace("Floorspace:", "").strip()
                elif "Staff" in text:
                    attributes["Personnel"] = text.replace("Staff:", "").strip()

        data = {
            "Nom du fournisseur": extract_text_safe(soup, [".id-text-sm.id-font-semibold.id-underline"]),
            "Profil du fournisseur": soup.select_one(".id-text-sm.id-font-semibold.id-underline")["href"] if soup.select_one(".id-text-sm.id-font-semibold.id-underline") else "NA",
            "Type de fournisseur": extract_supplier_type(soup),
            "Années d'expérience": extract_experience(soup),
            "Localisation": extract_location(soup),
        }
        data.update(attributes)
        return data

    except Exception as e:
        logging.error(f"❌ Erreur lors de l'extraction des données fournisseur : {e}")
        return {
            "Nom du fournisseur": "NA",
            "Profil du fournisseur": "NA",
            "Type de fournisseur": "NA",
            "Années d'expérience": "NA",
            "Localisation": "NA",
            "Évaluation du magasin": "NA",
            "Taux de livraison": "NA",
            "Temps de réponse": "NA",
            "Chiffre d'affaires": "NA",
            "Surface au sol": "NA",
            "Personnel": "NA",
            "Principaux marchés": "NA"
        }

def scrape_product(url, currency="XOF"):
    driver = setup_driver()
    product_data = {}
    try:
        logging.info(f"🌍 Accès à l'URL produit : {url}")
        driver.get(url)
        scroll_page(driver)

        product_data["details_attributes"] = {
            "pricing": scrape_product_pricing(driver, currency),
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

def spi3(url, currency="XOF"):
    data = scrape_product(url, currency)
    clean_data = preprocess_data(data)
    print(clean_data)
    print("Processus terminé!")
    return clean_data

if __name__ == "__main__":
    url = "https://www.alibaba.com/product-detail/Wholesale-Top-Quality-Heavyweight-Custom-420G_1601378754409.html?spm=a2700.shop_index.89.3.7018edb5E0bXUO"
    currency = input("Entrez la devise souhaitée (par défaut XOF) : ") or "XOF"
    spi3(url, currency)