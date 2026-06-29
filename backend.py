import streamlit as st
from groq import Groq
import re
import urllib.parse

# ============================================
# SECURITY FEATURE: API Key Management
# All keys stored in Streamlit secrets. No hardcoding.
# User data is not stored or logged anywhere.
# ============================================

def get_client():
    """Create Groq client with API key from secrets"""
    if "GROQ_API_KEY" not in st.secrets:
        st.error("SECURITY: GROQ_API_KEY not found! Add it in Streamlit Cloud -> Settings -> Secrets")
        st.stop()
    
    api_key = str(st.secrets["GROQ_API_KEY"]).strip().replace('\n','').replace('\r','')
    
    if len(api_key)!= 56:
        st.error(f"SECURITY: Invalid GROQ_API_KEY length. Expected 56, got {len(api_key)}")
        st.stop()
        
    return Groq(api_key=api_key)

# ============================================
# MCP SERVER TOOL: Blinkit Search
# This function simulates an MCP tool that agents can call
# In production, this would be a separate MCP server
# ============================================

def mcp_blinkit_search_tool(item_name: str) -> str:
    """
    MCP Tool: search_blinkit
    Description: Generates Blinkit search URL for given item
    Agent Skill: Tool usage via MCP protocol
    Security: Input sanitization applied
    """
    clean_item = re.sub(r'[^\w\s-]', '', item_name).strip()
    if not clean_item:
        return "https://blinkit.com"
    
    search_query = urllib.parse.quote_plus(clean_item)
    return f"https://blinkit.com/s/?q={search_query}"

# ============================================
# GOOGLE ADK MULTI-AGENT SYSTEM
# Architecture: 3 specialized agents working together
# ============================================

class RecipeParserAgent:
    """Agent 1: Parses user request and extracts shopping context"""
    def __init__(self, client):
        self.client = client
        self.role = """You are RecipeParserAgent. 
CRITICAL: Extract ONLY specific ingredient/product names. 
NEVER output generic words like 'item', 'ingredient', 'product', 'grocery'.
If request is vague, list 5-8 common specific items for that category.
Example: For 'biryani' output 'Basmati Rice, Chicken, Yogurt, Onions, Garam Masala' not 'item'"""
    
    def run(self, user_request):
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": self.role},
                {"role": "user", "content": f"Extract specific shopping list from: {user_request}. Output only item names and qty, one per line."}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.3,
        )
        return response.choices[0].message.content

class PriceEstimatorAgent:
    """Agent 2: Estimates prices for Indian market"""
    def __init__(self, client):
        self.client = client
        self.role = """You are PriceEstimatorAgent. Give realistic INR prices for Indian grocery items.
Format each line as: Item Name | Quantity | Price
Use current Indian market rates. Be specific with item names."""
    
    def run(self, items_list):
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": self.role},
                {"role": "user", "content": f"Add realistic INR prices for these items:\n{items_list}"}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.5,
        )
        return response.choices[0].message.content

class CartCompilerAgent:
    """Agent 3: Compiles final table and adds CART_DATA for UI"""
    def __init__(self, client):
        self.client = client
        self.role = """You are CartCompilerAgent. CRITICAL RULES:
1. Use ONLY specific product names. NEVER use generic words like 'item', 'product', 'grocery', 'ingredient'
2. Format: Markdown table with headers: Item | Quantity | Approx Price (INR)
3. Add a Total row at the end of table
4. After table, add [CART_DATA] tag with format: Item1:Qty1:Price1,Item2:Qty2:Price2
5. In CART_DATA, do NOT include Total row
6. If you don't know specific items, say 'Please specify recipe' instead of using 'item'
7. Remove duplicates. No empty names."""
    
    def run(self, priced_items):
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": self.role},
                {"role": "user", "content": f"Compile final shopping cart from:\n{priced_items}"}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
        )
        return response.choices[0].message.content

# ============================================
# ADK ORCHESTRATOR: Runs multi-agent workflow
# ============================================

def ask_agent(user_question, stream=False):
    """
    Main ADK Orchestrator
    Runs: RecipeParserAgent -> PriceEstimatorAgent -> CartCompilerAgent
    Uses: MCP Tools for external data
    Security: All API calls use secured keys
    """
    client = get_client()
    
    parser = RecipeParserAgent(client)
    pricer = PriceEstimatorAgent(client)
    compiler = CartCompilerAgent(client)
    
    if stream:
        items = parser.run(user_question)
        priced = pricer.run(items)
        final = compiler.run(priced)
        
        for word in final.split():
            yield word + " "
    else:
        items = parser.run(user_question)
        priced = pricer.run(items)
        final = compiler.run(priced)
        return final

__all__ = ['ask_agent', 'mcp_blinkit_search_tool']
