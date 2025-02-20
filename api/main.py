from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .database import get_db
from .models import Categorie, Produit
from scraper.les_spiders.spi1 import scrape_alibaba
from scraper.les_spiders.spi2 import spi2# Import du scraper Selenium
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from .metrics import metrics_middleware
from prometheus_fastapi_instrumentator import Instrumentator
from typing import List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.responses import JSONResponse
from pathlib import Path



# Obtenir le chemin absolu du dossier "static"
static_path = Path(__file__).parent.parent / "static"




app = FastAPI(
    title="API Alibaba Scraper",
    description="Accède aux données extraites d'Alibaba.",
    version="1.0")

"""
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

#from database import Base, engine

# Crée les tables dans la base de données
#Base.metadata.create_all(bind=engine)


REQUEST_COUNT = Counter("request_count", "Total des requêtes", ["endpoint"])
"""

app.middleware("http")(metrics_middleware)

BASE_DIR = Path(__file__).resolve().parent.parent # Obtient le chemin absolu
print(f"Base directory : {BASE_DIR}")  # <-- Debugging

# Monter les fichiers statiques
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Configurer les templates
templates = Jinja2Templates(directory=BASE_DIR / "templates")


class ExcludeStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Exclure les requêtes vers CSS, JS et ICO
        if request.url.path.endswith((".css", ".js", ".ico", ".jpg", ".png")):
            return Response(status_code=404)  # Répondre directement avec une erreur 404
        return await call_next(request)

    
#app.add_middleware(ExcludeStaticMiddleware)

@app.get("/metrics")
def get_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/metrics_json")
def get_metrics_json():
    raw_metrics = generate_latest().decode("utf-8").split("\n")
    
    formatted_metrics = {}
    for line in raw_metrics:
        if line and not line.startswith("#"):  # Ignorer les commentaires
            parts = line.split(" ")
            if len(parts) == 2:
                key, value = parts
                formatted_metrics[key] = float(value)

    return formatted_metrics

# URL de ton dashboard Grafana (remplace par ton lien)
GRAFANA_DASHBOARD_URL = "http://localhost:3000/public-dashboards/b60daaf626454322823e5e824e038c73"

import urllib3
urllib3.disable_warnings()

@app.get("/tb", response_class=HTMLResponse)
async def tb():
    grafana_url = "http://localhost:3100/d/ganitachi/dash2?orgId=1"
    html_content = f"""
    <html>
    <head>
        <title>Monitoring API - Grafana</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background-color: #f4f4f4;
            }}
            .container {{
                width: 80%;
                height: 90vh;
                background: white;
                border-radius: 8px;
                box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2);
                overflow: hidden;
            }}
            iframe {{
                width: 100%;
                height: 100%;
                border: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            
            <iframe 
                src="http://localhost:3100/d/ganitachi/dash2?orgId=1&from=1739482925152&to=1739486525152&theme=light"
                width="100%"
                height="500"
                frameborder="0"
                allowfullscreen>
            </iframe>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Cette route servira la page d'accueil avec le formulaire HTML
    return templates.TemplateResponse("Home.html", {"request": request})

@app.get("/choix", response_class=HTMLResponse)
async def home(request: Request):
    # Cette route servira la page d'accueil avec le formulaire HTML
    return templates.TemplateResponse("Choix.html", {"request": request})

@app.get("/Categorie", response_class=HTMLResponse)
async def home(request: Request):
    # Cette route servira la page d'accueil avec le formulaire HTML
    return templates.TemplateResponse("Scrap_Cat.html", {"request": request})

@app.get("/Produit", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    categories = db.query(Categorie).all()
    # Cette route servira la page d'accueil avec le formulaire HTML
    return templates.TemplateResponse("Scrap_Produit.html", {"request": request, "categories": categories})

@app.get("/Documentation", response_class=HTMLResponse)
async def home(request: Request):
    # Cette route servira la page d'accueil avec le formulaire HTML
    return templates.TemplateResponse("Documentation.html", {"request": request})

@app.get("/APropos", response_class=HTMLResponse)
async def home(request: Request):
    # Cette route servira la page d'accueil avec le formulaire HTML
    return templates.TemplateResponse("A-propos.html", {"request": request})

@app.get("/categories/")
def get_products(db: Session = Depends(get_db)):
    return db.query(Categorie).all()

@app.post("/scrape", response_class=HTMLResponse)
async def scrape(request: Request, db: Session = Depends(get_db)):
    db.query(Categorie).delete()
    db.commit()
    # Appelle le scraper et insère les données dans la base
    data = scrape_alibaba()
    scraped_data = data[0] # Appelle ton script Selenium
    etat = data[1]
    taille = data[2]
    #etat = etat.status_code
    for title, link in scraped_data.items():
        db.add(Categorie(title=title, link=link))
    db.commit()
    categories = db.query(Categorie).all()
    #categories_dict = [category.to_dict() for category in categories]
    # Renvoie un message à afficher sur la page HTML après le scraping
    message = "Scraping terminé avec succès"
    return templates.TemplateResponse("Scrap_Cat.html", {"request": request, "message": message, "categories": categories, "categories_dict": scraped_data, "etat" : etat, "taille" : taille})


@app.get("/produits/{title}", response_class=HTMLResponse)
async def produits_par_categorie(title: str, request: Request, db: Session = Depends(get_db)):
    # Filtrer les catégories par le titre
    
    scraped_data = spi2(title)  # Appelle ton script Selenium
    taille = len(scraped_data)
    for item in scraped_data:  # itérer sur chaque objet dans le tableau
        titre = item['title']  # récupère le titre
        link = item['url']  # récupère l'URL
        if link:  # Vérifie que le lien n'est pas vide
            produit = Produit(title=titre, link=link, categorie_id=title)  # Utilise le titre pour la catégorie
            db.add(produit)
    db.commit()

    categories = db.query(Categorie).all()


    categories = db.query(Categorie).all()
    Ma_Cat = db.query(Categorie).filter(Categorie.title == title).all()
    # Récupérer les produits qui appartiennent à cette catégorie
    produits = db.query(Produit).filter(Produit.categorie_id == title).all()
    
    return templates.TemplateResponse("Scrap_Produit.html", {
        "request": request, 
        "categories": categories,
        "produits": produits,
        "dicto" : scraped_data,
        "Ma_Cat" : Ma_Cat,
        "taille" : taille
    })




