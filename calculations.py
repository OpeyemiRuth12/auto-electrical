"""
AutoElect - Core Calculation Engine
------------------------------------
Step 1: Appliance load scheduling and diversity factor application.

This module does NOT depend on Streamlit, the UI, or floor plan upload.
It takes a plain list of selected appliances and returns the connected
load and maximum demand, so it can be tested on its own first.
"""

# ---------------------------------------------------------------------
# 1. Appliance Library
# ---------------------------------------------------------------------
# 'category' decides which diversity rule applies later.
# power_w values are typical ratings for common Nigerian household items.
# You should adjust/expand this list to match what you had in your
# earlier version, or add manufacturer values where you have them.

APPLIANCE_LIBRARY = {
    # Lighting
    "LED Bulb (9W)":              {"power_w": 9,    "category": "lighting"},
    "LED Bulb (12W)":             {"power_w": 12,   "category": "lighting"},
    "Fluorescent Tube":           {"power_w": 40,   "category": "lighting"},
    "Security/Flood Light":       {"power_w": 30,   "category": "lighting"},

    # General power / socket outlets
    "Standing Fan":               {"power_w": 60,   "category": "socket"},
    "Ceiling Fan":                {"power_w": 75,   "category": "socket"},
    "Television (LED 32-43in)":   {"power_w": 120,  "category": "socket"},
    "Satellite/DSTV Decoder":     {"power_w": 30,   "category": "socket"},
    "Wi-Fi Router":                {"power_w": 15,   "category": "socket"},
    "Laptop Charger":             {"power_w": 65,   "category": "socket"},
    "Phone Charger":              {"power_w": 10,   "category": "socket"},
    "Sound System":               {"power_w": 100,  "category": "socket"},
    "Blender":                    {"power_w": 400,  "category": "socket"},
    "Refrigerator (Medium)":      {"power_w": 150,  "category": "socket"},
    "Chest Freezer":              {"power_w": 250,  "category": "socket"},
    "Washing Machine":            {"power_w": 500,  "category": "socket"},
    "Air Conditioner (1HP)":      {"power_w": 750,  "category": "socket"},
    "Air Conditioner (1.5HP)":    {"power_w": 1100, "category": "socket"},
    "Air Conditioner (2HP)":      {"power_w": 1500, "category": "socket"},
    "Water Pump":                 {"power_w": 750,  "category": "socket"},
    "Electric Pressing Iron":     {"power_w": 1000, "category": "socket"},

    # Cooking
    "Electric Cooker/Hotplate":   {"power_w": 2000, "category": "cooking"},
    "Microwave Oven":             {"power_w": 1200, "category": "cooking"},
    "Electric Kettle":            {"power_w": 1500, "category": "cooking"},
    "Toaster":                    {"power_w": 800,  "category": "cooking"},

    # Water heating
    "Instant Shower Heater":      {"power_w": 3500, "category": "water_heating"},
    "Immersion Water Heater":     {"power_w": 3000, "category": "water_heating"},
}


# ---------------------------------------------------------------------
# 2. Connected Load
# ---------------------------------------------------------------------

def calculate_connected_load(selected_appliances):
    """
    selected_appliances: list of dicts, e.g.
        [{"name": "LED Bulb (9W)", "quantity": 10}, ...]

    Returns (breakdown_by_category_in_watts, total_connected_load_in_watts)
    """
    breakdown = {"lighting": 0, "socket": 0, "cooking": 0, "water_heating": 0}

    for item in selected_appliances:
        name = item["name"]
        qty = item.get("quantity", 1)

        if name not in APPLIANCE_LIBRARY:
            raise ValueError(f"'{name}' is not in the appliance library.")

        info = APPLIANCE_LIBRARY[name]
        breakdown[info["category"]] += info["power_w"] * qty

    total_connected_load = sum(breakdown.values())
    return breakdown, total_connected_load


# ---------------------------------------------------------------------
# 3. Diversity Factors -> Maximum Demand
# ---------------------------------------------------------------------
# Based on the IEE On-Site Guide domestic diversity allowances (the
# guidance document used alongside BS 7671 for this kind of sizing).
# These are a reasonable starting point - confirm the exact allowances
# against your reference copy and adjust if your lecturer expects a
# specific table.

def apply_diversity(breakdown):
    """
    breakdown: dict with keys 'lighting', 'socket', 'cooking', 'water_heating'
               (values in watts, from calculate_connected_load)

    Returns (demand_by_category_in_watts, maximum_demand_in_watts)
    """
    demand = {}

    # Lighting: 66% of total connected lighting load
    demand["lighting"] = breakdown["lighting"] * 0.66

    # Socket outlets/general power: 100% of first 1000W + 40% of remainder
    socket_load = breakdown["socket"]
    if socket_load <= 1000:
        demand["socket"] = socket_load
    else:
        demand["socket"] = 1000 + (socket_load - 1000) * 0.40

    # Cooking: 100% of first 10A (~2300W @ 230V) + 30% of remainder
    cooking_load = breakdown["cooking"]
    first_block = 2300
    if cooking_load <= first_block:
        demand["cooking"] = cooking_load
    else:
        demand["cooking"] = first_block + (cooking_load - first_block) * 0.30

    # Water heating: simplified as 100% for now.
    # TODO: refine to "100% largest + 100% second + 25% of the rest"
    # once we decide how multiple heaters are entered in the UI.
    demand["water_heating"] = breakdown["water_heating"]

    maximum_demand = sum(demand.values())
    return demand, maximum_demand


# ---------------------------------------------------------------------
# Quick test - run this file directly to sanity-check the logic
# ---------------------------------------------------------------------

if __name__ == "__main__":
    sample_house = [
        {"name": "LED Bulb (9W)", "quantity": 10},
        {"name": "Ceiling Fan", "quantity": 4},
        {"name": "Refrigerator (Medium)", "quantity": 1},
        {"name": "Television (LED 32-43in)", "quantity": 2},
        {"name": "Air Conditioner (1.5HP)", "quantity": 2},
        {"name": "Electric Cooker/Hotplate", "quantity": 1},
        {"name": "Instant Shower Heater", "quantity": 2},
    ]

    breakdown, connected_load = calculate_connected_load(sample_house)
    demand, max_demand = apply_diversity(breakdown)

    print("Connected load breakdown (W):", breakdown)
    print("Total connected load:", connected_load, "W")
    print()
    print("Demand after diversity (W):", {k: round(v) for k, v in demand.items()})
    print("Maximum demand:", round(max_demand), "W")
    print("Maximum demand:", round(max_demand / 230, 1), "A  (at 230V)")
