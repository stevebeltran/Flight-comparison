import streamlit as st
import pandas as pd
import folium
from folium import plugins
from folium.features import DivIcon
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import time
import random
import math
from datetime import datetime, timedelta

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Tactical Drone Command", initial_sidebar_state="collapsed")

# --- Session State Initialization ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'map_center' not in st.session_state: st.session_state.map_center = [39.8283, -98.5795]
if 'map_zoom' not in st.session_state: st.session_state.map_zoom = 4 
if 'base' not in st.session_state: st.session_state.base = None
if 'target' not in st.session_state: st.session_state.target = None
if 'inc_type' not in st.session_state: st.session_state.inc_type = None
if 'squad_cars' not in st.session_state: st.session_state.squad_cars = []
if 'sim_completed' not in st.session_state: st.session_state.sim_completed = False
if 'has_run_once' not in st.session_state: st.session_state.has_run_once = False
if 'best_officer_sq' not in st.session_state: st.session_state.best_officer_sq = None
if 't_officers' not in st.session_state: st.session_state.t_officers = None
if 'last_processed_click' not in st.session_state: st.session_state.last_processed_click = None
if 'anim_duration' not in st.session_state: st.session_state.anim_duration = 16 

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=Manrope:wght@400;600;700&display=swap');
    header[data-testid="stHeader"] { display: none; }
    .stApp { background-color: #050505 !important; color: #797979; font-family: 'Manrope', sans-serif; }
    h1, h2, h3, h4, h5, h6 { color: #ffffff !important; font-family: 'Manrope', sans-serif; margin-bottom: 0px !important; padding-bottom: 0px !important; }
    div[data-testid="stMetricValue"] { font-size: 1.1rem !important; color: #00D2FF; font-family: 'IBM Plex Mono', monospace; }
    .stProgress > div > div { height: 6px !important; }
    .stProgress > div > div > div > div { background-color: #00D2FF; }
    div.stButton > button, div[data-testid="stPopover"] > button { background-color: #111 !important; color: #ffffff !important; border: 1px solid #444 !important; }
    div.stButton > button:hover { border-color: #00D2FF !important; color: #00D2FF !important; }
    .drone-active { animation: dronePulse 0.8s infinite; font-weight: bold; font-family: 'IBM Plex Mono', monospace; font-size: 0.9rem; display: block; margin-bottom: -10px; }
    .drone-static { color: #ffffff; font-weight: bold; font-family: 'IBM Plex Mono', monospace; font-size: 0.9rem; display: block; margin-bottom: -10px; }
    @keyframes dronePulse { 0%, 49% { color: #797979; } 50%, 100% { color: #00D2FF; text-shadow: 0 0 8px #00D2FF; } }
    .incident-log { background-color: #111; border: 1px solid #333; border-radius: 5px; padding: 8px; font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; }
    .drone-card { background-color: #080808; border: 1px solid #222; border-radius: 4px; padding: 6px 10px; margin-top: 2px; }
    .metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
    .m-label { color: #797979; font-size: 0.55rem; text-transform: uppercase; }
    .m-val { color: #00D2FF; font-size: 0.95rem; font-family: 'IBM Plex Mono', monospace; font-weight: bold; }
    .log-critical { color: #ff4b4b; font-weight: bold; }
    .log-action { color: #00D2FF; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def load_data():
    try:
        df = pd.read_csv('drones.csv')
        df = df.dropna(subset=['model'])
        return df
    except:
        # Fallback Data: SKYDIO updated to 35 mins
        data = {
            'model': ['RESPONDER', 'GUARDIAN', 'SKYDIO X-10', 'MATRICE 4TD'],
            'flight_time_min': [42, 60, 35, 54], 
            'speed_mph': [22, 30, 36, 34],
            'range_miles': [5.0, 12.0, 7.5, 6.2]
        }
        return pd.DataFrame(data)

def get_full_recharge_time(model_name):
    # GUARDIAN updated to 3 minutes
    mapping = {
        'RESPONDER': 25,
        'GUARDIAN': 3, 
        'SKYDIO': 90,
        'MATRICE': 55
    }
    for key, val in mapping.items():
        if key in model_name.upper():
            return val
    return 60

def get_distance_miles(p1, p2):
    return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5 * 69

def generate_incident():
    incidents = [("SHOTS FIRED", "critical"), ("ARMED ROBBERY", "critical"), ("VEHICLE PURSUIT", "action")]
    inc, severity = random.choice(incidents)
    st.session_state.inc_type, st.session_state.inc_severity = inc, severity
    base_time = datetime.now()
    st.session_state.t_call = base_time
    st.session_state.t_launch = base_time + timedelta(seconds=random.randint(45, 90))

def randomize_squads():
    if st.session_state.base:
        st.session_state.squad_cars = []
        for _ in range(random.randint(3, 5)):
            r_mi = random.uniform(1.0, 6.0)
            angle = random.uniform(0, 2 * math.pi)
            st.session_state.squad_cars.append([st.session_state.base[0] + (r_mi * math.sin(angle))/69, st.session_state.base[1] + (r_mi * math.cos(angle))/69])

def calculate_responding_officer():
    best_dist, best_sq = float('inf'), None
    for sq in st.session_state.squad_cars:
        d = get_distance_miles(sq, st.session_state.target)
        if d < best_dist: best_dist, best_sq = d, sq
    st.session_state.best_officer_sq = best_sq
    travel_sec = (best_dist * 1.4) / (35.0 / 3600.0)
    st.session_state.t_officers = st.session_state.t_call + timedelta(seconds=travel_sec + 60)

# --- Layout ---
left_col, mid_col = st.columns([7, 3])

with mid_col:
    if st.session_state.step == 1:
        zip_in = st.text_input("ENTER ZIP FOR OPS CENTER", key="zip_input")
        if zip_in and len(zip_in) == 5:
            coords = get_lat_lon_from_zip(zip_in) if 'get_lat_lon_from_zip' in globals() else [34.0522, -118.2437]
            st.session_state.map_center, st.session_state.step = coords, 2
            st.rerun()
    elif st.session_state.step >= 2:
        st.markdown("### OPS CENTER")
        st.slider("Simulation Speed", 5, 120, key="anim_duration")
        incident_placeholder = st.empty()
        
        if st.session_state.step == 3:
            df = load_data()
            drone_ui_elements = []
            for _, row in df.iterrows():
                c1, c2 = st.columns([2, 1])
                ui = {'specs': row, 'name_text': c1.empty(), 'status_text': c2.empty(), 
                      'flight_bar': st.progress(0), 'metrics_html': st.empty(), 'cache': {}}
                drone_ui_elements.append(ui)

# --- Map Logic ---
with left_col:
    m = folium.Map(location=st.session_state.map_center, zoom_start=12, tiles="CartoDB dark_matter")
    if st.session_state.base:
        folium.Marker(st.session_state.base, icon=DivIcon(html='<div style="color:#00D2FF;font-size:24px;"><i class="fa fa-home"></i></div>')).add_to(m)
    if st.session_state.target:
        folium.Marker(st.session_state.target, icon=DivIcon(html='<div style="color:#FF0000;font-size:24px;"><i class="fa fa-crosshairs"></i></div>')).add_to(m)
    
    map_data = st_folium(m, height=800, use_container_width=True, key="map")
    if map_data.get('last_clicked'):
        c = [map_data['last_clicked']['lat'], map_data['last_clicked']['lng']]
        if c != st.session_state.last_processed_click:
            st.session_state.last_processed_click = c
            if not st.session_state.base: st.session_state.base = c
            else: 
                st.session_state.target = c
                randomize_squads()
                generate_incident()
                calculate_responding_officer()
                st.session_state.step, st.session_state.sim_completed = 3, False
            st.rerun()

# --- Simulation Logic ---
if st.session_state.step == 3 and not st.session_state.sim_completed:
    dist = get_distance_miles(st.session_state.base, st.session_state.target)
    sim_dur = 100 # Internal ticks
    
    for tick in range(101):
        curr_time_pct = tick / 100
        
        for d_ui in drone_ui_elements:
            specs = d_ui['specs']
            model = specs['model'].upper()
            speed = float(specs['speed_mph'])
            max_flight = float(specs['flight_time_min']) * 60
            
            t_out = dist / (speed / 3600)
            t_hov = (max_flight - (t_out * 2)) - 300
            t_total = (t_out * 2) + max(0, t_hov)
            
            curr_sim_time = curr_time_pct * t_total
            
            # Phase Logic
            if curr_sim_time < t_out:
                phase, color, prog = "OUTBOUND", "#00D2FF", curr_sim_time / t_out
            elif curr_sim_time < (t_out + t_hov):
                phase, color, prog = "ON SCENE", "#00D2FF", 1.0
            elif curr_sim_time < t_total:
                phase, color, prog = "RTB", "#00D2FF", 1.0 - ((curr_sim_time - t_out - t_hov) / t_out)
            else:
                # GUARDIAN SPECIAL CASE
                if "GUARDIAN" in model:
                    phase, color = "SWAPPING BATTERIES", "#00FF00"
                else:
                    phase, color = "RECHARGING", "#FFC300"
                prog = 0.0

            d_ui['name_text'].markdown(f"<span class='drone-static'>{model}</span>", unsafe_allow_html=True)
            d_ui['status_text'].markdown(f"<div style='text-align:right; color:{color}; font-weight:bold;'>{phase}</div>", unsafe_allow_html=True)
            d_ui['flight_bar'].progress(max(0.0, min(prog, 1.0)))
            
            # Metrics Card
            batt = max(0, 100 - (curr_sim_time / max_flight * 100)) if curr_sim_time < t_total else 100
            d_ui['metrics_html'].markdown(f"""
                <div class="drone-card"><div class="metric-grid">
                <div class="m-box"><div class="m-label">DIST</div><div class="m-val">{dist:.1f}mi</div></div>
                <div class="m-box"><div class="m-label">BATT</div><div class="m-val">{int(batt)}%</div></div>
                <div class="m-box"><div class="m-label">SPD</div><div class="m-val">{int(speed)}mph</div></div>
                </div></div>""", unsafe_allow_html=True)
        
        time.sleep(st.session_state.anim_duration / 100)
    
    st.session_state.sim_completed = True
    st.rerun()
