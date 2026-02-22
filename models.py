from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Column
from uuid import uuid4, UUID
from typing import Optional, Dict, Any,List
from enum import Enum

class StockStatus(str, Enum):
    IN_STOCK = "in-stock"
    LOW_STOCK = "low-stock"
    OUT_OF_STOCK = "out-of-stock"

class Product(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str
    category: str
    specs: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

class Listing(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    category_id: str
    subcategory_id: Optional[str] = None
    brand_id: str = Field(foreign_key="brand.id")
    name: str
    MRP: float
    supplier_price: float
    our_cut: float
    variants: Optional[List[Dict[str, Any]]] = Field(default_factory=list, sa_column=Column(JSON))
    variant_combinations: Optional[List[Dict[str, Any]]] = Field(default_factory=list, sa_column=Column(JSON))
    stock_status: StockStatus
    description: Optional[str] = None
    image_url: str | None = None

class User(SQLModel, table=True):
    __table_args__ = {"schema": "neon_auth"}
    __tablename__ = "user"
    
    id: UUID = Field(primary_key=True)
    email: str
    role: str = Field(default="user")
    name: Optional[str] = None

class Request(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: UUID = Field(foreign_key="neon_auth.user.id")
    product_id: str
    message: Optional[str] = None

class ShoppingCart(SQLModel, table=True):
    user_id: UUID = Field(primary_key=True, foreign_key="neon_auth.user.id")
    items: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))

class Category(SQLModel, table=True):
    id: str = Field(default_factory=lambda:(str(uuid4())),primary_key=True)
    name: str

class SubCategory(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    category_id: str = Field(foreign_key="category.id")
    name: str

class Brand(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str
    logo_url: str | None = None  # optional

class HeroContent(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    type: str = Field(default="newest") # 'newest', 'offer', 'manual_banner', 'featured'
    title: str
    subtitle: Optional[str] = None
    cta_text: Optional[str] = None
    cta_link: Optional[str] = None
    image_url: Optional[str] = None
    product_id: Optional[str] = Field(default=None, foreign_key="listing.id")
    is_active: bool = Field(default=True)
    priority: int = Field(default=10)
    start_date: Optional[str] = None # Using ISO 8601 string for simplicity in JS/Python boundaries
    end_date: Optional[str] = None