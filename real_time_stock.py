import serial
import struct
import time
import customtkinter as ctk
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
import threading

# --- CONFIG ---
COM_PORT = 'COM3' 
BAUD_RATE = 115200

# Top 6 NSE Stocks organized into 3 Trading Pairs
TICKERS = ["RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "INFY.NS", "ITC.NS", "SBIN.NS"]
MAX_POINTS = 50
SPEED_MS = 3000 # Wait 3 seconds between API requests due to heavy load

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class HFTRealMarketDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FPGA Multi-Stock HFT Dashboard - LIVE NSE")
        self.geometry("1400x900")
        
        # Serial Init
        self.ser = None
        self.connect_serial()

        # Buffers & States
        self.times = deque(maxlen=MAX_POINTS)
        self.prices = [0.0] * 6
        self.price_data = [deque(maxlen=MAX_POINTS) for _ in range(6)]
        self.pnl_data = deque(maxlen=MAX_POINTS)
        self.pnl = 0.0
        self.pair_states = [0, 0, 0]
        
        self.start_time = time.time()
        self.colors = ['#00eeff', '#0088ff', '#ff8800', '#ff4400', '#00ff88', '#00aa55']

        self.setup_ui()
        self.update_data()
        
    def connect_serial(self):
        try:
            self.ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.01)
            self.ser.reset_input_buffer()
            print(f"Connected to FPGA on {COM_PORT}")
        except Exception as e:
            print(f"Serial Error: {e}")

    def setup_ui(self):
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.pack(fill="x", padx=20, pady=10)
        
        self.title_lbl = ctk.CTkLabel(self.top_frame, text="LIVE NSE MULTI-STOCK ENGINE", font=ctk.CTkFont(family="Consolas", size=24, weight="bold"), text_color="#00eeff")
        self.title_lbl.pack(side="left", padx=20, pady=10)
        
        self.status_lbl = ctk.CTkLabel(self.top_frame, text="🔴 DISCONNECTED" if not self.ser else "🟢 CONNECTED", font=ctk.CTkFont(family="Consolas", size=18, weight="bold"))
        self.status_lbl.pack(side="right", padx=20, pady=10)

        # Metrics Panel
        self.metrics_frame = ctk.CTkFrame(self)
        self.metrics_frame.pack(fill="x", padx=20, pady=0)
        for i in range(4): self.metrics_frame.grid_columnconfigure(i, weight=1)
        
        self.val_prices = []
        self.val_states = []
        
        # Row 0: Pair 1
        self.val_prices.append(self.create_metric_card(self.metrics_frame, TICKERS[0], 0, 0, color=self.colors[0]))
        self.val_prices.append(self.create_metric_card(self.metrics_frame, TICKERS[1], 0, 1, color=self.colors[1]))
        self.val_states.append(self.create_metric_card(self.metrics_frame, "PAIR 1 STATE", 0, 2, color="#aaaaaa"))
        self.val_pnl = self.create_metric_card(self.metrics_frame, "TOTAL PNL (₹)", 0, 3, color="#00ff88", rowspan=3)

        # Row 1: Pair 2
        self.val_prices.append(self.create_metric_card(self.metrics_frame, TICKERS[2], 1, 0, color=self.colors[2]))
        self.val_prices.append(self.create_metric_card(self.metrics_frame, TICKERS[3], 1, 1, color=self.colors[3]))
        self.val_states.append(self.create_metric_card(self.metrics_frame, "PAIR 2 STATE", 1, 2, color="#aaaaaa"))

        # Row 2: Pair 3
        self.val_prices.append(self.create_metric_card(self.metrics_frame, TICKERS[4], 2, 0, color=self.colors[4]))
        self.val_prices.append(self.create_metric_card(self.metrics_frame, TICKERS[5], 2, 1, color=self.colors[5]))
        self.val_states.append(self.create_metric_card(self.metrics_frame, "PAIR 3 STATE", 2, 2, color="#aaaaaa"))

        # Graphs
        self.graph_frame = ctk.CTkFrame(self)
        self.graph_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        plt.style.use('dark_background')
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 5), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b')
        self.ax1.set_facecolor('#2b2b2b')
        self.ax2.set_facecolor('#2b2b2b')
        self.fig.tight_layout(pad=3.0)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def create_metric_card(self, parent, title, row, col, color="#ffffff", rowspan=1):
        frame = ctk.CTkFrame(parent, corner_radius=10, fg_color="#1a1a1a")
        frame.grid(row=row, column=col, rowspan=rowspan, padx=10, pady=5, sticky="nsew")
        
        lbl_title = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(family="Consolas", size=12))
        lbl_title.pack(pady=(10, 0))
        
        size = 22 if rowspan == 1 else 40
        lbl_val = ctk.CTkLabel(frame, text="...", font=ctk.CTkFont(family="Consolas", size=size, weight="bold"), text_color=color)
        lbl_val.pack(pady=(0, 10), expand=True)
        return lbl_val

    def get_live_prices(self):
        try:
            data = yf.download(tickers=TICKERS, period='1d', interval='1m', progress=False)
            latest = [float(data['Close'][ticker].iloc[-1]) for ticker in TICKERS]
            return latest
        except:
            return None

    def get_fpga_state(self, p1, p2):
        if not self.ser: return 0
        try:
            payload = struct.pack('>HH', int(p1*10)&0xFFFF, int(p2*10)&0xFFFF)
            self.ser.write(payload)
            raw = self.ser.read(1)
            return struct.unpack('>B', raw)[0] if raw else 0
        except: return 0

    def fetch_thread(self):
        latest_prices = self.get_live_prices()
        if latest_prices and len(latest_prices) == 6:
            self.prices = latest_prices
            
            # Hardware Multiplexer Loop
            for pair_idx in range(3):
                s1, s2 = self.prices[pair_idx*2], self.prices[pair_idx*2+1]
                self.pair_states[pair_idx] = self.get_fpga_state(s1, s2)
                
        # Schedule the UI update back on the main thread
        self.after(0, self.update_ui)

    def update_data(self):
        for state_lbl in self.val_states:
            state_lbl.configure(text="FETCHING...", text_color="#ffff00")
        threading.Thread(target=self.fetch_thread, daemon=True).start()
        self.after(SPEED_MS, self.update_data)

    def update_ui(self):
        t = time.time() - self.start_time
        
        for pair_idx in range(3):
            state = self.pair_states[pair_idx]
            status_str, color = "SCANNING", "#aaaaaa"
            
            # Base PnL off the first stock in the pair scaled down for visual tracking
            trade_amount = self.prices[pair_idx*2] * 0.001 
            
            if state == 1:
                status_str, color = "BUY EXEC", "#00ffcc"
                self.pnl += trade_amount
            elif state == 2:
                status_str, color = "SELL EXEC", "#ff4444"
                self.pnl -= trade_amount

            self.val_states[pair_idx].configure(text=status_str, text_color=color)

        # Update Metrics
        for i in range(6):
            if self.prices[i] > 0:
                self.val_prices[i].configure(text=f"{self.prices[i]:.2f}")
                self.price_data[i].append(self.prices[i])

        self.val_pnl.configure(text=f"₹{self.pnl:.2f}", text_color="#00ff88" if self.pnl >= 0 else "#ff4444")
        
        self.times.append(t)
        self.pnl_data.append(self.pnl)

        self.ax1.clear()
        for i in range(6):
            if self.price_data[i]:
                # Normalize to starting price to show relative pct movement on one chart
                normalized = [p / self.price_data[i][0] * 100 for p in self.price_data[i]]
                self.ax1.plot(self.times, normalized, color=self.colors[i], label=f"S{i+1}")
                
        self.ax1.legend(loc="upper left", facecolor="#1f1f1f", edgecolor="none", labelcolor="white", ncol=6)
        self.ax1.grid(color='#444444', linestyle='-', linewidth=0.5)
        self.ax1.set_ylabel("Normalized Price (%)")

        self.ax2.clear()
        self.ax2.plot(self.times, self.pnl_data, color='#00ff88', linewidth=2)
        self.ax2.fill_between(self.times, self.pnl_data, color='#00ff88', alpha=0.1)
        self.ax2.grid(color='#444444', linestyle='-', linewidth=0.5)
        self.ax2.set_ylabel("Portfolio P&L (₹)")

        self.canvas.draw_idle()

if __name__ == "__main__":
    app = HFTRealMarketDashboard()
    app.mainloop()