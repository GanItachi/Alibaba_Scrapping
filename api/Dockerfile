# Utiliser une image Python optimisée
FROM python:3.12-slim

# Éviter les problèmes de buffering des logs
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    wget unzip curl \
    && wget -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i /tmp/chrome.deb || apt-get -fy install \
    && rm -rf /tmp/chrome.deb

# ✅ Installe ChromeDriver (assure-toi que la version correspond à Chrome)
# RUN CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
#     wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" -O /tmp/chromedriver.zip && \
#     unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
#     chmod +x /usr/local/bin/chromedriver && \
#     rm /tmp/chromedriver.zip
# Installer les dépendances nécessaires
# RUN apt-get update && apt-get install -y wget unzip


# Télécharger et installer ChromeDriver
RUN wget -q "https://storage.googleapis.com/chrome-for-testing-public/133.0.6943.53/linux64/chromedriver-linux64.zip"  -O /tmp/chromedriver.zip && \
    unzip /tmp/chromedriver.zip -d /tmp/ && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64

RUN apt-get update && \
    apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    libasound2 \
    wget \
    curl \
    ca-certificates \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

RUN rm -rf /tmp/chrome-user-data

ADD . /app/

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances en premier pour profiter du cache Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Copier tout le projet (inutile de copier `static/` séparément)
#COPY . .

# Ajouter les permissions pour les fichiers statiques
RUN chmod -R 755 /app/static

# Exposer le port 8000
EXPOSE 8000

# Lancer FastAPI avec Uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
