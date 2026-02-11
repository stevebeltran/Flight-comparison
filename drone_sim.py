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

# --- CUSTOM CSS: CLEAN COCKPIT THEME ---
st.markdown("""
    <style>
    /* 1. HIDE STREAMLIT HEADER */
    header[data-testid="stHeader"] {
        display: none;
    }
    
    /* 2. DARK THEME */
    .stApp {
        background-color: #050505 !important;
        color: #e0e0e0;
    }
    
    /* 3. PADDING */
    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* 4. COMPACT SPACING */
    div.stVerticalBlock > div {
        gap: 0.5rem !important;
    }
    
    /* 5. METRICS */
    div[data-testid="stMetricValue"] {
        font-size: 1.1rem !important;
        color: #ffa500; 
        font-family: 'Consolas', monospace;
        text-shadow: 0px 0px 4px rgba(255, 165, 0, 0.5);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.6rem !important;
        color: #888;
        margin-bottom: -5px;
    }

    /* 6. PROGRESS BARS */
    .stProgress > div > div {
        height: 6px !important;
    }
    .stProgress > div > div > div > div {
        background-color: #00d4ff;
    }

    /* 7. BUTTONS */
    div.stButton > button {
        background-color: #222;
        color: #00d4ff;
        border: 1px solid #00d4ff;
        font-size: 0.8rem;
        padding: 0.25rem 0.5rem;
    }
    
    /* 8. INPUTS */
    .stTextInput input {
        background-color: #111;
        color: #fff;
        border: 1px solid #444;
    }
    
    /* 9. HEADERS */
    h3 { margin-bottom: 0px !important; padding-bottom: 0px !important; font-size: 1.2rem !important; color: #fff;}
    hr { margin: 0.5em 0 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def load_data():
    try:
        df = pd.read_csv('drones.csv')
        df = df.dropna(subset=['model'])
        df['model'] = df['model'].astype(str)
        df.columns = df.columns.str.strip()
        df['model'] = df['model'].replace('Interceptor', 'SKYDIO X-10')
        
        defaults = {'recharge_time_min': 60, 'burst_drain_factor': 1.5, 'max_wind_mph': 25}
        for col, val in defaults.items():
            if col not in df.columns: df[col] = val
            
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
    geolocator = Nominatim(user_agent="drone_sim_final_v2")
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
left_col, right_col = st.columns([7.5, 2.5])

# ==========================================
# RIGHT COLUMN: COMPACT COCKPIT
# ==========================================
with right_col:
    st.markdown("### 🚁 OPS CENTER")
    
    if st.session_state.step == 1:
        with st.form(key='zip_form'):
            c_in, c_btn = st.columns([2,1])
            # CHANGED: Placeholder is now 61047
            zip_in = c_in.text_input("ZIP", placeholder="61047", label_visibility="collapsed")
            if c_btn.form_submit_button("INIT"):
                if zip_in:
                    coords = get_lat_lon_from_zip(zip_in)
                    if coords:
                        st.session_state.map_center = coords
                        generate_weather()
                        st.session_state.step = 2
                        st.rerun()

    elif st.session_state.step >= 2:
        # STATUS BAR
        bar_c1, bar_c2, bar_c3 = st.columns([1.2, 1.2, 0.8])
        bar_c1.metric("WIND", f"{st.session_state.wind_speed} {st.session_state.wind_dir}")
        
        with bar_c2:
            st.write("") 
            is_burst = st.checkbox("🔥 BURST", value=st.session_state.burst_mode)
            st.session_state.burst_mode = is_burst
            
        bar_c3.write("") 
        if bar_c3.button("RESET"): reset_all()
        
        st.divider()

        # TARGET INFO
        if not st.session_state.base:
            st.warning("📍 SET BASE")
        elif not st.session_state.target:
            st.info("🎯 SET TARGET")
        else:
            dist = get_distance_miles(st.session_state.base, st.session_state.target)
            st.success(f"Target: {dist:.2f} mi")

        # DRONE FLEET SETUP
        if st.session_state.step == 3:
            df = load_data()
            
            # --- PRE-CALCULATION FOR RENAMING ---
            # We need to calculate times FIRST to determine ranking/names
            # Then we render the UI elements with those new names.
            temp_sim_data = []
            for index, row in df.iterrows():
                # Quick Physics Calc for Ranking
                if st.session_state.burst_mode: max_v = float(row['max_speed_mph'])
                else: max_v = float(row['speed_mph'])
                
                speed_mps = max_v / 3600
                t_out = dist / speed_mps
                
                batt_sec = float(row['flight_time_min']) * 60
                usable = batt_sec * 0.80
                cost = (t_out * 2) * (float(row['burst_drain_factor']) if st.session_state.burst_mode else 1.0)
                
                hover_sec = usable - cost
                possible = True
                if st.session_state.wind_speed > float(row['max_wind_mph']): possible = False
                elif hover_sec < 0: possible = False
                
                total_time = (t_out * 2) + (hover_sec if possible else 0)
                
                temp_sim_data.append({
                    'index': index,
                    'specs': row,
                    't_total': total_time,
                    'possible': possible
                })
            
            # SORT AND ASSIGN NAMES
            # Filter possible missions for valid ranking
            valid_missions = [d for d in temp_sim_data if d['possible']]
            valid_missions.sort(key=lambda x: x['t_total'])
            
            # Create a lookup for ranks
            rank_map = {} # index -> (Name, Color)
            for i, d in enumerate(valid_missions):
                if i == 0: rank_map[d['index']] = ("RED ONE", "#ff0000")
                elif i == 1: rank_map[d['index']] = ("YELLOW TWO", "#ffff00")
                else: rank_map[d['index']] = ("GREEN THREE", "#00ff00")
            
            # UI GENERATION LOOP
            drone_ui_elements = [] 
            for d_data in temp_sim_data:
                idx = d_data['index']
                row = d_data['specs']
                
                # Get Assigned Name (or fallback if it failed)
                if idx in rank_map:
                    display_name = f"{rank_map[idx][0]} ({row['model']})"
                    display_color = rank_map[idx][1]
                else:
                    display_name = f"GROUNDED ({row['model']})"
                    display_color = "#888888"

                with st.container():
                    # Colored Header
                    head_c1, head_c2 = st.columns([1.8, 1])
                    head_c1.markdown(f"<span style='color:{display_color}; font-weight:bold'>{display_name}</span>", unsafe_allow_html=True)
                    status_placeholder = head_c2.empty()
                    
                    m1, m2, m3, m4 = st.columns(4)
                    
                    ui_obj = {
                        'specs': row,
                        'status_text': status_placeholder,
                        'speed_bar': st.empty(),
                        'metric_speed': m1.empty(),
                        'metric_batt': m2.empty(),
                        'metric_eta': m3.empty(),
                        'metric_hover': m4.empty(),
                        'rank_color': display_color
                    }
                    drone_ui_elements.append(ui_obj)
                    ui_obj['speed_bar'] = st.progress(0)
                    st.divider()

# ==========================================
# LEFT COLUMN: HIGH CONTRAST MAP
# ==========================================
with left_col:
    m = folium.Map(
        location=st.session_state.map_center, 
        zoom_start=st.session_state.map_zoom, 
        tiles="CartoDB dark_matter" 
    )

    if st.session_state.base:
        folium.Marker(
            st.session_state.base, 
            tooltip="BASE", 
            icon=folium.Icon(color='white', icon='home', prefix='fa', icon_color='black')
        ).add_to(m)
        
        rings = [(2, '#00ff00'), (3, '#ffff00'), (4, '#ff9900'), (5, '#ff0000')]
        for r, c in rings:
            folium.Circle(
                location=st.session_state.base, radius=r * 1609.34,
                color=c, weight=2, fill=False, opacity=0.9, dash_array='4, 8'
            ).add_to(m)
            
            lat_offset = (r / 69.0)
            folium.map.Marker(
                [st.session_state.base[0] + lat_offset, st.session_state.base[1]],
                icon=DivIcon(
                    icon_size=(100,20), icon_anchor=(50,10),
                    html=f'<div style="font-size:10px; font-weight:900; color:{c}; text-shadow: 0 0 5px #000;">{r} MI</div>'
                )
            ).add_to(m)

    if st.session_state.target:
        folium.Marker(
            st.session_state.target, 
            tooltip="TARGET", 
            icon=folium.Icon(color='red', icon='crosshairs', prefix='fa')
        ).add_to(m)
        
        path_color = "#ff3333" if st.session_state.burst_mode else "#00ffff"
        plugins.AntPath(
            locations=[st.session_state.base, st.session_state.target],
            color=path_color, pulse_color="#ffffff",
            weight=4, delay=800, dash_array=[10, 20]     
        ).add_to(m)

    map_data = st_folium(m, height=850, use_container_width=True, key="map")

    if map_data['last_clicked']:
        coords = [map_data['last_clicked']['lat'], map_data['last_clicked']['lng']]
        if not st.session_state.base:
            st.session_state.base = coords
            st.rerun()
        elif st.session_state.target != coords:
            st.session_state.target = coords
            generate_weather()
            st.session_state.step = 3
            st.rerun()
        
        if map_data['zoom']: st.session_state.map_zoom = map_data['zoom']
        if map_data['center']: st.session_state.map_center = [map_data['center']['lat'], map_data['center']['lng']]

# ==========================================
# SIMULATION LOOP
# ==========================================
if st.session_state.step == 3 and st.session_state.base and st.session_state.target:
    
    dist_one_way = get_distance_miles(st.session_state.base, st.session_state.target)
    fleet_sim_data = []
    
    # 1. Physics
    for drone in drone_ui_elements:
        specs = drone['specs']
        
        wind_fail = st.session_state.wind_speed > float(specs['max_wind_mph'])
        
        if st.session_state.burst_mode:
            max_v = float(specs['max_speed_mph'])
            drain = float(specs['burst_drain_factor'])
        else:
            max_v = float(specs['speed_mph'])
            drain = 1.0
            
        speed_mps = max_v / 3600
        t_out = dist_one_way / speed_mps
        
        batt_sec = float(specs['flight_time_min']) * 60
        usable = batt_sec * 0.80
        
        cost = (t_out * 2) * drain
        hover_sec = usable - cost
        
        possible = True
        fail_msg = ""
        
        if wind_fail:
            possible = False
            fail_msg = "WIND"
        elif hover_sec < 0:
            possible = False
            fail_msg = "FUEL"
        elif dist_one_way > float(specs['range_miles']):
            possible = False
            fail_msg = "RANGE"
            
        total_time = (t_out * 2) + (hover_sec if possible else 0)
        
        fleet_sim_data.append({
            'ui': drone,
            't_out': t_out,
            't_hov': hover_sec if possible else 0,
            't_total': total_time,
            'batt_cap': batt_sec,
            'possible': possible,
            'fail_msg': fail_msg,
            'tgt_speed': max_v,
            'abs_max': float(specs['max_speed_mph']),
            'curr_v': 0,
            'drain': drain
        })

    # 2. Simulation Loop
    valid = [d for d in fleet_sim_data if d['possible']]
    sim_dur = max([d['t_total'] for d in valid]) if valid else 5
    
    for tick in range(101):
        curr_time = (tick / 100) * sim_dur
        
        for d in fleet_sim_data:
            ui = d['ui']
            
            if not d['possible']:
                ui['status_text'].markdown(f":red[**{d['fail_msg']}**]")
                ui['metric_speed'].metric("MPH", "0")
                ui['metric_batt'].metric("BAT", "0%")
                ui['metric_eta'].metric("ETA", "--")
                ui['metric_hover'].metric("SITE", "--")
                ui['speed_bar'].progress(0)
                continue
            
            phase_txt = ""
            phase_col = "#00ffff"
            eta = 0
            site_time = 0
            target_v = 0
            
            if curr_time < d['t_out']:
                phase_txt = ">> OUT"
                eta = d['t_out'] - curr_time
                target_v = d['tgt_speed']
            elif curr_time < (d['t_out'] + d['t_hov']):
                phase_txt = "HOVER"
                site_time = curr_time - d['t_out']
                target_v = 0
            elif curr_time < d['t_total']:
                phase_txt = "<< RTB"
                eta = d['t_total'] - curr_time
                site_time = d['t_hov']
                target_v = d['tgt_speed']
            else:
                # DONE STATUS
                phase_txt = "✓ SECURE" # Removed "DONE"
                phase_col = ui['rank_color'] # Reveal Rank Color
                site_time = d['t_hov']
                target_v = 0
                d['curr_v'] = 0 
            
            # Speed Calc
            if d['curr_v'] < target_v: d['curr_v'] += 1
            elif d['curr_v'] > target_v: d['curr_v'] -= 1
            if d['curr_v'] < 0: d['curr_v'] = 0
            
            # Render
            ui['status_text'].markdown(f"<span style='color:{phase_col}'>{phase_txt}</span>", unsafe_allow_html=True)
            ui['metric_speed'].metric("MPH", f"{int(d['curr_v'])}")
            
            ui['speed_bar'].progress(min(d['curr_v'] / d['abs_max'], 1.0))
            ui['metric_eta'].metric("ETA", f"{int(eta/60):02d}:{int(eta%60):02d}")
            ui['metric_hover'].metric("SITE", f"{int(site_time/60):02d}:{int(site_time%60):02d}")
            
            # Battery
            fly_time = 0
            hov_time = 0
            if curr_time < d['t_out']: fly_time = curr_time
            elif curr_time < (d['t_out'] + d['t_hov']): 
                fly_time = d['t_out']; hov_time = curr_time - d['t_out']
            elif curr_time < d['t_total']:
                fly_time = d['t_out'] + (curr_time - (d['t_out']+d['t_hov'])); hov_time = d['t_hov']
            else:
                fly_time = d['t_out'] * 2; hov_time = d['t_hov']
                
            used = (fly_time * d['drain']) + hov_time
            pct = max(0, 100 - (used / d['batt_cap'] * 100))
            ui['metric_batt'].metric("BAT", f"{int(pct)}%")

        # DOUBLED DURATION: 0.08 -> 0.16
        time.sleep(0.16)
