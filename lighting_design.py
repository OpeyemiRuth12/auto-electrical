"""
AutoElect - Lighting Design Module
------------------------------------
Step 3: Calculates the number of light fittings required for a room,
based on CIBSE recommended illuminance (lux) levels, using the lumen
method.

Formula:
    N = (E x A) / (F x UF x MF)

    N  = number of fittings required
    E  = required illuminance (lux)
    A  = room area (m^2)
    F  = luminous flux of one fitting (lumens)
    UF = utilisation factor - how much emitted light actually reaches
         the working plane (depends on room shape and surface colours)
    MF = maintenance factor - accounts for dirt build-up and lamp
         output dropping over time

UF and MF default to 0.5 and 0.8 here as reasonable starting values
for a typical residential room. Cross-check these against the CIBSE
guide you're citing - real values depend on room index and surface
reflectances, which we can add later if your report needs that level
of detail.
"""

import math

# CIBSE recommended illuminance levels for common residential rooms (lux)
ROOM_LUX_LEVELS = {
    "Living Room":       150,
    "Bedroom":           100,
    "Kitchen":           300,
    "Bathroom":          150,
    "Dining Room":       150,
    "Study/Home Office": 300,
    "Corridor/Hallway":  100,
    "Store Room":        100,
    "Garage":            150,
}

# Luminous flux (lumens) and wattage for common fitting types.
# These should match the lighting entries in calculations.py's
# APPLIANCE_LIBRARY so the two stay consistent.
FITTING_DATA = {
    "Fluorescent Tube":              {"lumens": 2600, "watts": 40},
    "LED Bulb (9W)":                 {"lumens": 806,  "watts": 9},
    "LED Bulb (12W)":                {"lumens": 1055, "watts": 12},
    "LED Downlight - Premium (15W)": {"lumens": 1500, "watts": 15},
}


def calculate_lighting(room_type, area_m2, fitting_name,
                        utilisation_factor=0.5, maintenance_factor=0.8):
    """
    room_type   : must be a key in ROOM_LUX_LEVELS
    area_m2     : floor area of the room (square metres)
    fitting_name: must be a key in FITTING_DATA

    Returns a dict with the required lux, fittings needed, and the
    resulting lighting load in watts for that room.
    """
    if room_type not in ROOM_LUX_LEVELS:
        raise ValueError(f"'{room_type}' is not in ROOM_LUX_LEVELS.")
    if fitting_name not in FITTING_DATA:
        raise ValueError(f"'{fitting_name}' is not in FITTING_DATA.")

    required_lux = ROOM_LUX_LEVELS[room_type]
    fitting = FITTING_DATA[fitting_name]

    fittings_needed = (required_lux * area_m2) / (
        fitting["lumens"] * utilisation_factor * maintenance_factor
    )
    fittings_needed = math.ceil(fittings_needed)
    lighting_load_w = fittings_needed * fitting["watts"]

    return {
        "room_type": room_type,
        "area_m2": area_m2,
        "required_lux": required_lux,
        "fitting_name": fitting_name,
        "fittings_needed": fittings_needed,
        "lighting_load_w": lighting_load_w,
    }


def calculate_building_lighting(rooms):
    """
    rooms: list of dicts like
        [{"room_type": "Living Room", "area_m2": 18, "fitting_name": "LED Bulb (9W)"}, ...]

    Returns (per_room_results, total_lighting_load_w)
    """
    results = []
    total_load = 0

    for room in rooms:
        result = calculate_lighting(
            room["room_type"], room["area_m2"], room["fitting_name"]
        )
        results.append(result)
        total_load += result["lighting_load_w"]

    return results, total_load


# ---------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------

if __name__ == "__main__":
    sample_rooms = [
        {"room_type": "Living Room", "area_m2": 18, "fitting_name": "LED Bulb (9W)"},
        {"room_type": "Kitchen", "area_m2": 10, "fitting_name": "LED Bulb (12W)"},
        {"room_type": "Bedroom", "area_m2": 12, "fitting_name": "LED Bulb (9W)"},
        {"room_type": "Bathroom", "area_m2": 5, "fitting_name": "LED Bulb (9W)"},
    ]

    results, total_load = calculate_building_lighting(sample_rooms)

    for r in results:
        print(
            f"{r['room_type']} ({r['area_m2']} m^2): needs {r['fittings_needed']} x "
            f"{r['fitting_name']} -> {r['lighting_load_w']} W"
        )

    print(f"\nTotal lighting load: {total_load} W")
