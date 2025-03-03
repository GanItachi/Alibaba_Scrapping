from fastapi import FastAPI, Depends, Request, Form
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
from scraper.les_spiders.spi3 import spi3,setup_driver, scrape_product_pricing, scrape_product, scrape_product_attributes, scrape_reviews, extract_supplier_info
from scraper.les_spiders.spi4 import scrape_alibaba_products
import json
from fastapi import FastAPI, Depends, Response
from fastapi.responses import JSONResponse, StreamingResponse
import io
import os
import csv
import pandas as pd
from api.utils import format_price, parse_min_order
#from .celery_config import scrape_categories_task
from fastapi.responses import RedirectResponse
#from celery.result import AsyncResult
# Obtenir le chemin absolu du dossier "static"
static_path = Path(__file__).parent.parent / "static"
from .scheduler import start_scheduler
#from .celery_config import celery
from celery.result import AsyncResult
from .tasks import scrape_all_produits
from .celery_config import celery_app

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
start_scheduler()
app.middleware("http")(metrics_middleware)

BASE_DIR = Path(__file__).resolve().parent.parent # Obtient le chemin absolu
print(f"Base directory : {BASE_DIR}")  # <-- Debugging

# Détecter le chemin absolu du dossier 'static'
static_path = os.path.join(os.path.dirname(__file__), "..", "static")

# Monter le dossier 'static' sous '/static'
app.mount("/static", StaticFiles(directory=static_path), name="static")

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
            .fullscreen-btn {{
                position: absolute;
                top: 10px;
                right: 10px;
                background-color: #007bff;
                color: white;
                border: none;
                padding: 10px 15px;
                font-size: 14px;
                cursor: pointer;
                border-radius: 5px;
                transition: 0.3s;
            }}
            .fullscreen-btn:hover {{
                background-color: #0056b3;
            }}
        </style>
    </head>
    <body>
    
        <div class="container" id="iframeContainer">
            <button class="fullscreen-btn" onclick="toggleFullScreen()">⛶ Plein écran</button>
            <iframe 
                src="http://localhost:3100/d/ganitachi/dash2?orgId=1&from=1739482925152&to=1739486525152&theme=light"
                width="100%"
                height="500"
                frameborder="0"
                allowfullscreen>
            </iframe>
        </div>
        <script>
            function toggleFullScreen() {{
                var iframeContainer = document.getElementById("iframeContainer");
                if (!document.fullscreenElement) {{
                    if (iframeContainer.requestFullscreen) {{
                        iframeContainer.requestFullscreen();
                    }} else if (iframeContainer.mozRequestFullScreen) {{
                        iframeContainer.mozRequestFullScreen();
                    }} else if (iframeContainer.webkitRequestFullscreen) {{
                        iframeContainer.webkitRequestFullscreen();
                    }} else if (iframeContainer.msRequestFullscreen) {{
                        iframeContainer.msRequestFullscreen();
                    }}
                }} else {{
                    if (document.exitFullscreen) {{
                        document.exitFullscreen();
                    }} else if (document.mozCancelFullScreen) {{
                        document.mozCancelFullScreen();
                    }} else if (document.webkitExitFullscreen) {{
                        document.webkitExitFullscreen();
                    }} else if (document.msExitFullscreen) {{
                        document.msExitFullscreen();
                    }}
                }}
            }}
        </script>
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

@app.get("/Types", response_class=HTMLResponse)
async def home(request: Request):
    # Cette route servira la page d'accueil avec le formulaire HTML
    return templates.TemplateResponse("Types.html", {"request": request})

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

@app.get("/Donnees", response_class=HTMLResponse)
async def home(request: Request):
    # Cette route servira la page d'accueil avec le formulaire HTML
    return templates.TemplateResponse("Faits.html", {"request": request})

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
        price_min, price_max = format_price(item['price'])
        discounted_price = item['discounted_price']
        min_order_qty, min_order_unit = parse_min_order(item['min_order'])

        if link:  # Vérifie que le lien n'est pas vide
            produit = Produit(
                title=titre,
                link=link,
                price_min=price_min,
                price_max=price_max,
                discounted_price = discounted_price,
                min_order_qty=min_order_qty,
                min_order_unit=min_order_unit,
                categorie_id=title  # Utilise le titre pour la catégorie
            )
            db.add(produit)

            db.commit()


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
    

    
@app.get("/InfoProd", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/InfoProd/URL")
async def scrapeprod(url: str):
    # driver = setup_driver()
    # driver.get(url)

    # data = {
    #     "pricing": scrape_product_pricing(driver),
    #     "attributes": scrape_product_attributes(driver),
    #     "reviews": scrape_reviews(driver, url),
    #     "supplier": extract_supplier_info(driver),
    # }
    

    #driver.quit()
    
    data = spi3(url)
    
    
    return data

@app.get("/search")
def home(request: Request):
    return templates.TemplateResponse("Recherch_prod.html", {"request": request, "results": None})

@app.post("/search/Prod")
def search(request: Request, keyword: str = Form(...), max_pages: int = Form(2)):
    results = scrape_alibaba_products(keyword, max_pages)
    return templates.TemplateResponse("Recherch_prod.html", {"request": request, "results": results, "keyword": keyword})

# Importe tes modèles
from .models import Produit  # adapter l'import en fonction de ta structure
# Assure-toi d'importer aussi get_db qui fournit ta session SQLAlchemy

###################################################################################
#-------------------------------Recup Base----------------------------------------#
###############################################################################

def get_categorie(db: Session):
    """Récupère toutes les catégories sous forme de liste de dictionnaires."""
    categories = db.query(Categorie).all()
    return [
        {
            "Titre": cat.title,
            "Lien": cat.link
        } 
        for cat in categories
    ]

def get_products(db: Session):
    """Récupère tous les produits sous forme de liste de dictionnaires."""
    produits = db.query(Produit).all()
    return [
        {
            "id": prod.id,
            "title": prod.title,
            "link": prod.link,
            "min_order_qty": prod.min_order_qty,
            "min_order_unit": prod.min_order_unit,
            "price_min": prod.price_min,
            "price_max": prod.price_max,
            "discounted_price": prod.discounted_price,
            "categorie": prod.categorie.title if prod.categorie else None,
        }
        for prod in produits
    ]

@app.get("/download/{data_type}/json", summary="Télécharger les catégories ou produits au format JSON")
def download_json(data_type: str, db: Session = Depends(get_db)):
    """
    Endpoint pour télécharger les catégories ou les produits en JSON.
    - `data_type` : "categories" pour les catégories, "products" pour les produits.
    """
    if data_type == "categories":
        data = get_categorie(db)
    elif data_type == "products":
        data = get_products(db)
    else:
        return JSONResponse(content={"error": "Type de données invalide"}, status_code=400)
    
    return JSONResponse(content=data)

@app.get("/download/{data_type}/csv", summary="Télécharger les catégories ou produits au format CSV")
def download_csv(data_type: str, db: Session = Depends(get_db)):
    """
    Endpoint pour télécharger les catégories ou les produits en CSV.
    - `data_type` : "categories" pour les catégories, "products" pour les produits.
    """
    if data_type == "categories":
        data = get_categorie(db)
    elif data_type == "products":
        data = get_products(db)
    else:
        return JSONResponse(content={"error": "Type de données invalide"}, status_code=400)
    
    if not data:
        return JSONResponse(content={"error": "Aucune donnée disponible"}, status_code=404)
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)

    output.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{data_type}.csv"'}
    return Response(content=output.getvalue(), media_type="text/csv", headers=headers)

@app.get("/download/{data_type}/excel", summary="Télécharger les catégories ou produits au format Excel")
def download_excel(data_type: str, db: Session = Depends(get_db)):
    """
    Endpoint pour télécharger les catégories ou les produits en Excel.
    - `data_type` : "categories" pour les catégories, "products" pour les produits.
    """
    if data_type == "categories":
        data = get_categorie(db)
    elif data_type == "products":
        data = get_products(db)
    else:
        return JSONResponse(content={"error": "Type de données invalide"}, status_code=400)
    
    if not data:
        return JSONResponse(content={"error": "Aucune donnée disponible"}, status_code=404)
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=data_type.capitalize())

    output.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{data_type}.xlsx"'}
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )
    
    

@app.api_route("/start_scraping", methods=["GET", "POST"])
def start_scraping():
    """ Lance le scraping de toutes les produits. """
    task = scrape_all_produits.delay()
    return {"task_id": task.id}

@app.get("/task_status/{task_id}")
def get_task_status(task_id: str):
    """ Récupère l'état de la tâche Celery. """
    task = AsyncResult(task_id, app=celery_app)
    if task.state == "PENDING":
        response = {"state": task.state, "progress": "0%"}
    elif task.state == "PROGRESS":
        progress = task.info
        response = {
            "state": task.state,
            "current_category": progress["category"],
            "progress": f"{progress['current']} / {progress['total']}"
        }
    elif task.state == "SUCCESS":
        response = {"state": "COMPLETED", "result": task.result}
    else:
        response = {"state": task.state, "info": str(task.info)}

    return response