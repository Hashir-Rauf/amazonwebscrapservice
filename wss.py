from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
import time

app = Flask(__name__)

def scrape_amazon_product(url):
    try:
        # Validate Amazon domain
        if "amazon." not in url:
            return {"error": "URL must be from Amazon."}

        with sync_playwright() as p:
            # Configure browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.goto(url)
            time.sleep(3)  # Wait for dynamic content to load

            # Get page content
            content = page.content()
            browser.close()

        soup = BeautifulSoup(content, 'html.parser')

        # ✅ Check for cosmetic categories in breadcrumb
        breadcrumb = soup.find("ul", class_="a-unordered-list a-horizontal a-size-small")
        if not breadcrumb or not any(
            tag.get_text(strip=True) in ["Beauty & Personal Care", "Skin Care"]
            for tag in breadcrumb.find_all("a", class_="a-link-normal a-color-tertiary")
        ):
            return {"error": "Product does not belong to a cosmetic category."}

        title = soup.find(id="productTitle")
        brand_row = soup.find("tr", class_="po-brand")
        brand = brand_row.find_all("span")[-1].get_text(strip=True) if brand_row else "N/A"

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

        return {
            "product_name": title.get_text(strip=True) if title else "N/A",
            "brand": brand if brand else "N/A",
            "ingredients": ingredients_list or "Not Found"
        }

    except Exception as e:
        return {"error": str(e)}

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing 'url' in request"}), 400

    result = scrape_amazon_product(url)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
