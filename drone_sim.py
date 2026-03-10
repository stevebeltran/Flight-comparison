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
if 'inc_type' not in st.session_state: st.session_state.inc_type = None
if 'squad_cars' not in st.session_state: st.session_state.squad_cars = []
if 'sim_completed' not in st.session_state: st.session_state.sim_completed = False
if 'has_run_once' not in st.session_state: st.session_state.has_run_once = False

# --- CUSTOM CSS: CLEAN COCKPIT THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=Manrope:wght@400;600;700&display=swap');

    header[data-testid="stHeader"] { display: none; }
    
    /* Global Typography & Colors */
    .stApp { 
        background-color: #050505 !important; 
        color: #797979; 
        font-family: 'Manrope', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 { 
        color: #ffffff !important; 
        font-family: 'Manrope', sans-serif;
        margin-bottom: 0px !important; 
        padding-bottom: 0px !important; 
    }
    
    h3 { font-size: 1.2rem !important; }
    
    .block-container { padding-top: 3rem !important; padding-bottom: 1rem !important; }
    div.stVerticalBlock > div { gap: 0.5rem !important; }
    
    /* Metrics */
    div[data-testid="stMetricValue"] {
        font-size: 1.1rem !important;
        color: #00D2FF; 
        font-family: 'IBM Plex Mono', monospace;
    }
    div[data-testid="stMetricLabel"] { 
        font-size: 0.6rem !important; 
        color: #797979; 
        margin-bottom: -5px; 
    }

    .stProgress > div > div { height: 6px !important; }
    .stProgress > div > div > div > div { background-color: #00D2FF; }

    div.stButton > button, div[data-testid="stPopover"] > button {
        background-color: #111;
        color: #ffffff;
        border: 1px solid #444;
        font-size: 0.8rem;
        font-family: 'Manrope', sans-serif;
    }
    div.stButton > button:hover, div[data-testid="stPopover"] > button:hover {
        border-color: #00D2FF;
        color: #00D2FF;
    }
    
    /* Input Styling */
    .stTextInput input, div[data-testid="stKeyup"] input { 
        background-color: #111 !important; 
        color: #ffffff !important; 
        border: 1px solid #444 !important; 
        font-family: 'IBM Plex Mono', monospace;
    }
    div[data-testid="stKeyup"] input {
        height: 24px !important;
        min-height: 24px !important;
        padding: 2px 8px !important;
        font-size: 0.85rem !important;
    }

    hr { margin: 0.5em 0 !important; border-color: #333 !important; }

    /* --- DRONE NAME PULSE (BRINC BLUE) --- */
    @keyframes dronePulse {
        0%, 49% { color: #797979; text-shadow: none; }
        50%, 100% { color: #00D2FF; text-shadow: 0 0 10px #00D2FF; }
    }
    .drone-active { animation: dronePulse 0.8s infinite; font-weight: bold; font-family: 'IBM Plex Mono', monospace; }
    .drone-static { color: #ffffff; font-weight: bold; text-shadow: none; font-family: 'IBM Plex Mono', monospace; }

    /* --- INCIDENT LOG CSS --- */
    .incident-log {
        background-color: #111;
        border: 1px solid #333;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 15px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        min-height: 125px; 
    }
    .log-header { color: #ffffff; font-size: 0.9rem; border-bottom: 1px solid #333; margin-bottom: 8px; padding-bottom: 4px; font-weight: bold; }
    .log-entry { margin-bottom: 4px; color: #797979; }
    .log-time { color: #797979; margin-right: 12px; }
    
    /* Muted Log Colors */
    .log-critical { color: #ffffff; font-weight: bold; }
    .log-action { color: #00D2FF; font-weight: bold; }
    .log-success { color: #00D2FF; font-weight: bold; }
    .log-info { color: #797979; font-weight: normal; }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def load_data():
    try:
        df = pd.read_csv('drones.csv')
        df = df.dropna(subset=['model'])
        df['model'] = df['model'].astype(str)
        df.columns = df.columns.str.strip()
        return df
    except:
        # Fallback dictionary with updated Cruise Speeds
        data = {
            'model': ['RESPONDER', 'GUARDIAN', 'SKYDIO X-10', 'MATRICE 4TD'],
            'flight_time_min': [42, 60, 40, 54],
            'speed_mph': [22, 30, 36, 34],
            'range_miles': [5.0, 12.0, 7.5, 6.2]
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
    if 't_officers' in st.session_state: del st.session_state['t_officers']

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

    if 't_call' in st.session_state:
        t_officer_dispatch = st.session_state.t_call + timedelta(seconds=60)
        officer_travel_sec = (best_officer_dist * 1.4) / (35.0 / 3600.0)
        st.session_state.t_officers = t_officer_dispatch + timedelta(seconds=officer_travel_sec)

# --- Layout: Dynamic Columns ---
left_col, mid_col = st.columns([7, 3])

# ==========================================
# COLUMN 2: OPS CENTER & BUDGET BUTTON
# ==========================================
with mid_col:
    # Top Actions Area
    if st.session_state.has_run_once:
        with st.popover("💰 VIEW BUDGET IMPACT", use_container_width=True):
            st.markdown("### BUDGET IMPACT")
            st.divider()
            
            calls_per_day = st.slider("ESTIMATED DAILY CALLS", min_value=1, max_value=100, value=20)
            cost_officer = 82
            cost_drone = 6
            savings_per_call = cost_officer - cost_drone
            
            st.markdown(f"""
            <div style="background: rgba(0, 210, 255, 0.05); border: 1px solid #00D2FF; padding: 15px; border-radius: 4px; text-align: center; margin-bottom: 15px; box-shadow: 0px 0px 10px rgba(0, 212, 255, 0.1);">
                <h6 style="color: #00D2FF; margin: 0; font-size: 0.8rem; letter-spacing: 1px; font-family: 'Manrope', sans-serif;">ANNUAL TAXPAYER SAVINGS</h6>
                <h2 style="color: #00D2FF; margin: 0; font-family: 'IBM Plex Mono', monospace;">$554,800</h2>
            </div>
            """, unsafe_allow_html=True)
            
            be_resp = 80000 / (savings_per_call * calls_per_day * 30.4)
            st.markdown(f"""
            <div style="border: 1px solid #333; padding: 10px; border-radius: 4px; margin-bottom: 10px; background: #050505; font-family: 'Manrope', sans-serif;">
                <h5 style="color: #ffffff; margin: 0; margin-bottom: 4px;">RESPONDER</h5>
                <div style="color: #797979; font-size: 0.85rem;">COVERAGE: <span style="color:#ffffff;">5 MI RADIUS</span></div>
                <div style="color: #797979; font-size: 0.85rem;">UNIT CAPEX: <span style="color:#ffffff;">$80,000</span></div>
                <div style="color: #797979; font-size: 0.85rem;">BREAK-EVEN: <span style="color:#00D2FF; font-weight:bold;">{be_resp:.1f} MONTHS</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            be_guard = 160000 / (savings_per_call * calls_per_day * 30.4)
            st.markdown(f"""
            <div style="border: 1px solid #333; padding: 10px; border-radius: 4px; margin-bottom: 10px; background: #050505; font-family: 'Manrope', sans-serif;">
                <h5 style="color: #ffffff; margin: 0; margin-bottom: 4px;">GUARDIAN</h5>
                <div style="color: #797979; font-size: 0.85rem;">COVERAGE: <span style="color:#ffffff;">12 MI RADIUS</span></div>
                <div style="color: #797979; font-size: 0.85rem;">UNIT CAPEX: <span style="color:#ffffff;">$160,000</span></div>
                <div style="color: #797979; font-size: 0.85rem;">BREAK-EVEN: <span style="color:#00D2FF; font-weight:bold;">{be_guard:.1f} MONTHS</span></div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔄 RESET SCENARIO", use_container_width=True):
                st.session_state.target = None
                st.session_state.sim_completed = False
                st.session_state.has_run_once = False 
                st.session_state.step = 2
                st.rerun()

    st.markdown("### 🚁 OPS CENTER")
    
    if st.session_state.step == 1:
        zip_col, space_col, logo_col = st.columns([1, 1, 2])
        with zip_col:
            zip_in = st_keyup("ZIP", placeholder="ZIP", label_visibility="collapsed", max_chars=5, key="zip_input")
        with logo_col:
            st.image("logo.png", use_container_width=True)
            
        if zip_in and len(zip_in) == 5:
            coords = get_lat_lon_from_zip(zip_in)
            if coords:
                st.session_state.map_center = coords
                st.session_state.step = 2
                st.rerun()
            else:
                st.error("Invalid ZIP code.")

    elif st.session_state.step >= 2:
        _col1, _col2, logo_col = st.columns([1, 1, 2])
        with logo_col:
            st.image("logo.png", use_container_width=True)
        
        st.divider()

        if not st.session_state.base:
            st.warning("📍 SET BASE")
        elif not st.session_state.target:
            st.info("🎯 SET TARGET")
        else:
            incident_placeholder = st.empty()

        if st.session_state.step == 3:
            df = load_data()
            drone_ui_elements = [] 
            for index, row in df.iterrows():
                with st.container():
                    head_c1, head_c2 = st.columns([1.8, 1])
                    name_placeholder = head_c1.empty()
                    name_placeholder.markdown(f"<span class='drone-static'>{row['model']}</span>", unsafe_allow_html=True)
                    status_placeholder = head_c2.empty()
                    
                    m1, m2, m3, m4 = st.columns(4)
                    ui_obj = {
                        'specs': row,
                        'name_text': name_placeholder,
                        'status_text': status_placeholder,
                        'flight_bar': st.progress(0),
                        'metric_hover': m1.empty(), 
                        'metric_eta': m2.empty(),   
                        'metric_adv': m3.empty(), 
                        'metric_batt': m4.empty(),  
                    }
                    drone_ui_elements.append(ui_obj)
                    st.divider()

# ==========================================
# COLUMN 1: MAP
# ==========================================
with left_col:
    m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles="CartoDB dark_matter")

    if st.session_state.base:
        # Changed Base icon to Custom DivIcon (Brinc Blue)
        base_html = """
        <div style="color: #00D2FF; font-size: 24px; text-shadow: 0 0 5px #000;">
            <i class="fa fa-home"></i>
        </div>
        """
        folium.Marker(st.session_state.base, icon=DivIcon(html=base_html, icon_anchor=(10,10))).add_to(m)
        
        rings = [(2, '#00D2FF'), (4, '#ffffff'), (6, '#797979'), (8, '#444444')]
        for r, c in rings:
            folium.Circle(location=st.session_state.base, radius=r * 1609.34, color=c, weight=1, fill=False, opacity=0.5, dash_array='4, 8').add_to(m)
            lat_offset = (r / 69.0)
            folium.map.Marker([st.session_state.base[0] + lat_offset, st.session_state.base[1]], icon=DivIcon(icon_size=(100,20), icon_anchor=(50,10), html=f'<div style="font-family: \'Manrope\', sans-serif; font-size:10px; font-weight:600; color:{c}; text-shadow: 0 0 5px #000;">{r} MI</div>')).add_to(m)

        is_responding = st.session_state.step == 3 and not st.session_state.sim_completed

        for sq in st.session_state.squad_cars:
            if is_responding:
                # Active responding car turns Red, remaining idle cars stay Brinc Blue
                car_color = "#FF0000" if sq == best_officer_sq else "#00D2FF"
            else:
                # All idle cars start Brinc Blue
                car_color = "#00D2FF"

            car_html = f"""
            <div style="color: {car_color}; font-size: 18px; text-shadow: 0 0 5px #000;">
                <i class="fa fa-car"></i>
            </div>
            """
            folium.Marker(sq, icon=DivIcon(html=car_html)).add_to(m)

    if st.session_state.target:
        # Changed Target icon to Custom DivIcon (Red)
        target_html = """
        <div style="color: #FF0000; font-size: 24px; text-shadow: 0 0 5px #000;">
            <i class="fa fa-crosshairs"></i>
        </div>
        """
        folium.Marker(st.session_state.target, icon=DivIcon(html=target_html, icon_anchor=(10,10))).add_to(m)
        
        plugins.AntPath(locations=[st.session_state.base, st.session_state.target], color="#00D2FF", pulse_color="#ffffff", weight=3, delay=800, dash_array=[10, 20]).add_to(m)
        
        if st.session_state.step == 3 and not st.session_state.sim_completed and best_officer_sq:
            # Responding Car Path is also Red
            plugins.AntPath(locations=[best_officer_sq, st.session_state.target], color="#FF0000", pulse_color="#ffffff", weight=3, delay=400, dash_array=[15, 30]).add_to(m)

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
        max_v = float(specs['speed_mph'])
        
        t_out = dist_one_way / (max_v / 3600)
        batt_sec = float(specs['flight_time_min']) * 60
        hover_sec = (batt_sec * 0.80) - (t_out * 2)
        
        possible = hover_sec >= 0 and dist_one_way <= float(specs['range_miles'])
        
        fleet_sim_data.append({
            'ui': drone, 't_out': t_out, 't_hov': hover_sec if possible else 0,
            't_total': (t_out * 2) + (hover_sec if possible else 0),
            'batt_cap': batt_sec, 'possible': possible,
            'fail_msg': "FUEL" if hover_sec < 0 else "RANGE"
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
        if i == 0: d['perf_color'] = "#00D2FF" 
        elif i == 1: d['perf_color'] = "#ffffff" 
        else: d['perf_color'] = "#797979" 

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

        for d in fleet_sim_data:
            ui = d['ui']
            if not d['possible']:
                ui['status_text'].markdown(f"<span style='color:#797979; font-weight:bold;'>{d['fail_msg']}</span>", unsafe_allow_html=True)
                ui['metric_eta'].metric("TIME TO TGT", "N/A")
                ui['metric_adv'].metric("ADVANTAGE", "N/A")
                ui['name_text'].markdown(f"<span class='drone-static'>{ui['specs']['model']}</span>", unsafe_allow_html=True)
                continue
            
            phase_txt, phase_col, site_time = "", "#00D2FF", 0
            is_active = False
            
            if curr_time < d['t_out']:
                phase_txt = ">> OUTBOUND"
                flight_prog = curr_time / d['t_out']
                is_active = True
            elif curr_time < (d['t_out'] + d['t_hov']):
                phase_txt, site_time = "ON SCENE", curr_time - d['t_out']
                flight_prog = 1.0
                is_active = True
            elif curr_time < d['t_total']:
                phase_txt, site_time = "<< RTB", d['t_hov']
                flight_prog = 1.0 - ((curr_time - d['t_out'] - d['t_hov']) / d['t_out'])
                is_active = True
            else:
                phase_txt, phase_col, site_time = "✓ AT STATION", d.get('perf_color', '#ffffff'), d['t_hov']
                flight_prog = 0.0
                is_active = False

            name_class = "drone-active" if is_active else "drone-static"
            ui['name_text'].markdown(f"<span class='{name_class}'>{ui['specs']['model']}</span>", unsafe_allow_html=True)

            ui['status_text'].markdown(f"<span style='color:{phase_col}; font-weight:bold; font-family: \"IBM Plex Mono\", monospace;'>{phase_txt}</span>", unsafe_allow_html=True)
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
        st.session_state.has_run_once = True 
        randomize_squads() 
        st.rerun()
        
    else:
        render_ui_state(sim_dur)
