import streamlit as st
import urllib.parse
from groq import Groq
try:
    from serpapi import GoogleSearch
    SERPAPI_AVAILABLE = True
except:
    SERPAPI_AVAILABLE = False

st.set_page_config(page_title="Smart Cart Agent", page_icon="🛒", layout="wide")

MIN_PRICE_PER_PERSON = {
    "biryani": 150,
    "burger": 99,
    "pizza": 199,
    "meal": 120,
    "thali": 100,
    "sandwich": 80,
    "dosa": 60,
    "idli": 40,
    "pasta": 130,
    "noodles": 80,
    "noodels": 80, # typo handle
    "maggi": 50,
    "roll": 90
}

INGREDIENTS_MAP = {
    "biryani": {
        "Basmati Rice": {"base": 250, "unit": "g"},
        "Chicken": {"base": 250, "unit": "g"},
        "Biryani Masala": {"base": 1, "unit": "packet"},
        "Onions": {"base": 150, "unit": "g"},
        "Curd": {"base": 100, "unit": "ml"},
        "Ghee": {"base": 50, "unit": "ml"}
    },
    "burger": {
        "Burger Buns": {"base": 1, "unit": "pc"},
        "Chicken Patty": {"base": 1, "unit": "pc"},
        "Cheese Slices": {"base": 1, "unit": "pc"},
        "Lettuce": {"base": 20, "unit": "g"},
        "Tomato": {"base": 50, "unit": "g"},
        "Mayonnaise": {"base": 1, "unit": "packet"}
    },
    "pizza": {
        "Pizza Base": {"base": 1, "unit": "pc"},
        "Pizza Sauce": {"base": 1, "unit": "packet"},
        "Mozzarella Cheese": {"base": 100, "unit": "g"},
        "Capsicum": {"base": 50, "unit": "g"},
        "Onion": {"base": 50, "unit": "g"}
    },
    "thali": {
        "Rice": {"base": 200, "unit": "g"},
        "Toor Dal": {"base": 100, "unit": "g"},
        "Vegetables Mix": {"base": 200, "unit": "g"},
        "Curd": {"base": 100, "unit": "ml"},
        "Chapati Flour": {"base": 150, "unit": "g"}
    },
    "dosa": {
        "Dosa Batter": {"base": 500, "unit": "g"},
        "Potato": {"base": 250, "unit": "g"},
        "Onion": {"base": 100, "unit": "g"},
        "Coconut Chutney Mix": {"base": 1, "unit": "packet"}
    },
    "noodles": {
        "Noodles": {"base": 1, "unit": "packet"},
        "Mixed Vegetables": {"base": 200, "unit": "g"},
        "Soy Sauce": {"base": 1, "unit": "bottle"},
        "Oil": {"base": 50, "unit": "ml"},
        "Onion": {"base": 100, "unit": "g"},
        "Capsicum": {"base": 100, "unit": "g"}
    }
}

def calculate_price(item, qty):
    item_lower = item.lower().strip()
    base_price = 100
    for food, min_val in MIN_PRICE_PER_PERSON.items():
        if food in item_lower:
            base_price = min_val
            break
    return base_price * int(qty)

def create_blinkit_link(item_name):
    encoded = urllib.parse.quote(item_name)
    return f"https://blinkit.com/s/?q={encoded}"

def fetch_ingredients_ai(item, qty):
    """Groq tho direct generate - SerpAPI avasaram ledu"""
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        prompt = f"""For {qty} person {item} Indian recipe, list 5-8 main ingredients with quantity.

Format EXACTLY like this, one per line:
Ingredient Name - Quantity

Example for Veg Noodles:
Noodles - 1 packet
Mixed Vegetables - 200g
Soy Sauce - 1 bottle
Oil - 50ml
Onion - 100g

No extra text. Indian portions. Correct spelling."""

        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300
        )

        result = []
        for line in response.choices[0].message.content.strip().split('\n'):
            if '-' in line:
                parts = line.split('-')
                name = parts[0].strip()
                qty_str = parts[1].strip()
                if name and qty_str:
                    result.append({
                        "name": name,
                        "qty": qty_str,
                        "link": create_blinkit_link(name)
                    })
        return result if result else None
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

def get_scaled_ingredients(item, qty):
    item_clean = item.lower().replace(" ", "").replace("noodels", "noodles")
    base_items = INGREDIENTS_MAP.get(item_clean, {})
    scaled_data = []

    for ing, data in base_items.items():
        scaled_qty = data["base"] * qty
        unit = data["unit"]

        if unit == "g" and scaled_qty >= 1000:
            qty_str = f"{scaled_qty/1000:.1f}kg"
        elif unit == "ml" and scaled_qty >= 1000:
            qty_str = f"{scaled_qty/1000:.1f}L"
        elif unit in ["packet", "pc", "bunch", "bottle"]:
            qty_str = f"{int(scaled_qty)} {unit}"
        else:
            qty_str = f"{int(scaled_qty)}{unit}"

        scaled_data.append({
            "name": ing,
            "qty": qty_str,
            "link": create_blinkit_link(ing)
        })

    return scaled_data

# ===== UI =====
st.title("🛒 Smart Cart Agent")
st.subheader("AI-Powered Recipe Ingredients + Blinkit Links")

col1, col2 = st.columns([3, 1])

with col1:
    option = st.selectbox(
        "Select Meal or Type Custom",
        options=list(MIN_PRICE_PER_PERSON.keys()) + ["Custom..."],
        format_func=lambda x: x.title() if x!= "Custom..." else "✍️ Type Your Own"
    )

    if option == "Custom...":
        item = st.text_input("Enter any recipe name", placeholder="e.g., Paneer Butter Masala, Pasta, Maggi")
    else:
        item = option

with col2:
    qty = st.number_input("People", min_value=1, max_value=20, value=1)

generate_btn = st.button("Generate Cart 🛍️", use_container_width=True, type="primary")

if generate_btn and item:
    total = calculate_price(item, qty)

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Meal", item.title())
    with c2:
        st.metric("People", qty)
    with c3:
        st.metric("Est. Total", f"₹{total}")

    st.divider()
    st.subheader("📝 Ingredients List")

    # 1. Known recipe check - typos handle chesam
    ingredients = get_scaled_ingredients(item, qty)

    # 2. Unknown recipe - AI tho direct generate
    if not ingredients:
        with st.spinner(f"Generating ingredients for {item}..."):
            ingredients = fetch_ingredients_ai(item, qty)

    # 3. Final fallback
    if not ingredients:
        st.warning("Could not generate ingredients. Using generic list.")
        ingredients = [
            {"name": item.title(), "qty": f"{qty*200}g", "link": create_blinkit_link(item)},
            {"name": "Oil", "qty": f"{qty*50}ml", "link": create_blinkit_link("Oil")},
            {"name": "Spices Mix", "qty": "1 packet", "link": create_blinkit_link("Spices")}
        ]

    # Display all ingredients
    for ing in ingredients:
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            st.write(f"**{ing['name']}**")
        with col2:
            st.write(ing['qty'])
        with col3:
            st.link_button("🛍️ Buy", ing['link'], use_container_width=True)

    st.divider()

    all_items = [ing['name'] for ing in ingredients]
    master_link = create_blinkit_link(",".join(all_items))

    st.success(f"✅ **{len(ingredients)} items ready** for {qty} person {item.title()}")
    st.link_button(
        "🛒 Add ALL Items to Blinkit at Once",
        master_link,
        use_container_width=True,
        type="primary"
    )

st.divider()
st.caption("Known: Biryani ₹150 | Burger ₹99 | Pizza ₹199 | Noodles ₹80 | Others: ₹100/person")
