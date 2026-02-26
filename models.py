from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Column, String
from uuid import uuid4, UUID
from typing import Optional, Dict, Any,List
from enum import Enum
from datetime import datetime, timezone

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
    category_id: str = Field(index=True)
    subcategory_id: Optional[str] = Field(default=None, index=True)
    brand_id: str = Field(foreign_key="brand.id", index=True)
    name: str
    MRP: float
    supplier_price: float
    our_cut: float
    variants: Optional[List[Dict[str, Any]]] = Field(default_factory=list, sa_column=Column(JSON))
    variant_combinations: Optional[List[Dict[str, Any]]] = Field(default_factory=list, sa_column=Column(JSON))
    stock_status: StockStatus
    description: Optional[str] = None
    image_url: str | None = None
    image_urls: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: Optional[str] = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), index=True)

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

class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    RETURN_REQUESTED = "return_requested"
    RETURNED = "returned"

class ReturnStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class Order(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: UUID = Field(foreign_key="neon_auth.user.id", index=True)
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    items: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    shipping_address: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    shipping_fee: float = Field(default=0.0)
    total_amount: float
    status: OrderStatus = Field(default=OrderStatus.PENDING, sa_column=Column(String, default=OrderStatus.PENDING.value, index=True))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ReturnRequest(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    order_id: str = Field(foreign_key="order.id", index=True)
    user_id: UUID = Field(foreign_key="neon_auth.user.id", index=True)
    reason: str
    status: ReturnStatus = Field(default=ReturnStatus.PENDING, sa_column=Column(String, default=ReturnStatus.PENDING.value, index=True))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CheckoutDetails(SQLModel, table=True):
    user_id: UUID = Field(primary_key=True, foreign_key="neon_auth.user.id")
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None

class GlobalNotice(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    message: str
    type: str = Field(default="info")  # 'info', 'warning', 'promo', 'urgent'
    is_active: bool = Field(default=True)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())