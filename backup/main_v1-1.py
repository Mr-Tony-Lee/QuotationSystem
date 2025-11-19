# 先把API com元件初始化
import os
import queue
from tkinter import *
from tkinter.ttk import *
from tkinter import messagebox,colorchooser,font,Button,Frame,Label
from tkinter import ttk
import comtypes.client
import comtypes.gen.SKCOMLib as sk

# 創建一個全域的消息隊列來處理 COM 事件
com_event_queue = queue.Queue()

comtypes.client.GetModule('SKCOM.dll') #加此行需將API放與py同目錄
skC = comtypes.client.CreateObject(sk.SKCenterLib,interface=sk.ISKCenterLib)
skOOQ = comtypes.client.CreateObject(sk.SKOOQuoteLib,interface=sk.ISKOOQuoteLib)
skO = comtypes.client.CreateObject(sk.SKOrderLib,interface=sk.ISKOrderLib)
skOSQ = comtypes.client.CreateObject(sk.SKOSQuoteLib,interface=sk.ISKOSQuoteLib)
skQ = comtypes.client.CreateObject(sk.SKQuoteLib,interface=sk.ISKQuoteLib)
skR = comtypes.client.CreateObject(sk.SKReplyLib,interface=sk.ISKReplyLib)

class StockInfo:
    def __init__(self):
        self.index = 0
        self.stock_no = ""
        self.stock_name = ""
        self.close_price = 0.0
        self.ref_price = 0.0
        self.open_price = 0.0
        self.high_price = 0.0
        self.low_price = 0.0
        self.total_volume = 0
        self.yesterday_volume = 0
        self.bid_price = 0.0
        self.bid_volume = 0
        self.ask_price = 0.0
        self.ask_volume = 0
    
    @property
    def change_percent(self):
        return 0 if self.ref_price == 0 else (self.close_price - self.ref_price) / self.ref_price * 100
    
    @property
    def volume_ratio(self):
        return 0 if self.yesterday_volume == 0 else self.total_volume / self.yesterday_volume
    
    def update(self, stock_data):
        scale = 10 ** stock_data.sDecimal
        self.stock_name = stock_data.bstrStockName
        self.close_price = stock_data.nClose / scale
        self.ref_price = stock_data.nRef / scale
        self.open_price = stock_data.nOpen / scale
        self.high_price = stock_data.nHigh / scale
        self.low_price = stock_data.nLow / scale
        self.total_volume = stock_data.nTQty
        self.yesterday_volume = stock_data.nYQty
        self.bid_price = stock_data.nBid / scale
        self.bid_volume = stock_data.nBc
        self.ask_price = stock_data.nAsk / scale
        self.ask_volume = stock_data.nAc

class FutureInfo:
    def __init__(self):
        self.future_no = ""
        self.future_name = ""
        self.close_price = 0.0
        self.ref_price = 0.0
        self.open_price = 0.0
        self.high_price = 0.0
        self.low_price = 0.0
        self.total_volume = 0
        self.yesterday_volume = 0
        self.bid_price = 0.0
        self.bid_volume = 0
        self.ask_price = 0.0
        self.ask_volume = 0
        # 期貨特有屬性
        self.settlement_price = 0.0
        self.open_interest = 0
        self.expiry_date = ""
        self.margin_ratio = 0.0
        self.multiplier = 1000  # 期貨合約乘數，預設1000
        self.underlying_stock = ""  # 標的股票代碼
    
    @property
    def change_percent(self):
        return 0 if self.ref_price == 0 else (self.close_price - self.ref_price) / self.ref_price * 100
    
    @property
    def volume_ratio(self):
        return 0 if self.yesterday_volume == 0 else self.total_volume / self.yesterday_volume
    
    @property
    def is_near_month(self):
        """判斷是否為近月合約"""
        return "近月" in self.future_name or "期近月" in self.future_name
    
    @property
    def contract_value(self):
        """計算合約價值"""
        return self.close_price * self.multiplier
    
    @property
    def spread_vs_settlement(self):
        """與結算價的價差"""
        return self.close_price - self.settlement_price if self.settlement_price > 0 else 0
    
    def update(self, future_data):
        """更新期貨資料"""
        try:
            # 檢查小數位數是否在合理範圍內
            decimal_places = getattr(future_data, 'sDecimal', 0)
            if decimal_places < 0 or decimal_places > 6:
                decimal_places = 2  # 預設使用2位小數
            
            scale = 10 ** decimal_places
            
            self.future_name = getattr(future_data, 'strStockName', '')
            self.close_price = getattr(future_data, 'nClose', 0) / scale
            self.ref_price = getattr(future_data, 'nRef', 0) / scale
            self.open_price = getattr(future_data, 'nOpen', 0) / scale
            self.high_price = getattr(future_data, 'nHigh', 0) / scale
            self.low_price = getattr(future_data, 'nLow', 0) / scale
            self.total_volume = getattr(future_data, 'nTQty', 0)
            self.yesterday_volume = getattr(future_data, 'nYQty', 0)
            self.bid_price = getattr(future_data, 'nBid', 0) / scale
            self.bid_volume = getattr(future_data, 'nBc', 0)
            self.ask_price = getattr(future_data, 'nAsk', 0) / scale
            self.ask_volume = getattr(future_data, 'nAc', 0)
            
            # 期貨特有資料（如果有的話）
            if hasattr(future_data, 'nSettlement'):
                self.settlement_price = future_data.nSettlement / scale
            if hasattr(future_data, 'nOpenInterest'):
                self.open_interest = future_data.nOpenInterest
                
        except Exception as e:
            print(f"更新期貨資料時發生錯誤: {e}")
    
    def get_contract_info(self):
        """取得合約基本資訊"""
        return {
            'code': self.future_no,
            'name': self.future_name,
            'underlying': self.underlying_stock,
            'multiplier': self.multiplier,
            'margin_ratio': self.margin_ratio,
            'expiry_date': self.expiry_date,
            'is_near_month': self.is_near_month
        }

class PriceSpreadInfo:
    def __init__(self):
        self.stock = StockInfo()
        self.future = FutureInfo()  # 使用 FutureInfo 而非 StockInfo
    
    @property
    def Spread_StockAsk_FutureBid(self):
        """股票賣價 - 期貨買價 (做多期貨、做空股票的價差)"""
        return self.stock.ask_price - self.future.bid_price if (self.stock.ask_price > 0 and self.future.bid_price > 0) else 0

    @property
    def Spread_FutureAsk_StockBid(self):
        """期貨賣價 - 股票買價 (做多股票、做空期貨的價差)"""
        return self.future.ask_price - self.stock.bid_price if (self.future.ask_price > 0 and self.stock.bid_price > 0) else 0

    @property
    def CompleteData(self):
        """檢查是否有完整的買賣價資料"""
        return (self.future.bid_price > 0 and self.future.ask_price > 0 and
                self.stock.bid_price > 0 and self.stock.ask_price > 0)
    
    @property
    def Positive_Future(self):
        """檢查期貨買賣量是否均大於0"""
        return (self.future.bid_volume > 0 and self.future.ask_volume > 0)
    
    @property
    def Positive_Stock(self):
        """檢查股票買賣量是否均大於0"""
        return (self.stock.bid_volume > 0 and self.stock.ask_volume > 0)
    
    @property
    def FutureFee(self):
        """計算期貨交易手續費 (假設為0.00002)"""
        return self.future.bid_price * 1000 * 0.00002 if self.future.bid_price > 0 else 0
    
    @property
    def StockCost(self):
        """計算股票交易成本 (假設為0.001425 + 0.003)"""
        return self.stock.ask_price * 1000 * (0.001425 + 0.003) if self.stock.ask_price > 0 else 0
    
    @property
    def ExpectProfit(self):
        """預期華價 (期貨賣價 - 期貨買價 + 股票賣價 - 股票買價) * 合約乘數"""
        return (self.future.ask_price - self.future.bid_price + self.stock.ask_price - self.stock.bid_price) * 500 if (self.future.ask_price > 0 and self.future.bid_price > 0 and self.stock.ask_price > 0 and self.stock.bid_price > 0) else 0
    
    @property
    def TotalCost(self):
        """計算總成本"""
        return self.FutureFee + self.StockCost + self.ExpectProfit
    
    @property
    def GrossProfit(self):
        """毛利 (價差 * 合約乘數)"""
        return abs(self.Spread_StockAsk_FutureBid) * 1000
    
    @property
    def NetProfit(self):
        """淨利 (毛利 - 總成本)"""
        return max(self.GrossProfit - self.TotalCost, 0)
    
    @property
    def NetProfitRate(self):
        """淨利率"""
        return (self.NetProfit / (self.future.bid_price * 1000)) * 100 if (self.future.bid_price > 0 and self.NetProfit > 0) else 0
    
    @property
    def EfficiencyScore(self):
        """效率分數"""
        return self.NetProfitRate / (abs(self.Spread_StockAsk_FutureBid) / self.future.bid_price * 100) if (self.future.bid_price > 0 and self.Spread_StockAsk_FutureBid != 0) else 0
    
    @property
    def OpportunityScore(self):
        """機會分數"""
        if not self.CompleteData or not self.Positive_Future or not self.Positive_Stock:
            return 0
        if self.NetProfitRate >= 0.005:
            return 4
        elif self.NetProfitRate >= 0.003:
            return 3
        elif self.NetProfitRate >= 0.001:
            return 2
        if self.NetProfitRate > 0:
            return 1
        return 0

    @property
    def ArbitrageDirection(self):
        if self.Spread_StockAsk_FutureBid > 0 and self.OpportunityScore > 1:
            return "買股賣期(正價差)"
        if self.Spread_FutureAsk_StockBid > 0 and self.OpportunityScore > 1:
            return "賣股買期(逆價差)"
        return None

    @property
    def stock_name(self):
        if self.stock.stock_name:
            return self.stock.stock_name
        elif self.future.future_name:
            # 從期貨名稱推導股票名稱
            name = self.future.future_name.replace("期近月", "").replace("(一般)", "")
            return name.strip()
        return ""
    
    @property
    def stock_code(self):
        return self.stock.stock_no
    
    @property
    def future_code(self):
        return self.future.future_no
    
    @property
    def spread_future_bid_stock_ask(self):
        """期貨買價 - 股票賣價 (做多期貨、做空股票的價差)"""
        return self.future.bid_price - self.stock.ask_price if (self.future.bid_price > 0 and self.stock.ask_price > 0) else 0
    
    @property
    def spread_stock_bid_future_ask(self):
        """股票買價 - 期貨賣價 (做多股票、做空期貨的價差)"""
        return self.stock.bid_price - self.future.ask_price if (self.stock.bid_price > 0 and self.future.ask_price > 0) else 0
    
    @property
    def complete_data(self):
        """檢查是否有完整的買賣價資料"""
        return (self.future.bid_price > 0 and self.future.ask_price > 0 and 
                self.stock.bid_price > 0 and self.stock.ask_price > 0)
    
    @property
    def arbitrage_opportunity(self):
        """檢查是否有套利機會"""
        if not self.complete_data:
            return None
        
        # 期貨溢價套利 (期貨高於股票)
        future_premium = self.spread_future_bid_stock_ask
        # 期貨折價套利 (股票高於期貨)
        stock_premium = self.spread_stock_bid_future_ask
        
        return {
            'future_premium': future_premium,
            'stock_premium': stock_premium,
            'has_arbitrage': abs(future_premium) > 1 or abs(stock_premium) > 1
        }
    
    @property
    def contract_spread_value(self):
        """計算合約價差價值 (考慮合約乘數)"""
        if self.complete_data:
            spread = self.spread_future_bid_stock_ask
            return spread * self.future.multiplier
        return 0
    
    def get_spread_analysis(self):
        """取得詳細的價差分析"""
        return {
            'stock_info': {
                'code': self.stock_code,
                'name': self.stock_name,
                'bid': self.stock.bid_price,
                'ask': self.stock.ask_price,
                'close': self.stock.close_price
            },
            'future_info': {
                'code': self.future_code,
                'name': self.future.future_name,
                'bid': self.future.bid_price,
                'ask': self.future.ask_price,
                'close': self.future.close_price,
                'multiplier': self.future.multiplier
            },
            'spreads': {
                'future_minus_stock': self.spread_future_bid_stock_ask,
                'stock_minus_future': self.spread_stock_bid_future_ask,
                'contract_value': self.contract_spread_value
            },
            'arbitrage': self.arbitrage_opportunity,
            'complete_data': self.complete_data
        }

# 顯示各功能狀態用的function
def WriteMessage(strMsg, listInformation):
    """安全的訊息寫入函數 - 使用隊列機制避免 COM 事件衝突"""
    import datetime
    
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    formatted_message = f"[{timestamp}] {strMsg}"
    
    # 將消息放入隊列，而不是直接操作 GUI
    com_event_queue.put(('message', formatted_message, listInformation))

def process_com_events(root):
    """處理 COM 事件隊列中的消息"""
    try:
        while True:
            try:
                event_type, message, listbox = com_event_queue.get_nowait()
                if event_type == 'message' and listbox is not None:
                    # 檢查 listbox 是否還存在
                    if listbox.winfo_exists():
                        listbox.insert('end', message)
                        listbox.see('end')
            except queue.Empty:
                break
            except Exception as e:
                WriteMessage(f"Error processing COM event: {e}", GlobalListInformation)
                break
    except Exception as e:  
        WriteMessage(f"Error in process_com_events: {e}", GlobalListInformation)

    # 每100ms檢查一次隊列
    root.after(100, lambda: process_com_events(root))

def SendReturnMessage(strType, nCode, strMessage,listInformation):
    GetMessage(strType, nCode, strMessage,listInformation)

def GetMessage(strType,nCode,strMessage,listInformation):
    strInfo = ""
    if (nCode != 0):
        strInfo ="【"+ skC.SKCenterLib_GetLastLogInfo()+ "】"
    WriteMessage("【" + strType + "】【" + strMessage + "】【" + skC.SKCenterLib_GetReturnCodeMessage(nCode) + "】" + strInfo,listInformation)

def load_stock_codes():
    """從 StockList.txt 讀取股票代碼和名稱"""
    try:
        stock_codes = {}  # 改為字典，儲存代碼和名稱的對應
        stock_name_to_codes = {}  # 新增反向對應字典
        with open("data/StockList.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0].strip()
                    code = parts[1].strip()
                    stock_codes[code] = name
                    stock_name_to_codes[name] = code  # 添加反向對應
        return stock_codes, stock_name_to_codes
    except Exception as e:
        WriteMessage(f"讀取 StockList.txt 時發生錯誤: {str(e)}", GlobalListInformation)
        return {}, {}
def load_future_codes():
    """從 FutureList.txt 讀取期貨代碼和名稱"""
    try:
        future_codes = {}  # 改為字典，儲存代碼和名稱的對應
        future_name_to_codes = {}  # 新增反向對應字典
        with open("data/FutureList.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                parts = line.split()
                if len(parts) >= 2:
                    code = parts[0].strip()
                    name = parts[1].strip()
                    if code and ("F00" in code or "期" in name):  # 期貨代碼格式
                        future_codes[code] = name
                        future_name_to_codes[name] = code  # 添加反向對應
        return future_codes, future_name_to_codes

    except Exception as e:
        WriteMessage(f"讀取 FutureList.txt 時發生錯誤: {str(e)}", GlobalListInformation)
        return {}, {}
def create_quote_template():
    """創建類似圖片的報價模板"""
    count = 1 
    all_items = {}
    with open("data/QuoteTemplate.txt", "w", encoding="utf-8") as f:
        f.write("# 報價模板（類似圖片格式）\n")
        f.write("# 格式: 索引/編\t代碼\t商品名稱\t買進價格\t賣出價格\t成交價格\t買量\t賣量\t總量\n\n")
        for code, name in future_codes_to_name.items():
            f.write(f"{count}\t{code}\t{name}\t0.00\t0.00\t0.00\t0\t0\t0\n")
            temp = FutureInfo()
            temp.future_no = code
            temp.future_name = name
            all_items[code] = temp
            count += 1
        for code, name in stock_codes_to_name.items():
            f.write(f"{count}\t{code}\t{name}\t0.00\t0.00\t0.00\t0\t0\t0\n")
            temp = StockInfo()
            temp.stock_no = code
            temp.stock_name = name
            all_items[code] = temp
            count += 1
        return all_items
    
#----------------------------------------------------------------------------------------------------------------------------------------------------
# 登入頁面
class FrameLogin(Frame):
    def __init__(self):
        Frame.__init__(self)
        self.FrameLogin = Frame(self)
        self.FrameLogin.pack(fill="both", expand=True)
        self.createWidgets()
    def createWidgets(self):
        # 使用者ID
        # === 登入區塊 ===
        login_group = ttk.LabelFrame(self.FrameLogin, text="登入設定")
        login_group.pack(fill="x", padx=10, pady=5)
        ttk.Label(login_group, text="UserID:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.entry_userid = ttk.Entry(login_group, width=20)
        self.entry_userid.grid(row=0, column=1, padx=5, pady=2)
        
        # 密碼
        ttk.Label(login_group, text="Password:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.entry_password = ttk.Entry(login_group, width=20, show="*")
        self.entry_password.grid(row=1, column=1, padx=5, pady=2)

        # 登入按鈕
        self.btn_login = ttk.Button(login_group, text="登入", command=self.buttonLogin_Click)
        self.btn_login.grid(row=0, column=2, padx=10, pady=2)
        
        # === 連線控制區塊 ===
        connection_group = ttk.LabelFrame(self.FrameLogin, text="連線控制")
        connection_group.pack(fill="x", padx=10, pady=5)
        
        # 連線按鈕
        self.btn_connection = ttk.Button(connection_group, text="建立連線", command=self.btnConnect_Click)
        self.btn_connection.grid(row=0, column=0, padx=5, pady=5)
        self.btn_connection.config(state="disabled")
        
        # === 狀態顯示區塊 ===
        status_group = ttk.LabelFrame(self.FrameLogin, text="連線狀態")
        status_group.pack(fill="x", padx=10, pady=5)
        
        # 登入狀態
        ttk.Label(status_group, text="登入狀態:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.label_login_status = ttk.Label(status_group, text="未登入", foreground="red")
        self.label_login_status.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        # 連線狀態
        ttk.Label(status_group, text="連線狀態:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.label_connection_status = ttk.Label(status_group, text="未連線", foreground="red")
        self.label_connection_status.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        # === 訊息顯示區塊 ===
        message_group = ttk.LabelFrame(self.FrameLogin, text="系統訊息")
        message_group.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 創建訊息框和滾動條
        message_frame = ttk.Frame(message_group)
        message_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 訊息列表框
        self.listInformation = Listbox(message_frame, height=15, font=("Consolas", 9))
        self.listInformation.pack(side="left", fill="both", expand=True)
        
        # 滾動條
        scrollbar = ttk.Scrollbar(message_frame, orient="vertical", command=self.listInformation.yview)
        scrollbar.pack(side="right", fill="y")
        self.listInformation.config(yscrollcommand=scrollbar.set)
        
        # 清除訊息按鈕
        btn_frame = ttk.Frame(message_group)
        btn_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Button(btn_frame, text="清除訊息", command=self.clear_messages).pack(side="left")
        ttk.Button(btn_frame, text="匯出訊息", command=self.export_messages).pack(side="left", padx=5)

        # ID 標籤（用於全域變數）
        self.labelID = ttk.Label(status_group, text="")
        self.labelID.grid(row=0, column=2, sticky="w", padx=20, pady=2)

        # 設定全域變數
        global GlobalListInformation, Global_ID
        GlobalListInformation = self.listInformation
        Global_ID = self.labelID
        
        # 初始訊息
        self.add_message("系統初始化完成")
        self.add_message("請輸入帳號密碼並點擊登入")

    def buttonLogin_Click(self):
        try:
            user_id = self.entry_userid.get().replace(' ', '')
            password = self.entry_password.get().replace(' ', '')
            
            if not user_id or not password:
                self.add_message("錯誤: 請輸入帳號和密碼")
                return
            
            self.add_message(f"正在嘗試登入... 帳號: {user_id}")
            
            # 設定日誌路徑
            log_path = os.path.split(os.path.realpath(__file__))[0] + "\\CapitalLog_Quote"
            m_nCode = skC.SKCenterLib_SetLogPath(log_path)
            self.add_message(f"日誌路徑設定: {log_path}")
            
            self.add_message(f"{user_id} , {password}")
            # 登入
            m_nCode = skC.SKCenterLib_Login(user_id, password)
            
            if m_nCode == 0:
                self.label_login_status.config(text="已登入", foreground="green")
                self.btn_connection.config(state="normal")
                Global_ID["text"] = user_id
                self.add_message("登入成功!")
            else:
                self.label_login_status.config(text="登入失敗", foreground="red")
                error_msg = skC.SKCenterLib_GetReturnCodeMessage(m_nCode)
                self.add_message(f"登入失敗: {error_msg} (Code: {m_nCode})")
        except Exception as e:
            self.label_login_status.config(text="登入錯誤", foreground="red")
            self.add_message(f"登入異常: {str(e)}")
    
    def btnConnect_Click(self):
        """建立連線"""
        try:  
            # 執行連線操作
            self.add_message("正在建立連線...")
            m_nCode = skQ.SKQuoteLib_EnterMonitorLONG()
            SendReturnMessage("建立連線", m_nCode, "執行 SKQuoteLib_EnterMonitorLONG()", self.listInformation)
            if m_nCode == 0:
                self.label_connection_status["text"] = "狀態: 已連線"
                self.label_connection_status["foreground"] = "green"
                self.add_message("連線建立成功")
            else:
                self.label_connection_status["text"] = f"狀態: 連線失敗 (錯誤碼: {m_nCode})"
                self.label_connection_status["foreground"] = "red"
                self.add_message(f"連線失敗，錯誤碼: {m_nCode}")            
        except Exception as e:
            self.label_connection_status.config(text="連線異常", foreground="red")
            self.add_message(f"連線異常: {str(e)}")
    
    def add_message(self, message):
        """添加訊息到訊息框"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self.listInformation.insert('end', formatted_message)
        self.listInformation.see('end')  # 自動滾動到最新訊息
        
        # 限制訊息數量，避免記憶體問題
        if self.listInformation.size() > 1000:
            self.listInformation.delete(0, 100)
    
    def clear_messages(self):
        """清除所有訊息"""
        self.listInformation.delete(0, 'end')
        self.add_message("訊息已清除")
    
    def export_messages(self):
        """匯出訊息到文件"""
        try:
            import datetime
            from tkinter import filedialog
            
            # 獲取所有訊息
            messages = []
            for i in range(self.listInformation.size()):
                messages.append(self.listInformation.get(i))
            
            if not messages:
                self.add_message("沒有訊息可匯出")
                return
            
            # 選擇保存文件
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="匯出訊息到文件"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"SK API 系統訊息匯出\n")
                    f.write(f"匯出時間: {datetime.datetime.now()}\n")
                    f.write("=" * 50 + "\n\n")
                    for message in messages:
                        f.write(message + "\n")
                self.add_message(f"訊息已匯出至: {filename}", GlobalListInformation)
        except Exception as e:
            self.add_message(f"匯出訊息失敗: {str(e)}")

stock_codes_to_name, stock_name_to_codes = load_stock_codes()
future_codes_to_name,future_name_to_codes = load_future_codes()
all_stocks = create_quote_template()  
spread_map = {}
stock_to_spreadmap_index = {}
future_to_spreadmap_index = {}

#----------------------------------------------------------------------------------------------------------------------------------------------------
# 報價頁面
class Quote(Frame):
    def __init__(self, root = None):
        Frame.__init__(self)
        self.Quote = Frame(self)
        self.Quote.pack(fill="both", expand=True)

        self.main_window = root

        self.initialize_spread_info()

        self.quote_timer_id = None
                
        self.createWidgets()

    def createWidgets(self):
        # 控制區域
        control_frame = ttk.LabelFrame(self.Quote, text="報價控制")
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # 開始訂閱按鈕
        self.btn_start_quote = ttk.Button(control_frame, text="開始訂閱報價", command=self.start_quote_subscription)
        self.btn_start_quote.pack(side="left", padx=5, pady=5)
        # self.btn_start_quote.config(state="disabled")
        
        # 停止訂閱按鈕
        self.btn_stop_quote = ttk.Button(control_frame, text="停止訂閱", command=self.stop_quote_subscription)
        self.btn_stop_quote.pack(side="left", padx=5, pady=5)
        self.btn_stop_quote.config(state="disabled")
        
        # 報價狀態標籤
        self.label_quote_count = ttk.Label(control_frame, text="配對組數: 0")
        self.label_quote_count.pack(side="right", padx=5, pady=5)
        
        # 報價表格區域
        table_frame = ttk.LabelFrame(self.Quote, text="期貨股票價差監控")
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 建立Treeview表格 - 類似圖片中的格式
        columns = ("索引/編", "代碼", "商品名稱", "買進價格", "賣出價格", "成交價格", "買量", "賣量", "總量")
        
        self.quote_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=25)
        
        # 設定欄位標題和寬度
        column_widths = {
            "索引/編": 60,
            "代碼": 80, 
            "商品名稱": 120,
            "買進價格": 80,
            "賣出價格": 80,
            "成交價格": 80,
            "買量": 60,
            "賣量": 60,
            "總量": 80
        }
        
        for col in columns:
            self.quote_tree.heading(col, text=col)
            self.quote_tree.column(col, width=column_widths[col], anchor="center")
        
        # 加入滾動條
        v_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.quote_tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.quote_tree.xview)
        self.quote_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # 配置表格和滾動條位置
        self.quote_tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
    
    def btnQueryStocks_Click(self):
        try:
            if skQ is None:
                messagebox.showerror("錯誤", "SK Quote 物件未初始化")
                return
                
            if(self.txtPageNo.get().replace(' ','') == ''):
                pn = 0
            else:
                pn = int(self.txtPageNo.get())
            m_nCode = skQ.SKQuoteLib_RequestStocks(pn,self.txtStocks.get().replace(' ',''))
        except Exception as e:
            messagebox.showerror("error！",e)
    
    def initialize_spread_info(self):
        """初始化期貨股票配對資訊 - 使用Compare_Map.txt和現有清單文件"""
        try:
            # 讀取配對表
            compare_map = self.load_compare_map()
            
            WriteMessage(f"讀取到 {len(compare_map)} 組配對關係",GlobalListInformation)
            WriteMessage(f"讀取到 {len(stock_codes_to_name)} 個股票代碼",GlobalListInformation)
            WriteMessage(f"讀取到 {len(future_codes_to_name)} 個期貨代碼",GlobalListInformation)

            # 添加所有期貨
            count = 1 
            for future_name, future_short, stock_name, stock_code in compare_map:
                spread_info = PriceSpreadInfo()
                
                spread_info.stock.stock_no = stock_code
                spread_info.stock.stock_name = stock_codes_to_name[stock_code]
                spread_info.future.future_no = future_name_to_codes[future_name]
                spread_info.future.future_name = future_name
                
                # 加入 stock, future 到 spread_map 的 index 
                future_to_spreadmap_index[spread_info.future.future_no] = count
                stock_to_spreadmap_index[spread_info.stock.stock_no] = count

                # index -> spread_info 
                spread_map[count] = spread_info
                count += 1
            count -= 1
            WriteMessage(f"配對初始化完成，共 {count} 組有效配對", GlobalListInformation)
        except Exception as e:
            WriteMessage(f"初始化配對資訊時發生錯誤: {str(e)}", GlobalListInformation)

    def load_compare_map(self):
        """讀取 Compare_Map.txt 文件"""
        try:
            compare_map = []
            if not os.path.exists("data/Compare_Map.txt"):
                WriteMessage("錯誤: 找不到 Compare_Map.txt 文件", GlobalListInformation)
                return compare_map

            with open("data/Compare_Map.txt", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    parts = line.split()
                    if len(parts) >= 4:
                        future_name = parts[0].strip()
                        future_short = parts[1].strip()
                        stock_name = parts[2].strip()
                        stock_code = parts[3].strip()
                        compare_map.append((future_name, future_short, stock_name, stock_code))
            
            return compare_map
            
        except Exception as e:
            WriteMessage(f"讀取 Compare_Map.txt 時發生錯誤: {str(e)}", GlobalListInformation)
            return []

    def start_quote_subscription(self):
        """開始訂閱報價 - 分別訂閱股票和期貨"""
        try:
            if not spread_map:
                WriteMessage("錯誤: 沒有配對資訊可訂閱", GlobalListInformation)
                return

            WriteMessage(f"開始訂閱股票商品 ({len(all_stocks)} 筆)...", GlobalListInformation)
            success_count = 1
            all_stocks_list = ", ".join(all_stocks.keys())
            try: 
                skQ.SKQuoteLib_RequestStocks(1, all_stocks_list)  # 一次請求所有股票
            except Exception as e:
                WriteMessage(f"訂閱股票時發生錯誤: {e}", GlobalListInformation)

            WriteMessage(f"訂閱完成，成功 {success_count}/{len(all_stocks)} 筆", GlobalListInformation)
            
            # 啟動按鈕狀態
            self.btn_start_quote.config(state="disabled")
            self.btn_stop_quote.config(state="normal")
            
            # 啟動報價更新計時器
            self.start_quote_timer()            
        except Exception as e:
            WriteMessage(f"訂閱報價時發生錯誤: {str(e)}", GlobalListInformation)

    def stop_quote_subscription(self):
        """停止訂閱報價"""
        try:
            # 停止定時器
            if self.quote_timer_id:
                self.main_window.after_cancel(self.quote_timer_id)
                self.quote_timer_id = None
            
            # 更新按鈕狀態
            self.btn_start_quote.config(state="normal")
            self.btn_stop_quote.config(state="disabled")
            
            WriteMessage("已停止報價訂閱", GlobalListInformation)
        except Exception as e:
            WriteMessage(f"停止訂閱時發生錯誤: {str(e)}", GlobalListInformation)

    def start_quote_timer(self):
        """開始報價更新計時器"""
        def update_quotes():
            try:
                self.update_quote_grid()
                # 排程下次更新
                self.quote_timer_id = self.main_window.after(1000, update_quotes)  # 每秒更新
            except Exception as e:
                WriteMessage(f"更新報價時發生錯誤: {str(e)}", GlobalListInformation)
        
        # 開始更新循環
        self.quote_timer_id = self.main_window.after(100, update_quotes)
    
    def update_quote_grid(self):
        """更新報價表格 - 類似圖片中的格式"""
        try:
            # 清除現有項目
            for item in self.quote_tree.get_children():
                self.quote_tree.delete(item)
            
            # 新增更新的資料
            active_count = 0
            stock_with_data = 0
            future_with_data = 0
            all_items = []
            
            # 添加期貨資料
            for code, name in future_codes_to_name.items():
                index = future_to_spreadmap_index.get(code)
                if index is not None:  # 檢查 index 是否存在
                    spread_info = spread_map[index]
                    if spread_info.future.future_no:
                        future_data = {
                            'type': '期貨',
                            'code': spread_info.future.future_no,
                            'name': spread_info.future.future_name or name,
                            'bid_price': spread_info.future.bid_price,
                            'ask_price': spread_info.future.ask_price,
                            'close_price': spread_info.future.close_price,
                            'bid_volume': spread_info.future.bid_volume,
                            'ask_volume': spread_info.future.ask_volume,
                            'total_volume': getattr(spread_info.future, 'total_volume', 0)
                        }
                        all_items.append(future_data)
                        if spread_info.future.bid_price > 0 or spread_info.future.ask_price > 0:
                            future_with_data += 1
            # 添加股票資料            
            for code, name in stock_codes_to_name.items():
                index = stock_to_spreadmap_index.get(code)
                if index is not None:  # 檢查 index 是否存在
                    spread_info = spread_map[index]        
                    if spread_info.stock.stock_no:
                        stock_data = {
                            'type': '股票',
                            'code': spread_info.stock.stock_no,
                            'name': spread_info.stock.stock_name or name,
                            'bid_price': spread_info.stock.bid_price,
                            'ask_price': spread_info.stock.ask_price,
                            'close_price': spread_info.stock.close_price,
                            'bid_volume': spread_info.stock.bid_volume,
                            'ask_volume': spread_info.stock.ask_volume,
                            'total_volume': getattr(spread_info.stock, 'total_volume', 0)
                        }
                        all_items.append(stock_data)
                        if spread_info.stock.bid_price > 0 or spread_info.stock.ask_price > 0:
                            stock_with_data += 1
            all_items.sort(key=lambda x: (x['type'], x['code']))  # 先期貨後股票排序
            # 顯示資料
            for index, item in enumerate(all_items, 1):
                if item['name'] or item['bid_price'] > 0 or item['ask_price'] > 0:
                    values = (
                        str(index),
                        item['code'],
                        item['name'][:10] if item['name'] else '',  # 限制名稱長度
                        f"{item['bid_price']:.2f}" if item['bid_price'] > 0 else "0.00",
                        f"{item['ask_price']:.2f}" if item['ask_price'] > 0 else "0.00",
                        f"{item['close_price']:.2f}" if item['close_price'] > 0 else "0.00",
                        str(item['bid_volume']) if item['bid_volume'] > 0 else "0",
                        str(item['ask_volume']) if item['ask_volume'] > 0 else "0",
                        str(item['total_volume']) if item['total_volume'] > 0 else "0"
                    )
                    self.quote_tree.insert("", "end", values=values)
                    active_count += 1 
            # 更新狀態顯示
            status_text = f"顯示筆數: {active_count} | 股票有資料: {stock_with_data} | 期貨有資料: {future_with_data}"
            self.label_quote_count.config(text=status_text)    
        except Exception as e:
            WriteMessage(f"更新表格時發生錯誤: {str(e)}", GlobalListInformation)
    
    # def check_missing_data(self):
    #     """檢查缺失資料的配對組合"""
    #     try:
    #         missing_futures = []
    #         missing_stocks = []
    #         no_data_pairs = []
            
    #         for spread_info in spread_map.values():
    #             # 檢查期貨是否有資料
    #             has_future_data = (spread_info.future.bid_price > 0 or 
    #                              spread_info.future.ask_price > 0 or 
    #                              spread_info.future.close_price > 0)
                
    #             # 檢查股票是否有資料
    #             has_stock_data = (spread_info.stock.bid_price > 0 or 
    #                             spread_info.stock.ask_price > 0 or 
    #                             spread_info.stock.close_price > 0)
                
    #             if not has_future_data:
    #                 future_code = getattr(spread_info.future, 'future_no', 'Unknown')
    #                 missing_futures.append(f"{future_code} ({spread_info.stock_name})")
                
    #             if not has_stock_data:
    #                 stock_code = getattr(spread_info.stock, 'stock_no', 'Unknown')
    #                 missing_stocks.append(f"{stock_code} ({spread_info.stock_name})")
                
    #             if not has_future_data and not has_stock_data:
    #                 no_data_pairs.append(f"{spread_info.stock_name}")
            
    #         # 建立結果視窗
    #         result_window = tk.Toplevel(self.main_window)
    #         result_window.title("缺失資料分析")
    #         result_window.geometry("600x400")
            
    #         # 建立筆記本控制項
    #         notebook = ttk.Notebook(result_window)
    #         notebook.pack(fill="both", expand=True, padx=10, pady=10)
            
    #         # 無期貨資料頁面
    #         future_frame = ttk.Frame(notebook)
    #         notebook.add(future_frame, text=f"無期貨資料 ({len(missing_futures)})")
    #         future_text = tk.Text(future_frame, wrap=tk.WORD)
    #         future_scroll = ttk.Scrollbar(future_frame, orient="vertical", command=future_text.yview)
    #         future_text.configure(yscrollcommand=future_scroll.set)
    #         future_text.pack(side="left", fill="both", expand=True)
    #         future_scroll.pack(side="right", fill="y")
    #         future_text.insert("1.0", "\n".join(missing_futures))
            
    #         # 無股票資料頁面
    #         stock_frame = ttk.Frame(notebook)
    #         notebook.add(stock_frame, text=f"無股票資料 ({len(missing_stocks)})")
    #         stock_text = tk.Text(stock_frame, wrap=tk.WORD)
    #         stock_scroll = ttk.Scrollbar(stock_frame, orient="vertical", command=stock_text.yview)
    #         stock_text.configure(yscrollcommand=stock_scroll.set)
    #         stock_text.pack(side="left", fill="both", expand=True)
    #         stock_scroll.pack(side="right", fill="y")
    #         stock_text.insert("1.0", "\n".join(missing_stocks))
            
    #         # 完全無資料頁面
    #         no_data_frame = ttk.Frame(notebook)
    #         notebook.add(no_data_frame, text=f"完全無資料 ({len(no_data_pairs)})")
    #         no_data_text = tk.Text(no_data_frame, wrap=tk.WORD)
    #         no_data_scroll = ttk.Scrollbar(no_data_frame, orient="vertical", command=no_data_text.yview)
    #         no_data_text.configure(yscrollcommand=no_data_scroll.set)
    #         no_data_text.pack(side="left", fill="both", expand=True)
    #         no_data_scroll.pack(side="right", fill="y")
    #         no_data_text.insert("1.0", "\n".join(no_data_pairs))
            
    #         WriteMessage(f"缺失資料分析: 無期貨資料{len(missing_futures)}筆, 無股票資料{len(missing_stocks)}筆, 完全無資料{len(no_data_pairs)}筆")
            
    #     except Exception as e:
    #         WriteMessage(f"檢查缺失資料時發生錯誤: {str(e)}")

#----------------------------------------------------------------------------------------------------------------------------------------------------
# 總整理頁面    
class FrameInformation(Frame):
    def __init__(self, root=None):
        Frame.__init__(self)
        self.Information = Frame(self)
        self.Information.pack(fill="both", expand=True)
        self.main_window = root

        self.info_timer_id = None
        self.createWidgets()

    def createWidgets(self):
        # 控制區域
        control_frame = ttk.LabelFrame(self.Information, text="整理控制")
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # 開始整理按鈕
        self.btn_start_info = ttk.Button(control_frame, text="開始整理", command=self.start_info)
        self.btn_start_info.pack(side="left", padx=5, pady=5)

        # 停止整理按鈕
        self.btn_stop_info = ttk.Button(control_frame, text="停止整理", command=self.stop_info)
        self.btn_stop_info.pack(side="left", padx=5, pady=5)
        self.btn_stop_info.config(state="disabled")

        # 報價表格區域
        table_frame = ttk.LabelFrame(self.Information, text="期貨股票價差監控")
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
        # 建立Treeview表格 - 類似圖片中的格式
        columns = ("期貨名稱", "對照股票", "期貨買價", "期貨委買", "期貨賣價", "期貨委賣", "期貨成交", "股票買價", "股票委買", "股票賣價", "股票委賣", "股票成交", "期-股差額", "股-期差額")
        
        self.info_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=25)
        
        # 設定欄位標題和寬度
        column_widths = {
            "期貨名稱": 100, "對照股票": 100, "期貨買價": 80, "期貨委買": 80, "期貨賣價": 80, "期貨委賣": 80, "期貨成交": 80,
            "股票買價": 80, "股票委買": 80, "股票賣價": 80, "股票委賣": 80, "股票成交": 80, "期-股差額": 80, "股-期差額": 80
        }
        for col in columns:
            self.info_tree.heading(col, text=col)
            self.info_tree.column(col, width=column_widths[col], anchor="center")

        # 加入滾動條
        v_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.info_tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.info_tree.xview)
        self.info_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        # 配置表格和滾動條位置
        self.info_tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
   
    def start_info(self):
        WriteMessage(f"開始整理 ({len(all_stocks)} 筆資料)...", GlobalListInformation)
        self.btn_start_info.config(state="disabled")
        self.btn_stop_info.config(state="normal")
        # 啟動整理更新計時器
        self.start_info_timer() 
    
    def start_info_timer(self):
        """開始整理更新計時器"""
        def update_info():
            try:
                self.update_info_grid()
                # 排程下次更新
                self.info_timer_id = self.main_window.after(1000, update_info)  # 每秒更新
            except Exception as e:
                WriteMessage(f"更新資訊時發生錯誤: {str(e)}", GlobalListInformation)
        
        # 開始更新循環
        self.info_timer_id = self.main_window.after(100, update_info)

    def stop_info(self):
        try:
            if self.info_timer_id:
                self.main_window.after_cancel(self.info_timer_id)
                self.info_timer_id = None

            self.btn_start_info.config(state="normal")
            self.btn_stop_info.config(state="disabled")

            WriteMessage("已停止整理", GlobalListInformation)
        except Exception as e:
            WriteMessage(f"停止整理時發生錯誤: {str(e)}", GlobalListInformation)
        
    def update_info_grid(self):
        try:
            for item in self.info_tree.get_children():
                self.info_tree.delete(item)
            for index, spread_info in spread_map.items():
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

                    future_to_stock_diff = (future_bid - stock_ask) if (future_bid > 0 and stock_ask > 0) else 0
                    stock_to_future_diff = (stock_bid - future_ask) if (stock_bid > 0 and future_ask > 0) else 0

                    values = (
                        future_codes_to_name[spread_info.future.future_no] or "",
                        stock_codes_to_name[spread_info.stock.stock_no] or "",
                        f"{future_bid:.2f}" if future_bid > 0 else "0.00",
                        str(future_bid_volume) if future_bid_volume > 0 else "0",
                        f"{future_ask:.2f}" if future_ask > 0 else "0.00",
                        str(future_ask_volume) if future_ask_volume > 0 else "0",
                        f"{future_close:.2f}" if future_close > 0 else "0.00",
                        f"{stock_bid:.2f}" if stock_bid > 0 else "0.00",
                        str(stock_bid_volume) if stock_bid_volume > 0 else "0",
                        f"{stock_ask:.2f}" if stock_ask > 0 else "0.00",
                        str(stock_ask_volume) if stock_ask_volume > 0 else "0",
                        f"{stock_close:.2f}" if stock_close > 0 else "0.00",
                        f"{future_to_stock_diff:.2f}" if future_to_stock_diff != 0 else "0.00",
                        f"{stock_to_future_diff:.2f}" if stock_to_future_diff != 0 else "0.00"
                    )
                    self.info_tree.insert("", "end", values=values)
        except Exception as e:
            WriteMessage(f"更新資訊表格時發生錯誤: {str(e)}", GlobalListInformation)
#----------------------------------------------------------------------------------------------------------------------------------------------------
# 輸出頁面    
class FrameOutput(Frame):
    def __init__(self, root=None):
        Frame.__init__(self)
        self.Output = Frame(self)
        self.Output.pack(fill="both", expand=True)

        self.main_window = root

        self.Output_timer_id = None
        self.createWidgets()

    def createWidgets(self):
        # 控制區域
        control_frame = ttk.LabelFrame(self.Output, text="整理控制")
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # 開始整理按鈕
        self.btn_start_output = ttk.Button(control_frame, text="開始輸出", command=self.start_info)
        self.btn_start_output.pack(side="left", padx=5, pady=5)

        # 停止整理按鈕
        self.btn_stop_output = ttk.Button(control_frame, text="停止輸出", command=self.stop_info)
        self.btn_stop_output.pack(side="left", padx=5, pady=5)
        self.btn_stop_output.config(state="disabled")

        # 報價表格區域
        table_frame = ttk.LabelFrame(self.Output, text="期貨股票輸出監控")
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
        # 建立Treeview表格 - 類似圖片中的格式
        columns = ("股票名稱","股票代碼", "期貨名稱", "期貨代碼", "機會評級", "套利方向", "淨利潤", "股票買價", "期貨賣價", "股票賣價", "期貨買價" )
        
        self.output_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=25)
        
        # 設定欄位標題和寬度
        column_widths = {
            "股票名稱": 100, "股票代碼": 100, "期貨名稱": 100, "期貨代碼": 100, "機會評級": 100, "套利方向": 100, "淨利潤": 100, "股票買價": 100, "期貨賣價": 100, "股票賣價": 100, "期貨買價": 100
        }
        for col in columns:
            self.output_tree.heading(col, text=col)
            self.output_tree.column(col, width=column_widths[col], anchor="center")

        # 加入滾動條
        v_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.output_tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.output_tree.xview)
        self.output_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        # 配置表格和滾動條位置
        self.output_tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
    def start_info(self):
        WriteMessage(f"開始輸出 ({len(all_stocks)} 筆資料)...", GlobalListInformation)
        self.btn_start_output.config(state="disabled")
        self.btn_stop_output.config(state="normal")
        # 啟動整理更新計時器
        self.start_info_timer()
    def start_info_timer(self):
        """開始整理更新計時器"""
        def update_info():
            try:
                self.update_output_grid()
                # 排程下次更新
                self.Output_timer_id = self.main_window.after(1000, update_info)  # 每秒更新
            except Exception as e:
                WriteMessage(f"更新資訊時發生錯誤: {str(e)}", GlobalListInformation)
        
        # 開始更新循環
        self.Output_timer_id = self.main_window.after(100, update_info)
    def stop_info(self):
        try:
            if self.Output_timer_id:
                self.main_window.after_cancel(self.Output_timer_id)
                self.Output_timer_id = None

            self.btn_start_output.config(state="normal")
            self.btn_stop_output.config(state="disabled")

            WriteMessage("已停止整理", GlobalListInformation)
        except Exception as e:
            WriteMessage(f"停止整理時發生錯誤: {str(e)}", GlobalListInformation)
    def update_output_grid(self):
        try:
            for item in self.output_tree.get_children():
                self.output_tree.delete(item)
            all_items = []
            for index, spread_info in spread_map.items():
                if spread_info.ArbitrageDirection != None and spread_info.OpportunityScore != 1:
                    values = (
                        stock_codes_to_name[spread_info.stock.stock_no] or "",
                        spread_info.stock.stock_no or "",
                        future_codes_to_name[spread_info.future.future_no] or "",
                        spread_info.future.future_no or "",
                        str(spread_info.OpportunityScore) or "",
                        spread_info.ArbitrageDirection or "",
                        f"{spread_info.NetProfit:.2f}" if spread_info.NetProfit != 0 else "0.00",
                        f"{spread_info.stock.bid_price:.2f}" if spread_info.stock.bid_price > 0 else "0.00",
                        f"{spread_info.future.ask_price:.2f}" if spread_info.future.ask_price > 0 else "0.00",
                        f"{spread_info.stock.ask_price:.2f}" if spread_info.stock.ask_price > 0 else "0.00",
                        f"{spread_info.future.bid_price:.2f}" if spread_info.future.bid_price > 0 else "0.00",
                    )
                    all_items.append((str(spread_info.OpportunityScore), values))
                # 先照機會評級排，再用淨利潤排序
                all_items.sort(key=lambda t: (int(t[0]), float(t[1][6])), reverse=True)  # 按機會評級和淨利潤排序

            for score, values in all_items:
                self.output_tree.insert("", "end", values=values)
        except Exception as e:
            WriteMessage(f"更新輸出表格時發生錯誤: {str(e)}", GlobalListInformation)
#----------------------------------------------------------------------------------------------------------------------------------------------------

#事件        
class SKQuoteLibEvents:
    def OnConnection(self, nKind, nCode):
        """COM 事件回調 - 輕量化處理，避免重入問題"""
        try:
            # 只處理基本的消息映射，避免複雜操作
            message_map = {
                3001: "Connected!, 還不可報價",
                3002: "DisConnected!",
                3003: "Stocks ready!, 可以開始訂閱股票報價",
                3021: "Connect Error!"
            }
            
            strMsg = message_map.get(nKind, f"Unknown nKind={nKind}, nCode={nCode}")
            
            # 使用隊列機制
            WriteMessage(f"{strMsg}", GlobalListInformation)
            
        except Exception as e:
            WriteMessage(f"OnConnection Exception: {e}", GlobalListInformation)

    def OnNotifyQuoteLONG(self, sMarketNo, nStockidx):
        """COM 事件回調 - 輕量化處理"""
        try:
            stock_data = sk.SKSTOCKLONG()
            skQ.SKQuoteLib_GetStockByIndexLONG(sMarketNo, nStockidx, stock_data)

            # stock_data = SK.SKQuoteLib_GetStockByStockNo(sMarketNo, nStockIdx)
            if stock_data is None:
                return
                
            stock_no = stock_data.bstrStockNo.strip()
            
            # 檢查是否為股票或期貨並更新對應的資料
            if stock_no in stock_to_spreadmap_index:
                # 這是股票
                index = stock_to_spreadmap_index[stock_no]
                spread_info = spread_map[index]
                spread_info.stock.update(stock_data)
                spread_info.stock.stock_no = stock_no
                # WriteMessage(f"更新股票資料: {stock_no}")
                
            elif stock_no in future_to_spreadmap_index:
                # 這是期貨
                index = future_to_spreadmap_index[stock_no]
                spread_info = spread_map[index]
                spread_info.future.update(stock_data)
                spread_info.future.future_no = stock_no
                # WriteMessage(f"更新期貨資料: {stock_no}")
            
            # 更新通用股票資料
            if stock_no in all_stocks:
                all_stocks[stock_no].update(stock_data)    
        except Exception as e:
            WriteMessage(f"OnNotifyQuoteLONG Exception: {e}", GlobalListInformation)

SKQuoteEvent=SKQuoteLibEvents()
SKQuoteLibEventHandler = comtypes.client.GetEvents(skQ, SKQuoteEvent)

class SKReplyLibEvent():
    def OnReplyMessage(self, bstrUserID, bstrMessages):
        """COM 事件回調 - 輕量化處理"""
        try:
            WriteMessage(str(bstrMessages), GlobalListInformation)
            return -1
        except Exception as e:
            WriteMessage(f"OnReplyMessage Exception: {e}", GlobalListInformation)
            return -1

SKReplyEvent = SKReplyLibEvent()
SKReplyLibEventHandler = comtypes.client.GetEvents(skR, SKReplyEvent)

if __name__ == '__main__':
    #Globals.initialize()
    root = Tk()
    root.title("PythonExampleQuote - 完整功能")
    root.geometry("1400x900")  # 設定較大的視窗尺寸
    
    # 創建主要的 Notebook
    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True, padx=10, pady=10)
    
    # 登入頁面
    login_frame = FrameLogin()
    notebook.add(login_frame, text="登入")
    
    # 報價來源頁面
    quote_page = Quote(root=root)
    notebook.add(quote_page, text="報價來源")
    
    # 總整理頁面
    info_frame = FrameInformation(root=root)
    notebook.add(info_frame, text="總整理")

    # 輸出頁面
    output_frame = FrameOutput(root=root)
    notebook.add(output_frame, text="輸出")

    # 啟動 COM 事件處理隊列
    process_com_events(root)

    root.mainloop()
