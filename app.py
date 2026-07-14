"""
AutoElect - Web Application (Streamlit)
-----------------------------------------
Wires together:
  - calculations.py     (appliance load + diversity -> maximum demand)
  - lighting_design.py  (room-based CIBSE lighting fitting calculation)
  - cable_sizing.py     (cable size + voltage drop check)
  - backup_power.py     (generator, inverter, battery, solar sizing)

Run with:
    python -m streamlit run app.py

IMPORTANT:
  - This file must sit in the SAME FOLDER as calculations.py,
    lighting_design.py, cable_sizing.py, and backup_power.py.
  - The .streamlit/config.toml folder (for the navy/gold theme) must
    also sit alongside this file, in a folder literally named ".streamlit".
"""

import streamlit as st
from calculations import APPLIANCE_LIBRARY, calculate_connected_load, apply_diversity
from lighting_design import ROOM_LUX_LEVELS, FITTING_DATA, calculate_building_lighting
from cable_sizing import select_cable, get_correction_factor
from backup_power import (
    BATTERY_TYPES,
    PEAK_SUN_HOURS_BY_REGION,
    size_generator,
    size_inverter,
    size_battery,
    size_solar_panels,
)
from design_tiers import TIER_PROFILES
from pdf_report import generate_report
from vision_parser import parse_floorplan_with_claude


st.set_page_config(page_title="AutoElect", page_icon="⚡", layout="centered")

LIGHTING_FITTING_NAMES = set(FITTING_DATA.keys())

CATEGORY_LABELS = {
    "socket": "General & Socket Appliances",
    "cooking": "Cooking Appliances",
    "water_heating": "Water Heating",
}

# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------
st.title("⚡ AutoElect")
st.caption("Automated Electrical Power Design System for Residential Buildings")
st.divider()

st.subheader("Design Tier")
tier = st.selectbox(
    "Choose your preferred design tier",
    list(TIER_PROFILES.keys()),
    index=1,
    help="Sets sensible defaults for safety margins and component choices "
         "below. Every tier is fully BS 7671:2018 / CIBSE compliant - "
         "Luxury just adds extra headroom and premium components, it "
         "does not relax any requirement."
)
tier_profile = TIER_PROFILES[tier]
st.caption(f"**{tier}:** {tier_profile['description']}")
st.divider()

tab_overview, tab_appliances, tab_lighting, tab_backup, tab_results = st.tabs(
    ["🏠 Overview", "🔌 Appliances", "💡 Lighting", "🔋 Backup Power", "📋 Cable & Results"]
)

# ---------------------------------------------------------------------
# Tab: Overview
# ---------------------------------------------------------------------
with tab_overview:
    st.subheader("How this works")
    st.write(
        "AutoElect calculates the electrical load for a residential building "
        "and recommends a suitable main cable size, in line with BS 7671:2018 "
        "and CIBSE guidance."
    )
    project_name = st.text_input("Project name (used on the PDF report)", value="")
    st.markdown(
        "1. **Appliances** — tick off what's in the building\n"
        "2. **Lighting** — enter each room's type and area\n"
        "3. **Backup Power** — set your backup preferences (location, battery type, duration)\n"
        "4. **Cable & Results** — set the cable run length and calculate"
    )
    st.info(
        "Fill in the Appliances, Lighting, and Backup Power tabs first, "
        "then head to Cable & Results to run the calculation."
    )

# ---------------------------------------------------------------------
# Tab: Appliances
# ---------------------------------------------------------------------
selected_appliances = []

with tab_appliances:
    st.subheader("Select Appliances")
    st.write("Enter the quantity for each appliance in the building.")

    for cat_key, cat_label in CATEGORY_LABELS.items():
        items = [
            name for name, info in APPLIANCE_LIBRARY.items()
            if info["category"] == cat_key and name not in LIGHTING_FITTING_NAMES
        ]
        with st.expander(cat_label, expanded=(cat_key == "socket")):
            cols = st.columns(2)
            for idx, name in enumerate(items):
                with cols[idx % 2]:
                    qty = st.number_input(name, min_value=0, max_value=50, value=0, step=1, key=name)
                    if qty > 0:
                        selected_appliances.append({"name": name, "quantity": qty})

    st.divider()
    st.subheader("Not in the list above?")
    custom_name = st.text_input("Appliance name (e.g. 'Deep Freezer - Large')")
    c1, c2, c3 = st.columns(3)
    with c1:
        custom_power = st.number_input("Power rating (Watts)", min_value=0, value=0, step=10)
    with c2:
        custom_category = st.selectbox(
            "Category", ["lighting", "socket", "cooking", "water_heating"]
        )
    with c3:
        custom_qty = st.number_input("Quantity", min_value=0, max_value=50, value=0, step=1, key="custom_qty")

# ---------------------------------------------------------------------
# Tab: Lighting
# ---------------------------------------------------------------------

with tab_lighting:
    st.subheader("Lighting Design")

    mode = st.radio(
        "Choose input mode:",
        ["Automatic (Claude Vision)", "Manual Entry"],
        index=0
    )

    if mode == "Automatic (Claude Vision)":
        uploaded_blueprint = st.file_uploader(
            "Upload a clear 2D layout (.png, .jpg, .jpeg)",
            type=["png", "jpg", "jpeg"]
        )

        if uploaded_blueprint is not None:
            st.image(uploaded_blueprint, caption="Uploaded Layout", use_container_width=True)

        if st.button("Run Automated Extraction"):
            with st.spinner("Analyzing via Claude Vision..."):
                extraction_results = parse_floorplan_with_claude(uploaded_blueprint)

            if isinstance(extraction_results, list):
                rooms = [
                    {
                        "room_type": r["room"],
                        "area_m2": r["area_m2"],
                        "fitting_name": tier_profile["recommended_fitting"]
                    }
                    for r in extraction_results
                ]
                lighting_results, total_lighting_load = calculate_building_lighting(rooms)

                st.success("Lighting design calculated!")
                st.table({
                    "Room": [r["room_type"] for r in lighting_results],
                    "Area (m²)": [r["area_m2"] for r in lighting_results],
                    "Fittings Needed": [r["fittings_needed"] for r in lighting_results],
                    "Fitting Type": [r["fitting_name"] for r in lighting_results],
                    "Load (W)": [r["lighting_load_w"] for r in lighting_results],
                })
            else:
                st.warning("Automatic extraction failed. Please use Manual Entry mode.")

    else:  # Manual Entry
        st.write("Enter each room manually:")
        num_rooms = st.number_input("Number of rooms", min_value=1, max_value=20, value=3, step=1)

        fitting_options = list(FITTING_DATA.keys())
        default_fitting_index = fitting_options.index(tier_profile["recommended_fitting"])

        rooms = []
        for i in range(int(num_rooms)):
            st.markdown(f"**Room {i + 1}**")
            col1, col2, col3 = st.columns(3)
            with col1:
                room_type = st.selectbox("Room type", list(ROOM_LUX_LEVELS.keys()), key=f"room_type_{i}")
            with col2:
                area = st.number_input("Area (m²)", min_value=0.0, value=0.0, step=0.5, key=f"room_area_{i}")
            with col3:
                fitting = st.selectbox("Fitting type", fitting_options, index=default_fitting_index, key=f"room_fitting_{i}")
            if area > 0:
                rooms.append({"room_type": room_type, "area_m2": area, "fitting_name": fitting})
            st.markdown("---")

        if rooms:
            lighting_results, total_lighting_load = calculate_building_lighting(rooms)
            st.success("Lighting design calculated!")
            st.table({
                "Room": [r["room_type"] for r in lighting_results],
                "Area (m²)": [r["area_m2"] for r in lighting_results],
                "Fittings Needed": [r["fittings_needed"] for r in lighting_results],
                "Fitting Type": [r["fitting_name"] for r in lighting_results],
                "Load (W)": [r["lighting_load_w"] for r in lighting_results],
            })
            
# ---------------------------------------------------------------------
# Tab: Backup Power
# ---------------------------------------------------------------------
with tab_backup:
    st.subheader("Backup Power Preferences")
    st.write(
        "These choices feed into the generator, inverter, battery, and "
        "solar panel sizing shown in the Results tab. Starting values "
        f"below are suggested for your **{tier}** tier - adjust as needed."
    )

    essential_load_percent = st.slider(
        "Essential load - % of the total building load that MUST stay on "
        "during a power outage",
        min_value=10, max_value=100,
        value=tier_profile["suggested_essential_load_percent"], step=5,
        help="E.g. fridge, lighting, security, a few sockets - usually not "
             "everything at once (like every AC running together)."
    )

    backup_hours = st.number_input(
        "Backup duration needed (hours)", min_value=1, max_value=24, value=6, step=1
    )

    battery_options = list(BATTERY_TYPES.keys())
    default_battery_index = battery_options.index(tier_profile["default_battery_type"])
    battery_type = st.selectbox("Battery type", battery_options, index=default_battery_index)

    region = st.selectbox(
        "Location / region (used for solar sun-hours estimate)",
        list(PEAK_SUN_HOURS_BY_REGION.keys())
    )

    panel_watts = st.number_input(
        "Solar panel wattage (per panel)", min_value=100, max_value=600, value=350, step=10
    )

# ---------------------------------------------------------------------
# Tab: Cable & Results
# ---------------------------------------------------------------------
with tab_results:
    st.subheader("Main Cable Details")
    cable_length = st.number_input(
        "Cable run length from meter to consumer unit (m)",
        min_value=1, max_value=200, value=10
    )

    c1, c2 = st.columns(2)
    with c1:
        ambient_temp_c = st.number_input(
            "Ambient temperature (°C)", min_value=20, max_value=60, value=30, step=1,
            help="BS 7671 cable ratings assume 30°C. Roof spaces and trunking runs "
                 "in Nigeria often run hotter - increase this for a realistic sizing."
        )
    with c2:
        num_grouped_circuits = st.number_input(
            "Circuits grouped/bunched together", min_value=1, max_value=10, value=1, step=1,
            help="How many circuits share the same conduit, trunking, or are in "
                 "contact along this run. 1 = this circuit runs alone."
        )

    calculate_clicked = st.button("Calculate", type="primary", use_container_width=True)

    if calculate_clicked:
        if custom_name.strip() and custom_power > 0 and custom_qty > 0:
            APPLIANCE_LIBRARY[custom_name.strip()] = {
                "power_w": custom_power,
                "category": custom_category,
            }
            selected_appliances.append({"name": custom_name.strip(), "quantity": custom_qty})

        if not selected_appliances and not rooms:
            st.warning("Select at least one appliance, or add at least one room with an area above 0.")
        else:
            # --- Lighting design (per room) ---
            if rooms:
                lighting_results, total_lighting_load = calculate_building_lighting(rooms)
            else:
                lighting_results, total_lighting_load = [], 0

            # --- Appliance load calculation ---
            if selected_appliances:
                breakdown, _ = calculate_connected_load(selected_appliances)
            else:
                breakdown = {"lighting": 0, "socket": 0, "cooking": 0, "water_heating": 0}

            breakdown["lighting"] += total_lighting_load
            connected_load = sum(breakdown.values())

            demand, max_demand_w = apply_diversity(breakdown)
            max_demand_a = max_demand_w / 230

            st.divider()
            st.subheader("Results")

            if lighting_results:
                with st.expander("Lighting design breakdown", expanded=False):
                    st.table({
                        "Room": [r["room_type"] for r in lighting_results],
                        "Area (m²)": [r["area_m2"] for r in lighting_results],
                        "Fittings Needed": [r["fittings_needed"] for r in lighting_results],
                        "Fitting Type": [r["fitting_name"] for r in lighting_results],
                        "Load (W)": [r["lighting_load_w"] for r in lighting_results],
                    })

            col1, col2, col3 = st.columns(3)
            col1.metric("Connected Load", f"{connected_load:.0f} W")
            col2.metric("Maximum Demand", f"{max_demand_w:.0f} W")
            col3.metric("Design Current", f"{max_demand_a:.1f} A")

            with st.expander("Load breakdown by category", expanded=False):
                st.table({
                    "Category": list(breakdown.keys()),
                    "Connected Load (W)": list(breakdown.values()),
                    "Demand After Diversity (W)": [round(demand[k]) for k in breakdown],
                })

            st.divider()
            st.subheader("Main Cable Sizing")
            if tier_profile["cable_oversize_steps"] > 0:
                st.caption(f"**{tier}** tier: cable sized {tier_profile['cable_oversize_steps']} "
                           f"standard step(s) above the minimum compliant size for extra headroom.")

            correction_factor = get_correction_factor(ambient_temp_c, num_grouped_circuits)
            if correction_factor < 1.0:
                st.caption(
                    f"Derating applied: {ambient_temp_c}°C ambient + {num_grouped_circuits} "
                    f"grouped circuit(s) → combined correction factor **{correction_factor}** "
                    f"(BS 7671 Tables 4B1 & 4C1)."
                )

            cable_result = select_cable(
                design_current_a=max_demand_a,
                length_m=cable_length,
                circuit_type="power",
                correction_factor=correction_factor,
                oversize_steps=tier_profile["cable_oversize_steps"],
            )

            c1, c2, c3 = st.columns(3)
            c1.metric("Protective Device", f"{cable_result['protective_device_a']} A")
            c2.metric("Cable Size", f"{cable_result['cable_size_mm2']} mm²")
            c3.metric("Voltage Drop", f"{cable_result['voltage_drop_percent']}%")

            if cable_result["compliant"]:
                st.success(
                    f"Compliant with BS 7671:2018 "
                    f"(limit: {cable_result['voltage_drop_limit_percent']}%)"
                )
            else:
                st.error(
                    f"Voltage drop exceeds BS 7671:2018 limit of "
                    f"{cable_result['voltage_drop_limit_percent']}%"
                )

            # --- Backup power sizing ---
            st.divider()
            st.subheader("Backup Power Sizing")
            st.caption(f"Sized using the **{tier}** design tier.")

            essential_load_w = max_demand_w * (essential_load_percent / 100)
            st.write(
                f"Essential load ({essential_load_percent}% of maximum demand): "
                f"**{essential_load_w:.0f} W**"
            )

            gen_result = size_generator(
                max_demand_w, safety_margin=tier_profile["generator_safety_margin"]
            )
            inv_result = size_inverter(essential_load_w)
            batt_result = size_battery(essential_load_w, backup_hours, battery_type=battery_type)
            solar_result = size_solar_panels(
                essential_load_w, backup_hours, region=region, panel_watts=panel_watts
            )

            st.markdown("**Generator** (sized for the full building load)")
            g1, g2 = st.columns(2)
            g1.metric("Required Capacity", f"{gen_result['required_kva']} kVA")
            g2.metric("Recommended Size", f"{gen_result['recommended_kva']} kVA")

            st.markdown("**Solar / Inverter / Battery** (sized for the essential load)")
            s1, s2, s3 = st.columns(3)
            s1.metric("Inverter", f"{inv_result['recommended_va']} VA")
            s2.metric("Battery Bank", f"{batt_result['units_needed']} × {batt_result['unit_ah']}Ah")
            s3.metric("Solar Panels", f"{solar_result['panels_needed']} × {solar_result['panel_watts']}W")

            with st.expander("Backup power calculation details", expanded=False):
                st.write(f"**Battery type:** {batt_result['battery_type']}")
                st.write(f"**Depth of discharge used:** {batt_result['depth_of_discharge'] * 100:.0f}%")
                st.write(f"**Battery bank voltage:** {batt_result['system_voltage']} V")
                st.write(f"**Total backup energy needed:** {batt_result['energy_needed_wh']:.0f} Wh")
                st.write(f"**Region:** {solar_result['region']}")
                st.write(f"**Peak sun hours used:** {solar_result['peak_sun_hours']}")

            # --- PDF report download ---
            st.divider()
            pdf_bytes = generate_report(
                project_name=project_name,
                tier=tier,
                breakdown=breakdown,
                demand=demand,
                connected_load=connected_load,
                max_demand_w=max_demand_w,
                max_demand_a=max_demand_a,
                lighting_results=lighting_results,
                cable_result=cable_result,
                cable_length=cable_length,
                gen_result=gen_result,
                inv_result=inv_result,
                batt_result=batt_result,
                solar_result=solar_result,
                essential_load_percent=essential_load_percent,
                backup_hours=backup_hours,
                ambient_temp_c=ambient_temp_c,
                num_grouped_circuits=num_grouped_circuits,
                correction_factor=correction_factor,
            )
            st.download_button(
                label="📄 Download PDF Design Report",
                data=pdf_bytes,
                file_name=f"AutoElect_Report_{(project_name or 'Untitled').replace(' ', '_')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
