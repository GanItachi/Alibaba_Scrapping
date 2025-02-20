from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Float, Date
from sqlalchemy.orm import relationship
from api.database import Base

# ✅ Table des Catégories
class Categorie(Base):
    __tablename__ = "categories"
    __table_args__ = {"schema": "public"}  

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    link = Column(String, unique=True, nullable=False)

    # Relation avec les produits
    products = relationship("Produit", back_populates="categorie", cascade="all, delete-orphan")

# ✅ Table des Produits
class Produit(Base):
    __tablename__ = "products"
    __table_args__ = {"schema": "public"}  

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    link = Column(String, unique=True, nullable=False)
    categorie_id = Column(Integer, ForeignKey("public.categories.id", ondelete="CASCADE"), nullable=False)  

    categorie = relationship("Categorie", back_populates="products")
    details = relationship("ProduitDetails", back_populates="produit", uselist=False, cascade="all, delete-orphan")


# ✅ Table des Détails des Produits
class ProduitDetails(Base):
    __tablename__ = "produits_details"
    __table_args__ = {"schema": "public"}  

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    produit_id = Column(Integer, ForeignKey("public.products.id", ondelete="CASCADE"), nullable=False)
    url = Column(String, unique=True, nullable=False)
    discount = Column(String, nullable=True)
    
    attributes = Column(JSON, nullable=False, default={})  # ✅ Stocke les attributs variables des produits

    supplier_id = Column(Integer, ForeignKey("public.suppliers.id", ondelete="SET NULL"))
    supplier = relationship("Supplier", back_populates="produit_details")

    reviews = relationship("Review", back_populates="produit_details", cascade="all, delete-orphan")
    pricing = relationship("Pricing", back_populates="produit_details", cascade="all, delete-orphan")  # ✅ Relation avec la table Pricing

    produit = relationship("Produit", back_populates="details")


# ✅ Table des Prix (Nouveauté)
class Pricing(Base):
    __tablename__ = "pricing"
    __table_args__ = {"schema": "public"}  

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    produit_id = Column(Integer, ForeignKey("public.produits_details.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(String, nullable=False)  # ✅ Ex: "1 - 99 pièces", ">= 100000 pièces"
    discounted_price = Column(String, nullable=False)
    original_price = Column(String, nullable=False)

    produit_details = relationship("ProduitDetails", back_populates="pricing")


# ✅ Table des Fournisseurs
class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = {"schema": "public"}  

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_name = Column(String, nullable=True)
    company_profile_link = Column(String, nullable=True)
    supplier_type = Column(String, nullable=True)
    experience_years = Column(Integer, nullable=True)
    location = Column(String, nullable=True)
    store_rating = Column(Float, nullable=True)
    delivery_rate = Column(Float, nullable=True)
    response_time = Column(String, nullable=True)
    revenue = Column(String, nullable=True)
    floorspace = Column(Float, nullable=True)
    staff = Column(Integer, nullable=True)
    main_markets = Column(String, nullable=True)

    produit_details = relationship("ProduitDetails", back_populates="supplier")  


# ✅ Table des Avis Clients
class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = {"schema": "public"}  

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    produit_id = Column(Integer, ForeignKey("public.produits_details.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Float, nullable=False)
    comment = Column(String, nullable=True)
    date = Column(Date, nullable=True)  # ✅ Conversion en format date
    reviewer_country = Column(String, nullable=True)

    produit_details = relationship("ProduitDetails", back_populates="reviews")
