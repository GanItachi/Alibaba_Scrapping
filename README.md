
---

# 🚀 Alibaba Scraper API

## 📌 Description

**Alibaba Scraper API** est une application basée sur **FastAPI** permettant de :

* Scraper automatiquement des **catégories** et **produits** d’Alibaba (via **Selenium**)
* Stocker les données dans **PostgreSQL**
* Gérer les tâches asynchrones avec **Celery + Redis**
* Fournir des options de téléchargement (JSON, CSV, Excel)
* Surveiller le pipeline avec **Prometheus + Grafana**
* Accéder facilement aux données via un **Tableau de bord**

👉 Ce projet s’adresse autant aux **développeurs** (qui veulent contribuer) qu’aux **utilisateurs finaux** (qui veulent juste lancer du scraping et télécharger des données).

---

## 🛠️ Technologies utilisées

* ⚡ **FastAPI** – API REST
* 🐇 **Celery** – Gestion des tâches asynchrones
* 🛑 **Redis** – Broker pour Celery
* 🌐 **Selenium** – Scraping
* 🗄️ **PostgreSQL** – Base de données
* 📦 **Docker & Docker Compose** – Conteneurisation
* 📉 **Prometheus** – Monitoring des métriques
* 📊 **Grafana** – Visualisation des métriques
* 🖥️ **PgAdmin** – Gestion de PostgreSQL

---

## ⚙️ Installation (Développeurs)

### 1. Cloner le projet

```bash
git clone https://github.com/ton-username/alibaba-scraper.git
cd alibaba-scraper
```

### 2. Lancer avec Docker

```bash
docker-compose up --build
```

### 3. Accéder aux services

* 🌐 **API FastAPI** : [http://127.0.0.1:8000](http://127.0.0.1:8000)
* 📊 **Tableau de Bord API** : [http://127.0.0.1:8000/tb](http://127.0.0.1:8000/tb)
* 🗄️ **PgAdmin** : [http://127.0.0.1:5050](http://127.0.0.1:5050)
* 📉 **Prometheus** : [http://127.0.0.1:9090](http://127.0.0.1:9090)
* 📊 **Grafana** : [http://127.0.0.1:3100](http://127.0.0.1:3100)

---

## 📂 Structure du projet

```
├── api
│   ├── main.py           # Entrée FastAPI
│   ├── tasks.py          # Tâches Celery
│   ├── models.py         # Modèles SQLAlchemy
│   ├── database.py       # Connexion DB
│   ├── scheduler.py      # Scraping automatique
│   ├── celery_config.py  # Config Celery
│   └── ...
├── static                # CSS / JS / Images
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## ⏳ Automatisation du scraping

* Le scraping est lancé automatiquement toutes les **6 heures** (modifiable dans `scheduler.py`)
* Lancement manuel possible via :

### API (navigateur)

```
http://127.0.0.1:8000/start_scraping
```

### Ligne de commande (`curl`)

```bash
curl -X POST http://127.0.0.1:8000/start_scraping
```

### Vérifier l’état d’une tâche

```bash
curl http://127.0.0.1:8000/status/<TASK_ID>
```

---

## 📊 Monitoring (Développeurs & Admins)

* **Prometheus** collecte automatiquement les métriques (nombre de tâches, temps d’exécution, erreurs, files d’attente).
* **Grafana** propose un dashboard visuel personnalisable.

👉 Exemples de métriques :

* `celery_tasks_total` → Nombre total de tâches exécutées
* `celery_task_duration_seconds` → Temps moyen d’exécution
* `celery_tasks_queued` → Nombre de tâches en attente

---

## 📖 Guide Utilisateur (Simple)

### 1. Accéder au Tableau de Bord

👉 [http://127.0.0.1:8000/tb](http://127.0.0.1:8000/tb)

Depuis cette interface, vous pouvez :

* Lancer un scraping
* Voir les résultats
* Télécharger les données

---

### 2. Télécharger les données

#### 📂 Catégories

* [JSON](http://127.0.0.1:8000/download/categories/json)
* [CSV](http://127.0.0.1:8000/download/categories/csv)
* [Excel](http://127.0.0.1:8000/download/categories/excel)

#### 📦 Produits

* [JSON](http://127.0.0.1:8000/download/produits/json)
* [CSV](http://127.0.0.1:8000/download/produits/csv)
* [Excel](http://127.0.0.1:8000/download/produits/excel)

---

### 3. Exemple d’utilisation rapide

1. Ouvrir le **Tableau de bord** : [http://127.0.0.1:8000/tb](http://127.0.0.1:8000/tb)
2. Cliquer sur **Lancer un scraping**
3. Attendre que les données soient disponibles
4. Télécharger en **CSV** pour ouvrir dans Excel

---

## 🔗 Liens utiles

* 📊 Tableau de Bord : [http://127.0.0.1:8000/tb](http://127.0.0.1:8000/tb)
* 🗄️ PgAdmin : [http://127.0.0.1:5050](http://127.0.0.1:5050)
* 📉 Prometheus : [http://127.0.0.1:9090](http://127.0.0.1:9090)
* 📊 Grafana : [http://127.0.0.1:3100](http://127.0.0.1:3100)

---

## 📜 Licence

Projet sous licence **MIT**.

---
