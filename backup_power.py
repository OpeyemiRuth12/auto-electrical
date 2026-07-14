"""
AutoElect - Backup Power Sizing Module
-----------------------------------------
Step 4: Sizes backup power for a residential building - a generator,
and a solar/inverter/battery combination - based on the building's
maximum demand and a specified backup duration.

These are simplified, defensible starting-point calculations. Real-world
sizing also accounts for motor starting/surge currents (AC compressors,
water pumps) in more detail, and available roof area for solar panels -
both are natural extensions once this basic version is confirmed working.
"""

import math

# ---------------------------------------------------------------------
# 1. Generator sizing
# ---------------------------------------------------------------------

STANDARD_GENERATOR_SIZES_KVA = [
    2.5, 3.5, 5, 6.5, 7.5, 10, 12.5, 15, 20, 25, 30, 40, 45, 60, 75, 100
]

def size_generator(max_demand_w, power_factor=0.8, safety_margin=1.25):
    """
    max_demand_w  : building's maximum demand, in watts (real power)
    power_factor  : assumed average power factor of the load
                    (0.8 is typical for a mixed residential load)
    safety_margin : allowance for starting surges (motors, compressors)
                    and future load growth

    Returns the required capacity and the next standard generator size up.
    """
    required_kva = (max_demand_w / power_factor / 1000) * safety_margin

    for size in STANDARD_GENERATOR_SIZES_KVA:
        if size >= required_kva:
            return {"required_kva": round(required_kva, 2), "recommended_kva": size}

    raise ValueError(
        "Required capacity exceeds standard generator sizes - "
        "extend STANDARD_GENERATOR_SIZES_KVA for this load."
    )


# ---------------------------------------------------------------------
# 2. Inverter sizing
# ---------------------------------------------------------------------

STANDARD_INVERTER_SIZES_VA = [1000, 1500, 2000, 2500, 3000, 3500, 5000, 6000, 7500, 10000, 15000]

def size_inverter(essential_load_w, power_factor=0.8, safety_margin=1.25):
    """
    essential_load_w : the portion of the load that must run on backup
                       power (not necessarily the whole building - this
                       is a value the designer/user specifies)

    Returns the required capacity and the next standard inverter size up.
    """
    required_va = (essential_load_w / power_factor) * safety_margin

    for size in STANDARD_INVERTER_SIZES_VA:
        if size >= required_va:
            return {"required_va": round(required_va, 2), "recommended_va": size}

    raise ValueError(
        "Required capacity exceeds standard inverter sizes - "
        "extend STANDARD_INVERTER_SIZES_VA for this load."
    )


# ---------------------------------------------------------------------
# 3. Battery bank sizing
# ---------------------------------------------------------------------
# Assumes complete battery modules already built to the system voltage
# (e.g. 48V lithium battery packs, common in the Nigerian solar market)
# rather than raw 12V cells needing series-string calculations.
#
# Battery type decides depth of discharge. Defaults to Lead-Acid/AGM -
# the more conservative choice - if the user doesn't specify, so the
# bank isn't undersized for whatever chemistry actually gets installed.

BATTERY_TYPES = {
    "Lead-Acid / AGM (cost-effective, shorter lifespan)": 0.5,
    "Lithium-Ion (higher upfront cost, deeper discharge, longer lifespan)": 0.8,
}

STANDARD_BATTERY_AH = [100, 150, 200, 220]

def size_battery(essential_load_w, backup_hours, system_voltage=48,
                  battery_type="Lead-Acid / AGM (cost-effective, shorter lifespan)",
                  inverter_efficiency=0.85, unit_ah=200):
    """
    essential_load_w    : average load to be backed up, in watts
    backup_hours        : hours of autonomy required
    system_voltage      : battery bank voltage (commonly 12/24/48V)
    battery_type        : must be a key in BATTERY_TYPES - decides the
                          depth of discharge used
    inverter_efficiency : 0.85 is a conservative, real-world assumption
                          (accounts for wiring/conversion losses, rather
                          than an idealised 90-95% figure)
    unit_ah             : Ah rating of a single battery module, used to
                          work out how many modules are needed
    """
    if battery_type not in BATTERY_TYPES:
        raise ValueError(f"'{battery_type}' is not in BATTERY_TYPES.")

    depth_of_discharge = BATTERY_TYPES[battery_type]

    energy_needed_wh = (essential_load_w * backup_hours) / inverter_efficiency
    required_ah = energy_needed_wh / (system_voltage * depth_of_discharge)
    units_needed = math.ceil(required_ah / unit_ah)

    return {
        "battery_type": battery_type,
        "depth_of_discharge": depth_of_discharge,
        "energy_needed_wh": round(energy_needed_wh, 1),
        "required_ah": round(required_ah, 1),
        "system_voltage": system_voltage,
        "unit_ah": unit_ah,
        "units_needed": units_needed,
    }


# ---------------------------------------------------------------------
# 4. Solar panel sizing
# ---------------------------------------------------------------------
# Peak sun hours vary meaningfully by region in Nigeria. These are
# commonly cited planning ranges, not site-measured data - check against
# a source like NASA POWER or Global Solar Atlas if your report needs
# precise, cited figures. Defaults to the lowest (safest) value if the
# user doesn't pick a region, so the array isn't undersized for a
# cloudier location than assumed.

PEAK_SUN_HOURS_BY_REGION = {
    "North (e.g. Sokoto, Kano, Maiduguri, Katsina)":                        6.0,
    "North Central (e.g. Abuja, Jos, Ilorin, Minna)":                       5.5,
    "Southwest (e.g. Lagos, Ibadan, Abeokuta, Akure)":                      4.5,
    "South-South / Southeast (e.g. Port Harcourt, Enugu, Calabar, Owerri)": 4.0,
}

def size_solar_panels(essential_load_w, daily_backup_hours,
                       region="South-South / Southeast (e.g. Port Harcourt, Enugu, Calabar, Owerri)",
                       panel_watts=350, system_losses=0.8):
    """
    essential_load_w    : average load to be backed up, in watts
    daily_backup_hours  : hours per day this load must be powered from
                          the battery (used to estimate the daily
                          energy solar must replace)
    region              : must be a key in PEAK_SUN_HOURS_BY_REGION -
                          decides the peak sun hours used
    panel_watts         : rated wattage of a single panel
    system_losses       : 0.8 (20% derating) accounts for wiring,
                          inverter, and dirt/heat losses - a standard
                          conservative planning figure
    """
    if region not in PEAK_SUN_HOURS_BY_REGION:
        raise ValueError(f"'{region}' is not in PEAK_SUN_HOURS_BY_REGION.")

    peak_sun_hours = PEAK_SUN_HOURS_BY_REGION[region]

    daily_energy_wh = essential_load_w * daily_backup_hours
    required_panel_watts = daily_energy_wh / (peak_sun_hours * system_losses)
    panels_needed = math.ceil(required_panel_watts / panel_watts)

    return {
        "region": region,
        "peak_sun_hours": peak_sun_hours,
        "daily_energy_wh": round(daily_energy_wh, 1),
        "required_panel_watts": round(required_panel_watts, 1),
        "panel_watts": panel_watts,
        "panels_needed": panels_needed,
    }


# ---------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------

if __name__ == "__main__":
    max_demand_w = 10815
    essential_load_w = max_demand_w * 0.5

    print("Generator sizing:")
    print(" ", size_generator(max_demand_w))

    print(f"\nEssential load (50% of max demand): {essential_load_w:.0f} W")

    print("\nInverter sizing:")
    print(" ", size_inverter(essential_load_w))

    print("\nBattery sizing - default (Lead-Acid, safest), 6hr backup:")
    print(" ", size_battery(essential_load_w, backup_hours=6))

    print("\nBattery sizing - Lithium-Ion chosen instead, 6hr backup:")
    print(" ", size_battery(
        essential_load_w, backup_hours=6,
        battery_type="Lithium-Ion (higher upfront cost, deeper discharge, longer lifespan)"
    ))

    print("\nSolar sizing - default region (safest, South-South/Southeast), 6hr/day:")
    print(" ", size_solar_panels(essential_load_w, daily_backup_hours=6))

    print("\nSolar sizing - Southwest region chosen, 6hr/day:")
    print(" ", size_solar_panels(
        essential_load_w, daily_backup_hours=6,
        region="Southwest (e.g. Lagos, Ibadan, Abeokuta, Akure)"
    ))
