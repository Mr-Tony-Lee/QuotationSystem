import comtypes.client
import comtypes.gen.SKCOMLib as sk
import os
from .logger import logger
from .models import StockInfo, FutureInfo

class SKClient:
    def __init__(self):
        self.skC = None
        self.skQ = None
        self.skR = None
        self.skO = None
        self.skOSQ = None
        self.skOOQ = None
        self._initialize_com()
        
        self.m_nCode = 0
        self.sk_order_lib_events = None
        
    def _initialize_com(self):
        try:
            # 確保 DLL 存在
            if not os.path.exists('SKCOM.dll'):
                logger.write_message("Error: SKCOM.dll not found (SKClient init)")
            
            # 加載模組 (如果已經加載過，comtypes 會處理)
            try:
                comtypes.client.GetModule('SKCOM.dll')
            except Exception as e:
                logger.write_message(f"GetModule failed: {e}")

            self.skC = comtypes.client.CreateObject(sk.SKCenterLib, interface=sk.ISKCenterLib)
            self.skQ = comtypes.client.CreateObject(sk.SKQuoteLib, interface=sk.ISKQuoteLib)
            self.skR = comtypes.client.CreateObject(sk.SKReplyLib, interface=sk.ISKReplyLib)
            self.skO = comtypes.client.CreateObject(sk.SKOrderLib, interface=sk.ISKOrderLib)
            self.skOSQ = comtypes.client.CreateObject(sk.SKOSQuoteLib, interface=sk.ISKOSQuoteLib)
            self.skOOQ = comtypes.client.CreateObject(sk.SKOOQuoteLib, interface=sk.ISKOOQuoteLib)
            
        except Exception as e:
            logger.write_message(f"COM Object Initialization failed: {e}")

    def login(self, user_id, password):
        try:
            log_path = os.path.split(os.path.realpath(__file__))[0] + "\\CapitalLog_Quote"
            if not os.path.exists(log_path):
                os.makedirs(log_path)
                
            self.skC.SKCenterLib_SetLogPath(log_path)
            logger.write_message(f"日誌路徑設定: {log_path}")
            
            self.user_id = user_id
            m_nCode = self.skC.SKCenterLib_Login(user_id, password)
            self.log_return_code("Login", m_nCode, "Login Check")
            return m_nCode
        except Exception as e:
            logger.write_message(f"Login failed: {e}")
            return -1

    def connect(self):
        try:
            m_nCode = self.skQ.SKQuoteLib_EnterMonitorLONG()
            self.log_return_code("Connect", m_nCode, "EnterMonitorLONG")
            
            # Initialize Order Lib (Call shared method)
            self.initialize_order_api()
            
            return m_nCode
            
            return m_nCode
        except Exception as e:
            logger.write_message(f"Connect failed: {e}")
            return -1

    def request_stocks(self, page_no, stock_ids):
        try:
            m_nCode = self.skQ.SKQuoteLib_RequestStocks(page_no, stock_ids)
            # self.log_return_code("RequestStocks", m_nCode, f"Requesting {stock_ids}")
            return m_nCode
        except Exception as e:
            logger.write_message(f"RequestStocks failed: {e}")
            return -1

            logger.write_message(f"RequestStocks failed: {e}")
            return -1

        except Exception as e:
            logger.write_message(f"RequestStocks failed: {e}")
            return -1

    def initialize_order_api(self):
        """Initializes the Order Library and reads certificate"""
        try:
            m_nCode = self.skO.SKOrderLib_Initialize()
            self.log_return_code("OrderInit", m_nCode, "SKOrderLib_Initialize")
            
            if getattr(self, 'user_id', None):
                m_nCode = self.skO.ReadCertByID(self.user_id)
                self.log_return_code("ReadCert", m_nCode, "ReadCertByID")
            return m_nCode
        except Exception as e:
            logger.write_message(f"Initialize Order API failed: {e}")
            return -1

    def get_user_account(self):
        try:
            m_nCode = self.skO.GetUserAccount()
            self.log_return_code("GetUserAccount", m_nCode, "Request User Account")
            return m_nCode
        except Exception as e:
            logger.write_message(f"GetUserAccount failed: {e}")
            return -1
            
            return m_nCode
        except Exception as e:
            logger.write_message(f"GetUserAccount failed: {e}")
            return -1

    def get_real_balance_report(self, login_id, account_id):
        try:
            m_nCode = self.skO.GetRealBalanceReport(login_id, account_id)
            self.log_return_code("GetRealBalanceReport", m_nCode, f"Request Real Balance {account_id}")
            return m_nCode
        except Exception as e:
            logger.write_message(f"GetRealBalanceReport failed: {e}")
            return -1
    def get_open_interest(self, login_id, account_id):
        try:
            # skO.GetOpenInterest(login_id, account_id)
            if not account_id:
                logger.write_message("錯誤: GetOpenInterest 需要帳號 (Account)")
                return -1
                
            m_nCode = self.skO.GetOpenInterest(login_id, account_id)
            self.log_return_code("GetOpenInterest", m_nCode, f"Request Open Interest {account_id}")
            return m_nCode
        except Exception as e:
            logger.write_message(f"GetOpenInterest failed: {e}")
            return -1

    def get_return_code_message(self, nCode):
        return self.skC.SKCenterLib_GetReturnCodeMessage(nCode)

    def log_return_code(self, func_name, nCode, message=""):
        msg = self.get_return_code_message(nCode)
        base_msg = f"【{func_name}】【{message}】【{msg}】"
        if nCode != 0:
            last_info = self.skC.SKCenterLib_GetLastLogInfo()
            base_msg += f"【{last_info}】"
        logger.write_message(base_msg)


class SKQuoteLibEvents:
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def OnConnection(self, nKind, nCode):
        try:
            message_map = {
                3001: "Connected!, 還不可報價",
                3002: "DisConnected!",
                3003: "Stocks ready!, 可以開始訂閱股票報價",
                3021: "Connect Error!"
            }
            strMsg = message_map.get(nKind, f"Unknown nKind={nKind}, nCode={nCode}")
            logger.write_message(f"{strMsg}")
        except Exception as e:
            logger.write_message(f"OnConnection Exception: {e}")

    def OnNotifyQuoteLONG(self, sMarketNo, nStockidx):
        try:
            stock_data = sk.SKSTOCKLONG()
            # Note: We need access to skQ here. 
            # Ideally skQ should be passed or accessible.
            # Assuming sk_client is available globally or passed.
            # For now let's assume we can access it via data_manager if we attach it there, 
            # or we need to pass skQ to this event handler class.
            
            # Use the global sk_client instance concept or pass it in __init__
            if self.data_manager.sk_client:
                 self.data_manager.sk_client.skQ.SKQuoteLib_GetStockByIndexLONG(sMarketNo, nStockidx, stock_data)
            else:
                 return

            if stock_data is None:
                return

            self.data_manager.update_quote(stock_data)

        except Exception as e:
            logger.write_message(f"OnNotifyQuoteLONG Exception: {e}")

class SKReplyLibEvent:
    def OnReplyMessage(self, bstrUserID, bstrMessages):
        try:
            logger.write_message(f"Reply: {str(bstrMessages)}")
            return -1
        except Exception as e:
            logger.write_message(f"OnReplyMessage Exception: {e}")
            return -1
            return -1

class SKOrderLibEvents:
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def OnOpenInterest(self, strData):
        try:
            # strData format is usually comma separated
            logger.write_message(f"OnOpenInterest: {strData}")
            # We can parse this and update a model or trigger a UI update via data_manager
            # For now, just log it. 
            # Ideally data_manager should have a method to handle position data.
            self.data_manager.update_position(strData, source='TF')
        except Exception as e:
            logger.write_message(f"OnOpenInterest Exception: {e}")

    def OnAccount(self, bstrLogInID, bstrAccountData):
        try:
            # Format: Market,BranchCode,BranchName,Account,IDNumber,Name
            logger.write_message(f"OnAccount: {bstrAccountData}")
            
            # 『市場,分公司代碼,分公司,帳號,身份證字號,姓名』
            parts = bstrAccountData.split(',')
            if len(parts) >= 6:
                account_data = {
                    'market': parts[0],
                    'branch_code': parts[1],
                    'branch_name': parts[2],
                    'account_no': parts[3],
                    'id_number': parts[4],
                    'name': parts[5]
                }
                if self.data_manager:
                    self.data_manager.add_account(bstrLogInID, account_data)
            else:
                 logger.write_message(f"OnAccount data format error: {bstrAccountData}")

        except Exception as e:
            logger.write_message(f"OnAccount Exception: {e}")

    def OnRealBalanceReport(self, bstrData):
        try:
            logger.write_message(f"OnRealBalanceReport: {bstrData}")
            if self.data_manager:
                self.data_manager.update_position(bstrData, source='TS')
        except Exception as e:
            logger.write_message(f"OnRealBalanceReport Exception: {e}")
