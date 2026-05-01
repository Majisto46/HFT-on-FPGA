import serial
import struct
import random
import time
import customtkinter as ctk
from collections import deque

# --- CONFIG ---
COM_PORT = 'COM3'  
BAUD_RATE = 115200
MAX_POINTS = 100
SPEED_MS = 60

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class NativeGraph(ctk.CTkCanvas):
    def __init__(self, master, title, colors, **kwargs):
        super().__init__(master, bg='#2b2b2b', highlightthickness=0, **kwargs)
        self.title = title
        self.colors = colors
        self.bind("<Configure>", self.on_resize)
        self.w = 400
        self.h = 200

    def on_resize(self, event):
        self.w = event.width
        self.h = event.height

    def draw(self, times, data_arrays, fill_bottom=False):
        self.delete("all")
        # Grid
        for i in range(1, 5):
            y = i * self.h / 5
            self.create_line(0, y, self.w, y, fill="#444444", dash=(2, 4))
            
        self.create_text(10, 10, anchor="nw", text=self.title, fill="#ffffff", font=("Consolas", 12))
            
        if not times or not data_arrays or len(times) < 2: return
        
        flat_all = [val for arr in data_arrays for val in arr]
        if not flat_all: return
        min_y, max_y = min(flat_all), max(flat_all)
        if max_y == min_y: max_y += 1; min_y -= 1
        
        y_range = max_y - min_y
        x_range = max(times) - min(times)
        if x_range == 0: x_range = 1

        for idx, arr in enumerate(data_arrays):
            if not arr: continue
            color = self.colors[idx % len(self.colors)]
            pts = []
            for t, val in zip(times, arr):
                x = ((t - min(times)) / x_range) * self.w
                y = self.h - (((val - min_y) / y_range) * self.h)
                pts.extend([x, y])
            if len(pts) >= 4:
                self.create_line(*pts, fill=color, width=2)
                if fill_bottom:
                    poly_pts = [pts[0], self.h] + pts + [pts[-2], self.h]
                    self.create_polygon(*poly_pts, fill=color, stipple='gray50')

class HFTSimulatorMulti(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FPGA Multi-Stock Engine (Native UI)")
        self.geometry("1400x900")
        self.ser = None
        self.connect_serial()

        self.times = deque(maxlen=MAX_POINTS)
        self.prices = [2800.0, 2805.0, 3500.0, 3510.0, 1200.0, 1195.0]
        self.price_data = [deque(maxlen=MAX_POINTS) for _ in range(6)]
        self.pnl_data = deque(maxlen=MAX_POINTS)
        self.pnl = 0.0
        self.pair_states = [0, 0, 0]
        self.start_time = time.time()
        self.counter = 0

        self.setup_ui()
        self.update_data()
        
    def connect_serial(self):
        try:
            self.ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.01)
            self.ser.reset_input_buffer()
            print(f"Connected to FPGA on {COM_PORT}")
        except Exception as e: print(f"Serial Error: {e}")

    def setup_ui(self):
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.pack(fill="x", padx=20, pady=10)
        self.title_lbl = ctk.CTkLabel(self.top_frame, text="MULTI-STOCK FPGA ENGINE", font=ctk.CTkFont("Consolas", 24, "bold"), text_color="#00aaff")
        self.title_lbl.pack(side="left", padx=20, pady=10)
        self.status_lbl = ctk.CTkLabel(self.top_frame, text="🔴 DISCONNECTED" if not self.ser else "🟢 CONNECTED", font=ctk.CTkFont("Consolas", 18, "bold"))
        self.status_lbl.pack(side="right", padx=20, pady=10)

        self.metrics_frame = ctk.CTkFrame(self)
        self.metrics_frame.pack(fill="x", padx=20, pady=0)
        for i in range(4): self.metrics_frame.grid_columnconfigure(i, weight=1)
        
        self.val_prices, self.val_states = [], []
        
        self.val_prices.append(self.create_metric_card(self.metrics_frame, "STOCK 1 (RELIANCE)", 0, 0))
        self.val_prices.append(self.create_metric_card(self.metrics_frame, "STOCK 2 (HDFCBANK)", 0, 1))
        self.val_states.append(self.create_metric_card(self.metrics_frame, "PAIR 1 STATE", 0, 2, color="#aaaaaa"))
        self.val_pnl = self.create_metric_card(self.metrics_frame, "PORTFOLIO PNL", 0, 3, color="#00ff88", rowspan=3)

        self.val_prices.append(self.create_metric_card(self.metrics_frame, "STOCK 3 (TCS)", 1, 0))
        self.val_prices.append(self.create_metric_card(self.metrics_frame, "STOCK 4 (INFY)", 1, 1))
        self.val_states.append(self.create_metric_card(self.metrics_frame, "PAIR 2 STATE", 1, 2, color="#aaaaaa"))

        self.val_prices.append(self.create_metric_card(self.metrics_frame, "STOCK 5 (ITC)", 2, 0))
        self.val_prices.append(self.create_metric_card(self.metrics_frame, "STOCK 6 (SBIN)", 2, 1))
        self.val_states.append(self.create_metric_card(self.metrics_frame, "PAIR 3 STATE", 2, 2, color="#aaaaaa"))

        self.graph_frame = ctk.CTkFrame(self)
        self.graph_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.colors = ['#00aaff', '#0055ff', '#ff8800', '#ff4400', '#00ff88', '#00aa55']
        
        # Native Graphs replace matplotlib
        self.price_graph = NativeGraph(self.graph_frame, "Normalized Portfolio Prices (%)", self.colors)
        self.price_graph.pack(fill="both", expand=True, pady=(0, 5))
        
        self.pnl_graph = NativeGraph(self.graph_frame, "Cumulative PnL (₹)", ['#00ff88'])
        self.pnl_graph.pack(fill="both", expand=True, pady=(5, 0))

    def create_metric_card(self, parent, title, row, col, color="#ffffff", rowspan=1):
        frame = ctk.CTkFrame(parent, corner_radius=10, fg_color="#1a1a1a")
        frame.grid(row=row, column=col, rowspan=rowspan, padx=10, pady=5, sticky="nsew")
        lbl_title = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont("Consolas", 12))
        lbl_title.pack(pady=(10, 0))
        size = 24 if rowspan == 1 else 42
        lbl_val = ctk.CTkLabel(frame, text="0.00", font=ctk.CTkFont("Consolas", size, "bold"), text_color=color)
        lbl_val.pack(pady=(0, 10), expand=True)
        return lbl_val

    def get_fpga_state(self, p1, p2):
        if not self.ser: return 0
        try:
            self.ser.write(struct.pack('>HH', int(p1*10)&0xFFFF, int(p2*10)&0xFFFF))
            raw = self.ser.read(1)
            return struct.unpack('>B', raw)[0] if raw else 0
        except: return 0

    def update_data(self):
        self.counter += 1
        self.times.append(time.time() - self.start_time)
        
        for i in range(6):
            self.prices[i] *= (1 + random.uniform(-0.001, 0.001))
            if self.counter % 40 == 20: self.prices[i] *= random.uniform(1.02, 1.08)
            elif self.counter % 40 == 0: self.prices[i] *= random.uniform(0.92, 0.98)
            self.price_data[i].append(self.prices[i])
            self.val_prices[i].configure(text=f"{self.prices[i]:.2f}", text_color=self.colors[i])

        for pair_idx in range(3):
            state = self.get_fpga_state(self.prices[pair_idx*2], self.prices[pair_idx*2+1])
            status_str, color = "SCANNING", "#aaaaaa"
            if state == 1:
                status_str, color = "BUY EXEC", "#00ffcc"
                self.pnl += 15.0
            elif state == 2:
                status_str, color = "SELL EXEC", "#ff4444"
                self.pnl -= 10.0
            self.val_states[pair_idx].configure(text=status_str, text_color=color)

        self.val_pnl.configure(text=f"₹{self.pnl:.2f}", text_color="#00ff88" if self.pnl >= 0 else "#ff4444")
        self.pnl_data.append(self.pnl)

        # Plot Native Arrays
        normalized = []
        for i in range(6):
            if self.price_data[i]:
                normalized.append([p / self.price_data[i][0] * 100 for p in self.price_data[i]])
                
        self.price_graph.draw(list(self.times), normalized)
        self.pnl_graph.draw(list(self.times), [list(self.pnl_data)], fill_bottom=True)

        self.after(SPEED_MS, self.update_data)

if __name__ == "__main__":
    app = HFTSimulatorMulti()
    app.mainloop()