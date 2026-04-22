"""
===============================================================================
Project: Smart Logistics Dispatch Automation (RPA)
Description: A desktop application using Tkinter, Pandas, and Playwright to 
             automate the sorting, prioritization, and dispatching of Last-Mile 
             delivery routes into specific operational waves.
Author: Fabio Lessa (Portfolio Version)
Note: URLs, UI selectors, and specific business rules have been anonymized 
      or generalized to comply with NDAs. This is for demonstration purposes.
===============================================================================
"""

import os
import re
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import pandas as pd
from playwright.sync_api import sync_playwright
import threading
import time
from datetime import datetime, timedelta

class LogisticsDispatchBot:
    def __init__(self, root):
        self.root = root
        self.root.title("Logistics Dispatch AutoBot - Portfolio Version")
        self.root.geometry("950x750")
        
        self.file_path = tk.StringVar()
        self.available_waves = [3, 4, 5, 6, 7, 8] 
        # ANONYMIZED URL AND HUB PREFIX
        self.system_url = 'https://example-logistics-erp.com/dispatch-tools'
        self.hub_prefix = "HUB-01" 
        
        self._create_ui()

    def _create_ui(self):
        # 1. Configuration Frame
        frame_top = tk.LabelFrame(self.root, text="1. Configuration", padx=10, pady=10)
        frame_top.pack(fill="x", padx=10, pady=5)
        
        tk.Button(frame_top, text="Select Route CSV", command=self.select_file, bg="#e0e0e0", height=2).pack(side="left", padx=5)
        tk.Label(frame_top, textvariable=self.file_path, fg="blue").pack(side="left", padx=10)

        # 2. Priority Rules Frame
        frame_info = tk.LabelFrame(self.root, text="2. Priority Rules Engine", padx=10, pady=10, fg="blue")
        frame_info.pack(fill="x", padx=10, pady=5)
        
        rules_text = (
            "Priority 1: Fleet Type (Large Van, Dedicated)\n"
            "Priority 2: Special Handling required\n"
            "Priority 3: Extra Capacity requests\n"
            "Priority 4: Long Distance (> 135 km)"
        )
        tk.Label(frame_info, text=rules_text, justify="left", font=("Arial", 9, "bold")).pack(anchor="w")

        # 3. Log/Monitoring Frame
        frame_log = tk.LabelFrame(self.root, text="Bot Monitoring Logs", padx=10, pady=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.txt_log = scrolledtext.ScrolledText(frame_log, height=15, font=("Consolas", 10))
        self.txt_log.pack(fill="both", expand=True)

        tk.Button(self.root, text="START AUTOMATION", command=self.start_thread, 
                  bg="#ffe600", fg="black", font=("Arial", 12, "bold"), height=2).pack(fill="x", padx=10, pady=10)

    def log_message(self, message):
        """Appends timestamped messages to the GUI log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.txt_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.txt_log.see(tk.END)

    def select_file(self):
        file = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if file: self.file_path.set(file)

    def clean_route_name(self, value):
        if pd.isna(value): return ""
        text = str(value)
        if "_" in text: return text.split('_')[0].strip()
        return text.strip()

    def calculate_priority(self, row):
        """Business logic to rank routes based on operational constraints."""
        vehicle_profile = str(row.get('VEHICLE_PROFILE', '')).upper()
        notes = str(row.get('NOTES', '')).upper()
        route_type = str(row.get('TYPE', '')).upper()
        try: dist = float(row.get('DISTANCE', 0))
        except: dist = 0

        # Generalized vehicle types
        priority_vehicles = ["VUC", "LARGE VAN", "DEDICATED FLEET"]
        for term in priority_vehicles:
            if term in vehicle_profile: return 0  
            
        if "SPECIAL" in notes: return 1
        if "EXTRA" in route_type: return 2
        if dist > 135: return 3
        
        return 4

    def get_target_date_string(self):
        """Generates dynamic date strings for UI interaction."""
        tomorrow = datetime.now() + timedelta(days=1)
        months = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 
                 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
        return f"{self.hub_prefix} | {tomorrow.day} {months[tomorrow.month]}"

    def smart_csv_reader(self, path):
        """Attempts multiple encodings and separators to parse the dispatch file safely."""
        attempts = [
            {'sep': ';', 'encoding': 'latin1'},
            {'sep': ',', 'encoding': 'utf-8-sig'},
            {'sep': ',', 'encoding': 'latin1'}
        ]
        for params in attempts:
            try:
                df = pd.read_csv(path, sep=params['sep'], encoding=params['encoding'])
                if 'Route' in df.columns: return df
            except: continue
        return None

    def start_thread(self):
        if not self.file_path.get():
            messagebox.showwarning("Error", "Please select a CSV file first!")
            return
        threading.Thread(target=self.execute_bot).start()

    def execute_bot(self):
        file_path = self.file_path.get()
        self.log_message("--- STARTING INITIALIZATION ---")
        
        try:
            # 1. Data Processing with Pandas
            df = self.smart_csv_reader(file_path)
            if df is None: 
                self.log_message("❌ Error: Invalid CSV format or missing 'Route' column.")
                return

            df.columns = df.columns.str.strip()
            df['Clean_Route'] = df['Route'].apply(self.clean_route_name)
            df['Priority_Rank'] = df.apply(self.calculate_priority, axis=1)
            
            # Sort by Rank (Ascending) and Distance (Descending)
            queue = df.sort_values(by=['Priority_Rank', 'DISTANCE'], ascending=[True, False]).reset_index(drop=True)
            
            total_routes = len(queue)
            num_waves = len(self.available_waves)
            
            # Distribute routes evenly across available waves
            base_alloc = total_routes // num_waves
            remainder = total_routes % num_waves
            
            distribution = [base_alloc + 1 if i < remainder else base_alloc for i in range(num_waves)]
            
            self.log_message(f"Wave Planning Setup:")
            for i, qty in enumerate(distribution):
                self.log_message(f" -> Wave {self.available_waves[i]}: {qty} routes")
            
            queue['Target_Wave'] = 0
            cursor = 0
            for i, qty in enumerate(distribution):
                wave_num = self.available_waves[i]
                queue.loc[cursor : cursor + qty - 1, 'Target_Wave'] = wave_num
                cursor += qty
                
        except Exception as e:
            self.log_message(f"Data Processing Error: {e}")
            return

        # 2. Web Automation with Playwright
        try:
            with sync_playwright() as p:
                session_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_session")
                if not os.path.exists(session_folder): os.makedirs(session_folder)

                self.log_message("Connecting to Chrome Browser instance...")
                
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=session_folder,
                    channel="chrome", 
                    headless=False,
                    args=["--start-maximized"]
                )
                
                page = browser.pages[0]
                page.goto(self.system_url)
                
                messagebox.showinfo("Action Required", "1. Login to ERP.\n2. Confirm Date.\n3. Click OK to start bot.")
                
                # Note: UI Selectors below are generalized for portfolio display.
                # In production, specific DOM elements or test-ids would be used.
                
                for i, row in queue.iterrows():
                    route = row['Clean_Route']
                    target_wave = int(row['Target_Wave'])
                    wave_name = f"Wave {target_wave}"
                    rank = row['Priority_Rank']
                    
                    reasons = {0: "💎 Fleet", 1: "🚨 Special", 2: "⭐ Extra", 3: "🚚 Long Dist", 4: "Standard"}
                    reason_txt = reasons.get(rank, "Standard")

                    self.log_message(f"[{i+1}/{total_routes}] Mapping {route} -> {wave_name} ({reason_txt})")

                    try:
                        # Attempt to locate route in UI
                        el = page.get_by_text(route, exact=True).first
                        if el.is_visible():
                            el.click()
                            time.sleep(0.3)
                            
                            # Click Move/Dispatch button
                            btn_move = page.get_by_role("button", name="Move Route")
                            if btn_move.is_visible():
                                btn_move.click()
                                time.sleep(1.0)
                                
                                # Modal interaction logic simplified for portfolio context...
                                # (Code simulates selecting the wave, checking capacity, and confirming)
                                self.log_message("✅ Dispatched successfully.")
                            else:
                                self.log_message("⚠️ Dispatch button unavailable.")
                                page.keyboard.press("Escape")
                        else:
                            self.log_message("❌ Route not found in current UI view.")
                    except Exception as e:
                        self.log_message(f"UI Interaction Error: {e}")
                        page.keyboard.press("Escape")
                        time.sleep(0.5)

                self.log_message("--- AUTOMATION COMPLETED ---")
                messagebox.showinfo("Done", "All routes have been processed!")
                browser.close()

        except Exception as e:
            self.log_message(f"FATAL ERROR: {e}")
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = LogisticsDispatchBot(root)
    root.mainloop()
