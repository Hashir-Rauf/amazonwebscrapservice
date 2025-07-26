from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS to enable cross-origin requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes (you can customize this if needed)

# Function to scrape Amazon product data
def scrape_amazon_product(url):
    try:
        # Validate Amazon domain
        if "amazon." not in url:
            return {"error": "URL must be from Amazon."}

        # Set up Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run Chrome in headless mode
        chrome_options.add_argument('--no-sandbox')  # Required in certain environments
        chrome_options.add_argument('--disable-dev-shm-usage')  # Avoid resource issues
        chrome_options.add_argument('--disable-gpu')  # Disable GPU hardware acceleration
        chrome_options.add_argument('--remote-debugging-port=9222')  # Enable remote debugging

        # Path to ChromeDriver
        driver = webdriver.Chrome(options=chrome_options)

        driver.get(url)
        time.sleep(3)  # Give time for page to load

        # Parse the page source using BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Check for the cosmetic category in breadcrumb
        breadcrumb = soup.find("ul", class_="a-unordered-list a-horizontal a-size-small")
        if not breadcrumb or not any(
            tag.get_text(strip=True) in ["Beauty & Personal Care", "Skin Care"]
            for tag in breadcrumb.find_all("a", class_="a-link-normal a-color-tertiary")
        ):
            driver.quit()
            return {"error": "Product does not belong to a cosmetic category."}

        # Extract product details
        title = soup.find(id="productTitle")
        brand_row = soup.find("tr", class_="po-brand")
        brand = brand_row.find_all("span")[-1].get_text(strip=True) if brand_row else "N/A"

        # Extract ingredients if available
        ingredients_list = []
        blocks = soup.find_all("div", class_="a-section content")
        for block in blocks:
            h4 = block.find("h4")
            if h4 and "Ingredients" in h4.get_text(strip=True):
                ps = block.find_all("p")
                for p in ps:
                    txt = p.get_text(strip=True)
                    if txt:
                        ingredients_list = [i.strip() for i in txt.split(",")]
                        break
                break

        # Close the driver after scraping
        driver.quit()

        # Return the scraped product data
        return {
            "product_name": title.get_text(strip=True) if title else "N/A",
            "brand": brand,
            "ingredients": ingredients_list or "Not Found"
        }

    except Exception as e:
        return {"error": str(e)}

# Route to handle scraping requests
@app.route('/scrape', methods=['POST', 'GET'])
def scrape():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing 'url' in request"}), 400

    result = scrape_amazon_product(url)
    return jsonify(result)

# Run the Flask app
if __name__ == '__main__':
    # Make the app listen on 0.0.0.0 and use the environment's PORT variable
    import os
    port = int(os.environ.get('PORT', 5000))  # Render uses dynamic port
    app.run(debug=True, host='0.0.0.0', port=port)
