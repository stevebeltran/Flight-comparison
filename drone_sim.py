# Column 1: TIME TO TGT (Always stays the same)
            eta_label = "TIME TO TGT"
            display_time = min(curr_time, d['t_out'])
            eta_val = f"{int(display_time/60):02d}:{int(display_time%60):02d}"
            
            # Column 2: ON SCENE
            hov_val = f"{int(site_time/60):02d}:{int(site_time%60):02d}"
            
            # Column 3: BATTERY (Swaps to RECHARGE when landed)
            pct = max(0, 100 - (used / d['batt_cap'] * 100))
            if is_rtb_complete:
                mission_progress = used / d['t_total'] if d['t_total'] > 0 else 0
                current_recharge_min = d['turnaround_min'] * mission_progress
                t_min = int(current_recharge_min)
                t_sec = int((current_recharge_min * 60) % 60)
                bat_label = "<span style='color: #ffffff;'>RECHARGE</span>"
                bat_val = f"{t_min:02d}m {t_sec:02d}s"
            else:
                bat_label = "BATTERY"
                bat_val = f"{int(pct)}%"
