import re
import json

def clean_text(text):
    """Nettoie une chaîne de texte et remplace les valeurs vides par 'Non spécifié'."""
    return text.strip() if text and text.strip() else "Non spécifié"

def clean_json(data):
    """Convertit un dictionnaire en JSON propre."""
    return json.dumps(data, ensure_ascii=False) if data else "{}"

def clean_price(price_text):
    """Convertit un prix en float, sinon renvoie 'Non spécifié'."""
    try:
        return float(re.sub(r"[^\d.]", "", price_text))
    except ValueError:
        return "Non spécifié"

def clean_percentage(text):
    """Extrait un pourcentage et le convertit en float, sinon renvoie 'Non spécifié'."""
    try:
        return float(re.search(r'(\d+)', text).group(1)) if text else "Non spécifié"
    except AttributeError:
        return "Non spécifié"

def clean_integer(text):
    """Extrait un nombre entier à partir d'un texte."""
    try:
        return int(re.search(r'(\d+)', text).group(1)) if text else "Non spécifié"
    except AttributeError:
        return "Non spécifié"

def extract_country_from_url(image_url):
    """Extrait le code pays d'un utilisateur à partir du lien de l'image du drapeau."""
    try:
        return image_url.split("/")[-1].split(".")[0] if image_url else "Non spécifié"
    except IndexError:
        return "Non spécifié"
