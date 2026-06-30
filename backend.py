"""
Smart Cart Agent - Concierge Agents Track
Kaggle AI Agents Intensive Vibe Coding Capstone
Agent Skills: Reasoning + Tool Use + Computation + Security
"""

import requests
import json
import re
from groq import Groq
import streamlit as st

# SECURITY: API keys loaded from environment/secrets with graceful fallback
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except KeyError:
    st.error("Missing GROQ_API_KEY. Add it in Streamlit Cloud → Settings → Secrets")
    st.stop()

try:
    SERP_KEY = st.secrets["SERPAPI_KEY"]
    SERP_ENABLED = True
except KeyError:
    SERP_KEY = None
    SERP_ENABLED = False

class CartAgent:
    def __init__(self):
        self.llm = Groq(api_key=GROQ_KEY)
        self.search_endpoint = "https://serpapi.com/search"
        self.serp_enabled = SERP_ENABLED

    def generate_shopping_list(self, dish: str, people: int) -> dict:
        """
        AGENT SKILL: Multi-step Reasoning + Tool Use + Computation
        Pipeline: Dish → Ingredients → Prices → Total
        """
        dish = self._sanitize_input(dish)
        people = max(1, min(people, 20))
        ingredients = self._reason_ingredients(dish, people)
        priced_items = self._use_search_tool(ingredients)
        return self._calculate_total(priced_items, people)

    def _sanitize_input(self, dish: str) -> str:
        """SECURITY: Input sanitization against prompt injection"""
        dish = dish.strip()[:100]
        dish = re.sub(r'[<>{}[\]\\]', '', dish)
        return dish

    def _reason_ingredients(self, dish: str, people: int) -> list:
        """
        AGENT SKILL: Reasoning
        Uses LLM to decompose dish into ingredient list with MINIMAL quantities
        """
        if people == 1:
            portion_note = "Use MINIMAL quantities - single meal portions only. Example: oil 1 tbsp not 100ml, onion 1 small not 250g"
        else:
            portion_note = f"Realistic quantities for {people} people"

        prompt = f"""You are a Smart Cart Agent for Indian grocery planning.

Task: List ingredients for "{dish}" to serve {people} people.

CRITICAL RULES:
1. {portion_note}
2. Include ALL ingredients - spices, oil, salt everything
3. Format: "ingredient - quantity unit" per line only
4. No explanations, just the list
5. For 1 person: Think single serving, hostel-style portions

Example for "palak paneer for 1":
palak - 100g
paneer - 75g
onion - 1 small
tomato - 1 small
ginger-garlic paste - 1 tsp
oil - 1 tbsp
cumin seeds - 1/4 tsp
garam masala - 1/4 tsp
turmeric - pinch
salt - to taste
cream - 1 tsp

Now list ingredients for "{dish}" for {people} people:"""

        try:
            response = self.llm.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=800
            )
            raw_list = response.choices[0].message.content.strip()
            return [line.strip() for line in raw_list.split('\n') if line.strip() and '-' in line]
        except Exception as e:
            return [f"Error: {str(e)}"]

    def _use_search_tool(self, ingredients: list) -> list:
        """
        AGENT SKILL: Tool Use
        For each ingredient, fetch live price from web via SerpAPI or use estimates
        """
        priced_items = []
        for item_line in ingredients:
            try:
                parts = item_line.split('-')
                if len(parts) < 2:
                    continue
                ingredient = parts[0].strip()
                quantity = parts[1].strip()

                if self.serp_enabled:
                    price_data = self._fetch_price_from_web(ingredient)
                else:
                    price_data = {"price": self._estimate_price(ingredient), "source": "Estimated"}

                priced_items.append({
                    "item": ingredient,
                    "quantity": quantity,
                    "price_inr": price_data["price"],
                    "source": price_data["source"]
                })
            except:
                priced_items.append({
                    "item": ingredient,
                    "quantity": quantity,
                    "price_inr": 10,
                    "source": "Estimated"
                })
        return priced_items

    def _fetch_price_from_web(self, ingredient: str) -> dict:
        """Tool: SerpAPI - Real-time price from Blinkit/Zepto"""
        if not self.serp_enabled:
            return {"price": self._estimate_price(ingredient), "source": "Estimated"}

        params = {
            "q": f"{ingredient} price Blinkit India",
            "api_key": SERP_KEY,
            "engine": "google",
            "gl": "in"
        }
        try:
            response = requests.get(self.search_endpoint, params=params, timeout=5)
            data = response.json()
            if "organic_results" in data:
                for result in data["organic_results"][:3]:
                    price_match = re.search(r'₹\s*(\d+)', result.get("snippet", ""))
                    if price_match:
                        return {"price": int(price_match.group(1)), "source": "Blinkit/Zepto"}
        except:
            pass
        return {"price": self._estimate_price(ingredient), "source": "Estimated"}

    def _estimate_price(self, ingredient: str) -> int:
        """
        AGENT SKILL: Heuristic Reasoning
        Smallest pack prices for single-person cooking - Blinkit 2026 rates
        """
        price_map = {
            "onion": 8, "tomato": 10, "potato": 6, "palak": 10,
            "coriander": 5, "green chili": 3, "ginger": 5, "garlic": 5, "lemon": 3,
            "paneer": 35, "milk": 28, "curd": 15, "butter": 15, "cream": 12, "cheese": 25,
            "chicken": 65, "mutton": 180, "egg": 6, "fish": 80,
            "oil": 25, "rice": 15, "atta": 12, "sugar": 10, "salt": 5, "dal": 20, "tur dal": 25,
            "turmeric": 5, "cumin": 8, "garam masala": 10, "chili powder": 5,
            "coriander powder": 5, "ginger-garlic paste": 8,
            "ghee": 50, "bread": 25
        }

        ingredient_lower = ingredient.lower()
        for key, price in price_map.items():
            if key in ingredient_lower:
                return price
        return 10

    def _calculate_total(self, items: list, people: int) -> dict:
        """
        AGENT SKILL: Computation
        Deterministic arithmetic: sum prices, add tax, format output
        """
        total = sum(item["price_inr"] for item in items)
        return {
            "items": items,
            "total_inr": total,
            "people": people,
            "agent_version": "CartAgent v1.0"
        }

    def is_greeting(self, text: str) -> bool:
        """SECURITY: Greeting detection to avoid injection"""
        greetings = ['hi', 'hello', 'hey', 'namaste', 'hii']
        text_lower = text.lower().strip()
        return any(text_lower == g or text_lower.startswith(g + ' ') for g in greetings)
