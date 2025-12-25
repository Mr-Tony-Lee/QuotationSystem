from tkinter import Frame, StringVar, Listbox, ttk, messagebox
from ..logger import logger
import pandas as pd

class FrameInformation(Frame):
    def __init__(self, master=None, data_manager=None, root=None):
        Frame.__init__(self, master)
        self.Information = Frame(self)
        self.Information.pack(fill="both", expand=True)
        self.main_window = root
        self.data_manager = data_manager

        self.info_timer_id = None
        self.info_tree_cache = {}
        self.info_last_data = {}
        
        # 篩選變數
        self.filter_enabled = False
        self.filter_names = []
        self.filter_future_to_stock_op = StringVar(value="無限制")
        self.filter_future_to_stock_value = StringVar(value="0")
        self.filter_stock_to_future_op = StringVar(value="無限制")
        self.filter_stock_to_future_value = StringVar(value="0")
        
        self.createWidgets()

    def createWidgets(self):
        control_frame = ttk.LabelFrame(self.Information, text="整理控制", style="TLabelframe")
        control_frame.pack(fill="x", padx=15, pady=10)
        
        self.btn_start_info = ttk.Button(control_frame, text="開始整理", command=self.start_info, width=15)
        self.btn_start_info.pack(side="left", padx=10, pady=10)

        self.btn_stop_info = ttk.Button(control_frame, text="停止整理", command=self.stop_info, width=15)
        self.btn_stop_info.pack(side="left", padx=10, pady=10)
        self.btn_stop_info.config(state="disabled")
        
        self.btn_enable_filter = ttk.Button(control_frame, text="啟用篩選", command=self.toggle_filter, width=15)
        self.btn_enable_filter.pack(side="left", padx=10, pady=10)
        
        self.label_filter_status = ttk.Label(control_frame, text="篩選: 停用", foreground="red", font=("Microsoft JhengHei UI", 10, "bold"))
        self.label_filter_status.pack(side="left", padx=10, pady=10)
        
        self.create_filter_panel()

        table_frame = ttk.LabelFrame(self.Information, text="期貨股票價差監控", style="TLabelframe")
        table_frame.pack(fill="both", expand=True, padx=15, pady=5)
    
        columns = ("期貨名稱", "對照股票", "期貨買價", "期貨委買", "期貨賣價", "期貨委賣", "期貨成交", 
                   "股票買價", "股票委買", "股票賣價", "股票委賣", "股票成交", "期-股差額", "股-期差額")
        
        self.info_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=25)
        
        column_widths = {
            "期貨名稱": 100, "對照股票": 100, "期貨買價": 80, "期貨委買": 80, "期貨賣價": 80, "期貨委賣": 80, "期貨成交": 80,
            "股票買價": 80, "股票委買": 80, "股票賣價": 80, "股票委賣": 80, "股票成交": 80, "期-股差額": 80, "股-期差額": 80
        }
        for col in columns:
            self.info_tree.heading(col, text=col)
            self.info_tree.column(col, width=column_widths[col], anchor="center")

        v_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.info_tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.info_tree.xview)
        self.info_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.info_tree.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
    
    def create_filter_panel(self):
        self.filter_frame = ttk.LabelFrame(self.Information, text="🔍 篩選條件", style="TLabelframe")
        
        row1 = ttk.Frame(self.filter_frame)
        row1.pack(fill="x", padx=5, pady=3)
        
        ttk.Label(row1, text="名稱:").pack(side="left", padx=5)
        self.entry_filter_name = ttk.Entry(row1, width=30)
        self.entry_filter_name.pack(side="left", padx=5)
        self.entry_filter_name.bind('<KeyRelease>', self.on_name_filter_change)
        
        ttk.Button(row1, text="添加名稱", command=self.add_name_filter).pack(side="left", padx=5)
        
        self.label_selected_names = ttk.Label(row1, text="已選: 無", foreground="blue")
        self.label_selected_names.pack(side="left", padx=10)
        
        ttk.Button(row1, text="清除名稱", command=self.clear_name_filter).pack(side="left", padx=5)
        ttk.Button(row1, text="清除篩選", command=self.clear_filter).pack(side="left", padx=10)
        
        self.name_suggest_frame = ttk.Frame(self.filter_frame)
        self.name_suggest_listbox = Listbox(self.name_suggest_frame, height=5)
        self.name_suggest_listbox.pack(fill="x")
        self.name_suggest_listbox.bind('<Double-Button-1>', self.select_suggested_name)
        
        row2 = ttk.Frame(self.filter_frame)
        row2.pack(fill="x", padx=5, pady=3)
        
        ttk.Label(row2, text="期-股差額:").pack(side="left", padx=5)
        future_to_stock_combo = ttk.Combobox(row2, textvariable=self.filter_future_to_stock_op, width=8, state="readonly")
        future_to_stock_combo['values'] = ("無限制", "大於", "小於")
        future_to_stock_combo.pack(side="left", padx=2)
        ttk.Entry(row2, textvariable=self.filter_future_to_stock_value, width=10).pack(side="left", padx=2)
        
        ttk.Label(row2, text="股-期差額:").pack(side="left", padx=15)
        stock_to_future_combo = ttk.Combobox(row2, textvariable=self.filter_stock_to_future_op, width=8, state="readonly")
        stock_to_future_combo['values'] = ("無限制", "大於", "小於")
        stock_to_future_combo.pack(side="left", padx=2)
        ttk.Entry(row2, textvariable=self.filter_stock_to_future_value, width=10).pack(side="left", padx=2)
    
    def toggle_filter(self):
        self.filter_enabled = not self.filter_enabled
        if self.filter_enabled:
            self.btn_enable_filter.config(text="停用篩選")
            self.label_filter_status.config(text="篩選: 啟用", foreground="green")
            self.filter_frame.pack(fill="x", padx=10, pady=5, before=self.Information.winfo_children()[2])
            logger.write_message("已啟用整理篩選")
        else:
            self.btn_enable_filter.config(text="啟用篩選")
            self.label_filter_status.config(text="篩選: 停用", foreground="red")
            self.filter_frame.pack_forget()
            logger.write_message("已停用整理篩選")
    
    def clear_filter(self):
        self.filter_names = []
        self.filter_future_to_stock_op.set("無限制")
        self.filter_future_to_stock_value.set("0")
        self.filter_stock_to_future_op.set("無限制")
        self.filter_stock_to_future_value.set("0")
        self.label_selected_names.config(text="已選: 無")
        self.entry_filter_name.delete(0, 'end')
        self.name_suggest_frame.pack_forget()
        logger.write_message("已清除所有篩選條件")
    
    def on_name_filter_change(self, event):
        search_text = self.entry_filter_name.get().strip().lower()
        if not search_text:
            self.name_suggest_frame.pack_forget()
            return

        suggestions = []
        # 從期貨名稱中搜尋
        for code, name in self.data_manager.future_codes_to_name.items():
            if search_text in name.lower() or search_text in code.lower():
                suggestions.append(f"{name} ({code})")
        
        # 從股票名稱中搜尋
        for code, name in self.data_manager.stock_codes_to_name.items():
            if search_text in name.lower() or search_text in code.lower():
                suggestions.append(f"{name} ({code})")
        
        self.name_suggest_listbox.delete(0, 'end')
        for suggestion in suggestions[:20]:
            self.name_suggest_listbox.insert('end', suggestion)
        
        if suggestions:
            self.name_suggest_frame.pack(fill="x", padx=5, pady=3)
        else:
            self.name_suggest_frame.pack_forget()
    
    def select_suggested_name(self, event):
        selection = self.name_suggest_listbox.curselection()
        if selection:
            selected_text = self.name_suggest_listbox.get(selection[0])
            self.entry_filter_name.delete(0, 'end')
            self.entry_filter_name.insert(0, selected_text)
            self.add_name_filter()
    
    def add_name_filter(self):
        name_text = self.entry_filter_name.get().strip()
        if not name_text:
            messagebox.showwarning("警告", "請輸入名稱")
            return
        
        if '(' in name_text:
            name = name_text.split('(')[0].strip()
        else:
            name = name_text
        
        if name and name not in self.filter_names:
            self.filter_names.append(name)
            self.update_selected_names_label()
            self.entry_filter_name.delete(0, 'end')
            self.name_suggest_frame.pack_forget()
            logger.write_message(f"已添加篩選名稱: {name}")
    
    def clear_name_filter(self):
        self.filter_names = []
        self.update_selected_names_label()
        logger.write_message("已清除名稱篩選")
    
    def update_selected_names_label(self):
        if self.filter_names:
            names_text = ", ".join(self.filter_names[:3])
            if len(self.filter_names) > 3:
                names_text += f" ... (共{len(self.filter_names)}個)"
            self.label_selected_names.config(text=f"已選: {names_text}")
        else:
            self.label_selected_names.config(text="已選: 無")
   
    def start_info(self):
        logger.write_message(f"開始整理 ({len(self.data_manager.all_stocks)} 筆資料)...")
        self.btn_start_info.config(state="disabled")
        self.btn_stop_info.config(state="normal")
        self.start_info_timer() 
    
    def start_info_timer(self):
        def update_info():
            try:
                self.update_info_grid()
                self.info_timer_id = self.main_window.after(1000, update_info)
            except Exception as e:
                logger.write_message(f"更新資訊時發生錯誤: {str(e)}")
        
        self.info_timer_id = self.main_window.after(100, update_info)

    def stop_info(self):
        try:
            if self.info_timer_id:
                self.main_window.after_cancel(self.info_timer_id)
                self.info_timer_id = None

            self.btn_start_info.config(state="normal")
            self.btn_stop_info.config(state="disabled")

            logger.write_message("已停止整理")
        except Exception as e:
            logger.write_message(f"停止整理時發生錯誤: {str(e)}")
        
    def update_info_grid(self):
        try:
            data_list = []
            
            for index, spread_info in self.data_manager.spread_map.items():
                if spread_info.future.future_no and spread_info.stock.stock_no:
                    future_bid = spread_info.future.bid_price
                    future_bid_volume = spread_info.future.bid_volume
                    future_ask = spread_info.future.ask_price
                    future_ask_volume = spread_info.future.ask_volume
                    future_close = spread_info.future.close_price

                    stock_bid = spread_info.stock.bid_price
                    stock_bid_volume = spread_info.stock.bid_volume
                    stock_ask = spread_info.stock.ask_price
                    stock_ask_volume = spread_info.stock.ask_volume
                    stock_close = spread_info.stock.close_price

                    future_to_stock_diff = (future_ask - stock_bid) if (stock_bid > 0 and future_ask > 0) else 0
                    stock_to_future_diff = (stock_ask - future_bid) if (future_bid > 0 and stock_ask > 0) else 0

                    future_name = self.data_manager.future_codes_to_name.get(spread_info.future.future_no, "")
                    stock_name = self.data_manager.stock_codes_to_name.get(spread_info.stock.stock_no, "")

                    data_list.append({
                        'index': index,
                        'future_name': future_name,
                        'stock_name': stock_name,
                        'future_bid': future_bid,
                        'future_bid_volume': future_bid_volume,
                        'future_ask': future_ask,
                        'future_ask_volume': future_ask_volume,
                        'future_close': future_close,
                        'stock_bid': stock_bid,
                        'stock_bid_volume': stock_bid_volume,
                        'stock_ask': stock_ask,
                        'stock_ask_volume': stock_ask_volume,
                        'stock_close': stock_close,
                        'future_to_stock_diff': future_to_stock_diff,
                        'stock_to_future_diff': stock_to_future_diff
                    })
            
            if not data_list:
                return
            
            df = pd.DataFrame(data_list)
            
            if self.filter_enabled:
                mask = pd.Series([True] * len(df))
                
                if self.filter_names:
                    name_mask = pd.Series([False] * len(df))
                    for filter_name in self.filter_names:
                        name_mask |= df['future_name'].str.contains(filter_name, case=False, na=False)
                        name_mask |= df['stock_name'].str.contains(filter_name, case=False, na=False)
                    mask &= name_mask
                
                if self.filter_future_to_stock_op.get() != "無限制":
                    try:
                        val = float(self.filter_future_to_stock_value.get())
                        if self.filter_future_to_stock_op.get() == "大於":
                            mask &= (df['future_to_stock_diff'] > val)
                        elif self.filter_future_to_stock_op.get() == "小於":
                            mask &= (df['future_to_stock_diff'] < val)
                    except:
                        pass
                
                if self.filter_stock_to_future_op.get() != "無限制":
                    try:
                        val = float(self.filter_stock_to_future_value.get())
                        if self.filter_stock_to_future_op.get() == "大於":
                            mask &= (df['stock_to_future_diff'] > val)
                        elif self.filter_stock_to_future_op.get() == "小於":
                            mask &= (df['stock_to_future_diff'] < val)
                    except:
                        pass
                
                df = df[mask]
            
            current_indices = set(df['index'])
            
            df['future_bid_str'] = df['future_bid'].apply(lambda x: f"{x:.2f}" if x > 0 else "0.00")
            df['future_bid_volume_str'] = df['future_bid_volume'].apply(lambda x: str(x) if x > 0 else "0")
            df['future_ask_str'] = df['future_ask'].apply(lambda x: f"{x:.2f}" if x > 0 else "0.00")
            df['future_ask_volume_str'] = df['future_ask_volume'].apply(lambda x: str(x) if x > 0 else "0")
            df['future_close_str'] = df['future_close'].apply(lambda x: f"{x:.2f}" if x > 0 else "0.00")
            df['stock_bid_str'] = df['stock_bid'].apply(lambda x: f"{x:.2f}" if x > 0 else "0.00")
            df['stock_bid_volume_str'] = df['stock_bid_volume'].apply(lambda x: str(x) if x > 0 else "0")
            df['stock_ask_str'] = df['stock_ask'].apply(lambda x: f"{x:.2f}" if x > 0 else "0.00")
            df['stock_ask_volume_str'] = df['stock_ask_volume'].apply(lambda x: str(x) if x > 0 else "0")
            df['stock_close_str'] = df['stock_close'].apply(lambda x: f"{x:.2f}" if x > 0 else "0.00")
            df['future_to_stock_diff_str'] = df['future_to_stock_diff'].apply(lambda x: f"{x:.2f}" if x != 0 else "0.00")
            df['stock_to_future_diff_str'] = df['stock_to_future_diff'].apply(lambda x: f"{x:.2f}" if x != 0 else "0.00")
            
            for _, row in df.iterrows():
                index = row['index']
                values = (
                    row['future_name'], row['stock_name'],
                    row['future_bid_str'], row['future_bid_volume_str'],
                    row['future_ask_str'], row['future_ask_volume_str'],
                    row['future_close_str'],
                    row['stock_bid_str'], row['stock_bid_volume_str'],
                    row['stock_ask_str'], row['stock_ask_volume_str'],
                    row['stock_close_str'],
                    row['future_to_stock_diff_str'], row['stock_to_future_diff_str']
                )
                
                tree_item = self.info_tree_cache.get(index)
                last_values = self.info_last_data.get(index)
                
                if last_values != values:
                    if tree_item and self.info_tree.exists(tree_item):
                        self.info_tree.item(tree_item, values=values)
                    else:
                        tree_item = self.info_tree.insert("", "end", values=values)
                        self.info_tree_cache[index] = tree_item
                    self.info_last_data[index] = values
            
            indices_to_remove = set(self.info_tree_cache.keys()) - current_indices
            for index in indices_to_remove:
                tree_item = self.info_tree_cache.get(index)
                if tree_item and self.info_tree.exists(tree_item):
                    self.info_tree.delete(tree_item)
                del self.info_tree_cache[index]
                if index in self.info_last_data:
                    del self.info_last_data[index]
                    
        except Exception as e:
            logger.write_message(f"更新資訊表格時發生錯誤: {str(e)}")
