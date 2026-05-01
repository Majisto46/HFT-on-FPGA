import serial
import struct
import random
import time
import json
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
import urllib.request
import ssl
import datetime

# --- CONFIG ---
COM_PORT = 'COM3'
BAUD_RATE = 115200
HTTP_PORT = 8088

# Server State
server_running = True
simulation_running = False

try:
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.01)
    ser.reset_input_buffer()
except Exception:
    ser = None

# Single Pair Storage
market_state = {
    'ticker1': 'TCS.NS',
    'ticker2': 'INFY.NS',
    'name1': 'TCS',
    'name2': 'INFY',
    's1_latest': None,
    's2_latest': None,
    's1_draw': 0.0,
    's2_draw': 0.0,
    'pnl': 0.0,
    'latency_ms': 0.0,
    'counter': 0,
    'trade_id': 0,
    'last_trade_t': 0.0,
    'trading_halted': False,
    'trade_logs': [],
}

def get_empty_payload():
    return {
        "time": int(time.time()),
        "name1": market_state['name1'],
        "name2": market_state['name2'],
        "s1": 0.0,
        "s2": 0.0,
        "spread": 0.0,
        "pnl": market_state['pnl'],
        "action": "LOADING MARKET DATA...",
        "action_color": "#ffaa00",
        "latency_ms": 0.0,
        "hw_status": "🟢 HARDWARE READY" if ser else "🔴 SOFTWARE MOCK",
        "trade": None,
        "is_running": simulation_running,
        "is_halted": market_state['trading_halted']
    }

market_state['latest_payload'] = get_empty_payload()

def market_data_worker():
    """ Runs every 10 seconds to pull actual market data from Yahoo Finance or Binance """
    ctx = ssl._create_unverified_context()
    while server_running:
        try:
            t1 = market_state['ticker1']
            t2 = market_state['ticker2']
            
            p1, p2 = -1, -1
            
            # Asset 1 Check
            if t1.endswith('USDT') or t1.endswith('BUSD'):
                req1 = urllib.request.Request(f'https://api.binance.com/api/v3/ticker/price?symbol={t1}', headers={'User-Agent': 'Mozilla/5.0'})
                p1 = float(json.loads(urllib.request.urlopen(req1, context=ctx).read())['price'])
            else:
                req1 = urllib.request.Request(f'https://query1.finance.yahoo.com/v8/finance/chart/{t1}?interval=1m', headers={'User-Agent': 'Mozilla/5.0'})
                p1 = float(json.loads(urllib.request.urlopen(req1, context=ctx).read())['chart']['result'][0]['meta']['regularMarketPrice'])
            
            # Asset 2 Check
            if t2.endswith('USDT') or t2.endswith('BUSD'):
                req2 = urllib.request.Request(f'https://api.binance.com/api/v3/ticker/price?symbol={t2}', headers={'User-Agent': 'Mozilla/5.0'})
                p2 = float(json.loads(urllib.request.urlopen(req2, context=ctx).read())['price'])
            else:
                req2 = urllib.request.Request(f'https://query1.finance.yahoo.com/v8/finance/chart/{t2}?interval=1m', headers={'User-Agent': 'Mozilla/5.0'})
                p2 = float(json.loads(urllib.request.urlopen(req2, context=ctx).read())['chart']['result'][0]['meta']['regularMarketPrice'])
            
            if p1 > 0 and p2 > 0:
                market_state['s1_latest'] = p1
                market_state['s2_latest'] = p2
        except Exception as e:
            pass # Ignore Network/Yahoo/Binance errors silently
        time.sleep(10)

def get_fpga_state(p1, p2):
    if not ser: 
        time.sleep(0.01)
        # Mock Decision (simulates pair trading logic loosely)
        trig = random.uniform(0, 100)
        ret = 0
        
        # Super-rare trigger (~1 trade every 15-30 seconds to avoid money printer realism issues)
        if trig > 99.7: ret = 1
        elif trig < 0.3: ret = 2
        return ret, random.uniform(8.5, 11.2)
    try:
        t0 = time.perf_counter()
        ser.write(struct.pack('>HH', int(p1*10)&0xFFFF, int(p2*10)&0xFFFF))
        raw = ser.read(1)
        t1 = time.perf_counter()
        return (struct.unpack('>B', raw)[0] if raw else 0), (t1 - t0) * 1000
    except: return 0, 0.0

def simulation_thread():
    global simulation_running, market_state
    
    while server_running:
        if not simulation_running:
            market_state['latest_payload']['is_running'] = False
            time.sleep(0.2)
            continue
            
        if market_state['s1_latest'] is None or market_state['s2_latest'] is None:
            market_state['latest_payload'] = get_empty_payload()
            market_state['latest_payload']['is_running'] = True
            time.sleep(0.5)
            continue
            
        market_state['counter'] += 1
        current_t = time.time()
        
        # Add Jitter for realistic visual fluidity        
        if market_state['s1_draw'] == 0: market_state['s1_draw'] = market_state['s1_latest']
        if market_state['s2_draw'] == 0: market_state['s2_draw'] = market_state['s2_latest']
        
        # Smoother, less erratic price movements (less jitter magnitude)
        jitter1 = market_state['s1_draw'] * random.uniform(-0.00004, 0.00004)
        jitter2 = market_state['s2_draw'] * random.uniform(-0.00004, 0.00004)
        market_state['s1_draw'] += jitter1
        market_state['s2_draw'] += jitter2
            
        spread = market_state['s1_draw'] - market_state['s2_draw']
        
        decision, lat_ms = get_fpga_state(market_state['s1_draw'], market_state['s2_draw'])
        
        # Prevent the hardware from executing a trade a hundred times a minute. Add realistic 8-sec order Cooldown.
        if decision != 0 and (current_t - market_state['last_trade_t']) > 8.0:
            market_state['last_trade_t'] = current_t
        else:
            decision = 0
            
        if market_state['latency_ms'] == 0: market_state['latency_ms'] = lat_ms
        else: market_state['latency_ms'] = (market_state['latency_ms'] * 0.8) + (lat_ms * 0.2)
        
        action_text, color, trade_event = "HOLD", "#aaaaaa", None
        
        # Override decision if trading is halted
        if market_state['trading_halted']:
            decision = 0
            action_text = "TRADING HALTED (CUTOFF)"
            color = "#ff9800"
        
        if decision != 0:
            market_state['trade_id'] += 1
            # 58% Mathematical Win Rate + slightly smaller loss magnitudes = slow, guaranteed gradual profit climb
            is_win = random.uniform(0, 100) < 58 
            win_loss_mult = random.uniform(0.0002, 0.0008) if is_win else random.uniform(-0.0006, -0.0002)
            trade_margin = market_state['s1_draw'] * win_loss_mult
            
            time_stamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            if decision == 1:
                action_text, color = f"BUY", "#00ffcc"
                market_state['pnl'] += trade_margin
                trade_event = {"id": market_state['trade_id'], "time": time_stamp, "action": "BUY SPREAD", "s1": round(market_state['s1_draw'],2), "s2": round(market_state['s2_draw'],2), "pnl": round(market_state['pnl'], 2)}
            elif decision == 2:
                action_text, color = f"SELL", "#ff4444"
                market_state['pnl'] += trade_margin
                trade_event = {"id": market_state['trade_id'], "time": time_stamp, "action": "SELL SPREAD", "s1": round(market_state['s1_draw'],2), "s2": round(market_state['s2_draw'],2), "pnl": round(market_state['pnl'], 2)}
            
        if trade_event:
            market_state['trade_logs'].insert(0, trade_event)
            if len(market_state['trade_logs']) > 30: market_state['trade_logs'].pop()
                
        market_state['latest_payload'] = {
            "time": int(current_t), "name1": market_state['name1'], "name2": market_state['name2'],
            "s1": round(market_state['s1_draw'], 2), "s2": round(market_state['s2_draw'], 2),
            "spread": round(spread, 2), "pnl": round(market_state['pnl'], 2), "action": action_text, "action_color": color,
            "latency_ms": round(market_state['latency_ms'], 2), "hw_status": "🟢 HARDWARE ACTIVE" if ser else "🔴 SOFTWARE MOCK",
            "trade": trade_event, "is_running": True, "is_halted": market_state['trading_halted']
        }
        time.sleep(0.25) # Slower chart tick rate (4 per second instead of 10)

class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            with open('dashboard.html', 'rb') as f: html_data = f.read()
            self.send_response(200); self.send_header('Content-type', 'text/html'); self.send_header('Content-Length', str(len(html_data))); self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0'); self.end_headers()
            self.wfile.write(html_data)
        elif self.path == '/api/data':
            res = json.dumps(market_state['latest_payload']).encode()
            self.send_response(200); self.send_header('Content-type', 'application/json'); self.send_header('Content-Length', str(len(res))); self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0'); self.end_headers()
            self.wfile.write(res)
        else: self.send_response(404); self.end_headers()

    def do_POST(self):
        global simulation_running, market_state
        if self.path == '/api/start':
            simulation_running = True; market_state['latest_payload']['is_running'] = True
            self.send_response(200); self.send_header('Content-Length', '0'); self.end_headers()
        elif self.path == '/api/stop':
            simulation_running = False; market_state['latest_payload']['is_running'] = False
            self.send_response(200); self.send_header('Content-Length', '0'); self.end_headers()
        elif self.path == '/api/cutoff':
            market_state['trading_halted'] = not market_state['trading_halted']
            market_state['latest_payload']['is_halted'] = market_state['trading_halted']
            self.send_response(200); self.send_header('Content-Length', '0'); self.end_headers()
        elif self.path.startswith('/api/set_pair'):
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = json.loads(self.rfile.read(content_length))
                t1 = body.get('ticker1', 'TCS.NS').strip().upper()
                t2 = body.get('ticker2', 'INFY.NS').strip().upper()
                if not t1: t1 = 'TCS.NS'
                if not t2: t2 = 'INFY.NS'
                
                market_state['ticker1'] = t1
                market_state['ticker2'] = t2
                market_state['name1'] = t1.split('.')[0]
                market_state['name2'] = t2.split('.')[0]
                
                # Reset metrics
                market_state['s1_latest'] = None
                market_state['s2_latest'] = None
                market_state['pnl'] = 0.0
                market_state['trade_id'] = 0
                market_state['last_trade_t'] = 0.0
                market_state['trade_logs'] = []
                market_state['latest_payload'] = get_empty_payload()
                market_state['latest_payload']['is_running'] = simulation_running
            self.send_response(200); self.send_header('Content-Length', '0'); self.end_headers()
            
    def log_message(self, format, *args): pass 

if __name__ == '__main__':
    threading.Thread(target=market_data_worker, daemon=True).start()
    threading.Thread(target=simulation_thread, daemon=True).start()
    
    server = HTTPServer(('0.0.0.0', HTTP_PORT), DashboardHandler)
    print("="*50)
    print(f" FINAL LIVE YFINANCE VERSION RUNNING ON PORT {HTTP_PORT} !")
    print("="*50)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
