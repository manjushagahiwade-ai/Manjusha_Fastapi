from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer, Enum, DateTime, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
import enum
from datetime import datetime

# Database connection settings
DATABASE_URL = "mysql+mysqlconnector://root:root@localhost/product_db"

# Create a SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Define enums for product category and unit of measure
class CategoryEnum(str, enum.Enum):
    finished = "finished"
    semi_finished = "semi-finished"
    raw = "raw"

class UnitEnum(str, enum.Enum):
    mtr = "mtr"
    mm = "mm"
    ltr = "ltr"
    ml = "ml"
    cm = "cm"
    mg = "mg"
    gm = "gm"
    unit = "unit"
    pack = "pack"

# Define the Product table model
class Product(Base):
    __tablename__ = 'product'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(Enum(CategoryEnum), nullable=False)
    description = Column(String(250), nullable=True)
    product_image = Column(String(255), nullable=True)
    sku = Column(String(100), unique=True, nullable=False)
    unit_of_measure = Column(Enum(UnitEnum), nullable=False)
    lead_time = Column(Integer, nullable=True)
    created_date = Column(TIMESTAMP, default=datetime.utcnow)
    updated_date = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

# Create tables in the database
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI()

# Pydantic models for validation
class ProductCreate(BaseModel):
    name: str
    category: CategoryEnum
    description: Optional[str] = None
    product_image: Optional[str] = None
    sku: str
    unit_of_measure: UnitEnum
    lead_time: Optional[int] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[CategoryEnum] = None
    description: Optional[str] = None
    product_image: Optional[str] = None
    sku: Optional[str] = None
    unit_of_measure: Optional[UnitEnum] = None
    lead_time: Optional[int] = None

class ProductOut(BaseModel):
    id: int
    name: str
    category: CategoryEnum
    description: Optional[str]
    product_image: Optional[str]
    sku: str
    unit_of_measure: UnitEnum
    lead_time: Optional[int]
    created_date: datetime
    updated_date: datetime

    class Config:
        orm_mode = True

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API Endpoints
@app.get("/product/list", response_model=List[ProductOut])
def list_products(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    try:
        products = db.query(Product).offset(skip).limit(limit).all()
        return products
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/product/{pid}/info", response_model=ProductOut)
def get_product_info(pid: int, db: Session = Depends(get_db)):
    try:
        product = db.query(Product).filter(Product.id == pid).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/product/add", response_model=ProductOut)
def add_product(product: ProductCreate, db: Session = Depends(get_db)):
    try:
        db_product = Product(**product.dict())
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error adding product: " + str(e))

@app.put("/product/{pid}/update", response_model=ProductOut)
def update_product(pid: int, product: ProductUpdate, db: Session = Depends(get_db)):
    try:
        db_product = db.query(Product).filter(Product.id == pid).first()
        if not db_product:
            raise HTTPException(status_code=404, detail="Product not found")

        for key, value in product.dict(exclude_unset=True).items():
            setattr(db_product, key, value)

        db.commit()
        db.refresh(db_product)
        return db_product
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error updating product: " + str(e))
