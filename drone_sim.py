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
if 'theme' not in st.session_state: st.session_state.theme = 'Dark'
if 'step' not in st.session_state: st.session_state.step = 1
if 'map_center' not in st.session_state: st.session_state.map_center = [39.8283, -98.5795]
if 'map_zoom' not in st.session_state: st.session_state.map_zoom = 13
if 'base' not in st.session_state: st.session_state.base = None
if 'target' not in st.session_state: st.session_state.target = None
if 'burst_mode' not in st.session_state: st.session_state.burst_mode = False
if 'wind_speed' not in st.session_state: st.session_state.wind_speed = 0
if 'wind_dir' not in st.session_state: st.session_state.wind_dir = "N"
if 'inc_type' not in st.session_state: st.session_state.inc_type = None
if 'squad_cars' not in st.session_state: st.session_state.squad_cars = []

# --- DYNAMIC CSS THEMING ---
if st.session_state.theme == 'Dark':
    bg_color = "#050505"
    text_color = "#e0e0e0"
    metric_val_color = "#ffa500"
    metric_lbl_color = "#888888"
    box_bg = "#111111"
    box_border = "#333333"
    btn_bg = "#222222"
    btn_text = "#00d4ff"
    header_color = "#ffffff"
    map_tiles = "CartoDB dark_matter"
    
    # Simulation Colors - Dark Mode
    color_fastest = "#00ff00"
    color_second = "#ffff00"
    color_third = "#ff0000"
    color_phase = "#00ffff"
else:
    bg_color = "#f4f4f4"
    text_color = "#111111"
    metric_val_color = "#d35400"
    metric_lbl_color = "#555555"
    box_bg = "#ffffff"
    box_border = "#cccccc"
    btn_bg = "#eeeeee"
    btn_text = "#0055ff"
    header_color = "#000000"
    map_tiles = "CartoDB positron"
    
    # Simulation Colors - Light Mode (Darker for readability on white)
    color_fastest = "#00aa00"
    color_second = "#cc7700"
    color_third = "#cc0000"
    color_phase = "#0055ff"

st.markdown(f"""
    <style>
    header[data-testid="stHeader"] {{ display: none; }}
    .stApp {{ background-color: {bg_color} !important; color: {text_color}; }}
    .block-container {{ padding-top: 3rem !important; padding-bottom: 1rem !important; }}
    div.stVerticalBlock > div {{ gap: 0.5rem !important; }}
    
    div[data-testid="stMetricValue"] {{
        font-size: 1.1rem !important;
        color: {metric_val_color}; 
        font-family: 'Consolas', monospace;
    }}
    div[data-testid="stMetricLabel"] {{ font-size: 0.6rem !important; color: {metric_lbl_color}; margin-bottom: -5px; }}

    .stProgress > div > div {{ height: 6px !important; }}
    .stProgress > div > div > div > div {{ background-color: {color_phase}; }}

    div.stButton > button {{
        background-color: {btn_bg};
        color: {btn_text};
        border: 1px solid {btn_text};
        font-size: 0.8rem;
    }}
    
    .stTextInput input {{ background-color: {box_bg}; color: {text_color}; border: 1px solid {box_border}; }}
    h3 {{ margin-bottom: 0px !important; padding-bottom: 0px !important; font-size: 1.2rem !important; color: {header_color};}}
    hr {{ margin: 0.5em 0 !important; border-color: {box_border} !important; }}

    /* --- INCIDENT LOG CSS --- */
    .incident-log {{
        background-color: {box_bg};
        border: 1px solid {box_border};
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 15px;
        font-family: 'Consolas', monospace;
        font-size: 0.85rem;
        min-height: 125px; 
    }}
    .log-header {{ color: {header_color}; font-size: 0.9rem; border-bottom: 1px solid {box_border}; margin-bottom: 8px; padding-bottom: 4px; font-weight: bold; }}
    .log-entry {{ margin-bottom: 4px; }}
    .log-time {{ color: {metric_lbl_color}; margin-right: 12px; }}
    .log-critical {{ color: {color_third}; font-weight: bold; }}
    .log-action {{ color: {color_phase}; font-weight: bold; }}
    .log-success {{ color: {color_fastest}; font-weight: bold; }}
    .log-info {{ color: {metric_val_color}; font-weight: bold; }}
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def load_data():
    try:
        df = pd.read_csv('drones.csv')
        df = df.dropna(subset=['model'])
        df['model'] = df['model'].astype(str)
        df.columns = df.columns.str.strip()
        
        defaults = {'recharge_time_min': 60, 'burst_drain_factor': 1.5, 'max_wind_mph': 25}
        for col, val in defaults.items():
            if col not in df.columns: df[col] = val
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
    geolocator = Nominatim(user_agent="drone_sim_performance_final")
    try:
        location = geolocator.geocode(f"{zip_code}, USA")
        if location: return [location.latitude, location.longitude]
    except: return None
    return None

def get_distance_miles(p1, p2):
    return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5 * 69

def generate_incident():
    incidents = [
        ("SHOTS FIRED", "critical"),
        ("ARMED ROBBERY", "critical"),
        ("OFFICER IN DISTRESS", "critical"),
        ("BURGLARY IN PROGRESS", "action"),
        ("VEHICLE PURSUIT", "action"),
        ("MISSING PERSON", "info"),
        ("SUSPICIOUS ACTIVITY", "info")
    ]
    inc, severity = random.choice(incidents)
    st.session_state.inc_type = inc
    st.session_state.inc_severity = severity
    
    hr = random.choice(list(range(18, 24)) + list(range(0, 4)))
    mn = random.randint(0, 59)
    sc = random.randint(0, 59)
    
    base_time = datetime.now().replace(hour=hr, minute=mn, second=sc)
    st.session_state.t_call = base_time
    st.session_state.t_launch = base_time + timedelta(seconds=random.randint(45, 120))
    
    if 't_officers' in st.session_state:
        del st.session_state['t_officers']

def randomize_squads():
    """Generates a fresh set of random squad cars around the base."""
    if st.session_state.base:
        st.session_state.squad_cars = []
        num_cars = random.randint(4, 8)
        for _ in range(num_cars):
            r_mi = random.uniform(0.5, 9.0) 
            angle = random.uniform(0, 2 * math.pi)
            d_lat = (r_mi * math.sin(angle)) / 69.172
            d_lon = (r_mi * math.cos(angle)) / (69.172 * math.cos(math.radians(st.session_state.base[0])))
            st.session_state.squad_cars.append([st.session_state.base[0] + d_lat, st.session_state.base[1] + d_lon])

def reset_all():
    st.session_state.step = 1
    st.session_state.base = None
    st.session_state.target = None
    st.session_state.squad_cars = []
    if 't_officers' in st.session_state:
        del st.session_state['t_officers']

def generate_weather():
    st.session_state.wind_speed = random.randint(0, 40)
    st.session_state.wind_dir = random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])


# --- Layout ---
left_col, right_col = st.columns([7.5, 2.5])

with right_col:
    # Top Action Bar with Theme Switcher
    top_c1, top_c2 = st.columns([3, 1])
    top_c1.markdown("### 🚁 OPS CENTER")
    st.session_state.theme = top_c2.selectbox("Theme", ["Dark", "Light"], label_visibility="collapsed")
    
    if st.session_state.step == 1:
        with st.form(key='zip_form'):
            c_in, c_btn = st.columns([2,1])
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
        bar_c1, bar_c2, bar_c3 = st.columns([1.2, 1.2, 0.8])
        bar_c1.metric("WIND", f"{st.session_state.wind_speed} {st.session_state.wind_dir}")
        with bar_c2:
            st.write("") 
            st.session_state.burst_mode = st.checkbox("🔥 BURST", value=st.session_state.burst_mode)
        if bar_c3.button("RESET"): reset_all()
        
        st.divider()

        if not st.session_state.base:
            st.warning("📍 SET BASE")
        elif not st.session_state.target:
            st.info("🎯 SET TARGET")
        else:
            dist = get_distance_miles(st.session_state.base, st.session_state.target)
            st.success(f"Target: {dist:.2f} mi")

            incident_placeholder = st.empty()

        if st.session_state.step == 3:
            df = load_data()
            drone_ui_elements = [] 
            for index, row in df.iterrows():
                with st.container():
                    head_c1, head_c2 = st.columns([1.8, 1])
                    head_c1.markdown(f"**{row['model']}**")
                    status_placeholder = head_c2.empty()
                    
                    m1, m2, m3, m4 = st.columns(4)
                    
                    ui_obj = {
                        'specs': row,
                        'status_text': status_placeholder,
                        'flight_bar': st.progress(0),
                        'metric_hover': m1.empty(), 
                        'metric_eta': m2.empty(),   
                        'metric_adv': m3.empty(), 
                        'metric_batt': m4.empty(),  
                    }
                    drone_ui_elements.append(ui_obj)
                    st.divider()

with left_col:
    m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles=map_tiles)

    if st.session_state.base:
        folium.Marker(st.session_state.base, icon=folium.Icon(color='white' if st.session_state.theme == 'Dark' else 'black', icon='home', prefix='fa')).add_to(m)
        
        rings = [(2, '#00ff00'), (3, '#ffff00'), (4, '#ff9900'), (5, '#ff0000'), (8, '#cc00ff')]
        for r, c in rings:
            folium.Circle(location=st.session_state.base, radius=r * 1609.34, color=c, weight=2, fill=False, opacity=0.9, dash_array='4, 8').add_to(m)
            lat_offset = (r / 69.0)
            folium.map.Marker([st.session_state.base[0] + lat_offset, st.session_state.base[1]], icon=DivIcon(icon_size=(100,20), icon_anchor=(50,10), html=f'<div style="font-size:10px; font-weight:900; color:{c}; text-shadow: 0 0 5px {"#000" if st.session_state.theme == "Dark" else "#fff"};">{r} MI</div>')).add_to(m)

        # Draw Patrol Squad Cars
        for sq in st.session_state.squad_cars:
            folium.Marker(sq, icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)

    if st.session_state.target:
        folium.Marker(st.session_state.target, icon=folium.Icon(color='red', icon='crosshairs', prefix='fa')).add_to(m)
        path_color = "#ff3333" if st.session_state.burst_mode else color_phase
        plugins.AntPath(locations=[st.session_state.base, st.session_state.target], color=path_color, pulse_color="#ffffff", weight=4, delay=800, dash_array=[10, 20]).add_to(m)

    map_data = st_folium(m, height=850, use_container_width=True, key="map")

    if map_data['last_clicked']:
        coords = [map_data['last_clicked']['lat'], map_data['last_clicked']['lng']]
        if not st.session_state.base:
            st.session_state.base = coords
            st.session_state.map_zoom = 11 
            randomize_squads() # Initial squad car spawn
            st.rerun()
        elif st.session_state.target != coords:
            st.session_state.target = coords
            generate_weather()
            generate_incident() 
            randomize_squads() # Re-randomize squad cars on new target click
            st.session_state.step = 3
            st.rerun()

# ==========================================
# SIMULATION LOOP
# ==========================================
if st.session_state.step == 3 and st.session_state.base and st.session_state.target:
    dist_one_way = get_distance_miles(st.session_state.base, st.session_state.target)
    
    # --- Officer Ground Routing Math (Closest Squad Car) ---
    best_officer_dist = float('inf')
    for sq in st.session_state.squad_cars:
        d = get_distance_miles(sq, st.session_state.target)
        if d < best_officer_dist:
            best_officer_dist = d
            
    if best_officer_dist == float('inf'): 
        best_officer_dist = dist_one_way

    officer_speed_mph = 35.0
    officer_route_dist = best_officer_dist * 1.4 
    officer_travel_sec = officer_route_dist / (officer_speed_mph / 3600.0)
    
    if 't_officers' not in st.session_state:
        st.session_state.t_officers = st.session_state.t_call + timedelta(seconds=60) + timedelta(seconds=officer_travel_sec)

    fleet_sim_data = []
    
    for drone in drone_ui_elements:
        specs = drone['specs']
        wind_fail = st.session_state.wind_speed > float(specs['max_wind_mph'])
        max_v = float(specs['max_speed_mph']) if st.session_state.burst_mode else float(specs['speed_mph'])
        drain = float(specs['burst_drain_factor']) if st.session_state.burst_mode else 1.0
        
        t_out = dist_one_way / (max_v / 3600)
        batt_sec = float(specs['flight_time_min']) * 60
        hover_sec = (batt_sec * 0.80) - ((t_out * 2) * drain)
        
        possible = not wind_fail and hover_sec >= 0 and dist_one_way <= float(specs['range_miles'])
        
        fleet_sim_data.append({
            'ui': drone, 't_out': t_out, 't_hov': hover_sec if possible else 0,
            't_total': (t_out * 2) + (hover_sec if possible else 0),
            'batt_cap': batt_sec, 'possible': possible,
            'fail_msg': "WIND" if wind_fail else "FUEL" if hover_sec < 0 else "RANGE",
            'drain': drain
        })

    valid = [d for d in fleet_sim_data if d['possible']]
    valid.sort(key=lambda x: x['t_total'], reverse=True) 
    
    fastest_t_out = min([d['t_out'] for d in valid]) if valid else 0
    t_drone_arrival = st.session_state.t_launch + timedelta(seconds=fastest_t_out)
    
    for d in fleet_sim_data:
        if d['possible']:
            drone_arrive_dt = st.session_state.t_launch + timedelta(seconds=d['t_out'])
            adv_sec = (st.session_state.t_officers - drone_arrive_dt).total_seconds()
            d['adv_min'] = adv_sec / 60.0
        else:
            d['adv_min'] = 0.0

    for i, d in enumerate(valid):
        if i == 0: d['perf_color'] = color_fastest 
        elif i == 1: d['perf_color'] = color_second 
        else: d['perf_color'] = color_third 

    sim_dur = max([d['t_total'] for d in valid]) if valid else 5
    
    for tick in range(101):
        curr_time = (tick / 100) * sim_dur

        log_events = [
            (st.session_state.t_call, f'<span class="log-{st.session_state.inc_severity}">{st.session_state.inc_type} - TARGET: {dist_one_way:.2f} MI</span>'),
            (st.session_state.t_launch, '<span class="log-action">DRONE LAUNCHED</span>')
        ]
        
        if curr_time >= fastest_t_out and valid:
            log_events.append((t_drone_arrival, '<span class="log-success">DRONE ON SCENE</span>'))

        officer_sec_since_launch = (st.session_state.t_officers - st.session_state.t_launch).total_seconds()
        if curr_time >= officer_sec_since_launch:
            log_events.append((st.session_state.t_officers, '<span class="log-info">OFFICERS ARRIVE</span>'))

        log_events.sort(key=lambda x: x[0])

        log_html = f"""
        <div class="incident-log">
            <div class="log-header">📋 INCIDENT LOG</div>
        """
        for dt, html_str in log_events:
            log_html += f'<div class="log-entry"><span class="log-time">{dt.strftime("%H:%M:%S")}</span>{html_str}</div>'
        
        log_html += "</div>"
        incident_placeholder.markdown(log_html, unsafe_allow_html=True)

        for d in fleet_sim_data:
            ui = d['ui']
            if not d['possible']:
                ui['status_text'].markdown(f":red[**{d['fail_msg']}**]")
                ui['metric_eta'].metric("TIME TO TGT", "N/A")
                ui['metric_adv'].metric("ADVANTAGE", "N/A")
                continue
            
            phase_txt, phase_col, site_time = "", color_phase, 0
            
            if curr_time < d['t_out']:
                phase_txt = ">> OUTBOUND"
                flight_prog = curr_time / d['t_out']
            elif curr_time < (d['t_out'] + d['t_hov']):
                phase_txt, site_time = "ON SCENE", curr_time - d['t_out']
                flight_prog = 1.0
            elif curr_time < d['t_total']:
                phase_txt, site_time = "<< RTB", d['t_hov']
                flight_prog = 1.0 - ((curr_time - d['t_out'] - d['t_hov']) / d['t_out'])
            else:
                phase_txt, phase_col, site_time = "✓ SECURE", d.get('perf_color', color_fastest), d['t_hov']
                flight_prog = 0.0

            ui['status_text'].markdown(f"<span style='color:{phase_col}; font-weight:bold;'>{phase_txt}</span>", unsafe_allow_html=True)
            ui['flight_bar'].progress(max(0.0, min(flight_prog, 1.0)))
            
            ui['metric_eta'].metric("TIME TO TGT", f"{int(d['t_out']/60):02d}:{int(d['t_out']%60):02d}")
            
            if d['adv_min'] > 0:
                adv_str = f"+{d['adv_min']:.1f} MIN"
            else:
                adv_str = f"{d['adv_min']:.1f} MIN"
                
            ui['metric_adv'].metric("ADVANTAGE", adv_str)
            ui['metric_hover'].metric("ON SCENE", f"{int(site_time/60):02d}:{int(site_time%60):02d}")
            
            used = (min(curr_time, d['t_out']) * d['drain']) + max(0, min(curr_time - d['t_out'], d['t_hov'])) + (max(0, min(curr_time - (d['t_out'] + d['t_hov']), d['t_out'])) * d['drain'])
            pct = max(0, 100 - (used / d['batt_cap'] * 100))
            ui['metric_batt'].metric("BATTERY", f"{int(pct)}%")

        time.sleep(0.16)
