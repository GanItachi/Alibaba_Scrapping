from .celery_workers import celery_app
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Categorie, Produit
from .utils import format_price, parse_min_order

import time

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scraper.les_spiders.spi1 import scrape_alibaba # Assure-toi que cette fonction existe et fonctionne
from scraper.les_spiders.spi2 import spi2


@celery_app.task
def scrape_and_store():
    db: Session = SessionLocal()  # Récupérer une nouvelle session propre à Celery

    try:
        db.query(Categorie).delete()  # Supprimer les anciennes données
        db.commit()

        # Exécuter le scraping
        data = scrape_alibaba()
        scraped_data, etat, taille = data

        # Stocker les nouvelles données
        for title, link in scraped_data.items():
            db.add(Categorie(title=title, link=link))
        db.commit()

    
        return {"message": "Scraping terminé", "etat": etat, "taille": taille}
    
    except Exception as e:
        db.rollback()
        raise e  # Pour que Celery logge l'erreur
    
    finally:
        db.close()  # Toujours fermer la session proprement



@celery_app.task(bind=True)
def scrape_all_produits(self):
    """ Scrape toutes les catégories et insère les produits dans la base. """
    db: Session = SessionLocal()
    categories = db.query(Categorie).all()
    total_categories = len(categories)

    for i, cat in enumerate(categories):
        title = cat.title
        scraped_data = spi2(title)  # Exécute le scraping Selenium

        for item in scraped_data:
            titre = item['title']
            link = item['url']
            price_min, price_max = format_price(item['price'])
            discounted_price = item['discounted_price']
            min_order_qty, min_order_unit = parse_min_order(item['min_order'])

            if link:  # Vérifie que le lien n'est pas vide
                produit = Produit(
                    title=titre,
                    link=link,
                    price_min=price_min,
                    price_max=price_max,
                    discounted_price=discounted_price,
                    min_order_qty=min_order_qty,
                    min_order_unit=min_order_unit,
                    categorie_id=title
                )
                db.add(produit)

        db.commit()

        # Mettre à jour l'état de la tâche
        self.update_state(
            state="PROGRESS",
            meta={
                "current": i + 1,
                "total": total_categories,
                "category": title
            }
        )
        time.sleep(2)  # Simulation d'attente

    db.close()
    return {"status": "COMPLETED", "total_categories": total_categories}

