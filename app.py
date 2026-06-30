import streamlit as st
from langchain_groq import ChatGroq
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from serpapi import GoogleSearch
import os

# ===== CONFIG =====
st.set_page_config(page_title="Smart Cart Agent", page_icon="🛒")

# ===== PRICE FLOOR - NEW ADDITION =====
MIN_PRICE_PER_PERSON = {
    "biryani": 150,
    "burger": 99,
    "pizza": 199,
    "meal": 120,
    "thali": 100
}

def enforce_price_floor(item_name, api_price=None):
    """API price takkuva unna minimum price istadi"""
    item_lower = item_name.lower().strip()

    base_price = 100 # default
    for food, min_val in MIN_PRICE_PER_PERSON.items():
        if food in item_lower:
            base_price = min_val
            break

    if api_price and isinstance(api_price, (int, float)) and api_price > 0:
        return max(api_price, base_price) # Yekkuva undedi
    else:
        return base_price

# ===== SERPAPI TOOL WITH PRICE FLOOR =====
def search_grocery_price(item):
    """Search price and apply minimum floor"""
    try:
        params = {
            "q": f"{item} price India",
            "api_key": st.secrets["SERPAPI_KEY"],
            "engine": "google_shopping"
        }
        search = GoogleSearch(params)
        results = search.get_dict()

        api_price = None
        if "shopping_results" in results and results["shopping_results"]:
            price_str = results["shopping_results"][0].get("price", "0")
            api_price = int(''.join(filter(str.isdigit, price_str[:6])))
    except:
        api_price = None

    # Price floor apply chesi return chey
    final_price = enforce_price_floor(item, api_price)
    return f"Price for {item}: ₹{final_price}"

price_tool = Tool(
    name="GroceryPriceChecker",
    func=search_grocery_price,
    description="Get grocery prices with minimum floor. Biryani ₹150+, Burger ₹99+ per person"
)

# ===== AGENT SETUP - NEE OLD PROMPT + PRICE RULE =====
SYSTEM_PROMPT = """
You are Smart Cart Agent for Indian families.

CRITICAL PRICING RULES:
1. Biryani = MINIMUM ₹150 per person
2. Burger = MINIMUM ₹99 per person
3. Pizza = MINIMUM ₹199 per person
4. Never quote below these prices even if search shows cheaper
5. Always use GroceryPriceChecker tool for prices

You help plan grocery meals and create Blinkit cart links.
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

# ===== STREAMLIT UI - NEE OLD UI EXACT GA =====
st.title("🛒 Smart Cart Agent - AI Grocery Planner")
st.caption("Kaggle Capstone 2026")

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask: '1 person biryani meal plan'"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Finding best prices..."):
            agent = init_agent()
            response = agent.run(prompt)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# ===== SIDEBAR - PRICE LIST =====
with st.sidebar:
    st.header("💰 Base Prices")
    st.caption("Minimum per person")
    for item, price in MIN_PRICE_PER_PERSON.items():
        st.markdown(f"**{item.title()}**: ₹{price}")

    st.divider()
    st.caption("Kaggle AI Agents Capstone 2026")
