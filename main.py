# main.py
import csv
import io
from typing import List, Optional

from fastapi import FastAPI, Depends, File, UploadFile, HTTPException, Query
from pydantic import BaseModel, validator, ValidationError
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# Database setup
DATABASE_URL = "sqlite:///./products.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy model for Product
class ProductDB(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    brand = Column(String, index=True, nullable=False)
    color = Column(String)
    size = Column(String)
    mrp = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)

Base.metadata.create_all(bind=engine)

# Pydantic model for validating request/response
class Product(BaseModel):
    sku: str
    name: str
    brand: str
    color: Optional[str] = None
    size: Optional[str] = None
    mrp: float
    price: float
    quantity: int

    @validator('price')
    def price_less_than_mrp(cls, v, values, **kwargs):
        if 'mrp' in values and v > values['mrp']:
            raise ValueError('price must not be greater than mrp')
        return v

    @validator('quantity')
    def quantity_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('quantity must be non-negative')
        return v

    class Config:
        from_attributes = True

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# FastAPI app initialization
app = FastAPI(
    title="Product Catalog API",
    description="A FastAPI application to manage a product catalog. This API allows you to upload a CSV file of products, store them in a database, and then list or search for products with various filters. The auto-generated documentation below provides detailed information about each endpoint.",
    version="1.0.0",
)


@app.post("/upload",
    summary="Upload a CSV file with product data",
    description="Upload a CSV file containing product information. Each row is validated and, if valid, stored in the database. The API returns a count of stored products and a list of any products that failed validation.",
    tags=["Products"],
)
async def upload_csv(file: UploadFile = File(..., description="A CSV file containing product data."), db: Session = Depends(get_db)):
    """
    ## Upload CSV File

    This endpoint accepts a CSV file with product data.

    ### CSV Format:
    The CSV file should have the following columns:
    - `sku` (string, required)
    - `name` (string, required)
    - `brand` (string, required)
    - `color` (string, optional)
    - `size` (string, optional)
    - `mrp` (float, required)
    - `price` (float, required)
    - `quantity` (integer, required)

    ### Validation Rules:
    - `price` must be less than or equal to `mrp`.
    - `quantity` must be greater than or equal to 0.
    - `sku`, `name`, `brand`, `mrp`, and `price` are required fields.

    ### Example Request:
    ```bash
    curl -X POST -F "file=@products.csv" http://localhost:8000/upload
    ```

    ### Example Response:
    ```json
    {
      "stored": 20,
      "failed": []
    }
    ```
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV file.")

    contents = await file.read()
    file_data = io.StringIO(contents.decode('utf-8'))
    csv_reader = csv.DictReader(file_data)

    
    failed_entries = []
    products_to_process = []
    skus_in_csv = set()

    # First pass: validate all rows and collect valid data
    for row in csv_reader:
        try:
            # Check for missing required fields manually before Pydantic
            required_fields = ['sku', 'name', 'brand', 'mrp', 'price', 'quantity']
            if any(field not in row or row[field] is None or row[field] == '' for field in required_fields):
                raise ValueError(f"Missing one or more required fields: {', '.join(required_fields)}")
            
            product_data = Product(**row)
            if product_data.sku in skus_in_csv:
                 failed_entries.append({"row": row, "error": "Duplicate SKU in CSV file."})
            else:
                products_to_process.append(product_data)
                skus_in_csv.add(product_data.sku)

        except (ValidationError, ValueError) as e:
            failed_entries.append({"row": row, "error": str(e)})

    if not products_to_process and failed_entries:
        return {"stored": 0, "failed": failed_entries}
    
    if not products_to_process:
        raise HTTPException(status_code=400, detail="CSV file is empty or contains no valid product data.")

    try:
        # Efficiently get all existing products from the DB
        existing_products_query = db.query(ProductDB).filter(ProductDB.sku.in_(skus_in_csv))
        existing_products_map = {p.sku: p for p in existing_products_query}

        for product_data in products_to_process:
            if product_data.sku in existing_products_map:
                # Update existing product
                db_product = existing_products_map[product_data.sku]
                for key, value in product_data.dict().items():
                    setattr(db_product, key, value)
            else:
                # Add new product
                db_product = ProductDB(**product_data.dict())
                db.add(db_product)
        
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"A database error occurred: {str(e)}")

    return {"stored": len(products_to_process), "failed": failed_entries}


@app.get("/products",
    response_model=List[Product],
    summary="List all products with pagination",
    description="Retrieve a list of all products stored in the database. This endpoint supports pagination using `page` and `limit` query parameters.",
    tags=["Products"],
)
def get_products(
    page: int = Query(1, ge=1, description="Page number to retrieve.", example=1),
    limit: int = Query(10, ge=1, le=100, description="Number of products to retrieve per page.", example=10),
    db: Session = Depends(get_db)
):
    """
    ## List Products

    Fetches a paginated list of all products.

    ### Query Parameters:
    - `page` (integer, optional, default: 1): The page number to retrieve.
    - `limit` (integer, optional, default: 10): The number of items per page.

    ### Example Request:
    ```bash
    # Get the second page with 5 items per page
    curl "http://localhost:8000/products?page=2&limit=5"
    ```

    ### Example Response:
    ```json
    [
        {
            "sku": "DRESS-PNK-S",
            "name": "Floral Summer Dress",
            "brand": "BloomWear",
            "color": "Pink",
            "size": "S",
            "mrp": 2499.0,
            "price": 2199.0,
            "quantity": 10
        }
    ]
    ```
    """
    offset = (page - 1) * limit
    products = db.query(ProductDB).offset(offset).limit(limit).all()
    return products


@app.get("/products/search",
    response_model=List[Product],
    summary="Search for products with filters",
    description="Search for products based on various filters like brand, color, and price range. All filters are optional and text-based filters are case-insensitive.",
    tags=["Products"],
)
def search_products(
    brand: Optional[str] = Query(None, description="Filter products by brand name (case-insensitive).", example="DenimWorks"),
    color: Optional[str] = Query(None, description="Filter products by color (case-insensitive).", example="red"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price for the product.", example=500),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price for the product.", example=1500),
    db: Session = Depends(get_db)
):
    """
    ## Search Products

    Allows searching for products using one or more filters.

    ### Query Parameters:
    - `brand` (string, optional): Filter by brand name (case-insensitive).
    - `color` (string, optional): Filter by color (case-insensitive).
    - `min_price` (float, optional): Filter by minimum price.
    - `max_price` (float, optional): Filter by maximum price.

    ### Example Request (Brand and Max Price):
    ```bash
    curl "http://localhost:8000/products/search?brand=denimworks&max_price=1500"
    ```

    ### Example Response:
    ```json
    [
        {
            "sku": "JEANS-BLK-030",
            "name": "Slim Fit Jeans",
            "brand": "DenimWorks",
            "color": "Black",
            "size": "30",
            "mrp": 1999.0,
            "price": 1499.0,
            "quantity": 18
        }
    ]
    ```
    """
    query = db.query(ProductDB)
    if brand:
        query = query.filter(ProductDB.brand.ilike(brand))
    if color:
        query = query.filter(ProductDB.color.ilike(color))
    if min_price is not None:
        query = query.filter(ProductDB.price >= min_price)
    if max_price is not None:
        query = query.filter(ProductDB.price <= max_price)

    products = query.all()
    return products

