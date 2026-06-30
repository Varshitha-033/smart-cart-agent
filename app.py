import streamlit as st
import os
from langchain_groq import ChatGroq
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from serpapi import GoogleSearch
import json

# ===== CONFIG =====
st.set_page_config(page_title="Smart Cart Agent", page_icon="🛒", layout="wide")

# ===== PRICE FLOOR CONFIG - EKKADA CHANGE CHEYALI =====
MIN_PRICE_PER_PERSON = {
    "biryani": 150,
    "burger": 99,
    "pizza": 199,
    "meal": 120,
    "thali": 100,
    "sandwich": 80,
    "roll": 90,
    "chicken": 180,
    "mutton": 250
}

DEFAULT_PRICE = 100 # Vere items ki default

# ===== PRICE CALCULATOR FUNCTION =====
def calculate_item_price(item_name, qty=1, api_price=None):
    """
    Minimum price enforce chestadi.
    API price takkuva unna kuda floor price istadi.
    """
    if not item_name:
        return DEFAULT_PRICE * qty

    item_lower = item_name.lower().strip()

    # 1. Base price find chey
    base_price = 0
    for food, min_val in MIN_PRICE_PER_PERSON.items():
        if food in item_lower:
            base_price = min_val
            break

    if base_price == 0:
        base_price = DEFAULT_PRICE

    # 2. API price tho compare chey
    if api_price and isinstance(api_price, (int, float)) and api_price > 0:
        final_price = max(api_price, base_price) # Yekkuva undedi
    else:
        final_price = base_price

    # 3. Quantity multiply
    total = final_price * int(qty)
    return int(total)

# ===== SERPAPI SEARCH WITH PRICE FLOOR =====
def search_grocery_price(item, location="India"):
    """SerpAPI tho price teesukuni floor apply chestadi"""
    try:
        params = {
            "q": f"{item} price {location}",
            "api_key": st.secrets["SERPAPI_KEY"],
            "engine": "google_shopping"
        }
        search = GoogleSearch(params)
        results = search.get_dict()

        # API nunchi price extract chey
        api_price = None
        if "shopping_results" in results and results["shopping_results"]:
            price_str = results["shopping_results"][0].get("price", "0")
            api_price = int(''.join(filter(str.isdigit, price_str[:6])))
    except:
        api_price = None

    # Price floor apply chesi return chey
    return calculate_item_price(item, qty=1, api_price=api_price)

# ===== LANGCHAIN TOOLS =====
def get_price_tool_func(query):
    """Agent ki price tool"""
    # "2 biryani" nunchi item, qty teesko
    parts = query.lower().split()
    qty = 1
    item = query

    for part in parts:
        if part.isdigit():
            qty = int(part)
            item = query.replace(part, "").strip()

    price = calculate_item_price(item, qty=qty)
    return f"{item.title()} for {qty} person: ₹{price}"

price_tool = Tool(
    name="GroceryPriceChecker",
    func=get_price_tool_func,
    description="Get minimum price for Indian grocery items. Input: '2 biryani' or 'burger'"
)

# ===== AGENT SETUP =====
SYSTEM_PROMPT = """
You are Smart Cart Agent for Indian families. You help plan grocery meals and create Blinkit cart.

CRITICAL PRICING RULES:
1. Biryani = MINIMUM ₹150 per person. Never quote below ₹150.
2. Burger = MINIMUM ₹99 per person. Never quote below ₹99.
3. Pizza = MINIMUM ₹199 per person.
4. Thali = MINIMUM ₹100 per person.
5. For all meal calculations, use these base rates even if online shows cheaper.
6. Always show breakdown: Item x Qty = Total

Example:
User: "1 person biryani"
You: "Chicken Biryani for 1 person: ₹150 (minimum base price)"

User: "2 people burger"
You: "Burger x 2 = ₹198 (₹99 per person)"
"""

def init_agent():
    llm = ChatGroq(
        groq_api_key=st.secrets["GROQ_API_KEY"],
        model_name="llama-3.1-70b-versatile",
        temperature=0.3
    )

    tools = [price_tool]

    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        agent_kwargs={"system_message": SYSTEM_PROMPT}
    )
    return agent

# ===== STREAMLIT UI =====
st.title("🛒 Smart Cart Agent - AI Grocery Planner")
st.caption("Kaggle Capstone 2026 | Biryani ₹150 | Burger ₹99 minimum")

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Chat history display
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask: '1 person biryani meal' or '2 burgers'"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Calculating best prices..."):
            agent = init_agent()
            response = agent.run(prompt)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# ===== SIDEBAR - PRICE LIST =====
with st.sidebar:
    st.header("💰 Base Price List")
    st.caption("Minimum per person")
    for item, price in MIN_PRICE_PER_PERSON.items():
        st.markdown(f"**{item.title()}**: ₹{price}")

    st.divider()
    st.caption("Kaggle AI Agents Capstone 2026")
    st.link_button("View on GitHub", "https://github.com/varshithagudisa/smart-cart-agent")
