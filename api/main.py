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
        if request.url.path.endswith((".css", ".js", ".ico")):
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


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Cette route servira la page d'accueil avec le formulaire HTML
    return templates.TemplateResponse("Page-1.html", {"request": request})

@app.get("/demo", response_class=HTMLResponse)
async def home(request: Request):
    # Cette route servira la page d'accueil avec le formulaire HTML
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/scrape/", response_class=HTMLResponse)
async def scrape(request: Request, db: Session = Depends(get_db)):
    # Appelle le scraper et insère les données dans la base
    scraped_data = scrape_alibaba()  # Appelle ton script Selenium
    for title, link in scraped_data.items():
        db.add(Categorie(title=title, link=link))
    db.commit()
    
    # Renvoie un message à afficher sur la page HTML après le scraping
    message = "Scraping terminé avec succès"
    return templates.TemplateResponse("index.html", {"request": request, "message": message})

@app.get("/categories/")
def get_products(db: Session = Depends(get_db)):
    return db.query(Categorie).all()


@app.post("/products/", response_class=HTMLResponse)
async def scrape(request: Request, db: Session = Depends(get_db)):
    # Appelle le scraper et insère les données dans la base
    scraped_data = spi2()  # Appelle ton script Selenium
    for title, link in scraped_data.items():
        db.add(Produit(title=title, link=link))
    db.commit()




