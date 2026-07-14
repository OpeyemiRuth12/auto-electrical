"""
AutoElect - Design Tier Profiles
-----------------------------------
Defines the three design preference tiers a user can choose from:
Cost-Effective, Standard, and Luxury.

IMPORTANT: tier never changes code compliance. All three tiers still
produce a fully BS 7671:2018 / CIBSE compliant design - the difference
is how much extra safety margin and which component grade is used.
"Cost-Effective" means minimum sufficient margin, not reduced safety.
"""

TIER_PROFILES = {
    "Cost-Effective": {
        "description": "Minimum compliant sizing - lowest upfront cost, no extra headroom.",
        "cable_oversize_steps": 0,
        "generator_safety_margin": 1.15,
        "default_battery_type": "Lead-Acid / AGM (cost-effective, shorter lifespan)",
        "suggested_essential_load_percent": 40,
        "recommended_fitting": "Fluorescent Tube",
    },
    "Standard": {
        "description": "Balanced sizing with a normal safety margin - the recommended default.",
        "cable_oversize_steps": 0,
        "generator_safety_margin": 1.25,
        "default_battery_type": "Lead-Acid / AGM (cost-effective, shorter lifespan)",
        "suggested_essential_load_percent": 50,
        "recommended_fitting": "LED Bulb (9W)",
    },
    "Luxury": {
        "description": "Extra headroom and premium components - higher upfront cost, more resilience and future-proofing.",
        "cable_oversize_steps": 1,
        "generator_safety_margin": 1.35,
        "default_battery_type": "Lithium-Ion (higher upfront cost, deeper discharge, longer lifespan)",
        "suggested_essential_load_percent": 75,
        "recommended_fitting": "LED Downlight - Premium (15W)",
    },
}


if __name__ == "__main__":
    for tier_name, profile in TIER_PROFILES.items():
        print(f"{tier_name}:")
        for key, value in profile.items():
            print(f"  {key}: {value}")
        print()
