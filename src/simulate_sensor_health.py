"""
AquaGuard AI - Realistic Sensor Health & Status Simulation
Adds sensor operational telemetry columns to both abnormal_consumption.csv and leak_identification.csv.
Adheres strictly to deterministic, continuous, multi-interval outage modeling.
"""

import pandas as pd
import numpy as np
import datetime
import os

RANDOM_SEED = 42

def simulate_sensor_health():
    print("Loading datasets for sensor status enrichment...")
    df_abn = pd.read_csv("data/synthetic/abnormal_consumption.csv")
    df_leak = pd.read_csv("data/synthetic/leak_identification.csv")
    
    df_abn['timestamp'] = pd.to_datetime(df_abn['timestamp'])
    df_leak['timestamp'] = pd.to_datetime(df_leak['timestamp'])
    
    # Sort by meter and timestamp
    df_abn = df_abn.sort_values(['meter_id', 'timestamp']).reset_index(drop=True)
    df_leak = df_leak.sort_values(['meter_id', 'timestamp']).reset_index(drop=True)
    
    n_rows = len(df_abn)
    print(f"Total rows to process: {n_rows:,}")
    
    meters = sorted(df_abn['meter_id'].unique())
    print(f"Meters ({len(meters)}): {meters}")
    
    # Define planned maintenance windows (Scenario E)
    # Meter M04 in ACADEMIC: 2026-08-10 09:00:00 to 2026-08-10 11:30:00 (30 steps)
    # Meter M10 in LIBRARY: 2026-08-20 14:00:00 to 2026-08-20 16:00:00 (24 steps)
    maintenance_windows = [
        {'meter_id': 'M04', 'start': pd.Timestamp('2026-08-10 09:00:00'), 'end': pd.Timestamp('2026-08-10 11:30:00')},
        {'meter_id': 'M10', 'start': pd.Timestamp('2026-08-20 14:00:00'), 'end': pd.Timestamp('2026-08-20 16:00:00')}
    ]
    
    # Define realistic power outage incidents (Scenario B - Power OFF)
    # Continuous outages lasting 4 to 12 steps (20 to 60 minutes)
    power_outages = [
        {'meter_id': 'M01', 'start': pd.Timestamp('2026-07-15 03:15:00'), 'steps': 8}, # 40 min
        {'meter_id': 'M05', 'start': pd.Timestamp('2026-07-22 14:20:00'), 'steps': 10}, # 50 min
        {'meter_id': 'M08', 'start': pd.Timestamp('2026-08-05 22:10:00'), 'steps': 6}, # 30 min
        {'meter_id': 'M12', 'start': pd.Timestamp('2026-09-08 11:05:00'), 'steps': 12}, # 60 min
        {'meter_id': 'M02', 'start': pd.Timestamp('2026-09-18 01:30:00'), 'steps': 7}  # 35 min
    ]
    
    # Define realistic communication failure incidents (Scenario C - Disconnected)
    # Continuous disconnection lasting 3 to 9 steps (15 to 45 minutes)
    comm_outages = [
        {'meter_id': 'M03', 'start': pd.Timestamp('2026-07-08 18:40:00'), 'steps': 5}, # 25 min
        {'meter_id': 'M06', 'start': pd.Timestamp('2026-07-29 07:10:00'), 'steps': 8}, # 40 min
        {'meter_id': 'M09', 'start': pd.Timestamp('2026-08-18 16:00:00'), 'steps': 4}, # 20 min
        {'meter_id': 'M11', 'start': pd.Timestamp('2026-09-02 10:25:00'), 'steps': 6}, # 30 min
        {'meter_id': 'M07', 'start': pd.Timestamp('2026-09-22 04:15:00'), 'steps': 9}  # 45 min
    ]
    
    # Transient single-step dropouts (1 interval missing reading - should NOT trigger alert)
    np.random.seed(RANDOM_SEED)
    transient_drops = [
        {'meter_id': 'M02', 'timestamp': pd.Timestamp('2026-07-12 12:05:00')},
        {'meter_id': 'M04', 'timestamp': pd.Timestamp('2026-07-25 08:30:00')},
        {'meter_id': 'M07', 'timestamp': pd.Timestamp('2026-08-14 19:15:00')},
        {'meter_id': 'M10', 'timestamp': pd.Timestamp('2026-09-05 15:45:00')}
    ]
    
    # Low battery simulation (Scenario F):
    # Meter M11 experiences battery depletion towards end of simulation
    low_battery_start = pd.Timestamp('2026-09-15 00:00:00')
    
    # Pre-build lookup sets
    maint_lookup = set()
    for w in maintenance_windows:
        cur = w['start']
        while cur <= w['end']:
            maint_lookup.add((w['meter_id'], cur))
            cur += pd.Timedelta(minutes=5)
            
    power_off_lookup = set()
    for p in power_outages:
        cur = p['start']
        for _ in range(p['steps']):
            power_off_lookup.add((p['meter_id'], cur))
            cur += pd.Timedelta(minutes=5)
            
    comm_disc_lookup = set()
    for c in comm_outages:
        cur = c['start']
        for _ in range(c['steps']):
            comm_disc_lookup.add((c['meter_id'], cur))
            cur += pd.Timedelta(minutes=5)
            
    transient_lookup = set((t['meter_id'], t['timestamp']) for t in transient_drops)
    
    # Existing sensor events from leak_identification:
    # event_types: sensor_drift, sensor_stuck, sensor_spike, sensor_missing
    leak_sensor_events = {}
    for idx, row in df_leak.dropna(subset=['event_type']).iterrows():
        etype = str(row['event_type'])
        if etype.startswith('sensor_'):
            leak_sensor_events[(row['meter_id'], row['timestamp'])] = etype
            
    print(f"Pre-configured Outage Windows:")
    print(f"  Planned Maintenance steps: {len(maint_lookup)}")
    print(f"  Power OFF outage steps:    {len(power_off_lookup)}")
    print(f"  Communication loss steps:  {len(comm_disc_lookup)}")
    print(f"  Transient glitch steps:    {len(transient_lookup)}")
    print(f"  Existing sensor events:    {len(leak_sensor_events)}")
    
    # Generate sensor columns per meter timeline
    sensor_power = []
    sensor_conn = []
    sensor_health = []
    last_reading_ts = []
    reading_rec = []
    missing_count = []
    battery_pct = []
    sensor_fault = []
    
    # Track state per meter
    # To simulate realistic battery discharge: baseline starts at 98-100%, slowly drops ~0.003% per step
    for m in meters:
        m_mask = (df_abn['meter_id'] == m)
        m_rows = df_abn[m_mask]
        
        last_valid_ts = m_rows['timestamp'].iloc[0]
        cur_missing = 0
        cur_batt = 99.5 if m != 'M11' else 85.0
        
        for _, row in m_rows.iterrows():
            ts = row['timestamp']
            key = (m, ts)
            
            # Battery discharge
            if m == 'M11' and ts >= low_battery_start:
                cur_batt = max(8.0, cur_batt - 0.025) # accelerates into low battery
            else:
                cur_batt = max(15.0, cur_batt - 0.0015)
                
            # Default state: HEALTHY
            p_stat = 'ON'
            c_stat = 'CONNECTED'
            h_stat = 'HEALTHY'
            rec = 1
            f_type = 'NONE'
            
            # Check existing injected sensor fault from leak dataset
            if key in leak_sensor_events:
                raw_etype = leak_sensor_events[key]
                if raw_etype == 'sensor_stuck':
                    f_type = 'SENSOR_STUCK'
                    h_stat = 'FAULTY'
                    rec = 1
                elif raw_etype == 'sensor_drift':
                    f_type = 'SENSOR_DRIFT'
                    h_stat = 'FAULTY'
                    rec = 1
                elif raw_etype == 'sensor_spike':
                    f_type = 'SENSOR_SPIKE'
                    h_stat = 'FAULTY'
                    rec = 1
                elif raw_etype == 'sensor_missing':
                    f_type = 'SENSOR_MISSING'
                    c_stat = 'DISCONNECTED'
                    h_stat = 'OFFLINE'
                    rec = 0
            
            # Check scenarios (Maintenance takes precedence)
            if key in maint_lookup:
                p_stat = 'OFF'
                c_stat = 'DISCONNECTED'
                h_stat = 'MAINTENANCE'
                rec = 0
                f_type = 'NONE'
            elif key in power_off_lookup:
                p_stat = 'OFF'
                c_stat = 'DISCONNECTED'
                h_stat = 'OFFLINE'
                rec = 0
                f_type = 'NONE'
            elif key in comm_disc_lookup:
                p_stat = 'ON'
                c_stat = 'DISCONNECTED'
                h_stat = 'OFFLINE'
                rec = 0
                f_type = 'NONE'
            elif key in transient_lookup:
                p_stat = 'ON'
                c_stat = 'CONNECTED'
                h_stat = 'WARNING'
                rec = 0
                f_type = 'NONE'
            elif cur_batt <= 20.0 and h_stat == 'HEALTHY':
                h_stat = 'WARNING'
                
            # Update reading received & consecutive missing counter
            if rec == 1:
                cur_missing = 0
                last_valid_ts = ts
            else:
                cur_missing += 1
                if cur_missing >= 2 and h_stat not in ['MAINTENANCE', 'FAULTY']:
                    # Reclassify to WARNING at 2, OFFLINE at 3+
                    if cur_missing == 2 and h_stat != 'OFFLINE':
                        h_stat = 'WARNING'
                    else:
                        h_stat = 'OFFLINE'
                        
            sensor_power.append(p_stat)
            sensor_conn.append(c_stat)
            sensor_health.append(h_stat)
            last_reading_ts.append(last_valid_ts.strftime('%Y-%m-%d %H:%M:%S'))
            reading_rec.append(rec)
            missing_count.append(cur_missing)
            battery_pct.append(round(cur_batt, 1))
            sensor_fault.append(f_type)
            
    print("Assigning enriched columns to abnormal_consumption...")
    df_abn['sensor_power_status'] = sensor_power
    df_abn['sensor_connectivity_status'] = sensor_conn
    df_abn['sensor_health_status'] = sensor_health
    df_abn['last_reading_timestamp'] = last_reading_ts
    df_abn['reading_received'] = reading_rec
    df_abn['missing_reading_count'] = missing_count
    df_abn['sensor_battery_pct'] = battery_pct
    df_abn['sensor_fault_type'] = sensor_fault
    
    print("Assigning enriched columns to leak_identification...")
    df_leak['sensor_power_status'] = sensor_power
    df_leak['sensor_connectivity_status'] = sensor_conn
    df_leak['sensor_health_status'] = sensor_health
    df_leak['last_reading_timestamp'] = last_reading_ts
    df_leak['reading_received'] = reading_rec
    df_leak['missing_reading_count'] = missing_count
    df_leak['sensor_battery_pct'] = battery_pct
    df_leak['sensor_fault_type'] = sensor_fault
    
    # Crucial Requirement: Missing readings MUST be represented as NaN, NEVER zero!
    # In abnormal_consumption, when reading_received == 0, interval_consumption_liters is NaN
    missing_mask = (df_abn['reading_received'] == 0)
    df_abn.loc[missing_mask, 'interval_consumption_liters'] = np.nan
    
    # In leak_identification, when reading_received == 0:
    # If power is OFF or communication is lost, telemetry measurements become unavailable (NaN)
    df_leak.loc[missing_mask, 'inlet_flow_lpm'] = np.nan
    df_leak.loc[missing_mask, 'pressure_bar'] = np.nan
    
    print("\\n--- Sensor Status Summary in Abnormal Dataset ---")
    print(df_abn['sensor_health_status'].value_counts())
    print("\\n--- Sensor Fault Type Summary ---")
    print(df_abn['sensor_fault_type'].value_counts())
    print("\\n--- Missing Reading Counts Distribution ---")
    print(df_abn['missing_reading_count'].value_counts().head(10))
    
    # Save back to both data/synthetic and dataset/ without altering original filenames
    print("\\nWriting enriched datasets to data/synthetic/ and dataset/...")
    df_abn.to_csv("data/synthetic/abnormal_consumption.csv", index=False)
    df_leak.to_csv("data/synthetic/leak_identification.csv", index=False)
    
    # Also sync dataset/ folder if it exists as physical files
    if os.path.exists("dataset/abnormal_consumption.csv"):
        df_abn.to_csv("dataset/abnormal_consumption.csv", index=False)
    if os.path.exists("dataset/leak_identification.csv"):
        df_leak.to_csv("dataset/leak_identification.csv", index=False)
        
    print("Datasets enriched and saved successfully!")

if __name__ == '__main__':
    simulate_sensor_health()
