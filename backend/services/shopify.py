import os
import httpx
from dotenv import load_dotenv

load_dotenv()

SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

MOCK_DATA = {
    "product": {
        "title": "Wireless Noise-Cancelling Headphones",
        "description": "Great sound. Comfortable fit.",
        "price": "79.99",
        "images": ["https://example.com/headphones.jpg"],
        "reviews": [
            "Good product but shipping took forever.",
            "Sound quality is okay."
        ],
        "faq": [
            {"q": "Is it waterproof?", "a": ""},
            {"q": "What is the battery life?", "a": ""}
        ],
        "policies": {
            "shipping": "",
            "returns": "Contact us for returns."
        }
    }
}


def fetch_store_data(use_mock: bool = True) -> dict:
    if use_mock:
        return MOCK_DATA

    # Real Shopify fetch (stub — fill later)
    query = """
    {
      products(first: 1) {
        edges {
          node {
            title
            descriptionHtml
            variants(first: 1) {
              edges {
                node {
                  price
                }
              }
            }
          }
        }
      }
    }
    """

    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    response = httpx.post(
        f"https://{SHOPIFY_STORE_URL}/admin/api/2024-01/graphql.json",
        json={"query": query},
        headers=headers
    )

    if response.status_code != 200:
        return MOCK_DATA  # fallback to mock on failure

    return response.json()