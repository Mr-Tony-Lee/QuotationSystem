import pandas as pd
import os
from io import StringIO
from typing import Union
# from .constants import StockList, FutureList, Compare_Map # Removed
from .models import StockInfo, FutureInfo, PriceSpreadInfo
from .logger import logger

class DataManager:
    def __init__(self):
        self.sk_client = None  # Reference to SKClient
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        
        self.stock_codes_to_name = {}
        self.stock_name_to_codes = {}
        self.future_codes_to_name = {}
        self.future_name_to_codes = {}
        
        self.all_stocks = {}  # dict[str, Union[StockInfo, FutureInfo]]
        self.spread_map = {}  # dict[int, PriceSpreadInfo]
        self.stock_to_spreadmap_index = {} # dict[str, int]
        self.future_to_spreadmap_index = {} # dict[str, int]
        
        self._load_data()
        self._initialize_spread_info()
        self._initialize_all_stocks()
        
        self.accounts = [] # list of dict: {login_id, market, branch_code, branch_name, account_no, id_number, name}
        
        self.position_callbacks = [] # list of callable
        self.kline_callbacks = {} # dict[stock_no, callable]
        self.kline_data = {} # dict[stock_no, list]

    def set_sk_client(self, client):
        self.sk_client = client

    def _read_file_content(self, filename):
        try:
            path = os.path.join(self.data_dir, filename)
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.write_message(f"Failed to read {filename}: {e}")
            return ""

    def _load_data(self):
        # Load StockList
        try:
            content = self._read_file_content('StockList.txt')
            if content:
                df = pd.read_csv(StringIO(content), sep=' ', header=None, names=['name', 'code'], dtype=str, engine='python')
                self.stock_codes_to_name = dict(zip(df['code'], df['name']))
                self.stock_name_to_codes = dict(zip(df['name'], df['code']))
        except Exception as e:
            logger.write_message(f"Load StockList Failed: {e}")

        # Load FutureList
        try:
            content = self._read_file_content('FutureList.txt')
            if content:
                df = pd.read_csv(StringIO(content), sep=' ', header=None, names=['code', 'name'], dtype=str, engine='python')
                self.future_codes_to_name = dict(zip(df['code'], df['name']))
                self.future_name_to_codes = dict(zip(df['name'], df['code']))
        except Exception as e:
            logger.write_message(f"Load FutureList Failed: {e}")

    def _initialize_spread_info(self):
        try:
            content = self._read_file_content('Compare_Map.txt')
            if content:
                df = pd.read_csv(StringIO(content), sep='\\s+', header=None, 
                                 names=['future_name', 'future_short', 'stock_name', 'stock_code'], 
                                 dtype=str, engine='python')
            compare_list = list(df.itertuples(index=False, name=None))
            
            count = 1
            for future_name, future_short, stock_name, stock_code in compare_list:
                spread_info = PriceSpreadInfo()
                
                # Setup Stock
                spread_info.stock.stock_no = stock_code
                spread_info.stock.stock_name = self.stock_codes_to_name.get(stock_code, stock_name)
                
                # Setup Future
                future_code = self.future_name_to_codes.get(future_name, "")
                spread_info.future.future_no = future_code
                spread_info.future.future_name = future_name
                
                if future_code:
                    self.future_to_spreadmap_index[future_code] = count
                else:
                    logger.write_message(f"Warning: Future code not found for {future_name}")

                if stock_code:
                    self.stock_to_spreadmap_index[stock_code] = count
                
                self.spread_map[count] = spread_info
                count += 1
                
            logger.write_message(f"配對初始化完成，共 {count-1} 組有效配對")
            
        except Exception as e:
            logger.write_message(f"Initialize Spread Info Failed: {e}")

    def _initialize_all_stocks(self):
        for code, name in self.future_codes_to_name.items():
            temp = FutureInfo()
            temp.future_no = code
            temp.future_name = name
            self.all_stocks[code] = temp
            
        for code, name in self.stock_codes_to_name.items():
            temp = StockInfo()
            temp.stock_no = code
            temp.stock_name = name
            self.all_stocks[code] = temp

    def update_quote(self, stock_data):
        stock_no = stock_data.bstrStockNo.strip()
        
        # Update Spread Map
        if stock_no in self.stock_to_spreadmap_index:
            index = self.stock_to_spreadmap_index[stock_no]
            self.spread_map[index].stock.update(stock_data)
            self.spread_map[index].stock.stock_no = stock_no
            
        elif stock_no in self.future_to_spreadmap_index:
            index = self.future_to_spreadmap_index[stock_no]
            self.spread_map[index].future.update(stock_data)
            self.spread_map[index].future.future_no = stock_no
            
        # Update All Stocks
        if stock_no in self.all_stocks:
            self.all_stocks[stock_no].update(stock_data)

    def add_account(self, login_id, account_data):
        """
        Store account info.
        data format: {market, branch_code, branch_name, account_no, id_number, name}
        """
        # Check for duplicates
        for acc in self.accounts:
            if acc['login_id'] == login_id and acc['account_no'] == account_data['account_no']:
                return

        account_info = {
            'login_id': login_id,
            **account_data
        }
        self.accounts.append(account_info)
        logger.write_message(f"Account added: {account_info['account_no']} ({account_info['name']})")
        
        # Notify position page if needed (or just let it query)
        # We could add an OnAccount callback list too if strictly needed.


    def add_position_callback(self, callback):
        self.position_callbacks.append(callback)
        
    def update_position(self, data_str, source='TF'):
        logger.write_message(f"DataManager received position data ({source}): {data_str}")
        for callback in self.position_callbacks:
            try:
                callback(data_str, source)
            except Exception as e:
                logger.write_message(f"Position callback failed: {e}")

    def register_kline_callback(self, stock_no, callback):
        """Register a callback for KLine updates for a specific stock"""
        self.kline_callbacks[stock_no] = callback

    def update_kline(self, stock_no, data_str):
        """
        Handle incoming KLine data. 
        Format usually: Date,Open,High,Low,Close,Volume
        It might be a full history dump or an update.
        """
        try:
            # logger.write_message(f"DataManager update_kline: {stock_no} len={len(data_str)}")
            
            if stock_no not in self.kline_data:
                self.kline_data[stock_no] = []
            
            new_records = []
            lines = data_str.strip().split('\n')
            
            # Simple parsing (adjust based on actual API format)
            # data_str might be "20230101,100,105,95,102,500"
            for line in lines:
                parts = line.split(',')
                if len(parts) >= 6:
                    record = {
                        'date': parts[0],
                        'open': float(parts[1]),
                        'high': float(parts[2]),
                        'low': float(parts[3]),
                        'close': float(parts[4]),
                        'volume': int(parts[5])
                    }
                    new_records.append(record)
            
            if new_records:
                self.kline_data[stock_no].extend(new_records)
                
                # Setup DataFrame for plotting
                # Note: We might want to optimize this to not create DF every time on high frequency
                # But for KLine usually it's okay.
                
                # Notify callback
                if stock_no in self.kline_callbacks:
                    self.kline_callbacks[stock_no](stock_no, new_records)
                    
        except Exception as e:
            logger.write_message(f"Update KLine failed: {e}")


    def get_market_data_df(self, filter_options=None):
        """Prepare data for Quote UI"""
        # This logic is moved from Quote.update_quote_grid
        # We can implement helper methods here to return raw data lists
        # allowing UI to handle DataFrame creation if it wants to keep UI logic separate
        # But for performance we can process here.
        
        data_list = []
        
        # Collect Data (Similar to Quote.update_quote_grid logic)
        for code, name in self.future_codes_to_name.items():
            index = self.future_to_spreadmap_index.get(code)
            if index is not None:
                spread_info = self.spread_map[index]
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
                        
        for code, name in self.stock_codes_to_name.items():
            index = self.stock_to_spreadmap_index.get(code)
            if index is not None:
                spread_info = self.spread_map[index]
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
        
        return pd.DataFrame(data_list) if data_list else pd.DataFrame()
