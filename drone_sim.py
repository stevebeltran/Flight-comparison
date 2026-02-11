import streamlit as st
import pandas as pd
import folium
from folium import plugins
from folium.features import DivIcon
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import time
import random

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Tactical Drone Command", initial_sidebar_state="collapsed")

# --- CUSTOM CSS: TACTICAL AMBER THEME ---
st.markdown("""
    <style>
    /* FORCE DARK BACKGROUND */
    .stApp, .block-container, div[data-testid="stHeader"] {
        background-color: #0b0c10 !important;
        color: #c5c6c7;
    }
    div.stVerticalBlock, div.stHorizontalBlock, div.element-container {
        background-color: transparent !important;
    }

    /* METRICS */
    div[data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
        color: #ffa500; 
        font-family: 'Consolas', 'Courier New', monospace;
        font-weight: 700;
        text-shadow: 0px 0px 5px rgba(255, 165, 0, 0.4);
    }
    div[data-testid="stMetricLabel"] {
        color: #45a29e;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* BUTTONS */
    div.stButton > button {
        background-color: #1f2833;
        color: #66fcf1;
        border: 1px solid #45a29e;
        border-radius: 2px;
        text-transform: uppercase;
        font-weight: bold;
    }
    div.stButton > button:hover {
        background-color: #45a29e;
        color: #0b0c10;
        border-color: #66fcf1;
        box-shadow: 0px 0px 10px #45a29e;
    }

    /* SPEEDOMETER BAR (Cyan) */
    .stProgress > div > div > div > div {
        background-color: #66fcf1;
        transition: width 0.1s linear;
    }
    
    /* INPUT FIELDS */
    .stTextInput > div > div > input {
        background-color: #1f2833;
        color: #fff;
        border: 1px solid #45a29e;
    }
    .stTextInput input::placeholder {
        color: #666;
        font-style: italic;
    }

    /* HEADERS */
    h1, h2, h3 {
        color: #66fcf1;
        font-family: 'Impact', sans-serif;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def load_data():
    try:
        df = pd.read_csv('drones.csv')
        df = df.dropna(subset=['model'])
        df['model'] = df['model'].astype(str)
        df.columns = df.columns.str.strip()
        
        # Force Rename
        df['model'] = df['model'].replace('Interceptor', 'SKYDIO X-10')
        
        if 'recharge_time_min' not in df.columns: df['recharge_time_min'] = 60
        if 'burst_drain_factor' not in df.columns: df['burst_drain_factor'] = 1.5
        if 'max_wind_mph' not in df.columns: df['max_wind_mph'] = 25 
            
        if df.empty: raise ValueError
        return df
    except:
        data = {
            'model': ['Scout', 'Heavy-Lift', 'SKYDIO X-10'],
            'flight_time_min': [25, 40, 15],
            'speed_mph': [22, 18, 55],
            'max_speed_mph': [35, 25, 80],
            'range_miles': [6, 9, 5],
            'recharge_time_min': [45, 60, 30],
            'burst_drain_factor': [1.2, 1.3, 1.5],
            'max_wind_mph': [25, 30, 40]
        }
        return pd.DataFrame(data)

def get_lat_lon_from_zip(zip_code):
    geolocator = Nominatim(user_agent="drone_sim_accel_v2")
    try:
        location = geolocator.geocode(f"{zip_code}, USA")
        if location: return [location.latitude, location.longitude]
    except: return None
    return None

def get_distance_miles(p1, p2):
    return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5 * 69

# --- Session State ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'map_center' not in st.session_state: st.session_state.map_center = [39.8283, -98.5795]
if 'map_zoom' not in st.session_state: st.session_state.map_zoom = 13
if 'base' not in st.session_state: st.session_state.base = None
if 'target' not in st.session_state: st.session_state.target = None
if 'burst_mode' not in st.session_state: st.session_state.burst_mode = False
if 'wind_speed' not in st.session_state: st.session_state.wind_speed = 0
if 'wind_dir' not in st.session_state: st.session_state.wind_dir = "N"

def reset_all():
    st.session_state.step = 1
    st.session_state.base = None
    st.session_state.target = None

def generate_weather():
    st.session_state.wind_speed = random.randint(0, 40)
    st.session_state.wind_dir = random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])

# --- Layout ---
left_col, right_col = st.columns([7, 3])

# ==========================================
# RIGHT COLUMN: OPS DECK
# ==========================================
with right_col:
    st.markdown("## 📡 OPS DECK")
    
    if st.session_state.step == 1:
        st.info("AWAITING SECTOR COORDINATES")
        with st.form(key='zip_form'):
            zip_input = st.text_input("ENTER ZIP CODE", value="", placeholder="e.g. 90210")
            submit_button = st.form_submit_button(label='INITIALIZE SECTOR')
            if submit_button:
                if zip_input:
                    coords = get_lat_lon_from_zip(zip_input)
                    if coords:
                        st.session_state.map_center = coords
                        generate_weather()
                        st.session_state.step = 2
                        st.rerun()
                    else:
                        st.error("COORDINATES NOT FOUND")
                else:
                    st.warning("PLEASE ENTER A ZIP CODE")

    elif st.session_state.step >= 2:
        w_col1, w_col2 = st.columns(2)
        w_col1.metric("WIND SPEED", f"{st.session_state.wind_speed} MPH")
        w_col2.metric("DIRECTION", f"{st.session_state.wind_dir}")
        st.markdown("---")
        
        c_reset, c_status = st.columns([1,2])
        c_reset.button("✖ RESET", on_click=reset_all, use_container_width=True)
        
        if not st.session_state.base:
            c_status.warning("⚠ SET BASE")
        elif not st.session_state.target:
            c_status.info("⌖ SET TARGET")
        else:
            dist = get_distance_miles(st.session_state.base, st.session_state.target)
            c_status.success(f"LOCKED: {dist:.2f} MI")
            
            st.markdown("---")
            is_burst = st.checkbox("🔥 BURST MODE (MAX SPEED)", value=st.session_state.burst_mode)
            st.session_state.burst_mode = is_burst
        
        st.markdown("---")
        
        if st.session_state.step == 3:
            df = load_data()
            drone_ui_elements = [] 
            
            for index, row in df.iterrows():
                with st.container():
                    st.markdown(f"### ✈ {row['model']}")
                    c1, c2, c3, c4, c5 = st.columns(5)
                    
                    ui_obj = {
                        'specs': row,
                        'status_text': st.empty(),
                        'speed_bar': st.progress(0),
                        'metric_eta': c1.empty(),
                        'metric_hover': c2.empty(), 
                        'metric_speed': c3.empty(),
                        'metric_batt': c4.empty(),
                        'metric_recharge': c5.empty()
                    }
                    drone_ui_elements.append(ui_obj)
                    st.markdown("---")

# ==========================================
# LEFT COLUMN: TACTICAL MAP
# ==========================================
with left_col:
    # UPDATED: Use 'CartoDB positron' for higher brightness/visibility while keeping clean look
    m = folium.Map(
        location=st.session_state.map_center, 
        zoom_start=st.session_state.map_zoom, 
        tiles="CartoDB positron" 
    )

    if st.session_state.base:
        folium.Marker(
            st.session_state.base, 
            tooltip="BASE ALPHA", 
            icon=folium.Icon(color='lightgray', icon='home', prefix='fa')
        ).add_to(m)
        
        # Rings: increased opacity slightly for visibility against light map
        rings = [(2, '#00aa00'), (3, '#ffa500'), (4, '#ff4500'), (5, '#ff0000')]
        for r, c in rings:
            folium.Circle(
                location=st.session_state.base, radius=r * 1609.34,
                color=c, weight=2, fill=False, opacity=0.8, dash_array='5, 10'
            ).add_to(m)
            
            lat_offset = (r / 69.0)
            folium.map.Marker(
                [st.session_state.base[0] + lat_offset, st.session_state.base[1]],
                icon=DivIcon(
                    icon_size=(150,36), icon_anchor=(75,10),
                    html=f'<div style="font-size: 9pt; font-weight: bold; color: {c}; background-color: rgba(255,255,255,0.8); padding: 2px 5px; border-radius: 4px; border: 1px solid {c}; text-align: center; width: 50px; margin-left: 50px;">{r} MI</div>'
                )
            ).add_to(m)

    if st.session_state.target:
        folium.Marker(
            st.session_state.target, 
            tooltip="TARGET BRAVO", 
            icon=folium.Icon(color='red', icon='crosshairs', prefix='fa')
        ).add_to(m)
        
        path_color = "#ff0000" if st.session_state.burst_mode else "#ffa500"
        plugins.AntPath(
            locations=[st.session_state.base, st.session_state.target],
            color=path_color, pulse_color="#000000", # Black pulses for visibility on light map
            weight=5, delay=800, dash_array=[1, 20], line_cap='round'      
        ).add_to(m)

    map_data = st_folium(m, height=850, use_container_width=True, key="tactical_map")

    if map_data['last_clicked']:
        clicked_coords = [map_data['last_clicked']['lat'], map_data['last_clicked']['lng']]
        needs_rerun = False
        
        if not st.session_state.base:
            st.session_state.base = clicked_coords
            needs_rerun = True
        else:
            if st.session_state.target != clicked_coords:
                st.session_state.target = clicked_coords
                st.session_state.step = 3
                needs_rerun = True
        
        if map_data['zoom']: st.session_state.map_zoom = map_data['zoom']
        if map_data['center']: st.session_state.map_center = [map_data['center']['lat'], map_data['center']['lng']]
        
        if needs_rerun: st.rerun()

# ==========================================
# SIMULATION ENGINE
# ==========================================
if st.session_state.step == 3 and st.session_state.base and st.session_state.target:
    
    dist_one_way = get_distance_miles(st.session_state.base, st.session_state.target)
    fleet_sim_data = []
    current_wind = st.session_state.wind_speed
    
    for drone in drone_ui_elements:
        specs = drone['specs']
        
        wind_limit = float(specs['max_wind_mph'])
        is_grounded_by_wind = current_wind > wind_limit
        
        if st.session_state.burst_mode:
            active_max_speed = float(specs['max_speed_mph'])
            drain_factor = float(specs['burst_drain_factor'])
        else:
            active_max_speed = float(specs['speed_mph'])
            drain_factor = 1.0 
            
        speed_mps = active_max_speed / 3600 
        time_to_scene_sec = dist_one_way / speed_mps
        
        total_battery_sec = float(specs['flight_time_min']) * 60
        usable_sec = total_battery_sec * 0.80 
        
        round_trip_sec_real = time_to_scene_sec * 2
        battery_cost_sec = round_trip_sec_real * drain_factor
        
        max_hover_sec_real = (usable_sec - battery_cost_sec)
        
        possible = True
        fail_reason = ""
        
        if is_grounded_by_wind:
            possible = False
            fail_reason = f"WIND LIMIT ({wind_limit} MPH)"
        elif max_hover_sec_real < 0:
            possible = False
            fail_reason = "FUEL CRITICAL"
        elif dist_one_way > float(specs['range_miles']):
            possible = False
            fail_reason = "OUT OF RANGE"
            
        mission_total_time = (time_to_scene_sec * 2) + (max_hover_sec_real if possible else 0)
        
        fleet_sim_data.append({
            'ui': drone,
            'time_outbound': time_to_scene_sec,
            'time_hover': max_hover_sec_real if possible else 0,
            'time_return': time_to_scene_sec,
            'total_mission_time': mission_total_time,
            'total_battery_cap': total_battery_sec,
            'possible': possible,
            'fail_reason': fail_reason,
            'target_speed': active_max_speed,
            'absolute_max_speed': float(specs['max_speed_mph']),
            'current_display_speed': 0, 
            'recharge_min': specs['recharge_time_min'],
            'drain_factor': drain_factor
        })

    # Ranking
    valid_missions = [d for d in fleet_sim_data if d['possible']]
    valid_missions.sort(key=lambda x: x['total_mission_time'])
    
    for rank, drone_data in enumerate(valid_missions):
        if rank == 0: drone_data['rank_color'] = "#ff0000" 
        elif rank == 1: drone_data['rank_color'] = "#ffff00" 
        else: drone_data['rank_color'] = "#00ff00" 

    valid_times = [d['total_mission_time'] for d in fleet_sim_data if d['possible']]
    sim_duration = max(valid_times) if valid_times else 5
    
    for tick in range(101):
        current_sim_time = (tick / 100) * sim_duration
        
        for drone_sim in fleet_sim_data:
            ui = drone_sim['ui']
            
            if not drone_sim['possible']:
                ui['status_text'].error(f"⛔ {drone_sim['fail_reason']}")
                ui['metric_eta'].metric("ETA", "N/A")
                ui['metric_hover'].metric("ON SCENE", "00:00")
                ui['metric_batt'].metric("BATTERY", "0%") # Changed Label
                ui['metric_recharge'].metric("RECHARGE", "--")
                ui['metric_speed'].metric("VELOCITY", "0 MPH")
                ui['speed_bar'].progress(0)
                continue
            
            ui['metric_recharge'].metric("RECHARGE", f"{int(drone_sim['recharge_min'])} min")

            t_out = drone_sim['time_outbound']
            t_hov = drone_sim['time_hover']
            t_ret = drone_sim['time_return']
            t_total = drone_sim['total_mission_time']
            
            phase = ""
            display_color = "#66fcf1" 
            eta_val = 0
            on_scene_val = 0
            
            target_v = 0 
            
            if current_sim_time < t_out:
                phase = ">>> INBOUND >>>"
                eta_val = t_out - current_sim_time
                target_v = drone_sim['target_speed']
                
            elif current_sim_time < (t_out + t_hov):
                phase = "● ON SCENE"
                on_scene_val = current_sim_time - t_out
                target_v = 0 
                
            elif current_sim_time < t_total:
                phase = "<<< RTB <<<"
                eta_val = t_total - current_sim_time
                on_scene_val = t_hov
                target_v = drone_sim['target_speed']
                
            else:
                phase = "✓ SECURE"
                on_scene_val = t_hov
                display_color = drone_sim.get('rank_color', '#ffa500')
                target_v = 0 
                # FORCE ZERO AT END OF MISSION TO FIX "STUCK" BUG
                drone_sim['current_display_speed'] = 0 

            # Increment/Decrement Speed
            if drone_sim['current_display_speed'] < target_v:
                drone_sim['current_display_speed'] += 1
            elif drone_sim['current_display_speed'] > target_v:
                drone_sim['current_display_speed'] -= 1

            # Ensure we don't accidentally display -1
            if drone_sim['current_display_speed'] < 0: drone_sim['current_display_speed'] = 0

            ui['metric_eta'].metric("ETA", f"{int(eta_val/60):02d}:{int(eta_val%60):02d}")
            ui['metric_hover'].metric("ON SCENE", f"{int(on_scene_val/60):02d}:{int(on_scene_val%60):02d}")
            
            current_v = drone_sim['current_display_speed']
            ui['metric_speed'].metric("VELOCITY", f"{int(current_v)} MPH")

            speed_pct = current_v / drone_sim['absolute_max_speed']
            ui['speed_bar'].progress(min(speed_pct, 1.0))

            # BATTERY CALC
            time_flying = 0
            time_hovering = 0
            
            if current_sim_time < t_out:
                time_flying = current_sim_time
            elif current_sim_time < (t_out + t_hov):
                time_flying = t_out
                time_hovering = current_sim_time - t_out
            elif current_sim_time < t_total:
                time_flying = t_out + (current_sim_time - (t_out + t_hov))
                time_hovering = t_hov
            else:
                time_flying = t_out + t_ret
                time_hovering = t_hov
            
            batt_used_seconds = (time_flying * drone_sim['drain_factor']) + time_hovering
            batt_drain_pct = (batt_used_seconds / drone_sim['total_battery_cap']) * 100
            current_batt = max(0, 100 - batt_drain_pct)
            
            status_html = f"<span style='color:{display_color}; font-weight:bold; font-size:1.2em; text-shadow: 0px 0px 5px {display_color};'>{phase}</span>"
            ui['status_text'].markdown(status_html, unsafe_allow_html=True)
                
            ui['metric_batt'].metric("BATTERY", f"{int(current_batt)}%") # Changed Label
        
        time.sleep(0.08)