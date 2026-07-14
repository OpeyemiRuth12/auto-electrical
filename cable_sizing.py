"""
AutoElect - Cable Sizing Module
--------------------------------
Step 2: Selects a protective device (MCB) and cable size for a circuit,
then checks the voltage drop, based on BS 7671:2018 current-carrying
capacity and voltage drop tables.

Simplified to: PVC/thermoplastic insulated, copper conductor, twin and
earth cable, Reference Method C (clipped direct) - the most common
domestic wiring method. The exact mV/A/m and current rating figures
below are representative of BS 7671 Appendix 4 tables - cross-check
them against your own reference copy before quoting them in the report,
since your lecturer may want the exact table numbers cited.
"""

# ---------------------------------------------------------------------
# 1. Cable data table (simplified extract of BS 7671 Appendix 4)
# ---------------------------------------------------------------------

CABLE_TABLE = {
    1.0:  {"current_rating_a": 15.5, "mv_per_a_per_m": 44},
    1.5:  {"current_rating_a": 19.5, "mv_per_a_per_m": 29},
    2.5:  {"current_rating_a": 27,   "mv_per_a_per_m": 18},
    4.0:  {"current_rating_a": 36,   "mv_per_a_per_m": 11},
    6.0:  {"current_rating_a": 46,   "mv_per_a_per_m": 7.3},
    10.0: {"current_rating_a": 63,   "mv_per_a_per_m": 4.4},
    16.0: {"current_rating_a": 82,   "mv_per_a_per_m": 2.8},
    25.0: {"current_rating_a": 106,  "mv_per_a_per_m": 1.75},
    35.0: {"current_rating_a": 131,  "mv_per_a_per_m": 1.25},
    50.0: {"current_rating_a": 158,  "mv_per_a_per_m": 0.93},
}

STANDARD_MCB_RATINGS = [6, 10, 16, 20, 25, 32, 40, 45, 50, 63, 80, 100]

# Permissible voltage drop as % of nominal voltage (BS 7671:2018)
VOLTAGE_DROP_LIMIT = {
    "lighting": 0.03,   # 3%
    "power":    0.05,   # 5%
}

# ---------------------------------------------------------------------
# Cable derating (correction) factors
# ---------------------------------------------------------------------
# BS 7671 current ratings assume a 30C ambient temperature and a single
# circuit (no grouping). Real installations - especially roof spaces
# and trunking runs in Nigeria's climate - often run hotter than that,
# and circuits are frequently bunched together. Both reduce how much
# current a cable can actually carry safely.

# Ambient temperature correction, Ca (BS 7671 Table 4B1, 70C
# thermoplastic/PVC insulated cables). 30C is the reference temperature
# (factor = 1.00, i.e. no derating).
AMBIENT_TEMP_CORRECTION = {
    25: 1.03,
    30: 1.00,
    35: 0.94,
    40: 0.87,
    45: 0.79,
    50: 0.71,
    55: 0.61,
    60: 0.50,
}

# Grouping correction, Cg (BS 7671 Table 4C1) - cables bunched together
# in the same conduit/trunking or touching each other.
GROUPING_CORRECTION = {
    1: 1.00,
    2: 0.80,
    3: 0.70,
    4: 0.65,
    5: 0.60,
    6: 0.57,
    7: 0.52,
    8: 0.52,
    9: 0.52,
    10: 0.48,
}


def get_ambient_temp_correction(ambient_temp_c=30):
    """
    Returns Ca for the given ambient temperature. Rounds UP to the next
    tabulated (hotter) band if the exact value isn't listed - the safe
    direction, since assuming a cooler environment than reality is what
    leads to an undersized cable. Temperatures above the table's range
    use the most conservative (lowest) factor available.
    """
    for temp in sorted(AMBIENT_TEMP_CORRECTION.keys()):
        if ambient_temp_c <= temp:
            return AMBIENT_TEMP_CORRECTION[temp]
    return AMBIENT_TEMP_CORRECTION[max(AMBIENT_TEMP_CORRECTION.keys())]


def get_grouping_correction(num_grouped_circuits=1):
    """
    Returns Cg for the given number of circuits grouped together.
    Counts above the table's range use the most conservative factor
    available, flagged for manual verification via the returned value
    being reused rather than extrapolated.
    """
    if num_grouped_circuits in GROUPING_CORRECTION:
        return GROUPING_CORRECTION[num_grouped_circuits]
    return GROUPING_CORRECTION[max(GROUPING_CORRECTION.keys())]


def get_correction_factor(ambient_temp_c=30, num_grouped_circuits=1):
    """
    Combined correction factor: Cf = Ca x Cg
    Pass this straight into select_cable()'s correction_factor argument.
    """
    ca = get_ambient_temp_correction(ambient_temp_c)
    cg = get_grouping_correction(num_grouped_circuits)
    return round(ca * cg, 3)


# ---------------------------------------------------------------------
# 2. Pick the next standard MCB rating >= design current
# ---------------------------------------------------------------------

def select_protective_device(design_current_a):
    for rating in STANDARD_MCB_RATINGS:
        if rating >= design_current_a:
            return rating
    raise ValueError(
        "Design current exceeds standard MCB ratings - this load "
        "likely needs to be split across more than one circuit."
    )


# ---------------------------------------------------------------------
# 3. Main cable sizing function
# ---------------------------------------------------------------------

def select_cable(design_current_a, length_m, circuit_type="power",
                  correction_factor=1.0, nominal_voltage=230, oversize_steps=0):
    """
    design_current_a : circuit design current, Ib (A)
    length_m         : one-way cable run length (m)
    circuit_type     : "lighting" or "power" - decides the voltage drop limit
    correction_factor: combined derating factor for ambient temp/grouping/
                       insulation (leave as 1.0 if not accounted for yet)
    nominal_voltage  : supply voltage, default 230V
    oversize_steps   : how many standard sizes ABOVE the minimum compliant
                       size to select instead - used for the "Luxury"
                       design tier to add extra headroom/future-proofing.
                       0 = minimum compliant size (default).

    Returns a dict with the selected protective device, cable size,
    voltage drop, and whether it complies with BS 7671 limits.
    """
    protective_device = select_protective_device(design_current_a)

    # Minimum tabulated current rating the cable must have: It >= In / Cf
    required_capacity = protective_device / correction_factor

    chosen_size = None
    for size, data in sorted(CABLE_TABLE.items()):
        if data["current_rating_a"] >= required_capacity:
            chosen_size = size
            break

    if chosen_size is None:
        raise ValueError(
            "No cable in the table is large enough - extend "
            "CABLE_TABLE with bigger sizes for this load."
        )

    def voltage_drop_for(size):
        mv = CABLE_TABLE[size]["mv_per_a_per_m"]
        vd_v = (mv * design_current_a * length_m) / 1000
        vd_pct = (vd_v / nominal_voltage) * 100
        return vd_v, vd_pct

    limit_percent = VOLTAGE_DROP_LIMIT[circuit_type] * 100
    voltage_drop_v, voltage_drop_percent = voltage_drop_for(chosen_size)
    compliant = voltage_drop_percent <= limit_percent

    # If voltage drop fails on current-rating grounds, step up cable
    # sizes until the voltage drop also passes
    if not compliant:
        for size in sorted(CABLE_TABLE.keys()):
            if size <= chosen_size:
                continue
            vd_v, vd_pct = voltage_drop_for(size)
            if vd_pct <= limit_percent:
                chosen_size = size
                voltage_drop_v, voltage_drop_percent = vd_v, vd_pct
                compliant = True
                break

    # Apply tier-based oversizing on top of the minimum compliant size
    if oversize_steps > 0:
        sizes_sorted = sorted(CABLE_TABLE.keys())
        current_idx = sizes_sorted.index(chosen_size)
        new_idx = min(current_idx + oversize_steps, len(sizes_sorted) - 1)
        chosen_size = sizes_sorted[new_idx]
        voltage_drop_v, voltage_drop_percent = voltage_drop_for(chosen_size)
        compliant = voltage_drop_percent <= limit_percent

    return {
        "protective_device_a": protective_device,
        "cable_size_mm2": chosen_size,
        "current_rating_a": CABLE_TABLE[chosen_size]["current_rating_a"],
        "voltage_drop_v": round(voltage_drop_v, 2),
        "voltage_drop_percent": round(voltage_drop_percent, 2),
        "voltage_drop_limit_percent": limit_percent,
        "compliant": compliant,
    }


# ---------------------------------------------------------------------
# Quick test - run this file directly to sanity-check the logic
# ---------------------------------------------------------------------

if __name__ == "__main__":
    print("Power circuit - 20A design current, 25m run:")
    for k, v in select_cable(20, 25, circuit_type="power").items():
        print(f"  {k}: {v}")

    print("\nLighting circuit - 5A design current, 15m run:")
    for k, v in select_cable(5, 15, circuit_type="lighting").items():
        print(f"  {k}: {v}")

    print("\nMain incoming cable - 47A (from calculations.py), 10m run:")
    for k, v in select_cable(47, 10, circuit_type="power").items():
        print(f"  {k}: {v}")

    print("\nSame main cable, Luxury tier (oversize_steps=1):")
    for k, v in select_cable(47, 10, circuit_type="power", oversize_steps=1).items():
        print(f"  {k}: {v}")

    print("\nSame main cable, but 40C ambient + 3 circuits grouped together:")
    cf = get_correction_factor(ambient_temp_c=40, num_grouped_circuits=3)
    print(f"  Combined correction factor: {cf}")
    for k, v in select_cable(47, 10, circuit_type="power", correction_factor=cf).items():
        print(f"  {k}: {v}")
