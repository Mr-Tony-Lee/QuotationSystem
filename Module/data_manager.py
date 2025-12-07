import pandas as pd
from io import StringIO
from typing import Union
from .constants import StockList, FutureList, Compare_Map
from .models import StockInfo, FutureInfo, PriceSpreadInfo
from .logger import logger

class DataManager:
    def __init__(self):
        self.sk_client = None  # Reference to SKClient
        
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

    def set_sk_client(self, client):
        self.sk_client = client

    def _load_data(self):
        # Load StockList
        try:
            df = pd.read_csv(StringIO(StockList), sep=' ', header=None, names=['name', 'code'], dtype=str, engine='python')
            self.stock_codes_to_name = dict(zip(df['code'], df['name']))
            self.stock_name_to_codes = dict(zip(df['name'], df['code']))
        except Exception as e:
            logger.write_message(f"Load StockList Failed: {e}")

        # Load FutureList
        try:
            df = pd.read_csv(StringIO(FutureList), sep=' ', header=None, names=['code', 'name'], dtype=str, engine='python')
            self.future_codes_to_name = dict(zip(df['code'], df['name']))
            self.future_name_to_codes = dict(zip(df['name'], df['code']))
        except Exception as e:
            logger.write_message(f"Load FutureList Failed: {e}")

    def _initialize_spread_info(self):
        try:
            df = pd.read_csv(StringIO(Compare_Map), sep='\\s+', header=None, 
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
