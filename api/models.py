from .database import Base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class Categorie(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    link = Column(String)
    
     # Relation avec les produits
    products = relationship("Produit", back_populates="categorie")
    
class Produit(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    link = Column(String)
    categorie_id = Column(Integer, ForeignKey("categories.id"))  # Clé étrangère vers la table catégories

    # Relation avec la catégorie
    categorie = relationship("Categorie", back_populates="products")

# Création des tables
from .database import engine
Base.metadata.create_all(bind=engine)
