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
    div.stVerticalBlock > div { gap: 0.5rem !important; }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.1rem !important;
        color: #ffa500; 
        font-family: 'Consolas', monospace;
        text-shadow: 0px 0px 4px rgba(255, 165, 0, 0.5);
    }
    div[data-testid="stMetricLabel"] { font-size: 0.6rem !important; color: #888; margin-bottom: -5px; }

    .stProgress > div > div { height: 6px !important; }
    .stProgress > div > div > div > div { background-color: #00d4ff; }

    div.stButton > button {
        background-color: #222;
        color: #00d4ff;
        border: 1px solid #00d4ff;
        font-size: 0.8rem;
    }
    
    .stTextInput input, div[data-testid="stKeyup"] input { background-color: #111; color: #fff; border: 1px solid #444; }
    h3 { margin-bottom: 0px !important; padding-bottom: 0px !important; font-size: 1.2rem !important; color: #fff;}
    hr { margin: 0.5em 0 !important; border-color: #333 !important; }

    /* --- INCIDENT LOG CSS --- */
    .incident-log {
        background-color: #111;
        border: 1px solid #333;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 15px;
        font-family: 'Consolas', monospace;
        font-size: 0.85rem;
        min-height: 125px; 
    }
    .log-header { color: #fff; font-size: 0.9rem; border-bottom: 1px solid #333; margin-bottom: 8px; padding-bottom: 4px; font-weight: bold; }
    .log-entry { margin-bottom: 4px; }
    .log-time { color: #888; margin-right: 12px; }
    .log-critical { color: #ff0000; font-weight: bold; }
    .log-action { color: #00ffff; font-weight: bold; }
    .log-success { color: #00ff00; font-weight: bold; }
    .log-info { color: #ffa500; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def load_data():
    try:
        df = pd.read_csv('drones.csv')
        df = df.dropna(subset=['model'])
        df['model'] = df['model'].astype(str)
        df.columns = df.columns.str.strip()
        
        defaults = {'max_wind_mph': 25}
        for col, val in defaults.items():
            if col not in df.columns: df[col] = val
        return df
    except:
        data = {
            'model': ['RESPONDER', 'GUARDIAN', 'SKYDIO X-10', 'MATRICE 4TD'],
            'flight_time_min': [42, 60, 40, 54],
            'speed_mph': [45, 50, 45, 47],
            'range_miles': [5, 12, 7.5, 6.2],
            'max_wind_mph': [28, 42, 28, 26]
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
    if st.session_state.base:
        st.session_state.squad_cars = []
        num_cars = random.randint(3, 5) 
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
    st.session_state.sim_completed = False
    if 't_officers' in st.session_state:
        del st.session_state['t_officers']

def generate_weather():
    st.session_state.wind_speed = random.randint(0, 40)
    st.session_state.wind_dir = random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])

# --- Pre-Calculate Officer Logic ---
best_officer_dist = float('inf')
best_officer_sq = None
officer_travel_sec = 0
t_officer_dispatch = None

if st.session_state.base and st.session_state.target and st.session_state.squad_cars:
    for sq in st.session_state.squad_cars:
        d = get_distance_miles(sq, st.session_state.target)
        if d < best_officer_dist:
            best_officer_dist = d
            best_officer_sq = sq
    
    if best_officer_dist == float('inf'): 
        best_officer_dist = get_distance_miles(st.session_state.base, st.session_state.target)
        best_officer_sq = st.session_state.base

    # Police dispatch assumes 60 seconds after call drops
    if 't_call' in st.session_state:
        t_officer_dispatch = st.session_state.t_call + timedelta(seconds=60)
        officer_travel_sec = (best_officer_dist * 1.4) / (35.0 / 3600.0)
        st.session_state.t_officers = t_officer_dispatch + timedelta(seconds=officer_travel_sec)

# --- Layout ---
left_col, right_col = st.columns([7.5, 2.5])

with right_col:
    st.markdown("### 🚁 OPS CENTER")
    
    if st.session_state.step == 1:
        zip_in = st_keyup("ZIP", placeholder="Enter 5-digit ZIP", label_visibility="collapsed", max_chars=5, key="zip_input")
        if zip_in and len(zip_in) == 5:
            coords = get_lat_lon_from_zip(zip_in)
            if coords:
                st.session_state.map_center = coords
                generate_weather()
                st.session_state.step = 2
                st.rerun()
            else:
                st.error("Invalid ZIP code. Please try again.")

    elif st.session_state.step >= 2:
        bar_c1, bar_c2 = st.columns([2.0, 1.0])
        bar_c1.metric("WIND", f"{st.session_state.wind_speed} {st.session_state.wind_dir}")
        
        # Displays the logo in place of the old reset button
        try:
            bar_c2.image("logo.png", use_container_width=True)
        except:
            pass
        
        st.divider()

        if not st.session_state.base:
            st.warning("📍 SET BASE")
        elif not st.session_state.target:
            st.info("🎯 SET TARGET")
        else:
            incident_placeholder = st.empty()

        if st.session_state.step == 3:
            # --- DRONE FLEET TRACKERS ---
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
    m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles="CartoDB dark_matter")

    if st.session_state.base:
        folium.Marker(st.session_state.base, icon=folium.Icon(color='white', icon='home', prefix='fa')).add_to(m)
        
        rings = [(2, '#00ff00'), (4, '#ffff00'), (6, '#ff9900'), (8, '#cc00ff')]
        for r, c in rings:
            folium.Circle(location=st.session_state.base, radius=r * 1609.34, color=c, weight=2, fill=False, opacity=0.9, dash_array='4, 8').add_to(m)
            lat_offset = (r / 69.0)
            folium.map.Marker([st.session_state.base[0] + lat_offset, st.session_state.base[1]], icon=DivIcon(icon_size=(100,20), icon_anchor=(50,10), html=f'<div style="font-size:10px; font-weight:900; color:{c}; text-shadow: 0 0 5px #000;">{r} MI</div>')).add_to(m)

        is_responding = st.session_state.step == 3 and not st.session_state.sim_completed

        for sq in st.session_state.squad_cars:
            if is_responding and sq == best_officer_sq:
                # The primary dispatched unit flashes aggressive 50/50 Red and Blue
                car_html = """
                <style>
                @keyframes dispatchPulse {
                    0%, 49% { color: #ff0000; text-shadow: 0 0 15px #ff0000; transform: scale(1.3); }
                    50%, 100% { color: #00d4ff; text-shadow: 0 0 15px #00d4ff; transform: scale(1.3); }
                }
                .dispatch-car {
                    animation: dispatchPulse 0.3s infinite;
                    font-size: 24px;
                    z-index: 1000;
                }
                </style>
                <div class="dispatch-car"><i class="fa fa-car"></i></div>
                """
            elif is_responding:
                # Other units show a slow 75/25 pulse
                car_html = """
                <style>
                @keyframes sirenPulse {
                    0%, 75% { color: #00d4ff; text-shadow: 0 0 5px #00d4ff; transform: scale(1); }
                    76%, 100% { color: #ff0000; text-shadow: 0 0 15px #ff0000; transform: scale(1.15); }
                }
                .siren-car {
                    animation: sirenPulse 0.8s infinite;
                    font-size: 18px;
                }
                </style>
                <div class="siren-car"><i class="fa fa-car"></i></div>
                """
            else:
                # Standard fade-in holding pattern
                car_html = """
                <style>
                @keyframes carFadeIn {
                    0% { opacity: 0; transform: scale(0.3); }
                    100% { opacity: 1; transform: scale(1); }
                }
                .fade-car {
                    animation: carFadeIn 2.5s ease-in-out;
                    color: #00d4ff;
                    font-size: 18px;
                    text-shadow: 0 0 5px #000;
                }
                </style>
                <div class="fade-car"><i class="fa fa-car"></i></div>
                """
            folium.Marker(sq, icon=DivIcon(html=car_html)).add_to(m)

    if st.session_state.target:
        folium.Marker(st.session_state.target, icon=folium.Icon(color='red', icon='crosshairs', prefix='fa')).add_to(m)
        
        # Drone straight-line path (Cyan)
        plugins.AntPath(locations=[st.session_state.base, st.session_state.target], color="#00ffff", pulse_color="#ffffff", weight=4, delay=800, dash_array=[10, 20]).add_to(m)
        
        # Officer Code 3 ground path (Red/Blue Dash)
        if st.session_state.step == 3 and not st.session_state.sim_completed and best_officer_sq:
            plugins.AntPath(locations=[best_officer_sq, st.session_state.target], color="#0055ff", pulse_color="#ff0000", weight=4, delay=400, dash_array=[15, 30]).add_to(m)

    map_data = st_folium(m, height=850, use_container_width=True, key="map")

    if map_data['last_clicked']:
        coords = [map_data['last_clicked']['lat'], map_data['last_clicked']['lng']]
        if not st.session_state.base:
            st.session_state.base = coords
            st.session_state.map_zoom = 12 
            randomize_squads() 
            st.session_state.sim_completed = False
            st.rerun()
        elif st.session_state.target != coords:
            st.session_state.target = coords
            generate_weather()
            generate_incident() 
            st.session_state.step = 3
            st.session_state.sim_completed = False
            st.rerun()

# ==========================================
# SIMULATION LOOP OR STATIC RENDER
# ==========================================
if st.session_state.step == 3 and st.session_state.base and st.session_state.target:
    dist_one_way = get_distance_miles(st.session_state.base, st.session_state.target)
    
    fleet_sim_data = []
    for drone in drone_ui_elements:
        specs = drone['specs']
        wind_fail = st.session_state.wind_speed > float(specs['max_wind_mph'])
        max_v = float(specs['speed_mph'])
        
        t_out = dist_one_way / (max_v / 3600)
        batt_sec = float(specs['flight_time_min']) * 60
        hover_sec = (batt_sec * 0.80) - (t_out * 2)
        
        possible = not wind_fail and hover_sec >= 0 and dist_one_way <= float(specs['range_miles'])
        
        fleet_sim_data.append({
            'ui': drone, 't_out': t_out, 't_hov': hover_sec if possible else 0,
            't_total': (t_out * 2) + (hover_sec if possible else 0),
            'batt_cap': batt_sec, 'possible': possible,
            'fail_msg': "WIND" if wind_fail else "FUEL" if hover_sec < 0 else "RANGE"
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
        if i == 0: d['perf_color'] = "#00ff00" 
        elif i == 1: d['perf_color'] = "#ffff00" 
        else: d['perf_color'] = "#ff0000" 

    sim_dur = max([d['t_total'] for d in valid]) if valid else 5
    
    def render_ui_state(curr_time, log_html_override=None):
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

        if log_html_override is None:
            log_html = f"""<div class="incident-log"><div class="log-header">📋 INCIDENT LOG</div>"""
            for dt, html_str in log_events:
                log_html += f'<div class="log-entry"><span class="log-time">{dt.strftime("%H:%M:%S")}</span>{html_str}</div>'
            log_html += "</div>"
        else:
            log_html = log_html_override
            
        incident_placeholder.markdown(log_html, unsafe_allow_html=True)

        # --- Drone Updates ---
        for d in fleet_sim_data:
            ui = d['ui']
            if not d['possible']:
                ui['status_text'].markdown(f":red[**{d['fail_msg']}**]")
                ui['metric_eta'].metric("TIME TO TGT", "N/A")
                ui['metric_adv'].metric("ADVANTAGE", "N/A")
                continue
            
            phase_txt, phase_col, site_time = "", "#00ffff", 0
            
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
                phase_txt, phase_col, site_time = "✓ AT STATION", d.get('perf_color', '#00ff00'), d['t_hov']
                flight_prog = 0.0

            ui['status_text'].markdown(f"<span style='color:{phase_col}; font-weight:bold;'>{phase_txt}</span>", unsafe_allow_html=True)
            ui['flight_bar'].progress(max(0.0, min(flight_prog, 1.0)))
            
            ui['metric_eta'].metric("TIME TO TGT", f"{int(d['t_out']/60):02d}:{int(d['t_out']%60):02d}")
            
            adv_str = f"+{d['adv_min']:.1f} MIN" if d['adv_min'] > 0 else f"{d['adv_min']:.1f} MIN"
            ui['metric_adv'].metric("ADVANTAGE", adv_str)
            ui['metric_hover'].metric("ON SCENE", f"{int(site_time/60):02d}:{int(site_time%60):02d}")
            
            used = min(curr_time, d['t_out']) + max(0, min(curr_time - d['t_out'], d['t_hov'])) + max(0, min(curr_time - (d['t_out'] + d['t_hov']), d['t_out']))
            pct = max(0, 100 - (used / d['batt_cap'] * 100))
            ui['metric_batt'].metric("BATTERY", f"{int(pct)}%")

    if not st.session_state.sim_completed:
        for tick in range(101):
            curr_time = (tick / 100) * sim_dur
            render_ui_state(curr_time)
            time.sleep(0.16)

        time.sleep(3.0) 
        st.session_state.sim_completed = True
        st.rerun()
        
    else:
        render_ui_state(sim_dur)
