# ... (rest of your existing code above) ...
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
        
        # ==========================================
        # FINANCIAL IMPACT CALCULATOR
        # ==========================================
        with right_col:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 💰 BUDGET IMPACT ANALYSIS")
            st.divider()
            
            # Interactive slider for stakeholders
            calls_per_day = st.slider("ESTIMATED DAILY CALLS (AT THIS RANGE)", min_value=1, max_value=100, value=10)
            
            # Fixed Costs
            cost_officer = 82
            cost_drone = 6
            savings_per_call = cost_officer - cost_drone
            annual_savings = savings_per_call * calls_per_day * 365
            
            # Sub-metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("SQUAD CAR", f"${cost_officer}")
            c2.metric("DRONE", f"${cost_drone}")
            c3.metric("SAVINGS/CALL", f"${savings_per_call}")
            
            # High-visibility Tactical ROI Output
            st.markdown(f"""
            <div style="
                background: rgba(0, 255, 0, 0.05); 
                border: 1px solid #00ff00; 
                box-shadow: 0px 0px 10px rgba(0, 255, 0, 0.2);
                padding: 15px; 
                border-radius: 4px; 
                text-align: center; 
                margin-top: 15px;">
                <h6 style="color: #888; margin: 0; font-size: 0.8rem; letter-spacing: 1px;">PROJECTED ANNUAL TAXPAYER SAVINGS</h6>
                <h1 style="color: #00ff00; margin: 0; font-family: 'Consolas', monospace; text-shadow: 0 0 10px rgba(0,255,0,0.5);">
                    ${annual_savings:,.0f}
                </h1>
            </div>
            """, unsafe_allow_html=True)
            
            # Optional Reset Button to clear the map and start a new scenario
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔄 RESET SIMULATION", use_container_width=True):
                st.session_state.target = None
                st.session_state.sim_completed = False
                st.session_state.step = 2
                st.rerun()
