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
    def Spread_FutureAsk_StockBid(self):
        """ 正價差 : 期貨賣價 - 股票買價 > 0 """
        """ 做多現貨、做空期貨"""
        return self.future.ask_price - self.stock.bid_price if (self.future.ask_price > 0 and self.stock.bid_price > 0) else 0
        

    @property
    def Spread_StockAsk_FutureBid(self):
        """逆價差 : 股票賣價 - 期貨買價"""
        """ 做多期貨、做空現貨"""
        return self.stock.ask_price - self.future.bid_price if (self.stock.ask_price > 0 and self.future.bid_price > 0) else 0

    @property
    def CompleteData(self):
        """檢查是否有完整的買賣價資料"""
        return (self.future.bid_price > 0 and self.future.ask_price > 0 and self.stock.bid_price > 0 and self.stock.ask_price > 0)
    
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
    def TotalCost(self):
        """計算總成本"""
        return self.FutureFee + self.StockCost 
    
    @property
    def PosGrossProfit(self):
        """正價差毛利 (價差 * 合約乘數)"""
        return self.Spread_FutureAsk_StockBid * 1000
    @property
    def NegGrossProfit(self):
        """逆價差毛利 (價差 * 合約乘數)"""
        return self.Spread_StockAsk_FutureBid * 1000
    
    @property
    def PosNetProfit(self):
        """正價差淨利"""
        return self.PosGrossProfit - self.TotalCost
    
    @property
    def NegNetProfit(self):
        """逆價差淨利"""
        return self.NegGrossProfit - self.TotalCost
    
    @property
    def PosNetProfitRate(self):
        """正價差淨利率"""
        return (self.PosNetProfit / (self.stock.ask_price * 1000)) * 100 if (self.stock.ask_price > 0 and self.PosNetProfit > 0) else 0
    
    @property
    def NegNetProfitRate(self):
        """逆價差淨利率"""
        return (self.NegNetProfit / (self.stock.bid_price * 1000)) * 100 if (self.stock.bid_price > 0 and self.NegNetProfit > 0) else 0

    @property
    def ArbitrageDirection(self):
        if self.Spread_FutureAsk_StockBid > 0 and self.PosNetProfit > self.NegNetProfit and self.PosNetProfitRate >= 0.001:
            return "買股賣期(正價差)"
        if self.Spread_StockAsk_FutureBid > 0 and self.NegNetProfitRate >= 0.001:
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
        future_premium = self.Spread_FutureAsk_StockBid
        # 期貨折價套利 (股票高於期貨)
        stock_premium = self.Spread_StockAsk_FutureBid
        
        return {
            'future_premium': future_premium,
            'stock_premium': stock_premium,
            'has_arbitrage': abs(future_premium) > 1 or abs(stock_premium) > 1
        }
    
    @property
    def contract_spread_value(self):
        """計算合約價差價值 (考慮合約乘數)"""
        if self.complete_data:
            spread = self.Spread_FutureAsk_StockBid
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
                'future_minus_stock': self.Spread_FutureAsk_StockBid,
                'stock_minus_future': self.Spread_StockAsk_FutureBid,
                'contract_value': self.contract_spread_value
            },
            'arbitrage': self.arbitrage_opportunity,
            'complete_data': self.complete_data
        }
