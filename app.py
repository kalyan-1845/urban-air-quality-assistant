"""AeroLife — Urban Air Quality Assistant.

A production-ready GenAI application built with Google Gemini, Streamlit, and
Open-Meteo Air Quality API for Google PromptWars Hackathon 2026.

Author: Bhoompally Kalyan Reddy (kalyan-1845)
"""

import json
import streamlit as st
import plotly.graph_objects as go
import air_quality_service as aq_service
import gemini_engine

# Streamlit Page Configuration
st.set_page_config(
    page_title="AeroLife — Urban Air Quality Assistant",
    page_icon="🍃",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (Dark Mode, Glassmorphism, Google Fonts, Accessibility)
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #F3F4F6;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    letter-spacing: -0.02em;
}

/* Glassmorphism Cards */
.stCard, .metric-box, .routine-card, .hack-card, .swap-card {
    background: rgba(17, 24, 39, 0.75);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(75, 85, 99, 0.4);
    border-radius: 14px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.routine-card:hover, .hack-card:hover, .swap-card:hover {
    transform: translateY(-2px);
    border-color: rgba(99, 102, 241, 0.6);
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(99, 102, 241, 0.2);
}

/* Badges */
.badge {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-right: 0.5rem;
}

.badge-mask-none { background: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.4); }
.badge-mask-cloth { background: rgba(59, 130, 246, 0.2); color: #60A5FA; border: 1px solid rgba(59, 130, 246, 0.4); }
.badge-mask-n95 { background: rgba(245, 158, 11, 0.2); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.4); }
.badge-mask-stay { background: rgba(239, 68, 68, 0.2); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.4); }

.pill-tag {
    background: #1F2937;
    color: #9CA3AF;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.8rem;
    border: 1px solid #374151;
}

/* Custom Buttons */
.stButton > button {
    background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
    color: white;
    font-weight: 600;
    border: none;
    border-radius: 10px;
    padding: 0.6rem 1.5rem;
    transition: all 0.25s ease;
    box-shadow: 0 4px 14px 0 rgba(79, 70, 229, 0.4);
}

.stButton > button:hover {
    background: linear-gradient(135deg, #4338CA 0%, #6D28D9 100%);
    box-shadow: 0 6px 20px 0 rgba(79, 70, 229, 0.6);
    transform: translateY(-1px);
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_aqi_gauge(aqi_val: int, tier_name: str, tier_color: str):
    """Render a modern Plotly semi-circular AQI gauge."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=aqi_val,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": f"<b>Air Quality Index (AQI)</b><br><span style='font-size:0.85em;color:{tier_color}'>{tier_name}</span>", "font": {"size": 18, "color": "#F3F4F6", "family": "Outfit"}},
            number={"font": {"size": 42, "color": "#FFFFFF", "family": "Outfit"}},
            gauge={
                "axis": {"range": [0, 500], "tickwidth": 1, "tickcolor": "#4B5563", "tickvals": [0, 50, 100, 200, 300, 400, 500]},
                "bar": {"color": tier_color, "thickness": 0.28},
                "bgcolor": "#1F2937",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 50], "color": "rgba(16, 185, 129, 0.25)"},
                    {"range": [50, 100], "color": "rgba(59, 130, 246, 0.25)"},
                    {"range": [100, 200], "color": "rgba(245, 158, 11, 0.25)"},
                    {"range": [200, 300], "color": "rgba(249, 115, 22, 0.25)"},
                    {"range": [300, 400], "color": "rgba(239, 68, 68, 0.25)"},
                    {"range": [400, 500], "color": "rgba(127, 29, 29, 0.4)"},
                ],
            },
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=260,
        margin={"l": 25, "r": 25, "t": 35, "b": 15},
    )
    return fig


# ---------------- SIDEBAR CONTROLS ----------------
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/2/2f/Google_2015_logo.svg",
        width=110,
    )
    st.markdown("### **AeroLife Settings**")
    st.markdown(
        "<span style='font-size:0.8rem;color:#9CA3AF;'>Google PromptWars: Virtual • Challenge 06</span>",
        unsafe_allow_html=True,
    )
    st.divider()

    # City Selector
    city_options = ["Delhi", "Hyderabad", "Mumbai", "Bengaluru", "Kolkata", "Chennai", "Custom City..."]
    selected_city_opt = st.selectbox("📍 Select Urban Center", city_options, index=0)
    
    if selected_city_opt == "Custom City...":
        target_city = st.text_input("Enter City / Locality Name", value="Gurugram")
    else:
        target_city = selected_city_opt

    # Household Profile
    household_options = [
        "Family with Infants (<2 yrs) & Toddlers",
        "Elderly Parents (>65 yrs)",
        "Household with Asthmatic / Respiratory Patients",
        "Working Adults & Office Commuters",
        "Active Outdoor Athletes & Runners",
        "General Urban Household",
    ]
    target_household = st.selectbox("👥 Household Profile", household_options, index=0)

    # Lifestyle / Commute Mode
    lifestyle_options = [
        "Two-Wheeler / Bike Daily Commuter",
        "Public Transit (Bus / Metro / Train)",
        "Car Commuter (Single Occupancy)",
        "Work From Home / Remote Worker",
        "School Going Children & Daily Pickup",
    ]
    target_lifestyle = st.selectbox("🚗 Commute & Lifestyle", lifestyle_options, index=0)

    custom_notes = st.text_area(
        "📝 Specific Concerns (Optional)",
        placeholder="e.g. Ground floor apartment near traffic signal, morning bronchitis symptoms...",
        help="Custom context passed to Gemini prompt engine",
    )

    st.divider()
    refresh_button = st.button("✨ Generate AI Advisory", use_container_width=True)
    st.markdown(
        "<div style='text-align:center; font-size:0.75rem; color:#6B7280; margin-top:1rem;'>"
        "Evaluated for Google PromptWars 2026<br>Public GitHub: <b>kalyan-1845</b></div>",
        unsafe_allow_html=True,
    )


# ---------------- MAIN APP LAYOUT ----------------
# Header
col_header, col_badge = st.columns([3, 1])
with col_header:
    st.markdown(
        "<h1 style='margin-bottom:0.2rem;'>🍃 AeroLife <span style='font-size:0.5em;color:#818CF8;font-weight:400;'>Urban Smog Intelligence</span></h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#9CA3AF;font-size:1.05rem;'>Navigating winter smog with hyper-personalized low-emission routines, indoor air hacks, and sustainable swaps.</p>",
        unsafe_allow_html=True,
    )
with col_badge:
    st.markdown(
        "<div style='text-align:right; margin-top:0.8rem;'>"
        "<span class='pill-tag' style='color:#34D399; border-color:#059669;'>● Challenge 06 Live</span> "
        "<span class='pill-tag'>Gemini 1.5 Flash</span>"
        "</div>",
        unsafe_allow_html=True,
    )

# Fetch Air Quality Data
with st.spinner(f"Querying atmospheric sensors for {target_city}..."):
    aq_data = aq_service.fetch_live_air_quality(target_city)

# Metric Showcase Cards
m_col1, m_col2, m_col3, m_col4 = st.columns([1.5, 1, 1, 1.5])

with m_col1:
    st.plotly_chart(
        render_aqi_gauge(aq_data["aqi"], aq_data["category"]["tier"], aq_data["category"]["color"]),
        use_container_width=True,
        config={"displayModeBar": False},
    )

with m_col2:
    st.markdown(
        f"<div class='metric-box'>"
        f"<div style='font-size:0.8rem;color:#9CA3AF;'>PM2.5 CONCENTRATION</div>"
        f"<div style='font-size:2rem;font-weight:700;color:#F43F5E;font-family:Outfit;'>{aq_data['pm25']} <span style='font-size:0.5em;color:#9CA3AF;'>µg/m³</span></div>"
        f"<div style='font-size:0.75rem;color:#FB7185;'>{round(aq_data['pm25'] / 15.0, 1)}x WHO 24h limit</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

with m_col3:
    st.markdown(
        f"<div class='metric-box'>"
        f"<div style='font-size:0.8rem;color:#9CA3AF;'>PM10 CONCENTRATION</div>"
        f"<div style='font-size:2rem;font-weight:700;color:#F59E0B;font-family:Outfit;'>{aq_data['pm10']} <span style='font-size:0.5em;color:#9CA3AF;'>µg/m³</span></div>"
        f"<div style='font-size:0.75rem;color:#FBBF24;'>Coarse inhalable dust</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

with m_col4:
    cat = aq_data["category"]
    st.markdown(
        f"<div class='metric-box' style='border-left:4px solid {cat['color']};'>"
        f"<div style='font-size:0.8rem;color:#9CA3AF;'>COMMUNITY HEALTH TIER</div>"
        f"<div style='font-size:1.25rem;font-weight:600;color:{cat['color']};margin:0.2rem 0;'>{cat['badge']}</div>"
        f"<div style='font-size:0.8rem;color:#D1D5DB;line-height:1.3;'>{cat['action']}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

# Cache / Generate AI Advisory
session_key = f"{target_city}_{aq_data['aqi']}_{target_household}_{target_lifestyle}"

if "advisory_data" not in st.session_state or st.session_state.get("last_key") != session_key or refresh_button:
    with st.spinner("Synthesizing personalized prompt matrix with Google Gemini..."):
        advisory = gemini_engine.generate_air_quality_advisory(
            city=target_city,
            aqi=aq_data["aqi"],
            pm25=aq_data["pm25"],
            pm10=aq_data["pm10"],
            family_profile=target_household,
            lifestyle=target_lifestyle,
            custom_concerns=custom_notes,
        )
        st.session_state["advisory_data"] = advisory
        st.session_state["last_key"] = session_key
else:
    advisory = st.session_state["advisory_data"]

# Executive Summary Banner
st.markdown(
    f"<div style='background:rgba(30, 41, 59, 0.7); border-radius:10px; padding:1rem 1.25rem; border-left:4px solid #6366F1; margin-bottom:1.5rem;'>"
    f"<span style='font-weight:600; color:#A5B4FC; text-transform:uppercase; font-size:0.8rem; letter-spacing:0.05em;'>AI Environmental Health Briefing</span><br>"
    f"<span style='color:#E2E8F0; font-size:0.95rem; line-height:1.5;'>{advisory['summary']}</span>"
    f"</div>",
    unsafe_allow_html=True,
)

# ---------------- CORE FEATURE TABS ----------------
tab_routine, tab_hacks, tab_swaps, tab_sim, tab_inspector = st.tabs([
    "🕒 Low-Emission Daily Routines",
    "🏠 Indoor Air Quality Hacks",
    "🔄 Sustainable Swaps & Impact",
    "📊 Environmental Impact Simulator",
    "🧠 Prompt & Architecture Inspector",
])

# TAB 1: LOW-EMISSION ROUTINES
with tab_routine:
    st.markdown("### 🌅 Time-Blocked Daily Pollution Navigation")
    st.markdown("<p style='color:#9CA3AF;'>Designed to bypass ground-level inversion smog peaks and minimize household respiratory dose.</p>", unsafe_allow_html=True)

    r_cols = st.columns(len(advisory["daily_routines"]))
    for idx, routine in enumerate(advisory["daily_routines"]):
        mask_class = "badge-mask-none"
        if "N95" in routine["mask_required"]:
            mask_class = "badge-mask-n95"
        elif "Stay" in routine["mask_required"]:
            mask_class = "badge-mask-stay"
        elif "Cloth" in routine["mask_required"]:
            mask_class = "badge-mask-cloth"

        with r_cols[idx]:
            st.markdown(
                f"<div class='routine-card' style='min-height:220px;'>"
                f"<div style='font-size:0.75rem; color:#818CF8; font-weight:600;'>{routine['time_of_day']}</div>"
                f"<div style='font-size:1.1rem; font-weight:600; color:#FFFFFF; margin:0.3rem 0;'>{routine['activity']}</div>"
                f"<div style='margin-bottom:0.75rem;'><span class='badge {mask_class}'>🎭 {routine['mask_required']}</span></div>"
                f"<div style='font-size:0.85rem; color:#CBD5E1; line-height:1.4;'>{routine['recommendation']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

# TAB 2: INDOOR AIR QUALITY HACKS
with tab_hacks:
    st.markdown("### 🛠️ Low-Cost, Science-Backed Indoor Interventions")
    st.markdown("<p style='color:#9CA3AF;'>Keep indoor PM2.5 levels up to 70% lower than toxic outdoor air without expensive equipment.</p>", unsafe_allow_html=True)

    h_col1, h_col2 = st.columns(2)
    for idx, hack in enumerate(advisory["indoor_hacks"]):
        col = h_col1 if idx % 2 == 0 else h_col2
        with col:
            st.markdown(
                f"<div class='hack-card'>"
                f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;'>"
                f"<span class='pill-tag' style='color:#818CF8;'>📂 {hack['category']}</span>"
                f"<span style='font-size:0.8rem; color:#34D399; font-weight:600;'>Estimated Cost: ₹{int(hack['estimated_cost_inr']):,}</span>"
                f"</div>"
                f"<div style='font-size:1.15rem; font-weight:600; color:#FFFFFF; margin-bottom:0.4rem;'>{hack['title']}</div>"
                f"<div style='font-size:0.88rem; color:#CBD5E1; line-height:1.45; margin-bottom:0.6rem;'>{hack['action_steps']}</div>"
                f"<div style='font-size:0.75rem; color:#9CA3AF;'>Difficulty: <b>{hack['difficulty_level']}</b></div>"
                f"</div>",
                unsafe_allow_html=True,
            )

# TAB 3: SUSTAINABLE SWAPS & IMPACT
with tab_swaps:
    st.markdown("### 🔄 Daily Habit Replacements & Quantified Emission Reductions")
    st.markdown("<p style='color:#9CA3AF;'>Direct proof that individual choices compound to clean community skies.</p>", unsafe_allow_html=True)

    for swap in advisory["sustainable_swaps"]:
        st.markdown(
            f"<div class='swap-card'>"
            f"<div style='display:flex; gap:1.5rem; flex-wrap:wrap; margin-bottom:0.6rem;'>"
            f"<div style='flex:1; min-width:240px; background:rgba(239, 68, 68, 0.1); border:1px solid rgba(239, 68, 68, 0.25); border-radius:8px; padding:0.75rem;'>"
            f"<div style='font-size:0.75rem; color:#F87171; font-weight:600; text-transform:uppercase;'>Current High-Pollution Habit</div>"
            f"<div style='font-size:0.95rem; color:#FECACA; margin-top:0.25rem;'>❌ {swap['current_habit']}</div>"
            f"</div>"
            f"<div style='flex:1; min-width:240px; background:rgba(16, 185, 129, 0.1); border:1px solid rgba(16, 185, 129, 0.25); border-radius:8px; padding:0.75rem;'>"
            f"<div style='font-size:0.75rem; color:#34D399; font-weight:600; text-transform:uppercase;'>Sustainable Clean Swap</div>"
            f"<div style='font-size:0.95rem; color:#A7F3D0; margin-top:0.25rem;'>✅ {swap['sustainable_swap']}</div>"
            f"</div>"
            f"</div>"
            f"<div style='display:flex; gap:1.5rem; align-items:center; background:#111827; border-radius:8px; padding:0.65rem 1rem; margin-bottom:0.5rem;'>"
            f"<div style='font-size:0.85rem; color:#FBBF24;'>🌱 <b>{swap['co2_saved_kg_month']} kg</b> CO₂ Saved/Month</div>"
            f"<div style='font-size:0.85rem; color:#38BDF8;'>🛡️ <b>-{int(swap['pm25_exposure_reduction_pct'])}%</b> Personal PM2.5 Inhalation</div>"
            f"</div>"
            f"<div style='font-size:0.85rem; color:#9CA3AF; line-height:1.4;'><b>Scientific Impact Rationale:</b> {swap['impact_explanation']}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

# TAB 4: IMPACT SIMULATOR
with tab_sim:
    st.markdown("### 📈 Interactive Carbon & Smog Mitigation Calculator")
    st.markdown("<p style='color:#9CA3AF;'>Simulate what happens when your neighborhood adopts these sustainable swaps over 6 months.</p>", unsafe_allow_html=True)

    sim_col1, sim_col2 = st.columns([1, 2])
    with sim_col1:
        households_count = st.slider("Households Participating in Community", min_value=1, max_value=500, value=25, step=5)
        ev_metro_adoption = st.slider("Public Transit / EV Carpool Adoption %", min_value=10, max_value=100, value=60, step=5)
        compost_adoption = st.slider("Colony Biomass Composting Adoption %", min_value=10, max_value=100, value=80, step=5)

        total_co2_month = households_count * (78.5 * (ev_metro_adoption / 100.0) + 42.0 * (compost_adoption / 100.0))
        st.metric("Total Monthly CO₂ Abated", f"{int(total_co2_month):,} kg", f"~{int(total_co2_month / 22)} trees saved equivalent")

    with sim_col2:
        months = ["Month 1", "Month 2", "Month 3", "Month 4", "Month 5", "Month 6"]
        co2_cumulative = [int(total_co2_month * (m_idx + 1)) for m_idx in range(6)]
        
        sim_fig = go.Figure()
        sim_fig.add_trace(go.Bar(x=months, y=co2_cumulative, marker_color="#6366F1", name="Cumulative CO₂ Avoided (kg)"))
        sim_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            title="<b>Projected Community CO₂ Reduction Over 6 Months (kg)</b>",
            title_font={"size": 15, "color": "#F3F4F6", "family": "Outfit"},
            xaxis={"tickfont": {"color": "#9CA3AF"}, "showgrid": False},
            yaxis={"tickfont": {"color": "#9CA3AF"}, "gridcolor": "rgba(75, 85, 99, 0.3)"},
            height=280,
            margin={"l": 20, "r": 20, "t": 40, "b": 20},
        )
        st.plotly_chart(sim_fig, use_container_width=True, config={"displayModeBar": False})

# TAB 5: PROMPT & ARCHITECTURE INSPECTOR (FOR EVALUATORS)
with tab_inspector:
    st.markdown("### 🔍 System Prompt & Guardrails Architecture")
    st.markdown("<p style='color:#9CA3AF;'>Direct transparency into the prompt engineering mechanisms evaluated by Google PromptWars.</p>", unsafe_allow_html=True)

    insp_col1, insp_col2 = st.columns(2)
    with insp_col1:
        st.markdown("#### System Prompt Directive")
        st.code(gemini_engine.SYSTEM_PROMPT, language="markdown")

    with insp_col2:
        st.markdown("#### JSON Pydantic Validation Schema")
        st.code(json.dumps(advisory, indent=2), language="json")

# Health Disclaimer
st.markdown("---")
st.markdown(
    f"<div style='font-size:0.75rem; color:#6B7280; text-align:center;'>"
    f"⚠️ <b>Medical Disclaimer:</b> {advisory['disclaimer']}<br>"
    f"Environmental Data Sources: Open-Meteo Air Quality Global API, CPCB India Standards, WHO 2021 Global Guidelines."
    f"</div>",
    unsafe_allow_html=True,
)
