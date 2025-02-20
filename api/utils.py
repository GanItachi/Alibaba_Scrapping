import re
import json
from datetime import datetime
from sqlalchemy.orm import Session
from api.models import Produit, ProduitDetails, Pricing, Supplier, Review

def clean_text(text):
    """Nettoie une chaîne de texte et remplace les valeurs vides par 'Non spécifié'."""
    return text.strip() if text and text.strip() else "Non spécifié"



import re
from datetime import datetime

def preprocess_data(raw_data):
    """
    Fonction pour prétraiter les données brutes avant insertion dans la base.
    """

    if not raw_data:
        print("⚠️ Aucune donnée à traiter.")
        return {}

    details = raw_data.get("details_attributes", {})
    pricing_data = details.get("pricing", {}).get("pricing", [])
    attributes = details.get("attributes", {})

    # ✅ Extraction des prix (garder en string, mais nettoyer)
    processed_pricing = []
    for price in pricing_data:
        try:
            processed_pricing.append({
                "quantity": price.get("quantity_range", "").strip(),
                "discounted_price": price.get("discounted_price", "").replace("$", "").strip(),
                "original_price": price.get("original_price", "").replace("$", "").strip()
            })
        except Exception as e:
            print(f"⚠️ Erreur lors du traitement des prix : {e}")

    # ✅ Extraction des avis (conversion date)
    reviews_data = raw_data.get("reviews_supplier", {}).get("reviews", [])
    processed_reviews = []
    for review in reviews_data:
        try:
            review_date = None
            if review.get("date"):
                try:
                    review_date = datetime.strptime(review["date"], "%b %d, %Y").date()
                except ValueError:
                    review_date = None  # Format incorrect, on ignore

            processed_reviews.append({
                "rating": float(review.get("rating", 0)),
                "comment": review.get("comment", "").strip(),
                "date": review_date,
                "reviewer_country": review.get("country", "").strip()
            })
        except Exception as e:
            print(f"⚠️ Erreur lors du traitement des avis : {e}")

    # ✅ Extraction des infos du fournisseur
    supplier_data = raw_data.get("reviews_supplier", {}).get("supplier", {})

    # ✅ Conversion de "Années d'expérience" en int
    experience_str = supplier_data.get("Années d'expérience", "").strip()
    experience_match = re.search(r"\d+", experience_str)
    experience_years = int(experience_match.group()) if experience_match else None

    # ✅ Conversion de "Surface au sol" en float (NA -> None)
    floorspace_str = supplier_data.get("Surface au sol", "").replace("m²", "").strip()
    try:
        floorspace = float(floorspace_str) if floorspace_str.replace(".", "", 1).isdigit() else None
    except ValueError:
        floorspace = None

    # ✅ Conversion de "Évaluation du magasin" en float
    try:
        store_rating = float(supplier_data.get("Évaluation du magasin", "0").split("/")[0]) if supplier_data.get("Évaluation du magasin") else None
    except ValueError:
        store_rating = None

    # ✅ Conversion de "Taux de livraison" en float
    try:
        delivery_rate = float(supplier_data.get("Taux de livraison", "0").replace("%", "").strip()) if supplier_data.get("Taux de livraison") else None
    except ValueError:
        delivery_rate = None

    # ✅ Conversion de "Personnel" en int
    try:
        staff = int(supplier_data.get("Personnel", "0")) if supplier_data.get("Personnel") else None
    except ValueError:
        staff = None

    processed_supplier = {
        "company_name": supplier_data.get("Nom du fournisseur", "").strip(),
        "company_profile_link": supplier_data.get("Profil du fournisseur", "").strip(),
        "supplier_type": supplier_data.get("Type de fournisseur", "").strip(),
        "experience_years": experience_years,
        "location": supplier_data.get("Localisation", "").strip(),
        "store_rating": store_rating,
        "delivery_rate": delivery_rate,
        "response_time": supplier_data.get("Temps de réponse", "").strip(),
        "revenue": supplier_data.get("Chiffre d'affaires", "").strip(),
        "floorspace": floorspace,
        "staff": staff,
        "main_markets": supplier_data.get("Principaux marchés", "").strip()
    }

    return {
        "details": {
            "discount": details.get("pricing", {}).get("discount", "").strip(),
            "attributes": attributes
        },
        "pricing": processed_pricing,
        "reviews": processed_reviews,
        "supplier": processed_supplier
    }



def store_data(db: Session, clean_data: dict, url: str):
    """
    Stocke les données prétraitées dans les tables correspondantes.
    """
    try:
        # 1️⃣ ✅ Récupération du produit basé sur l'URL
        product = db.query(Produit).filter(Produit.link == url).first()

        if not product:
            print(f"⚠️ Produit introuvable pour l'URL: {url}")
            return
        
        product_id = product.id  

        # 2️⃣ ✅ Insertion du fournisseur
        supplier_data = clean_data.get("supplier", {})
        supplier = Supplier(
            company_name=supplier_data.get("company_name"),
            company_profile_link=supplier_data.get("company_profile_link"),
            supplier_type=supplier_data.get("supplier_type"),
            experience_years=supplier_data.get("experience_years"),
            location=supplier_data.get("location"),
            store_rating=supplier_data.get("store_rating"),
            delivery_rate=supplier_data.get("delivery_rate"),
            response_time=supplier_data.get("response_time"),
            revenue=supplier_data.get("revenue"),
            floorspace=supplier_data.get("floorspace"),
            staff=supplier_data.get("staff"),
            main_markets=supplier_data.get("main_markets"),
        )
        db.add(supplier)
        db.commit()
        db.refresh(supplier)  # ✅ Récupérer l'ID du fournisseur

        # 3️⃣ ✅ Insertion des détails du produit
        details_data = clean_data.get("details", {})
        produit_details = ProduitDetails(
            produit_id=product_id,  # ✅ Correction ici
            url=url,
            discount=details_data.get("discount"),
            attributes=details_data.get("attributes"),
            supplier_id=supplier.id  # ✅ Lien avec le fournisseur
        )
        db.add(produit_details)
        db.commit()
        db.refresh(produit_details)  # ✅ Récupérer l'ID du détail du produit

        # 4️⃣ ✅ Insertion des prix
        for price_data in clean_data.get("pricing", []):
            pricing = Pricing(
                produit_id=produit_details.id,  # ✅ Correction ici
                quantity=price_data.get("quantity"),
                discounted_price=price_data.get("discounted_price"),
                original_price=price_data.get("original_price")
            )
            db.add(pricing)

        db.commit()

        # 5️⃣ ✅ Insertion des avis clients
        for review_data in clean_data.get("reviews", []):
            review = Review(
                produit_id=produit_details.id,  # ✅ Correction ici
                rating=review_data.get("rating"),
                comment=review_data.get("comment"),
                date=review_data.get("date"),
                reviewer_country=review_data.get("reviewer_country")
            )
            db.add(review)

        db.commit()

        print("✅ Données insérées avec succès !")

    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de l'insertion des données: {e}")

    finally:
        db.close()  # Fermeture de la session proprement




