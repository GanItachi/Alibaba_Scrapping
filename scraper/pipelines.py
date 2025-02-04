# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter

import sys
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from les_spiders.spi1 import scrape_alibaba
from api.database import insert_data

class SpiderPipeline: 
    def process_item(self, item, spider):
        return item

def clean_data(data: dict) -> dict:
    # Pour l'instant, on retourne simplement les données.
    # Tu pourras ajouter des transformations plus tard.
    return data


def run_scraping_pipeline():
    raw_data = scrape_alibaba()
    insert_data(raw_data)
    print("Pipeline terminé.")


if __name__ == "__main__":
    run_scraping_pipeline()
