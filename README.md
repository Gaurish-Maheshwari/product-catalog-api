# Product Catalog API & Frontend

A complete solution for managing a **product catalog**, featuring a robust **FastAPI backend** and a **Streamlit frontend** for seamless interaction.

---

## Features

- **FastAPI Backend** – High-performance asynchronous API built with Python  
- **CSV Upload** – Upload product data via CSV file  
- **Data Validation** – Enforced with Pydantic (price <= MRP, quantity >= 0)  
- **SQLite Database** – Efficient storage for validated product data  
- **Paginated Listing** – Retrieve products with simple pagination  
- **Advanced Search** – Filter by brand, color (case-insensitive), and price range  
- **Streamlit Frontend** – Interactive UI for uploading CSVs and searching products  
- **Dockerized Backend** – Fully containerized for easy deployment  
- **Unit Tested** – Backend logic tested using pytest  
- **Interactive Docs** – Auto-generated API docs via Swagger UI

---

## Project Structure

.
├── Dockerfile              # Defines the Docker image for the backend API  
├── frontend.py             # Streamlit frontend application  
├── main.py                 # FastAPI backend application  
├── products.csv            # Sample CSV data for testing  
├── products.db             # SQLite database (created on first run)  
├── README.md               # Project documentation  
├── requirements.txt        # Python dependencies  
└── test_main.py            # Unit tests (pytest)

---

## Setup and Installation

### Prerequisites

- Python 3.9+  
- Docker and Docker Desktop  

---

### Local Setup

1. Clone the repository:

git clone [Link](https://github.com/Gaurish-Maheshwari/product-catalog-api.git)
cd product-catalog-api  

2. Create and activate a virtual environment:

python3 -m venv venv  
source venv/bin/activate  

3. Install the required dependencies:

pip install -r requirements.txt  

---

## Running the Application

You can run the application in two ways: locally for development or using Docker for the backend.

---

### Method 1: Local Development (Recommended)

This method allows you to run both the backend and frontend and see code changes live.

1. Run the Backend API (Terminal 1):  
Open a terminal and run the following command to start the FastAPI server.

uvicorn main:app --reload  

The API will be available at http://127.0.0.1:8000  

2. Run the Streamlit Frontend (Terminal 2):  
Open a new terminal window and run the following command.

streamlit run frontend.py  

The web interface will be available at http://localhost:8501  

---

### Method 2: Using Docker (Backend Only)

This method runs the backend API inside a Docker container.

1. Build the Docker Image:  
From the project root, run:

docker build -t product-catalog-api .  

2. Run the Docker Container:

docker run -d -p 8000:8000 --name product-catalog-container product-catalog-api  

The API will be running in the background and accessible at http://localhost:8000.  
You can still run the Streamlit frontend locally to interact with it.

---

## Running the Unit Tests

To ensure the API is working correctly, you can run the test suite.

1. Activate your virtual environment:

source venv/bin/activate  

2. Run pytest:

pytest  

---

## API Documentation

Once the backend is running, you can access the interactive API documentation by navigating to:

http://localhost:8000/docs  

From this page, you can test every endpoint directly.

---

## API Endpoints

1. Upload CSV  
Endpoint: POST /upload  
Description: Uploads a products.csv file.  
Example:

curl -X POST -F "file=@products.csv" http://localhost:8000/upload  

---

2. List Products  
Endpoint: GET /products  
Description: Returns a paginated list of all products.  
Example:

curl "http://localhost:8000/products?page=1&limit=5"  

---

3. Search Products  
Endpoint: GET /products/search  
Description: Searches for products with filters.  
Example:

curl "http://localhost:8000/products/search?brand=BloomWear&max_price=2200"  

---

## Technologies Used

- FastAPI  
- Streamlit  
- SQLite  
- Pydantic  
- Docker  
- pytest  

---

## Author

Gaurish Maheshwari 
gaurish.maheshwari.cer22@itbhu.ac.in 

