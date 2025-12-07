from tkinter import Frame, StringVar, ttk, messagebox
import queue
from ..logger import logger
import pandas as pd

class PositionPage(Frame):
    def __init__(self, master=None, sk_client=None, data_manager=None, root=None):
        Frame.__init__(self, master)
        self.pack(fill="both", expand=True)

        self.sk_client = sk_client
        self.data_manager = data_manager
        self.main_window = root
        
        # 緩存 Position item IDs
        self.tree_item_cache = {} 
        self.last_data_cache = {} 
        
        # Thread-safe queue for data updates
        self.update_queue = queue.Queue()
        self._start_queue_processing() 
        
        # Register callback
        if self.data_manager:
            self.data_manager.add_position_callback(self.update_position_data)
        
        self.createWidgets()
        

        
        # if self.data_manager:
        #     self.check_initial_account()
            
    # def check_initial_account(self):
    #     if self.data_manager and self.data_manager.accounts:
    #         # Auto-fill first account
    #         acc = self.data_manager.accounts[0]
    #         self.entry_account.delete(0, "end")
    #         self.entry_account.insert(0, acc['account_no'])
    #         self.label_status.config(text=f"已選帳號: {acc['account_no']}")
        
    def createWidgets(self):
        # 標題與控制區
        control_frame = ttk.LabelFrame(self, text="持倉查詢")
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # 查詢按鈕
        self.btn_query_position = ttk.Button(control_frame, text="查詢持倉 (GetOpenInterest)", command=self.query_position)
        self.btn_query_position.pack(side="left", padx=5, pady=5)
        
        # 顯示提示
        ttk.Label(control_frame, text="自動查詢所有帳戶 (TF/TS)").pack(side="left", padx=5, pady=5)

        # 狀態標籤
        self.label_status = ttk.Label(control_frame, text="狀態: 就緒")
        self.label_status.pack(side="left", padx=10, pady=5)
        
        # === 期貨部位 ===
        frame_futures = ttk.LabelFrame(self, text="期貨倉位")
        frame_futures.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 欄位: 市場別, 帳號, 商品, 買賣別, 未平倉部位, 當沖未平倉部位, 平均成本, 單口手續費, 交易稅, LOGIN_ID
        cols_futures = ("市場別", "帳號", "商品", "買賣別", "未平倉部位", "當沖未平倉部位", "平均成本", "單口手續費", "交易稅", "LOGIN_ID")
        self.tree_futures = self._create_treeview(frame_futures, cols_futures)
        
        # === 證券部位 ===
        frame_securities = ttk.LabelFrame(self, text="證券倉位")
        frame_securities.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 欄位: 股票代號, 今日委買, 今日委賣, 今日買進成交, 今日賣出成交, 即時庫存, LOGIN_ID, ACCOUNT_NO
        cols_securities = ("股票代號", "今日委買", "今日委賣", "今日買進成交", "今日賣出成交", "即時庫存", "LOGIN_ID", "ACCOUNT_NO")
        self.tree_securities = self._create_treeview(frame_securities, cols_securities)

    def _create_treeview(self, parent, columns):
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=8)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor="center")
            
        v_scroll = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        h_scroll = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        return tree

    def query_position(self):
        try:
            # 1. Check if we have accounts
            if not self.data_manager or not self.data_manager.accounts:
                messagebox.showwarning("警告", "無帳號資料，請先登入或等待資料同步")
                return

            self.label_status.config(text="查詢中... (正在查詢所有帳號)")
            
            # 2. Iterate and query
            for acc in self.data_manager.accounts:
                login_id = acc['login_id']
                market = acc['market'] # 'TS', 'TF', 'OS' etc.
                account_no = acc['account_no']
                branch_code = acc['branch_code']
                
                # Format: BranchCode + AccountNo (as per request)
                # Ensure no delimiters unless API requires them, usually concatenated or as is?
                # The user said: "branch_code + account_no". 
                # Let's assume concatenation: "98001234567"
                # But wait, OnAccount gave us split parts. 
                # sk_api GetOpenInterest usually takes the full string or whatever format Capital needs.
                # Usually Capital API "Account" param is the full string like "98001234567".
                
                # Let's construct it.
                # Note: `acc['account_no']` from OnAccount split might be just the account part or full?
                # API Msg: "市場,分公司代碼,分公司,帳號,身份證字號,姓名" -> '9800' and '1234567'.
                # So we combine them.
                
                full_account_str = f"{branch_code}{account_no}"
                
                logger.write_message(f"自動查詢: Market={market}, Login={login_id}, Acc={full_account_str}")
                
                if market == 'TF': # Futures
                    self.sk_client.get_open_interest(login_id, full_account_str)
                elif market == 'TS': # Securities
                    self.sk_client.get_real_balance_report(login_id, full_account_str)
                else:
                    logger.write_message(f"略過未知市場或 OS: {market}")
                    
            self.label_status.config(text="查詢請求已發送 (請查看 Grid)")
                
        except Exception as e:
            logger.write_message(f"查詢持倉失敗: {e}")
            self.label_status.config(text="查詢發生例外")

    def update_position_data(self, data_str, source='TF'):
        # 這是被 Callback 呼叫的方法 (來自 COM thread)，將資料放入 Queue，不直接操作 UI 或 call after
        self.update_queue.put((data_str, source))

    def _start_queue_processing(self):
        self._process_queue()
        
    def _process_queue(self):
        try:
            while True:
                # Get all available items
                data_str, source = self.update_queue.get_nowait()
                self._update_position_ui(data_str, source)
        except queue.Empty:
            pass
        finally:
            # Reschedule check
            self.after(100, self._process_queue)

    def _update_position_ui(self, data_str, source):
        try:
            target_tree = self.tree_futures if source == 'TF' else self.tree_securities
            
            # 清空舊資料
            for item in target_tree.get_children():
                target_tree.delete(item)
                
            # 解析 data_str
            # API 每一筆資料以「,」分隔 Maybe multiple lines joined by some char? 
            # Usually users said "每一筆資料以「,」分隔" implies one record per callback or line.
            # Assuming data_str might contain multiple records or just one.
            # Safety split by lines (if any)
            lines = data_str.split('\n')
            if len(lines) == 1:
                # try split by semi-colon just in case
                if ';' in data_str:
                    lines = data_str.split(';')
                
            for line in lines:
                line = line.strip()
                if not line: continue
                
                # Check for terminator "##"
                if line.startswith("##"):
                    continue

                vals = line.split(',')
                
                parsed_vals = []
                if source == 'TF':
                    # TF Format: 0:市場別, 1:帳號, 2:商品, 3:買賣別, 4:未平倉部位, 5:當沖未平倉部位, 6:平均成本, 7:一點價值, 8:單口手續費, 9:交易稅, 10:LOGIN_ID
                    if len(vals) >= 11:
                        # Keep: 0, 1, 2, 3, 4, 5, 6, 8, 9, 10
                        indices = [0, 1, 2, 3, 4, 5, 6, 8, 9, 10]
                        parsed_vals = [vals[i] for i in indices]
                    else:
                        parsed_vals = vals # Fallback
                        
                elif source == 'TS':
                    # TS Format: 0:股票代號, ..., 7:今日委買, 8:今日委賣, 9:今日買進成交, 10:今日賣出成交, ..., 14:即時庫存, ..., 17:LOGIN_ID, 18:ACCOUNT_NO
                    # Target Cols: 股票代號, 今日委買, 今日委賣, 今日買進成交, 今日賣出成交, 即時庫存, LOGIN_ID, ACCOUNT_NO
                    if len(vals) >= 19:
                        indices = [0, 7, 8, 9, 10, 14, 17, 18]
                        parsed_vals = [vals[i] for i in indices]
                    else:
                        parsed_vals = vals # Fallback
                
                # 插入
                target_tree.insert("", "end", values=parsed_vals)
                
            self.label_status.config(text=f"資料已更新 ({source})")
            
        except Exception as e:
            logger.write_message(f"解析持倉資料錯誤: {e}")
