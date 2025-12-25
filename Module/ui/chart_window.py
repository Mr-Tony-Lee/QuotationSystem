import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import mplfinance as mpf
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from ..logger import logger
from datetime import datetime

class ChartWindow(tk.Toplevel):
    def __init__(self, master=None, stock_code=None, stock_name=None, sk_client=None, data_manager=None):
        super().__init__(master)
        self.title(f"技術線圖 - {stock_name} ({stock_code})")
        self.geometry("800x600")
        
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.sk_client = sk_client
        self.data_manager = data_manager
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.logger_msg(f"Initializing ChartWindow for {stock_code}")
        
        self.create_widgets()
        
        # Register callback
        if self.data_manager:
            self.data_manager.register_kline_callback(self.stock_code, self.on_data_update)
            
        # Delay request to allow window to prevent freeze during init
        self.after(500, self.request_data)
        
    def logger_msg(self, msg):
        logger.write_message(f"[ChartWindow] {msg}")

    def create_widgets(self):
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(side="top", fill="x", padx=5, pady=5)
        
        ttk.Button(toolbar, text="重新整理", command=self.request_data).pack(side="left", padx=5)
        self.label_status = ttk.Label(toolbar, text="狀態: 準備中...", foreground="blue")
        self.label_status.pack(side="left", padx=10)
        
        # Plot Area
        self.plot_frame = ttk.Frame(self)
        self.plot_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Initialize Figure and Canvas ONCE
        # Use simple black background figure
        self.fig = Figure(figsize=(8, 6), dpi=100, facecolor='black')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("black")
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def request_data(self):
        if self.sk_client and self.stock_code:
            self.label_status.config(text="請求數據中...")
            self.logger_msg("Requesting KLine data...")
            # Request 1-min KLine (Type 0), Newest first (Type 1)
            self.sk_client.request_kline(self.stock_code, 0, 1)
            
    def on_data_update(self, stock_code, new_records):
        # Debounce: If update is already scheduled, don't schedule another one immediately
        if hasattr(self, '_update_pending') and self._update_pending:
            return
            
        self._update_pending = True
        self.after(500, self._process_update_chart) # Wait 500ms to accumulate data

    def _process_update_chart(self):
        self._update_pending = False
        self.update_chart()

    def update_chart(self):
        try:
            if not self.data_manager or self.stock_code not in self.data_manager.kline_data:
                self.label_status.config(text="無數據")
                return
                
            data = self.data_manager.kline_data[self.stock_code]
            if not data:
                self.label_status.config(text="無數據")
                return

            self.logger_msg(f"Updating chart with {len(data)} records")

            # Slice data BEFORE creating DataFrame
            if len(data) > 200:
                display_data = data[-200:]
            else:
                display_data = data

            df = pd.DataFrame(display_data)
            
            # Format columns
            try:
                df['Date'] = pd.to_datetime(df['date'])
            except:
                df['Date'] = pd.date_range(end=datetime.now(), periods=len(df), freq='T')
            
            df.set_index('Date', inplace=True)
            df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
            
            self.draw_plot(df)
            self.label_status.config(text=f"已更新: {len(df)} 筆數據")

        except Exception as e:
            self.logger_msg(f"Chart Render Error: {e}")
            self.label_status.config(text=f"繪圖錯誤: {e}")

    def draw_plot(self, df):
        try:
            # Clear previous axes safely
            self.ax.clear()
            self.ax.grid(True, color='gray', linestyle='--', linewidth=0.5)
            self.ax.set_facecolor("black")
            
            # Use mpf.plot with ax=self.ax (External Axes Mode)
            # Custom style for black background with visible text
            mc = mpf.make_marketcolors(up='r', down='g', inherit=True)
            
            # Explicitly set text colors to white
            my_rc = {
                'font.size': 8,
                'axes.facecolor': 'black',
                'figure.facecolor': 'black',
                'axes.edgecolor': 'white',     # 邊框顏色
                'axes.labelcolor': 'white',    # 標籤顏色
                'xtick.color': 'white',        # X軸刻度顏色
                'ytick.color': 'white',        # Y軸刻度顏色
                'grid.color': 'gray',          # 網格顏色
            }
            
            s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc, rc=my_rc)
            
            mpf.plot(df, type='candle', volume=False, ax=self.ax, style=s, warn_too_much_data=1000)
            
            # Manually force colors ensuring visibility
            self.ax.tick_params(axis='x', colors='white',  labelcolor='white')
            self.ax.tick_params(axis='y', colors='white',  labelcolor='white')
            self.ax.yaxis.label.set_color('white')
            self.ax.xaxis.label.set_color('white')
            self.ax.spines['bottom'].set_color('white')
            self.ax.spines['top'].set_color('white')
            self.ax.spines['left'].set_color('white')
            self.ax.spines['right'].set_color('white')
            
            self.canvas.draw()
        except Exception as e:
             self.logger_msg(f"MPF Plot Error: {e}")
             raise e

    def on_close(self):
        if self.data_manager:
            if self.stock_code in self.data_manager.kline_callbacks:
                 pass
        self.destroy()
