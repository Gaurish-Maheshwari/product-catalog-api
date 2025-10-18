import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from main import app, get_db, Base

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#Create the test database and tables before tests run
Base.metadata.create_all(bind=engine)

#Dependency override to use the test database
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


#This fixture will run before each test function, ensuring a clean database
@pytest.fixture(scope="function", autouse=True)
def setup_and_teardown_database():
    #Create the tables
    Base.metadata.create_all(bind=engine)
    yield
    #Drop the tables after the test is done
    Base.metadata.drop_all(bind=engine)

#Test Cases

def test_upload_valid_csv():
    """
    Tests uploading a valid CSV file. Expects a 200 OK response
    and the correct count of stored and failed items.
    """
    csv_content = (
        "sku,name,brand,color,size,mrp,price,quantity\n"
        "TEST-001,Test Shirt,TestBrand,Red,M,1000,800,10\n"
        "TEST-002,Test Jeans,TestBrand,Blue,32,2000,1500,5\n"
    )
    files = {'file': ('test.csv', csv_content, 'text/csv')}
    response = client.post("/upload", files=files)
    
    assert response.status_code == 200
    assert response.json() == {"stored": 2, "failed": []}

def test_upload_csv_with_validation_errors():
    """
    Tests a CSV where some rows are invalid (price > mrp, negative quantity).
    """
    csv_content = (
        "sku,name,brand,color,size,mrp,price,quantity\n"
        "VALID-001,Valid Item,GoodBrand,Green,L,1000,900,10\n"
        "INVALID-PRICE,Bad Item,BadBrand,Red,M,1000,1200,5\n"
        "INVALID-QTY,Bad Item,BadBrand,Red,M,1000,800,-1\n"
    )
    files = {'file': ('test.csv', csv_content, 'text/csv')}
    response = client.post("/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["stored"] == 1
    assert len(data["failed"]) == 2

def test_upload_csv_with_missing_required_fields():
    """
    Tests a CSV with missing required fields in a row.
    """
    csv_content = (
        "sku,name,brand,mrp,price,quantity\n"
        "TEST-001,Test Shirt,TestBrand,1000,800,10\n" # Valid row
        "TEST-002,Test Jeans,,1500,1200,5\n" # Missing brand
    )
    files = {'file': ('test.csv', csv_content, 'text/csv')}
    response = client.post("/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["stored"] == 1
    assert len(data["failed"]) == 1
    assert "Missing one or more required fields" in data["failed"][0]["error"]

def test_get_products_with_pagination():
    """
    Tests the /products endpoint for correct pagination.
    """
    # First, upload some data to test against
    csv_content = "\n".join([
        "sku,name,brand,mrp,price,quantity",
        *[f"SKU-{i},Product {i},BrandA,100,50,{i}" for i in range(15)]
    ])
    files = {'file': ('test.csv', csv_content, 'text/csv')}
    client.post("/upload", files=files)
    
    # Test first page
    response = client.get("/products?page=1&limit=10")
    assert response.status_code == 200
    assert len(response.json()) == 10

    # Test second page
    response = client.get("/products?page=2&limit=10")
    assert response.status_code == 200
    assert len(response.json()) == 5

def test_search_products_case_insensitive():
    """
    Tests the case-insensitive search for brand and color.
    """
    csv_content = (
        "sku,name,brand,color,size,mrp,price,quantity\n"
        "SHIRT-01,Shirt,CoolWear,Red,M,1000,800,10\n"
        "JEANS-01,Jeans,DenimWorks,Blue,32,2000,1500,5\n"
    )
    files = {'file': ('test.csv', csv_content, 'text/csv')}
    client.post("/upload", files=files)

    # Search for brand with different casing
    response = client.get("/products/search?brand=coolwear")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["brand"] == "CoolWear"
    
    # Search for color with different casing
    response = client.get("/products/search?color=RED")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["color"] == "Red"

def test_search_products_by_price_range():
    """
    Tests the search functionality for a given price range.
    """
    csv_content = (
        "sku,name,brand,mrp,price,quantity\n"
        "ITEM-500,Item 1,BrandX,1000,500,10\n"
        "ITEM-1000,Item 2,BrandX,1500,1000,10\n"
        "ITEM-1500,Item 3,BrandX,2000,1500,10\n"
    )
    files = {'file': ('test.csv', csv_content, 'text/csv')}
    client.post("/upload", files=files)
    
    # Test with min_price
    response = client.get("/products/search?min_price=1000")
    assert response.status_code == 200
    assert len(response.json()) == 2

    # Test with max_price
    response = client.get("/products/search?max_price=1000")
    assert response.status_code == 200
    assert len(response.json()) == 2

    # Test with both min and max price
    response = client.get("/products/search?min_price=600&max_price=1400")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["sku"] == "ITEM-1000"

# Clean test db
@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    """Clean up the test database file once all tests are finished."""
    def remove_test_db():
        if os.path.exists(SQLALCHEMY_DATABASE_URL.split("///")[1]):
            os.remove(SQLALCHEMY_DATABASE_URL.split("///")[1])
    request.addfinalizer(remove_test_db)
