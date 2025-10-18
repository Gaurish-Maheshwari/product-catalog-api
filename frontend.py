import streamlit as st
import pandas as pd
import requests
import io

API_BASE_URL = "http://localhost:8000"


st.set_page_config(
    page_title="Product Catalog Manager",
    layout="wide",
)

st.title("Product Catalog Manager")
st.markdown("A simple UI to interact with the Product Catalog API.")


def get_products(page=1, limit=10):
    """Fetches all products with pagination."""
    try:
        response = requests.get(f"{API_BASE_URL}/products", params={"page": page, "limit": limit})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching products: {e}")
        return []

def search_products(brand, color, min_price, max_price):
    """Searches for products based on filters."""
    params = {
        "brand": brand if brand else None,
        "color": color if color else None,
        "min_price": min_price if min_price > 0 else None,
        "max_price": max_price if max_price > 0 else None,
    }
    # Filter out None values
    params = {k: v for k, v in params.items() if v is not None}
    
    try:
        response = requests.get(f"{API_BASE_URL}/products/search", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error during search: {e}")
        return []


#Upload CSV Section
st.header("Upload Product CSV")
uploaded_file = st.file_uploader(
    "Choose a CSV file to upload",
    type="csv",
    help="The CSV should contain columns: sku, name, brand, color, size, mrp, price, quantity"
)

if uploaded_file is not None:
    with st.spinner('Uploading and processing file...'):
        files = {'file': (uploaded_file.name, uploaded_file.getvalue(), 'text/csv')}
        try:
            response = requests.post(f"{API_BASE_URL}/upload", files=files)
            
            if response.status_code == 200:
                result = response.json()
                st.success(f"File processed successfully! Stored: {result['stored']} products.")
                if result['failed']:
                    st.warning("Some products failed validation:")
                    failed_df = pd.DataFrame(result['failed'])
                    st.dataframe(failed_df)
            else:
                st.error(f"Error uploading file: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            st.error(f"Could not connect to the API: {e}")

st.divider()

#Search and View Products Section
st.header("Search and View Products")

#Search Filters
col1, col2, col3, col4 = st.columns(4)
with col1:
    search_brand = st.text_input("Brand", help="Case-insensitive brand search")
with col2:
    search_color = st.text_input("Color", help="Case-insensitive color search")
with col3:
    search_min_price = st.number_input("Min Price", min_value=0.0, step=100.0)
with col4:
    search_max_price = st.number_input("Max Price", min_value=0.0, step=100.0)

if st.button("Search Products"):
    with st.spinner("Searching..."):
        search_results = search_products(search_brand, search_color, search_min_price, search_max_price)
        if search_results:
            st.success(f"Found {len(search_results)} matching products.")
            st.dataframe(pd.DataFrame(search_results), use_container_width=True)
        else:
            st.info("No products found matching your criteria.")

st.divider()

#View All Products (Paginated)
st.header("View All Products")

col_page, col_limit, _ = st.columns([1, 1, 3])
with col_page:
    page_num = st.number_input("Page", min_value=1, value=1, step=1)
with col_limit:
    page_limit = st.selectbox("Products per page", [10, 25, 50, 100], index=0)

if st.button("Load All Products"):
    with st.spinner("Loading products..."):
        all_products = get_products(page=page_num, limit=page_limit)
        if all_products:
            st.dataframe(pd.DataFrame(all_products), use_container_width=True)
        else:
            st.info("No more products to display on this page.")
