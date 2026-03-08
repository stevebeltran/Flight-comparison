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
from st_keyup import st_keyup

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Tactical Drone Command", initial_sidebar_state="collapsed")

# --- Session State Initialization ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'map_center' not in st.session_state: st.session_state.map_center = [39.8283, -98.5795]
if 'map_zoom' not in st.session_state: st.session_state.map_zoom = 13
if 'base' not in st.session_state: st.session_state.base = None
if 'target' not in st.session_state: st.session_state.target = None
if 'wind_speed' not in st.session_state: st.session_state.wind_speed = 0
if 'wind_dir' not in st.session_state: st.session_state.wind_dir = "N"
if 'inc_type' not in st.session_state: st.session_state.inc_type = None
if 'squad_cars' not in st.session_state: st.session_state.squad_cars = []
if 'sim_completed' not in st.session_state: st.session_state.sim_completed = False

# --- CUSTOM CSS: CLEAN COCKPIT THEME ---
st.markdown("""
    <style>
    header[data-testid="stHeader"] { display: none; }
    .stApp { background-color: #050505 !important; color: #e0e0e0; }
    .block-container { padding-top: 3rem !important; padding-bottom: 1rem !important; }
    
    /* Metrics & Text */
    div[data-testid="stMetricValue"] {
        font-size: 1.1rem !important;
        color: #ffa500; 
        font-family: 'Consolas', monospace;
        text-shadow: 0px 0px 4px rgba(255, 165, 0, 0.5);
    }
    div[data-testid="stMetricLabel"] { font-size: 0.6rem !important; color: #888; margin-bottom: -5px; }

    /* Tactical Drone Name Pulse */
    @keyframes dronePulse {
        0% { color: #fff; text-shadow: 0 0 0px #00d4ff; }
        50% { color: #00d4ff; text-shadow: 0 0 10px #00d4ff; }
        100% { color: #fff; text-shadow: 0 0 0px #00d4ff; }
    }
    .drone-active { animation: dronePulse 1.5s infinite; font-weight: bold; }
    .drone-static { color: #888; font-weight: bold; }

    /* Map Car Animations */
    @keyframes dispatchPulse {
        0%, 49% { color: #ff0000; transform: scale(1.3); }
        50%, 100% { color: #00d4ff; transform: scale(1.3); }
    }
    @keyframes sirenPulse {
        0%, 75% { color: #00d4ff; transform: scale(1); }
        76%, 100% { color: #ff0000; transform: scale(1.2); }
    }

    /* Logo Glow */
    [data-testid="stImage"] {
        border: 1px solid #00d4ff;
        border-radius: 4px;
        padding: 5px;
        box-shadow: 0px 0px 15px rgba(0, 212, 255, 0.3);
        background: rgba(0, 212, 255, 0.05);
    }

    .stProgress > div > div { height: 6px !important; }
    .stProgress > div > div > div > div { background-color: #00d4ff; }

    .incident-log {
        background-color: #111;
        border: 1px solid #333;
        border-radius: 5px;
        padding: 10px;
        font-family: 'Consolas', monospace;
        font-size: 0.85rem;
    }
    .log-critical { color: #ff0000; font-weight: bold; }
    .log-action { color: #00ffff; font-weight: bold; }
    .log-success { color: #00ff00; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def load_data():
    data = {
        'model': ['RESPONDER', 'GUARDIAN', 'SKYDIO X-10', 'MATRICE 4TD'],
        'flight_time_min': [42, 60, 40, 54],
        'speed_mph': [45, 50, 45, 47],
        'range_miles': [5, 12, 7.5, 6.2],
        'max_wind_mph': [28, 42, 28, 26]
    }
    return pd.DataFrame(data)

def get_lat_lon_from_zip(zip_code):
    geolocator = Nominatim(user_agent="drone_sim_performance_v3")
    try:
        location = geolocator.geocode(f"{zip_code}, USA")
        return [location.latitude, location.longitude] if location else None
    except: return None

def get_distance_miles(p1, p2):
    return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5 * 69

def generate_incident():
    inc, sev = random.choice([("SHOTS FIRED", "critical"), ("ARMED ROBBERY", "critical"), ("VEHICLE PURSUIT", "action")]), "critical"
    st.session_state.inc_type, st.session_state.inc_severity = inc, sev
    st.session_state.t_call = datetime.now()
    st.session_state.t_launch = st.session_state.t_call + timedelta(seconds=random.randint(30, 60))

def randomize_squads():
    st.session_state.squad_cars = []
    for _ in range(random.randint(3, 5)):
        r_mi, angle = random.uniform(1.0, 6.0), random.uniform(0, 2 * math.pi)
        st.session_state.squad_cars.append([st.session_state.base[0] + (r_mi * math.sin(angle))/69, st.session_state.base[1] + (r_mi * math.cos(angle))/69])

# --- Main Layout ---
left_col, right_col = st.columns([7.5, 2.5])

with right_col:
    st.markdown("### 🚁 OPS CENTER")
    header_cols = st.columns([1, 1, 2])
    
    if st.session_state.step == 1:
        with header_cols[0]: zip_in = st_keyup("ZIP", max_chars=5, key="z")
        with header_cols[2]: st.image("logo.png", use_container_width=True)
        if zip_in and len(zip_in) == 5:
            coords = get_lat_lon_from_zip(zip_in)
            if coords: st.session_state.map_center, st.session_state.step = coords, 2; st.rerun()

    elif st.session_state.step >= 2:
        with header_cols[0]: st.metric("WIND", f"{st.session_state.wind_speed} MPH")
        with header_cols[2]: st.image("logo.png", use_container_width=True)
        st.divider()

        if st.session_state.step == 3:
            df = load_data()
            drone_ui = []
            for _, row in df.iterrows():
                with st.container():
                    c1, c2 = st.columns([1.8, 1])
                    name_placeholder = c1.empty()
                    status_placeholder = c2.empty()
                    m_cols = st.columns(4)
                    drone_ui.append({'specs': row, 'name_p': name_placeholder, 'status_p': status_placeholder, 'bar': st.progress(0), 'm_eta': m_cols[1].empty(), 'm_adv': m_cols[2].empty(), 'm_batt': m_cols[3].empty()})
                    st.divider()
            incident_placeholder = st.empty()

with left_col:
    m = folium.Map(location=st.session_state.map_center, zoom_start=12, tiles="CartoDB dark_matter")
    if st.session_state.base:
        folium.Marker(st.session_state.base, icon=folium.Icon(color='white', icon='home', prefix='fa')).add_to(m)
        best_car = None
        if st.session_state.target:
            best_car = min(st.session_state.squad_cars, key=lambda x: get_distance_miles(x, st.session_state.target))
            folium.Marker(st.session_state.target, icon=folium.Icon(color='red', icon='crosshairs', prefix='fa')).add_to(m)
            
        for sq in st.session_state.squad_cars:
            anim = "dispatchPulse" if (sq == best_car and st.session_state.step == 3 and not st.session_state.sim_completed) else "sirenPulse" if (st.session_state.step == 3 and not st.session_state.sim_completed) else ""
            car_style = f"animation: {anim} 0.5s infinite;" if anim else "color: #00d4ff;"
            folium.Marker(sq, icon=DivIcon(html=f'<div style="{car_style} font-size: 20px;"><i class="fa fa-car"></i></div>')).add_to(m)

    map_data = st_folium(m, height=850, use_container_width=True, key="map")
    if map_data['last_clicked']:
        coords = [map_data['last_clicked']['lat'], map_data['last_clicked']['lng']]
        if not st.session_state.base: st.session_state.base = coords; randomize_squads(); st.rerun()
        else: st.session_state.target = coords; generate_incident(); st.session_state.wind_speed = random.randint(5, 35); st.session_state.step = 3; st.session_state.sim_completed = False; st.rerun()

# --- Simulation Logic ---
if st.session_state.step == 3 and not st.session_state.sim_completed:
    dist = get_distance_miles(st.session_state.base, st.session_state.target)
    sim_data = []
    for d in drone_ui:
        t_out = dist / (d['specs']['speed_mph'] / 3600)
        possible = st.session_state.wind_speed <= d['specs']['max_wind_mph']
        sim_data.append({'ui': d, 't_out': t_out, 't_total': t_out * 2.5, 'possible': possible})

    for tick in range(101):
        curr_time = (tick / 100) * max([s['t_total'] for s in sim_data])
        for s in sim_data:
            ui = s['ui']
            if not s['possible']:
                ui['name_p'].markdown(f"<span class='drone-static'>{s['ui']['specs']['model']}</span>", unsafe_allow_html=True)
                ui['status_p'].error("WIND FAIL")
                continue
            
            in_flight = curr_time < s['t_total']
            p_class = "drone-active" if in_flight else "drone-static"
            ui['name_p'].markdown(f"<span class='{p_class}'>{s['ui']['specs']['model']}</span>", unsafe_allow_html=True)
            
            prog = min(1.0, curr_time / s['t_out']) if curr_time < s['t_out'] else 1.0 if curr_time < (s['t_out'] * 1.5) else max(0, 1.0 - (curr_time - s['t_out']*1.5)/s['t_out'])
            ui['bar'].progress(prog)
            ui['status_p'].info("IN FLIGHT" if in_flight else "RETURNED")
            ui['m_batt'].metric("BATT", f"{int(100 - (curr_time/50))}%")
        
        time.sleep(0.05)
    st.session_state.sim_completed = True
    st.rerun()
