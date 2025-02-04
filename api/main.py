from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .database import get_db
from .models import Categorie, Produit
from scraper.les_spiders.spi1 import scrape_alibaba
from scraper.les_spiders.spi2 import spi2# Import du scraper Selenium
from fastapi.staticfiles import StaticFiles

app = FastAPI()

#from database import Base, engine

# Crée les tables dans la base de données
#Base.metadata.create_all(bind=engine)


# Configurer Jinja2 pour servir des fichiers HTML
templates = Jinja2Templates(directory="templates")

# Définir le dossier contenant les fichiers statiques
app.mount("/static", StaticFiles(directory="static"), name="static")

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




