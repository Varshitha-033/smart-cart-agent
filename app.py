import streamlit as st
from groq import Groq
from serpapi import GoogleSearch
import os

st.set_page_config(page_title="Smart Cart Agent", page_icon="🛒")

# ===== PRICE FLOOR =====
MIN_PRICE_PER_PERSON = {
    "biryani": 150,
    "burger": 99,
    "pizza": 199,
    "meal": 120,
    "thali": 100
}

def enforce_price_floor(item_name, api_price=None):
    item_lower = item_name.lower().strip()
    base_price = 100
    for food, min_val in MIN_PRICE_PER_PERSON.items():
        if food in item_lower:
            base_price = min_val
            break

    if api_price and isinstance(api_price, (int, float)) and api_price > 0:
        return max(api_price, base_price)
    return base_price

def search_grocery_price(item):
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

    return enforce_price_floor(item, api_price)

# ===== GROQ FIX - MODEL NAME + MESSAGE FORMAT =====
def get_agent_response(user_prompt, chat_history):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    # Price info prepare chey
    price_info = ""
    for food in MIN_PRICE_PER_PERSON.keys():
        if food in user_prompt.lower():
            price = search_grocery_price(food)
            price_info += f"\n{food.title()}: ₹{price}/person"

    system_msg = f"""You are Smart Cart Agent for Indian families.

CRITICAL RULES:
1. Biryani = MINIMUM ₹150 per person
2. Burger = MINIMUM ₹99 per person
3. Pizza = MINIMUM ₹199 per person
4. Never quote below these prices

Price data: {price_info}

Give clear breakdown with totals."""

    # Messages clean chey - only role + content strings
    clean_history = []
    for msg in chat_history:
        if msg["role"] in ["user", "assistant"] and msg.get("content"):
            clean_history.append({
                "role": msg["role"],
                "content": str(msg["content"])
            })

    messages = [{"role": "system", "content": system_msg}]
    messages.extend(clean_history)
    messages.append({"role": "user", "content": str(user_prompt)})

    # FIX: Correct model name for Groq
    response = client.chat.completions.create(
        model="llama-3.1-70b-versatile", # Ee model 100% work avtadi
        messages=messages,
        temperature=0.3,
        max_tokens=800
    )
    return response.choices[0].message.content

# ===== STREAMLIT UI =====
st.title("🛒 Smart Cart Agent - AI Grocery Planner")
st.caption("Kaggle Capstone 2026")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask: '1 person biryani meal plan'"):
    # User message add chey
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Finding best prices..."):
            try:
                # Last 5 messages mathrame history ga pampu - current prompt exclude chey
                history = st.session_state.messages[:-1][-5:]
                response = get_agent_response(prompt, history)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                error_msg = f"Error: {str(e)}\n\nCheck GROQ_API_KEY in secrets."
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# ===== SIDEBAR =====
with st.sidebar:
    st.header("💰 Base Prices")
    st.caption("Minimum per person")
    for item, price in MIN_PRICE_PER_PERSON.items():
        st.markdown(f"**{item.title()}**: ₹{price}")
    st.divider()
    st.caption("Kaggle AI Agents Capstone 2026")
