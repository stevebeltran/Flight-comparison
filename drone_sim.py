with st.popover("🚁 VIEW AIR ASSET COST", use_container_width=True):
                # Wrapped everything in a master div with a black background to prevent Streamlit's white default
                st.markdown(f"""
                <div style="background-color: #050505; padding: 10px; border-radius: 5px;">
                    <div style="text-align: center; margin-bottom: 20px; margin-top: 10px;">
                        <div style="display: inline-block; border: 1px solid rgba(0, 210, 255, 0.3); border-radius: 50%; padding: 4px;">
                            <div style="border: 2px solid rgba(0, 210, 255, 0.6); border-radius: 50%; padding: 6px;">
                                <div style="border: 2px solid #00D2FF; border-radius: 50%; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 10px rgba(0, 210, 255, 0.5);">
                                    <span style="color: #00D2FF; font-weight: bold; font-family: sans-serif; font-size: 16px;">🔗</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <hr style="border-color: #333; margin-bottom: 20px;">
                    
                    <div style="background-color: #000000; border: 1px solid #222; padding: 20px; border-radius: 4px; text-align: center; margin-bottom: 15px;">
                        <h6 style="color: #ffffff; margin: 0; font-size: 0.85rem; letter-spacing: 1px; font-family: 'Manrope', sans-serif;">EST. HELICOPTER COST FOR THIS CALL</h6>
                        <h2 style="color: #00D2FF; margin: 15px 0; font-family: 'IBM Plex Mono', monospace; font-size: 2.5rem;">${heli_cost:.2f}</h2>
                        <div style="color: #797979; font-size: 0.7rem;">BASED ON $850/HR OP COST</div>
                    </div>
                    
                    <div style="border: 1px solid #222; padding: 15px; border-radius: 4px; background-color: #000000; font-family: 'Manrope', sans-serif;">
                        <div style="color: #797979; font-size: 0.9rem; margin-bottom: 8px;">ROUND-TRIP DISTANCE: <span style="color:#ffffff;">{dist * 2:.1f} MI</span></div>
                        <div style="color: #797979; font-size: 0.9rem; margin-bottom: 8px;">CRUISE SPEED: <span style="color:#ffffff;">120 MPH</span></div>
                        <div style="color: #797979; font-size: 0.9rem;">TOTAL FLIGHT TIME (W/ HOVER): <span style="color:#ffffff;">60 MIN</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
