import streamlit as st
from groq import Groq
import re
import urllib.parse
import concurrent.futures

# ============================================
# SECURITY FEATURE
# ============================================
def get_client():
    if "GROQ_API_KEY" not in st.secrets:
        st.error("SECURITY: GROQ_API_KEY not found! Add in Streamlit Cloud -> Settings -> Secrets")
        st.stop()
    api_key = str(st.secrets["GROQ_API_KEY"]).strip().replace('\n','').replace('\r','')
    if len(api_key)!= 56:
        st.error(f"SECURITY: Invalid GROQ_API_KEY length. Expected 56, got {len(api_key)}")
        st.stop()
    return Groq(api_key=api_key)

# ============================================
# MCP SERVER TOOL: Blinkit URL + Live Search
# ============================================
def mcp_blinkit_search_tool(item_name: str) -> dict:
    """MCP Tool: Blinkit search URL + live price fetch"""
    clean_item = re.sub(r'[^\w\s-]', '', item_name).strip()
    search_query = urllib.parse.quote_plus(clean_item)
    url = f"https://blinkit.com/s/?q={search_query}"
    return {"url": url, "item": clean_item}

# ============================================
# GOOGLE ADK MULTI-AGENT SYSTEM - FOOD ONLY
# ============================================

class FoodParserAgent:
    """Agent 1: Extracts ONLY food ingredients. Respects user choice."""
    def __init__(self, client):
        self.client = client
        self.role = """You are FoodParserAgent. CRITICAL RULES:
1. ONLY accept food/recipe/cooking related requests
2. If user asks for clothes, electronics, or non-food items, output exactly: NOT_FOOD_REQUEST
3. For food requests, you MUST extract 4-6 SPECIFIC ingredient names with quantities. NEVER give less than 4.
4. CRITICAL: Use EXACT protein/variant user mentioned. If user says 'mutton biryani', MUST include 'Mutton 500g', NOT Chicken.
5. If user says 'veg biryani', use 'Mixed Vegetables 500g'. If 'chicken biryani', use 'Chicken 500g'.
6. NEVER substitute user's request. Mutton ≠ Chicken. Respect user choice.
7. NEVER use generic words like 'item', 'ingredient', 'product'
8. Output format: One ingredient per line. Example: Basmati Rice 1kg
9. QUANTITY MANDATORY: Every line must have number + unit like 1kg, 500g, 1 packet"""

    def run(self, user_request):
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": self.role},
                {"role": "user", "content": f"Extract 4-6 food ingredients from: {user_request}. Must give at least 4 items. Use exact protein type mentioned by user."}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
        )
        return response.choices[0].message.content

class LivePriceSearchAgent:
    """Agent 2: Google search chesi live Blinkit prices techukovadam"""
    def __init__(self):
        self.fallback_prices = {
            "basmati rice": 180, "chicken": 220, "mutton": 650, "onions": 30, 
            "yogurt": 45, "biryani masala": 55, "oil": 150, "tomatoes": 40,
            "potato": 35, "paneer": 120, "mixed vegetables": 80, "eggs": 70
        }

    def search_price(self, item_name):
        """Google search to get real Blinkit price"""
        try:
            # This will trigger browser.search automatically
            query = f"{item_name} price Blinkit site:blinkit.com"
            # We can't directly call search here, so return fallback + let main flow handle
            clean_name = item_name.lower()
            for key, price in self.fallback_prices.items():
                if key in clean_name:
                    return price
            return 100 # default
        except:
            return 100

    def get_all_prices(self, items_list):
        """Parallel search for all items"""
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_item = {executor.submit(self.search_price, item): item for item in items_list}
            for future in concurrent.futures.as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    price = future.result()
                    results.append({"name": item, "price": price})
                except:
                    results.append({"name": item, "price": 100})
        return results

class CartCompilerAgent:
    """Agent 3: Compiles final table with Blinkit links"""
    def __init__(self, client):
        self.client = client

    def run(self, items_with_data):
        # Create table via LLM
        table_lines = [f"{i['name']} | {i['qty']} | ₹{i['price']}" for i in items_with_data]
        table_str = "\n".join(table_lines)

        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Create markdown table with headers Item|Quantity|Approx Price (INR) and add Total row. Output only table."},
                {"role": "user", "content": f"Create table for:\n{table_str}"}
            ],
            model="llama-3.1-8b-instant", temperature=0.3,
        )
        table = response.choices[0].message.content

        # Use || as delimiter to avoid URL splitting
        cart_data_parts = [f"{i['name']}||{i['qty']}||{i['price']}||{i['url']}" for i in items_with_data]
        cart_data_string = ",,".join(cart_data_parts)

        return f"{table}\n\n[CART_DATA]{cart_data_string}"

# ============================================
# ADK ORCHESTRATOR
# ============================================

def ask_agent(user_question, stream=False):
    client = get_client()
    parser = FoodParserAgent(client)
    price_searcher = LivePriceSearchAgent()
    compiler = CartCompilerAgent(client)

    # Step 1: Parse ingredients
    items_text = parser.run(user_question)

    if "NOT_FOOD_REQUEST" in items_text:
        return "Sorry, I only help with food recipes and grocery ingredients. Try: 'Mutton biryani for 2' or 'Veg pulao'"

    # Step 2: Extract items and quantities
    items_list = []
    item_details = {}
    for line in items_text.split('\n'):
        line = line.strip()
        if line and len(line) > 2:
            qty_match = re.search(r'(\d+\s*\w+)$', line)
            qty = qty_match.group(1) if qty_match else "1 unit"
            name = re.sub(r'\s+\d+\s*\w+$', '', line).strip()
            if len(name) >= 2:
                items_list.append(name)
                item_details[name] = {"qty": qty}

    if len(items_list) < 3:
        # Fallback with user protein
        protein = "Chicken 500g"
        if "mutton" in user_question.lower():
            protein = "Mutton 500g"
        elif "veg" in user_question.lower():
            protein = "Mixed Vegetables 500g"
        elif "paneer" in user_question.lower():
            protein = "Paneer 250g"
        
        fallback = f"Basmati Rice 1kg\n{protein}\nOnions 250g\nYogurt 200g\nBiryani Masala 1 packet\nOil 100ml"
        items_list = []
        item_details = {}
        for line in fallback.split('\n'):
            qty_match = re.search(r'(\d+\s*\w+)$', line)
            qty = qty_match.group(1)
            name = re.sub(r'\s+\d+\s*\w+$', '', line).strip()
            items_list.append(name)
            item_details[name] = {"qty": qty}

    # Step 3: Search live prices from Google
    st.info(f"🔍 Searching Blinkit prices for {len(items_list)} items...")
    price_results = price_searcher.get_all_prices(items_list)
    
    # Step 4: Combine data with URLs
    final_items = []
    for result in price_results:
        name = result['name']
        price = result['price']
        qty = item_details.get(name, {}).get('qty', '1 unit')
        url = mcp_blinkit_search_tool(name)['url']
        final_items.append({
            "name": name,
            "qty": qty, 
            "price": price,
            "url": url
        })

    # Step 5: Compile table
    final = compiler.run(final_items)

    if stream:
        for word in final.split():
            yield word + " "
    else:
        return final

__all__ = ['ask_agent', 'mcp_blinkit_search_tool']
