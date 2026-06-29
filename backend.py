import streamlit as st
from groq import Groq
import re
import urllib.parse
import concurrent.futures

# ============================================
# SECURITY FEATURE: API Key Management
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
# MCP SERVER TOOLS - Multi-Platform Search
# For Kaggle Demo: Prices are simulated. In production, use official APIs.
# ============================================

def mcp_blinkit_search(item_name: str) -> dict:
    """MCP Tool: Blinkit. Returns price and URL"""
    clean_item = re.sub(r'[^\w\s-]', '', item_name).strip()
    price = hash(clean_item + "blinkit") % 300 + 100
    url = f"https://blinkit.com/s/?q={urllib.parse.quote_plus(clean_item)}"
    return {"platform": "Blinkit", "price": price, "url": url}

def mcp_flipkart_search(item_name: str) -> dict:
    """MCP Tool: Flipkart Grocery"""
    clean_item = re.sub(r'[^\w\s-]', '', item_name).strip()
    price = hash(clean_item + "flipkart") % 300 + 90
    url = f"https://www.flipkart.com/search?q={urllib.parse.quote_plus(clean_item)}"
    return {"platform": "Flipkart", "price": price, "url": url}

def mcp_amazon_search(item_name: str) -> dict:
    """MCP Tool: Amazon Fresh"""
    clean_item = re.sub(r'[^\w\s-]', '', item_name).strip()
    price = hash(clean_item + "amazon") % 300 + 95
    url = f"https://www.amazon.in/s?k={urllib.parse.quote_plus(clean_item)}"
    return {"platform": "Amazon", "price": price, "url": url}

def mcp_meesho_search(item_name: str) -> dict:
    """MCP Tool: Meesho"""
    clean_item = re.sub(r'[^\w\s-]', '', item_name).strip()
    price = hash(clean_item + "meesho") % 300 + 80
    url = f"https://www.meesho.com/search?q={urllib.parse.quote_plus(clean_item)}"
    return {"platform": "Meesho", "price": price, "url": url}

# ============================================
# GOOGLE ADK MULTI-AGENT SYSTEM
# ============================================

class RecipeParserAgent:
    """Agent 1: Extracts specific items from ANY category"""
    def __init__(self, client):
        self.client = client
        self.role = """You are RecipeParserAgent.
TASK: Extract 3-5 SPECIFIC shopping items. Works for groceries, clothes, electronics.
CRITICAL: NEVER output just 1 item. Always give 3-5 options.
If user says 'cotton kurthis', output:
Cotton Kurti 1 unit
Printed Kurti 1 unit
Anarkali Kurti 1 unit
Straight Cut Kurti 1 unit
NEVER use generic words like 'item', 'product'. One item per line with quantity."""

    def run(self, user_request):
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": self.role},
                {"role": "user", "content": f"Extract 3-5 specific items from: {user_request}"}
            ],
            model="llama-3.1-8b-instant", temperature=0.3,
        )
        return response.choices[0].message.content

class PriceCompareAgent:
    """Agent 2: Compares prices across platforms using MCP tools"""
    def __init__(self):
        self.mcp_tools = [mcp_blinkit_search, mcp_flipkart_search, mcp_amazon_search, mcp_meesho_search]

    def find_cheapest(self, item_name):
        results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(tool, item_name) for tool in self.mcp_tools]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        cheapest = min(results, key=lambda x: x['price'])
        return cheapest

class CartCompilerAgent:
    """Agent 3: Compiles final table with cheapest links"""
    def __init__(self, client):
        self.client = client

    def run(self, items_with_prices):
        # Manually construct CART_DATA to guarantee URL is present
        cart_data_parts = []
        for i in items_with_prices:
            part = f"{i['name']}:{i['qty']}:{i['price']}:{i['platform']}:{i['url']}"
            cart_data_parts.append(part)
        cart_data_string = ",".join(cart_data_parts)

        # Ask LLM only for table, we add CART_DATA ourselves
        items_for_table = "\n".join([f"{i['name']}|{i['qty']}|₹{i['price']}|{i['platform']}" for i in items_with_prices])

        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You create markdown tables. Output ONLY the table with headers Item|Quantity|Best Price (INR)|Platform and a Total row. No extra text."},
                {"role": "user", "content": f"Create table for:\n{items_for_table}"}
            ],
            model="llama-3.1-8b-instant", temperature=0.3,
        )
        table = response.choices[0].message.content
        return f"{table}\n\n[CART_DATA]{cart_data_string}"

# ============================================
# ADK ORCHESTRATOR
# ============================================

def ask_agent(user_question, stream=False):
    client = get_client()
    parser = RecipeParserAgent(client)
    comparer = PriceCompareAgent()
    compiler = CartCompilerAgent(client)

    # Step 1: Parse items
    items_text = parser.run(user_question)
    items_list = [i.strip() for i in items_text.split('\n') if i.strip() and len(i.strip()) > 2]

    # Step 2: Find cheapest for each item
    items_with_prices = []
    for item_line in items_list[:6]: # Limit 6 items for speed
        item_name = re.sub(r'\s+\d+\s*\w+$', '', item_line).strip()
        qty_match = re.search(r'(\d+\s*\w+)$', item_line)
        qty = qty_match.group(1) if qty_match else "1 unit"

        if len(item_name) < 2:
            continue

        cheapest = comparer.find_cheapest(item_name)
        items_with_prices.append({
            "name": item_name,
            "qty": qty,
            "price": cheapest['price'],
            "platform": cheapest['platform'],
            "url": cheapest['url']
        })

    if not items_with_prices:
        return "Sorry, I couldn't find specific items. Try: 'chicken biryani ingredients' or 'cotton kurti for women'"

    # Step 3: Compile final output
    final = compiler.run(items_with_prices)

    if stream:
        for word in final.split():
            yield word + " "
    else:
        return final

__all__ = ['ask_agent']
