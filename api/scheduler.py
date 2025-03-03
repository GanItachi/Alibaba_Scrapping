from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from celery.result import AsyncResult
from .tasks import scrape_and_store, scrape_all_produits

def run_scraping():
    task = scrape_and_store.delay()  # Lancer la tâche Celery
    print(f"🔄 Scraping lancé avec l'ID : {task.id}")
    
    
def start_scraping():
    task = scrape_all_produits.delay()
    print(f"🔄 Scraping de toutes les catégories lancé avec l'ID : {task.id}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_scraping, "cron", day=1, hour=2, minute=0)

    
    scheduler.add_job(start_scraping, "cron", day_of_week="mon", hour=3, minute=0)

    print("✅ Scraping automatique activé :")
    print("   - Toutes les 6h pour les nouv categories")
    print("   - Chaque semaine pour tous les produits")

    scheduler.start()

# Appelle `start_scheduler()` seulement quand le script principal tourne
if __name__ == "__main__":
    start_scheduler()

