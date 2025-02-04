import psycopg2
from psycopg2.extras import execute_values
import os

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os


# Connexion à PostgreSQL
def get_connection():
    return psycopg2.connect(
        dbname="alibaba_scraper",
        user="GanToma",
        password="232003",
        host="localhost",  # Ou l'IP si le serveur est distant
        port="5432"
    )

# Insérer les données scrapées
def insert_data(data: dict):
    conn = get_connection()
    cur = conn.cursor()
    sql = "INSERT INTO alibaba_data (title, href) VALUES %s ON CONFLICT (title) DO NOTHING;"
    
    values = [(title, href) for title, href in data.items()]
    
    execute_values(cur, sql, values)
    conn.commit()
    cur.close()
    conn.close()

    print(f"{len(values)} nouvelles entrées ajoutées.")

DATABASE_URL = "postgresql://GanToma:232003@localhost:5432/alibaba_scraper"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
