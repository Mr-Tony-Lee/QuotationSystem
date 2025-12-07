from tkinter import Frame, StringVar, Listbox, ttk, messagebox
from ..logger import logger
import pandas as pd

class Quote(Frame):
    def __init__(self, master=None, sk_client=None, data_manager=None, root=None):
        Frame.__init__(self, master)
        self.Quote = Frame(self)
        self.Quote.pack(fill="both", expand=True)

        self.sk_client = sk_client
        self.data_manager = data_manager
        self.main_window = root

        self.quote_timer_id = None
        
        # 🚀 性能優化：緩存 Treeview item IDs
        self.tree_item_cache = {}  # {code: tree_item_id}
        self.last_data_cache = {}  # {code: last_values}
        
        # 🔍 篩選功能變數
        self.filter_type = StringVar(value="全部")
        self.filter_names = []
        self.filter_bid_op = StringVar(value="無限制")
        self.filter_bid_value = StringVar(value="0")
        self.filter_ask_op = StringVar(value="無限制")
        self.filter_ask_value = StringVar(value="0")
        self.filter_close_op = StringVar(value="無限制")
        self.filter_close_value = StringVar(value="0")
        self.filter_bid_vol_op = StringVar(value="無限制")
        self.filter_bid_vol_value = StringVar(value="0")
        self.filter_ask_vol_op = StringVar(value="無限制")
        self.filter_ask_vol_value = StringVar(value="0")
        self.filter_total_vol_op = StringVar(value="無限制")
        self.filter_total_vol_value = StringVar(value="0")
        self.filter_enabled = False

        self.createWidgets()

    def createWidgets(self):
        # 控制區域
        control_frame = ttk.LabelFrame(self.Quote, text="報價控制")
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # 開始訂閱按鈕
        self.btn_start_quote = ttk.Button(control_frame, text="開始訂閱報價", command=self.start_quote_subscription)
        self.btn_start_quote.pack(side="left", padx=5, pady=5)
        
        # 停止訂閱按鈕
        self.btn_stop_quote = ttk.Button(control_frame, text="停止訂閱", command=self.stop_quote_subscription)
        self.btn_stop_quote.pack(side="left", padx=5, pady=5)
        self.btn_stop_quote.config(state="disabled")
        
        # 啟用/停用篩選按鈕
        self.btn_enable_filter = ttk.Button(control_frame, text="啟用篩選", command=self.toggle_filter)
        self.btn_enable_filter.pack(side="left", padx=10, pady=5)
        
        # 篩選狀態顯示
        self.label_filter_status = ttk.Label(control_frame, text="篩選: 停用", foreground="red")
        self.label_filter_status.pack(side="left", padx=5, pady=5)
        
        # 報價狀態標籤
        self.label_quote_count = ttk.Label(control_frame, text="配對組數: 0")
        self.label_quote_count.pack(side="right", padx=5, pady=5)
        
        # 🔍 篩選區域
        self.create_filter_panel()
        
        # 報價表格區域
        table_frame = ttk.LabelFrame(self.Quote, text="期貨股票價差監控")
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 建立Treeview表格
        columns = ("類型", "代碼", "商品名稱", "買進價格", "賣出價格", "成交價格", "買量", "賣量", "總量")
        
        self.quote_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=25)
        
        column_widths = {
            "類型": 60, "代碼": 80, "商品名稱": 120, "買進價格": 80, "賣出價格": 80, 
            "成交價格": 80, "買量": 60, "賣量": 60, "總量": 80
        }
        
        for col in columns:
            self.quote_tree.heading(col, text=col)
            self.quote_tree.column(col, width=column_widths[col], anchor="center")
        
        # 加入滾動條
        v_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.quote_tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.quote_tree.xview)
        self.quote_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        self.quote_tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
    
    def create_filter_panel(self):
        """創建篩選面板"""
        self.filter_frame = ttk.LabelFrame(self.Quote, text="🔍 篩選條件")
        
        # 第一行：類型篩選
        row1 = ttk.Frame(self.filter_frame)
        row1.pack(fill="x", padx=5, pady=3)
        
        ttk.Label(row1, text="類型:").pack(side="left", padx=5)
        type_combo = ttk.Combobox(row1, textvariable=self.filter_type, width=10, state="readonly")
        type_combo['values'] = ("全部", "股票", "期貨")
        type_combo.pack(side="left", padx=5)
        
        ttk.Button(row1, text="清除篩選", command=self.clear_filter).pack(side="left", padx=10)
        
        # 第二行：名稱篩選
        row2 = ttk.Frame(self.filter_frame)
        row2.pack(fill="x", padx=5, pady=3)
        
        ttk.Label(row2, text="名稱:").pack(side="left", padx=5)
        self.entry_filter_name = ttk.Entry(row2, width=30)
        self.entry_filter_name.pack(side="left", padx=5)
        self.entry_filter_name.bind('<KeyRelease>', self.on_name_filter_change)
        
        ttk.Button(row2, text="添加名稱", command=self.add_name_filter).pack(side="left", padx=5)
        
        self.label_selected_names = ttk.Label(row2, text="已選: 無", foreground="blue")
        self.label_selected_names.pack(side="left", padx=10)
        
        ttk.Button(row2, text="清除名稱", command=self.clear_name_filter).pack(side="left", padx=5)
        
        # 名稱建議列表框
        self.name_suggest_frame = ttk.Frame(self.filter_frame)
        self.name_suggest_listbox = Listbox(self.name_suggest_frame, height=5)
        self.name_suggest_listbox.pack(fill="x")
        self.name_suggest_listbox.bind('<Double-Button-1>', self.select_suggested_name)

        # 第三行：價格篩選
        row3 = ttk.Frame(self.filter_frame)
        row3.pack(fill="x", padx=5, pady=3)
        
        filters = [
            ("買進價:", self.filter_bid_op, self.filter_bid_value),
            ("賣出價:", self.filter_ask_op, self.filter_ask_value),
            ("成交價:", self.filter_close_op, self.filter_close_value),
            ("買量:", self.filter_bid_vol_op, self.filter_bid_vol_value),
            ("賣量:", self.filter_ask_vol_op, self.filter_ask_vol_value),
            ("總量:", self.filter_total_vol_op, self.filter_total_vol_value)
        ]

        for label, op_var, val_var in filters:
            ttk.Label(row3, text=label).pack(side="left", padx=5)
            combo = ttk.Combobox(row3, textvariable=op_var, width=8, state="readonly")
            combo['values'] = ("無限制", "大於", "小於")
            combo.pack(side="left", padx=2)
            ttk.Entry(row3, textvariable=val_var, width=10).pack(side="left", padx=2)

    def toggle_filter(self):
        self.filter_enabled = not self.filter_enabled
        if self.filter_enabled:
            self.btn_enable_filter.config(text="停用篩選")
            self.label_filter_status.config(text="篩選: 啟用", foreground="green")
            self.filter_frame.pack(fill="x", padx=10, pady=5, before=self.Quote.winfo_children()[2])
            logger.write_message("已啟用報價篩選")
        else:
            self.btn_enable_filter.config(text="啟用篩選")
            self.label_filter_status.config(text="篩選: 停用", foreground="red")
            self.filter_frame.pack_forget()
            logger.write_message("已停用報價篩選")
    
    def clear_filter(self):
        self.filter_type.set("全部")
        self.filter_names = []
        self.filter_bid_op.set("無限制")
        self.filter_bid_value.set("0")
        self.filter_ask_op.set("無限制")
        self.filter_ask_value.set("0")
        self.filter_close_op.set("無限制")
        self.filter_close_value.set("0")
        self.filter_bid_vol_op.set("無限制")
        self.filter_bid_vol_value.set("0")
        self.filter_ask_vol_op.set("無限制")
        self.filter_ask_vol_value.set("0")
        self.filter_total_vol_op.set("無限制")
        self.filter_total_vol_value.set("0")
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
        for code, name in self.data_manager.stock_codes_to_name.items():
            if search_text in name.lower() or search_text in code.lower():
                suggestions.append(f"{name} ({code})")
        
        for code, name in self.data_manager.future_codes_to_name.items():
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
            
    def start_quote_subscription(self):
        try:
            if not self.data_manager.spread_map:
                logger.write_message("錯誤: 沒有配對資訊可訂閱")
                return

            logger.write_message(f"開始訂閱股票商品 ({len(self.data_manager.all_stocks)} 筆)...")
            
            all_stocks_list = ", ".join(self.data_manager.all_stocks.keys())
            try: 
                if self.sk_client:
                    self.sk_client.request_stocks(1, all_stocks_list)
            except Exception as e:
                logger.write_message(f"訂閱股票時發生錯誤: {e}")

            logger.write_message(f"訂閱請求發送完成")
            
            self.btn_start_quote.config(state="disabled")
            self.btn_stop_quote.config(state="normal")
            
            self.start_quote_timer()            
        except Exception as e:
            logger.write_message(f"訂閱報價時發生錯誤: {str(e)}")

    def stop_quote_subscription(self):
        try:
            if self.quote_timer_id:
                self.main_window.after_cancel(self.quote_timer_id)
                self.quote_timer_id = None
            
            self.btn_start_quote.config(state="normal")
            self.btn_stop_quote.config(state="disabled")
            
            logger.write_message("已停止報價訂閱")
        except Exception as e:
            logger.write_message(f"停止訂閱時發生錯誤: {str(e)}")

    def start_quote_timer(self):
        def update_quotes():
            try:
                self.update_quote_grid()
                self.quote_timer_id = self.main_window.after(1000, update_quotes)
            except Exception as e:
                logger.write_message(f"更新報價時發生錯誤: {str(e)}")
        
        self.quote_timer_id = self.main_window.after(100, update_quotes)

    def update_quote_grid(self):
        try:
            data_list = []
            
            # Use DataManager to get raw data or access data directly
            # For better separation, we iterate over data_manager's data
            
            # --- Collecting futures ---
            for code, name in self.data_manager.future_codes_to_name.items():
                index = self.data_manager.future_to_spreadmap_index.get(code)
                if index is not None:
                    spread_info = self.data_manager.spread_map[index]
                    if spread_info.future.future_no:
                        bid_price = spread_info.future.bid_price
                        ask_price = spread_info.future.ask_price
                        close_price = spread_info.future.close_price
                        
                        if name or bid_price > 0 or ask_price > 0:
                             data_list.append({
                                'type': '期貨',
                                'code': code,
                                'name': spread_info.future.future_name or name,
                                'bid_price': bid_price,
                                'ask_price': ask_price,
                                'close_price': close_price,
                                'bid_volume': spread_info.future.bid_volume,
                                'ask_volume': spread_info.future.ask_volume,
                                'total_volume': getattr(spread_info.future, 'total_volume', 0)
                            })
                            
            # --- Collecting stocks ---
            for code, name in self.data_manager.stock_codes_to_name.items():
                index = self.data_manager.stock_to_spreadmap_index.get(code)
                if index is not None:
                    spread_info = self.data_manager.spread_map[index]
                    if spread_info.stock.stock_no:
                        bid_price = spread_info.stock.bid_price
                        ask_price = spread_info.stock.ask_price
                        close_price = spread_info.stock.close_price
                        
                        if name or bid_price > 0 or ask_price > 0:
                            data_list.append({
                                'type': '股票',
                                'code': code,
                                'name': spread_info.stock.stock_name or name,
                                'bid_price': bid_price,
                                'ask_price': ask_price,
                                'close_price': close_price,
                                'bid_volume': spread_info.stock.bid_volume,
                                'ask_volume': spread_info.stock.ask_volume,
                                'total_volume': getattr(spread_info.stock, 'total_volume', 0)
                            })
            
            if not data_list:
                self.label_quote_count.config(text="無資料")
                return
            
            df = pd.DataFrame(data_list)
            total_count = len(df)

            # Filtering
            if self.filter_enabled:
                mask = pd.Series([True] * len(df))
                
                if self.filter_type.get() != "全部":
                    mask &= (df['type'] == self.filter_type.get())
                
                if self.filter_names:
                    name_mask = pd.Series([False] * len(df))
                    for filter_name in self.filter_names:
                        name_mask |= df['name'].str.contains(filter_name, case=False, na=False)
                    mask &= name_mask

                ops = [
                    ('bid_price', self.filter_bid_op, self.filter_bid_value),
                    ('ask_price', self.filter_ask_op, self.filter_ask_value),
                    ('close_price', self.filter_close_op, self.filter_close_value),
                    ('bid_volume', self.filter_bid_vol_op, self.filter_bid_vol_value),
                    ('ask_volume', self.filter_ask_vol_op, self.filter_ask_vol_value),
                    ('total_volume', self.filter_total_vol_op, self.filter_total_vol_value),
                ]

                for col, op_var, val_var in ops:
                    if op_var.get() != "無限制":
                        try:
                            val = float(val_var.get())
                            if op_var.get() == "大於":
                                mask &= (df[col] > val)
                            elif op_var.get() == "小於":
                                mask &= (df[col] < val)
                        except:
                            pass
                
                df = df[mask]
                filtered_count = total_count - len(df)
            else:
                filtered_count = 0
            
            stock_with_data = len(df[df['type'] == '股票'])
            future_with_data = len(df[df['type'] == '期貨'])
            current_codes = set(df['code'])
            
            # GUI Update
            df['name_short'] = df['name'].str[:10]
            df['bid_price_str'] = df['bid_price'].apply(lambda x: f"{x:.2f}" if x > 0 else "0.00")
            df['ask_price_str'] = df['ask_price'].apply(lambda x: f"{x:.2f}" if x > 0 else "0.00")
            df['close_price_str'] = df['close_price'].apply(lambda x: f"{x:.2f}" if x > 0 else "0.00")
            df['bid_volume_str'] = df['bid_volume'].apply(lambda x: str(x) if x > 0 else "0")
            df['ask_volume_str'] = df['ask_volume'].apply(lambda x: str(x) if x > 0 else "0")
            df['total_volume_str'] = df['total_volume'].apply(lambda x: str(x) if x > 0 else "0")
            
            active_count = 0
            for _, row in df.iterrows():
                code = row['code']
                values = (
                    row['type'], code, row['name_short'], row['bid_price_str'], row['ask_price_str'],
                    row['close_price_str'], row['bid_volume_str'], row['ask_volume_str'], row['total_volume_str']
                )
                
                tree_item = self.tree_item_cache.get(code)
                last_values = self.last_data_cache.get(code)
                
                if last_values != values:
                    if tree_item and self.quote_tree.exists(tree_item):
                        self.quote_tree.item(tree_item, values=values)
                    else:
                        tree_item = self.quote_tree.insert("", "end", values=values)
                        self.tree_item_cache[code] = tree_item
                    self.last_data_cache[code] = values
                
                active_count += 1
            
            codes_to_remove = set(self.tree_item_cache.keys()) - current_codes
            for code in codes_to_remove:
                tree_item = self.tree_item_cache.get(code)
                if tree_item and self.quote_tree.exists(tree_item):
                    self.quote_tree.delete(tree_item)
                del self.tree_item_cache[code]
                if code in self.last_data_cache:
                    del self.last_data_cache[code]
            
            if self.filter_enabled and filtered_count > 0:
                status_text = f"顯示: {active_count} | 股票: {stock_with_data} | 期貨: {future_with_data} | 已篩選: {filtered_count}"
            else:
                status_text = f"顯示筆數: {active_count} | 股票有資料: {stock_with_data} | 期貨有資料: {future_with_data}"
            self.label_quote_count.config(text=status_text)
            
        except Exception as e:
            logger.write_message(f"更新表格時發生錯誤: {str(e)}")
