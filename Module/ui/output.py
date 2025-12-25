import datetime
import os
from tkinter import Frame, ttk
from ..logger import logger

class FrameOutput(Frame):
    def __init__(self, master=None, data_manager=None, root=None):
        Frame.__init__(self, master)
        self.Output = Frame(self)
        self.Output.pack(fill="both", expand=True)

        self.main_window = root
        self.data_manager = data_manager

        self.Output_timer_id = None
        self.last_high_profit_data = None
        self.createWidgets()

    def createWidgets(self):
        control_frame = ttk.LabelFrame(self.Output, text="整理控制", style="TLabelframe")
        control_frame.pack(fill="x", padx=15, pady=10)
        
        self.btn_start_output = ttk.Button(control_frame, text="開始輸出", command=self.start_info, width=15)
        self.btn_start_output.pack(side="left", padx=10, pady=10)

        self.btn_stop_output = ttk.Button(control_frame, text="停止輸出", command=self.stop_info, width=15)
        self.btn_stop_output.pack(side="left", padx=10, pady=10)
        self.btn_stop_output.config(state="disabled")

        table_frame = ttk.LabelFrame(self.Output, text="期貨股票輸出監控", style="TLabelframe")
        table_frame.pack(fill="both", expand=True, padx=15, pady=5)
    
        columns = ("股票名稱","股票代碼", "期貨名稱", "期貨代碼", "正價差" , "逆價差" ,"套利方向", "淨利潤", "總交易成本"  )
        
        self.output_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=25)
        
        column_widths = {
            "股票名稱": 100, "股票代碼": 100, "期貨名稱": 100, "期貨代碼": 100, 
            "正價差": 100 , "逆價差": 100, "套利方向": 100, "淨利潤": 100, "總交易成本": 100
        }
        for col in columns:
            self.output_tree.heading(col, text=col)
            self.output_tree.column(col, width=column_widths[col], anchor="center")

        v_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.output_tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.output_tree.xview)
        self.output_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.output_tree.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
    def start_info(self):
        logger.write_message(f"開始輸出 ({len(self.data_manager.all_stocks)} 筆資料)...")
        self.btn_start_output.config(state="disabled")
        self.btn_stop_output.config(state="normal")
        self.start_info_timer()
        
    def start_info_timer(self):
        def update_info():
            try:
                self.update_output_grid()
                self.Output_timer_id = self.main_window.after(1000, update_info)
            except Exception as e:
                logger.write_message(f"更新資訊時發生錯誤: {str(e)}")
        
        self.Output_timer_id = self.main_window.after(100, update_info)
        
    def stop_info(self):
        try:
            if self.Output_timer_id:
                self.main_window.after_cancel(self.Output_timer_id)
                self.Output_timer_id = None

            self.btn_start_output.config(state="normal")
            self.btn_stop_output.config(state="disabled")

            logger.write_message("已停止整理")
        except Exception as e:
            logger.write_message(f"停止整理時發生錯誤: {str(e)}")
            
    def update_output_grid(self):
        try:
            # Rebuilding logic as in main_3.py (delete all and re-insert sorted)
            for item in self.output_tree.get_children():
                self.output_tree.delete(item)
            all_items = []
            
            # 用於排序和比對的原始資料列表
            current_high_profit_data = []

            for index, spread_info in self.data_manager.spread_map.items():
                if spread_info.ArbitrageDirection is not None:
                    max_profit = max(spread_info.PosNetProfit, spread_info.NegNetProfit)
                    
                    if max_profit > 5000:
                        # 收集原始資料以便後續排序與比對
                        current_high_profit_data.append({
                            'profit': max_profit,
                            'stock_name': spread_info.stock.stock_name,
                            'stock_no': spread_info.stock.stock_no,
                            'future_name': spread_info.future.future_name
                        })

                    values = (
                        self.data_manager.stock_codes_to_name.get(spread_info.stock.stock_no, ""),
                        spread_info.stock.stock_no or "",
                        self.data_manager.future_codes_to_name.get(spread_info.future.future_no, ""),
                        spread_info.future.future_no or "",
                        f"{spread_info.Spread_FutureAsk_StockBid:.2f}",
                        f"{spread_info.Spread_StockAsk_FutureBid:.2f}",
                        spread_info.ArbitrageDirection or "",
                        f"{max_profit:.2f}",
                        f"{spread_info.TotalCost:.2f}",
                    )
                    all_items.append(values)
            
            # 針對高獲利資料進行排序 (由大到小)
            current_high_profit_data.sort(key=lambda x: x['profit'], reverse=True)
            
            # 比對資料是否與上一次不同 (Deduplication)
            if current_high_profit_data != self.last_high_profit_data:
                self.last_high_profit_data = current_high_profit_data
                
                # 若有資料則寫入檔案
                if current_high_profit_data:
                    try:
                        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log_content = f"\n[{timestamp}] 總共有 {len(current_high_profit_data)} 筆符合大於 5000 的資料 (已排序):\n"
                        
                        for idx, item in enumerate(current_high_profit_data, 1):
                            msg = f"{item['stock_name']}({item['stock_no']}) - 期貨:{item['future_name']} 淨利潤: {item['profit']:.2f}"
                            log_content += f"{idx}. {msg}\n"
                        
                        if not os.path.exists("Logs"):
                            os.makedirs("Logs")
                            
                        with open("Logs/HighProfit.log", "a", encoding="utf-8") as f:
                            f.write(log_content)
                            
                        # GUI 只顯示摘要 avoid spam
                        logger.write_message(f"[{timestamp}] 高獲利資料變動，已輸出 {len(current_high_profit_data)} 筆至 Logs/HighProfit.log")
                    except Exception as e:
                        logger.write_message(f"寫入 Logs/HighProfit.log 失敗: {e}")
            
            # Sort by Net Profit (index 7) as float, descending
            all_items.sort(key=lambda t: float(t[7]), reverse=True)

            for values in all_items:
                self.output_tree.insert("", "end", values=values)
        except Exception as e:
            logger.write_message(f"更新輸出表格時發生錯誤: {str(e)}")
