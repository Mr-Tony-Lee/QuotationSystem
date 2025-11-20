#----------------------------------------------------------------------------------------------------------------------------------------------------
# Import 必要模組
import os
import queue
from tkinter import *
from tkinter.ttk import *
from tkinter import messagebox,colorchooser,font,Button,Frame,Label,BooleanVar
from tkinter import ttk
import comtypes.client
import comtypes.gen.SKCOMLib as sk
import pandas as pd
from io import StringIO
from typing import Union

#----------------------------------------------------------------------------------------------------------------------------------------------------
# 創建一個全域的消息隊列來處理 COM 事件
com_event_queue = queue.Queue()

comtypes.client.GetModule('SKCOM.dll') #加此行需將API放與py同目錄
skC = comtypes.client.CreateObject(sk.SKCenterLib,interface=sk.ISKCenterLib)
skOOQ = comtypes.client.CreateObject(sk.SKOOQuoteLib,interface=sk.ISKOOQuoteLib)
skO = comtypes.client.CreateObject(sk.SKOrderLib,interface=sk.ISKOrderLib)
skOSQ = comtypes.client.CreateObject(sk.SKOSQuoteLib,interface=sk.ISKOSQuoteLib)
skQ = comtypes.client.CreateObject(sk.SKQuoteLib,interface=sk.ISKQuoteLib)
skR = comtypes.client.CreateObject(sk.SKReplyLib,interface=sk.ISKReplyLib)

#----------------------------------------------------------------------------------------------------------------------------------------------------
# 基本 class 和資料
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

    # @property
    # def EfficiencyScore(self):
    #     """效率分數"""
    #     return self.NetProfitRate / (abs(self.Spread_StockAsk_FutureBid) / self.future.bid_price * 100) if (self.future.bid_price > 0 and self.Spread_StockAsk_FutureBid != 0) else 0
    
    # @property
    # def OpportunityScore(self):
    #     """機會分數"""
    #     NetProfitRate = max(self.PosNetProfitRate,self.NegNetProfitRate)
    #     if not self.CompleteData or not self.Positive_Future or not self.Positive_Stock:
    #         return 0
    #     if NetProfitRate >= 0.005:
    #         return 4
    #     elif NetProfitRate >= 0.003:
    #         return 3
    #     elif NetProfitRate >= 0.001:
    #         return 2
    #     if NetProfitRate > 0:
    #         return 1
    #     return 0

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

StockList = """
元大台灣50 0050
元大高股息 0056
富邦上証 006205
元大上證50 006206
國泰中國A50 00636
富邦深100 00639
群益深証中小 00643
元大美債20年 00679B
國泰20年美債 00687B
元大美債1-3 00719B
統一FANG+ 00757
中信高評級公司債 00772B
國泰永續高股息 00878
富邦越南 00885
國泰智能電動車 00893
群益台灣精選高息 00919
群益台ESG低碳50 00923
復華台灣科技優息 00929
群益ESG投等債20+ 00937B
元大台灣價值高息 00940
台泥 1101
亞泥 1102
大成 1210
統一 1216
台塑 1301
南亞 1303
國喬 1312
中石化 1314
東陽 1319
台化 1326
遠東新 1402
南紡 1440
儒鴻 1476
聚陽 1477
士電 1503
東元 1504
中興電 1513
和大 1536
精華 1565
亞德客-KY 1590
華新 1605
大亞 1609
葡萄王 1707
長興 1717
中纖 1718
台肥 1722
美時 1795
台玻 1802
正隆 1904
華紙 1905
永豐餘 1907
榮成 1909
中鋼 2002
東和鋼鐵 2006
中鴻 2014
大成鋼 2027
上銀 2049
川湖 2059
正新 2105
裕隆 2201
為升 2231
光寶科 2301
聯電 2303
台達電 2308
金寶 2312
華通 2313
鴻海 2317
中環 2323
仁寶 2324
國巨 2327
廣宇 2328
台積電 2330
精英 2331
友訊 2332
旺宏 2337
光罩 2338
台亞 2340
華邦電 2344
智邦 2345
聯強 2347
佳世達 2352
宏碁 2353
鴻準 2354
敬鵬 2355
英業達 2356
華碩 2357
致茂 2360
金像電 2368
大同 2371
技嘉 2376
微星 2377
瑞昱 2379
廣達 2382
台光電 2383
群光 2385
威盛 2388
正崴 2392
億光 2393
凌陽 2401
漢唐 2404
南亞科 2408
友達 2409
中華電 2412
美律 2439
超豐 2441
京元電子 2449
聯發科 2454
全新 2455
飛宏 2457
義隆 2458
可成 2474
強茂 2481
兆赫 2485
一詮 2486
瑞軒 2489
華新科 2492
宏達電 2498
中工 2515
冠德 2520
興富發 2542
華固 2548
長榮 2603
新興 2605
裕民 2606
陽明 2609
華航 2610
萬海 2615
長榮航 2618
台灣高鐵 2633
漢翔 2634
彰銀 2801
臺企銀 2834
華南金 2880
富邦金 2881
國泰金 2882
凱基金 2883
玉山金 2884
元大金 2885
兆豐金 2886
台新金 2887
新光金 2888
永豐金 2890
中信金 2891
第一金 2892
農林 2913
潤泰全 2915
神基 3005
晶豪科 3006
大立光 3008
奇鋐 3017
亞光 3019
聯詠 3034
智原 3035
文曄 3036
欣興 3037
晶技 3042
健鼎 3044
台灣大 3045
僑威 3078
聯亞 3081
穩懋 3105
璟德 3152
景碩 3189
原相 3227
緯創 3231
威剛 3260
欣銓 3264
鈊象 3293
雙鴻 3324
精材 3374
新日興 3376
明泰 3380
玉晶光 3406
創意 3443
群創 3481
力旺 3529
台勝科 3532
嘉澤 3533
同致 3552
健策 3653
世芯-KY 3661
TPK-KY 3673
家登 3680
碩禾 3691
大聯大 3702
神達 3706
日月光投控 3711
富采 3714
晟德 4123
中天 4128
智擎 4162
泰博 4736
合一 4743
遠傳 4904
新唐 4919
和碩 4938
臻鼎-KY 4958
榮剛 5009
祥碩 5269
信驊 5274
世界 5347
中光電 5371
中磊 5388
台半 5425
宣德 5457
中美晶 5483
長虹 5534
中租-KY 5871
上海商銀 5876
合庫金 5880
寶雅 5904
群益證 6005
彩晶 6116
新普 6121
亞翔 6139
頎邦 6147
嘉聯益 6153
信昌電 6173
瑞儀 6176
合晶 6182
廣明 6188
聯茂 6213
旺矽 6223
力成 6239
立端 6245
矽格 6257
台郡 6269
同欣電 6271
台燿 6274
台表科 6278
胡連 6279
康舒 6282
啟碁 6285
樺漢 6414
元晶 6443
保瑞 6472
環球晶 6488
台塑化 6505
精測 6510
達發 6526
高端疫苗 6547
緯穎 6669
台灣虎航 6757
力積電 6770
台虹 8039
網家 8044
南電 8046
元太 8069
宏捷科 8086
至上 8112
南茂 8150
達方 8163
群聯 8299
金居 8358
大江 8436
富邦媒 8454
寶成 9904
美利達 9914
百和 9938
宏全 9939
潤泰新 9945
世紀鋼 9958
加權指數 TSE
電子 TSE23
金融保險 TSE28
台灣中型100指數 TWMC
"""

FutureList = """
CAF00 南亞期近月
CBF00 中鋼期近月
CCF00 聯電期近月(一般)
CDF00 台積電期近月(一般)
CEF00 富邦金期近月
CFF00 台塑期近月
CGF00 仁寶期近月
CHF00 友達期近月
CJF00 華南金期近月
CKF00 國泰金期近月
CLF00 兆豐金期近月
CMF00 台新金期近月
CNF00 中信金期近月
CQF00 統一期近月
CRF00 遠東新期近月
CSF00 華新期近月
CUF00 中環期近月
CWF00 佳世達期近月
CXF00 大同期近月
CYF00 南亞科期近月
CZF00 長榮期近月
DAF00 陽明期近月
DBF00 華航期近月
DCF00 彰銀期近月
DEF00 永豐金期近月
DFF00 台泥期近月
DGF00 台化期近月
DHF00 鴻海期近月
DIF00 旺宏期近月
DJF00 華碩期近月
DKF00 廣達期近月
DLF00 中華電期近月
DNF00 玉山金期近月
DOF00 元大金期近月
DPF00 第一金期近月
DQF00 群創期近月
DSF00 宏碁期近月
DVF00 聯發科期近月
DWF00 潤泰全期近月
DXF00 緯創期近月
DYF00 亞泥期近月
DZF00 大成期近月
EEF00 國喬期近月
EGF00 中石化期近月
EHF00 東陽期近月
EKF00 南紡期近月
EMF00 東元期近月
EPF00 亞德客-KY期近月
EYF00 中纖期近月
EZF00 台肥期近月
FBF00 東和鋼鐵期近月
FCF00 中鴻期近月
FEF00 大成鋼期近月
FFF00 上銀期近月
FGF00 川湖期近月
FKF00 正新期近月
FNF00 裕隆期近月
FQF00 光寶科期近月
FRF00 台達電期近月
FSF00 金寶期近月
FTF00 華通期近月
FVF00 精英期近月
FWF00 友訊期近月
FYF00 台亞期近月
FZF00 華邦電期近月
GAF00 聯強期近月
GCF00 鴻準期近月
GHF00 技嘉期近月
GIF00 微星期近月
GJF00 瑞昱期近月
GKF00 群光期近月
GLF00 正崴期近月
GMF00 億光期近月
GNF00 凌陽期近月
GOF00 漢唐期近月
GRF00 京元電子期近月
GUF00 全新期近月
GVF00 飛宏期近月
GWF00 義隆期近月
GXF00 可成期近月
GYF00 強茂期近月
GZF00 兆赫期近月
HAF00 瑞軒期近月
HBF00 華新科期近月
HCF00 宏達電期近月
HHF00 中工期近月
HIF00 冠德期近月
HLF00 興富發期近月
HOF00 華固期近月
HQF00 新興期近月
HSF00 長榮航期近月
IAF00 臺企銀期近月
IHF00 農林期近月
IIF00 晶豪科期近月
IJF00 大立光期近月
IMF00 亞光期近月
IOF00 聯詠期近月
IPF00 智原期近月
IQF00 文曄期近月
IRF00 欣興期近月
ITF00 晶技期近月
IXF00 景碩期近月
IYF00 新日興期近月
IZF00 明泰期近月
JBF00 創意期近月
JFF00 嘉澤期近月
JMF00 健策期近月
JNF00 TPK-KY期近月
JPF00 大聯大期近月
JSF00 和碩期近月
JWF00 長虹期近月
JXF00 群益證期近月
JZF00 嘉聯益期近月
KAF00 瑞儀期近月
KBF00 聯茂期近月
KCF00 力成期近月
KDF00 同欣電期近月
KEF00 台表科期近月
KFF00 康舒期近月
KGF00 啟碁期近月
KIF00 台虹期近月
KKF00 達方期近月
KLF00 寶成期近月
KOF00 宏全期近月
KPF00 潤泰新期近月
KSF00 聚陽期近月
KUF00 台玻期近月
KWF00 廣宇期近月
LBF00 健鼎期近月
LCF00 台灣大期近月
LEF00 玉晶光期近月
LIF00 台郡期近月
LMF00 美利達期近月
LOF00 合庫金期近月
LQF00 英業達期近月
LRF00 凱基金期近月
LTF00 遠傳期近月
LUF00 臻鼎-KY期近月
LVF00 中租-KY期近月
LWF00 儒鴻期近月
LXF00 國巨期近月
LYF00 南電期近月
MAF00 葡萄王期近月
MBF00 敬鵬期近月
MJF00 致茂期近月
MKF00 美律期近月
MQF00 矽格期近月
MVF00 百和期近月
MYF00 精華期近月
NAF00 穩懋期近月
NBF00 璟德期近月
NDF00 威剛期近月
NEF00 欣銓期近月
NGF00 碩禾期近月
NIF00 晟德期近月
NJF00 榮剛期近月
NLF00 世界期近月
NMF00 中光電期近月
NOF00 中美晶期近月
NQF00 新普期近月
NSF00 頎邦期近月
NUF00 網家期近月
NVF00 元太期近月
NWF00 群聯期近月
NYF00 元大台灣50ETF期近月(一般)
OAF00 富邦上証期近月
OBF00 元大上證50期近月
ODF00 為升期近月
OEF00 彩晶期近月
OHF00 胡連期近月
OJF00 國泰中國A50期近月
OKF00 富邦深100期近月
OLF00 小型大立光期近月
OMF00 小型精華期近月
OOF00 群益深証中小期近月
OPF00 智邦期近月
OQF00 樺漢期近月
ORF00 和大期近月
OSF00 榮成期近月
OTF00 聯亞期近月
OUF00 同致期近月
OVF00 台燿期近月
OWF00 環球晶期近月
OXF00 精測期近月
OYF00 小型精測期近月
OZF00 日月光投控期近月
PAF00 原相期近月
PBF00 小型環球晶期近月
PCF00 智擎期近月
PDF00 泰博期近月
PEF00 台半期近月
PFF00 元大高股息期近月
PGF00 台灣高鐵期近月
PHF00 祥碩期近月
PIF00 力旺期近月
PJF00 台光電期近月
PKF00 信昌電期近月
PLF00 合晶期近月
PMF00 大江期近月
PNF00 小型祥碩期近月
PPF00 宣德期近月
PQF00 金居期近月
PRF00 宏捷科期近月
PSF00 神達期近月
PTF00 雙鴻期近月
PUF00 小型聯發科期近月
PVF00 緯穎期近月
PWF00 小型緯穎期近月
PXF00 鈊象期近月
PYF00 小型鈊象期近月
PZF00 信驊期近月
QAF00 小型信驊期近月
QBF00 富采期近月
QCF00 裕民期近月
QDF00 台勝科期近月
QEF00 小型國巨期近月
QFF00 小型台積電期近月(一般)
QGF00 小型瑞昱期近月
QHF00 小型聯詠期近月
QIF00 小型穩懋期近月
QJF00 小型玉晶光期近月
QKF00 永豐餘期近月
QLF00 精材期近月
QMF00 小型上銀期近月
QNF00 小型群聯期近月
QOF00 長興期近月
QPF00 正隆期近月
QQF00 僑威期近月
QRF00 小型華碩期近月
QSF00 小型南電期近月
QTF00 超豐期近月
QUF00 南茂期近月
QVF00 光罩期近月
QWF00 威盛期近月
QXF00 萬海期近月
QYF00 高端疫苗期近月
QZF00 力積電期近月
RAF00 奇鋐期近月
RBF00 中磊期近月
RCF00 漢翔期近月
RDF00 中天期近月
REF00 新唐期近月
RFF00 小型嘉澤期近月
RGF00 小型健策期近月
RIF00 國泰永續高股息期近月
RJF00 大亞期近月
RKF00 金像電期近月
RLF00 元晶期近月
RMF00 富邦媒期近月
RNF00 合一期近月
ROF00 立端期近月
RPF00 寶雅期近月
RQF00 小型富邦媒期近月
RRF00 小型寶雅期近月
RSF00 小型力旺期近月
RUF00 世紀鋼期近月
RVF00 小型台達電期近月
RWF00 小型創意期近月
RXF00 富邦越南期近月
RYF00 群益台ESG低碳50期近月
RZF00 元大美債20年期近月(一般)
SAF00 美時期近月
SBF00 華紙期近月
SCF00 小型聚陽期近月
SDF00 中興電期近月
SEF00 小型智邦期近月
SFF00 小型台光電期近月
SGF00 國泰智能電動車期近月
SIF00 元大美債1-3期近月
SJF00 神基期近月
SKF00 至上期近月
SLF00 小型技嘉期近月
SMF00 群益台灣精選高息期近月
SNF00 復華台灣科技優息期近月
SQF00 中信高評級公司債期近月
SRF00 小型元大台灣50ETF期近月(一般)
SSF00 小型元大高股息期近月
SUF00 元大台灣價值高息期近月
SVF00 小型川湖期近月
SWF00 小型世紀鋼期近月
SYF00 家登期近月
SZF00 小型家登期近月
UAF00 士電期近月
UBF00 亞翔期近月
UCF00 廣明期近月
UEF00 上海商銀期近月
UFF00 台塑化期近月
UGF00 達發期近月
UHF00 小型奇鋐期近月
UIF00 小型達發期近月
UJF00 群益ESG投等債20+期近月
UKF00 國泰20年美債期近月
ULF00 小型雙鴻期近月
UMF00 世芯-KY期近月
UOF00 小型世芯-KY期近月
UPF00 保瑞期近月
UQF00 小型保瑞期近月
URF00 統一FANG+期近月
USF00 小型統一FANG+期近月
UTF00 一詮期近月
UUF00 台灣虎航期近月
UVF00 旺矽期近月
UWF00 小型旺矽期近月
"""

Compare_Map = """
南亞期近月 南亞期 南亞 1303
中鋼期近月 中鋼期 中鋼 2002
聯電期近月(一般) 聯電期 聯電 2303
台積電期近月(一般) 台積電期 台積電 2330
富邦金期近月 富邦金期 富邦金 2881
台塑期近月 台塑期 台塑 1301
仁寶期近月 仁寶期 仁寶 2324
友達期近月 友達期 友達 2409
華南金期近月 華南金期 華南金 2880
國泰金期近月 國泰金期 國泰金 2882
兆豐金期近月 兆豐金期 兆豐金 2886
台新金期近月 台新金期 台新金 2887
中信金期近月 中信金期 中信金 2891
統一期近月 統一期 統一 1216
遠東新期近月 遠東新期 遠東新 1402
華新期近月 華新期 華新 1605
中環期近月 中環期 中環 2323
佳世達期近月 佳世達期 佳世達 2352
大同期近月 大同期 大同 2371
南亞科期近月 南亞科期 南亞科 2408
長榮期近月 長榮期 長榮 2603
陽明期近月 陽明期 陽明 2609
華航期近月 華航期 華航 2610
彰銀期近月 彰銀期 彰銀 2801
永豐金期近月 永豐金期 永豐金 2890
台泥期近月 台泥期 台泥 1101
台化期近月 台化期 台化 1326
鴻海期近月 鴻海期 鴻海 2317
旺宏期近月 旺宏期 旺宏 2337
華碩期近月 華碩期 華碩 2357
廣達期近月 廣達期 廣達 2382
中華電期近月 中華電期 中華電 2412
玉山金期近月 玉山金期 玉山金 2884
元大金期近月 元大金期 元大金 2885
第一金期近月 第一金期 第一金 2892
群創期近月 群創期 群創 3481
宏碁期近月 宏碁期 宏碁 2353
聯發科期近月 聯發科期 聯發科 2454
潤泰全期近月 潤泰全期 潤泰全 2915
緯創期近月 緯創期 緯創 3231
亞泥期近月 亞泥期 亞泥 1102
大成期近月 大成期 大成 1210
國喬期近月 國喬期 國喬 1312
中石化期近月 中石化期 中石化 1314
東陽期近月 東陽期 東陽 1319
南紡期近月 南紡期 南紡 1440
東元期近月 東元期 東元 1504
亞德客-KY期近月 亞德客-KY期 亞德客-KY 1590
中纖期近月 中纖期 中纖 1718
台肥期近月 台肥期 台肥 1722
東和鋼鐵期近月 東和鋼鐵期 東和鋼鐵 2006
中鴻期近月 中鴻期 中鴻 2014
大成鋼期近月 大成鋼期 大成鋼 2027
上銀期近月 上銀期 上銀 2049
川湖期近月 川湖期 川湖 2059
正新期近月 正新期 正新 2105
裕隆期近月 裕隆期 裕隆 2201
光寶科期近月 光寶科期 光寶科 2301
台達電期近月 台達電期 台達電 2308
金寶期近月 金寶期 金寶 2312
華通期近月 華通期 華通 2313
精英期近月 精英期 精英 2331
友訊期近月 友訊期 友訊 2332
台亞期近月 台亞期 台亞 2340
華邦電期近月 華邦電期 華邦電 2344
聯強期近月 聯強期 聯強 2347
鴻準期近月 鴻準期 鴻準 2354
技嘉期近月 技嘉期 技嘉 2376
微星期近月 微星期 微星 2377
瑞昱期近月 瑞昱期 瑞昱 2379
群光期近月 群光期 群光 2385
正崴期近月 正崴期 正崴 2392
億光期近月 億光期 億光 2393
凌陽期近月 凌陽期 凌陽 2401
漢唐期近月 漢唐期 漢唐 2404
京元電子期近月 京元電子期 京元電子 2449
全新期近月 全新期 全新 2455
飛宏期近月 飛宏期 飛宏 2457
義隆期近月 義隆期 義隆 2458
可成期近月 可成期 可成 2474
強茂期近月 強茂期 強茂 2481
兆赫期近月 兆赫期 兆赫 2485
瑞軒期近月 瑞軒期 瑞軒 2489
華新科期近月 華新科期 華新科 2492
宏達電期近月 宏達電期 宏達電 2498
中工期近月 中工期 中工 2515
冠德期近月 冠德期 冠德 2520
興富發期近月 興富發期 興富發 2542
華固期近月 華固期 華固 2548
新興期近月 新興期 新興 2605
長榮航期近月 長榮航期 長榮航 2618
臺企銀期近月 臺企銀期 臺企銀 2834
農林期近月 農林期 農林 2913
晶豪科期近月 晶豪科期 晶豪科 3006
大立光期近月 大立光期 大立光 3008
亞光期近月 亞光期 亞光 3019
聯詠期近月 聯詠期 聯詠 3034
智原期近月 智原期 智原 3035
文曄期近月 文曄期 文曄 3036
欣興期近月 欣興期 欣興 3037
晶技期近月 晶技期 晶技 3042
景碩期近月 景碩期 景碩 3189
新日興期近月 新日興期 新日興 3376
明泰期近月 明泰期 明泰 3380
創意期近月 創意期 創意 3443
嘉澤期近月 嘉澤期 嘉澤 3533
健策期近月 健策期 健策 3653
TPK-KY期近月 TPK-KY期 TPK-KY 3673
大聯大期近月 大聯大期 大聯大 3702
和碩期近月 和碩期 和碩 4938
長虹期近月 長虹期 長虹 5534
群益證期近月 群益證期 群益證 6005
嘉聯益期近月 嘉聯益期 嘉聯益 6153
瑞儀期近月 瑞儀期 瑞儀 6176
聯茂期近月 聯茂期 聯茂 6213
力成期近月 力成期 力成 6239
同欣電期近月 同欣電期 同欣電 6271
台表科期近月 台表科期 台表科 6278
康舒期近月 康舒期 康舒 6282
啟碁期近月 啟碁期 啟碁 6285
台虹期近月 台虹期 台虹 8039
達方期近月 達方期 達方 8163
寶成期近月 寶成期 寶成 9904
宏全期近月 宏全期 宏全 9939
潤泰新期近月 潤泰新期 潤泰新 9945
聚陽期近月 聚陽期 聚陽 1477
台玻期近月 台玻期 台玻 1802
廣宇期近月 廣宇期 廣宇 2328
健鼎期近月 健鼎期 健鼎 3044
台灣大期近月 台灣大期 台灣大 3045
玉晶光期近月 玉晶光期 玉晶光 3406
台郡期近月 台郡期 台郡 6269
美利達期近月 美利達期 美利達 9914
合庫金期近月 合庫金期 合庫金 5880
英業達期近月 英業達期 英業達 2356
凱基金期近月 凱基金期 凱基金 2883
遠傳期近月 遠傳期 遠傳 4904
臻鼎-KY期近月 臻鼎-KY期 臻鼎-KY 4958
中租-KY期近月 中租-KY期 中租-KY 5871
儒鴻期近月 儒鴻期 儒鴻 1476
國巨期近月 國巨期 國巨 2327
南電期近月 南電期 南電 8046
葡萄王期近月 葡萄王期 葡萄王 1707
敬鵬期近月 敬鵬期 敬鵬 2355
致茂期近月 致茂期 致茂 2360
美律期近月 美律期 美律 2439
矽格期近月 矽格期 矽格 6257
百和期近月 百和期 百和 9938
精華期近月 精華期 精華 1565
穩懋期近月 穩懋期 穩懋 3105
璟德期近月 璟德期 璟德 3152
威剛期近月 威剛期 威剛 3260
欣銓期近月 欣銓期 欣銓 3264
碩禾期近月 碩禾期 碩禾 3691
晟德期近月 晟德期 晟德 4123
榮剛期近月 榮剛期 榮剛 5009
世界期近月 世界期 世界 5347
中光電期近月 中光電期 中光電 5371
中美晶期近月 中美晶期 中美晶 5483
新普期近月 新普期 新普 6121
頎邦期近月 頎邦期 頎邦 6147
網家期近月 網家期 網家 8044
元太期近月 元太期 元太 8069
群聯期近月 群聯期 群聯 8299
元大台灣50ETF期近月(一般) 元大台灣50ETF期 元大台灣50ETF 0050
富邦上証期近月 富邦上証期 富邦上証 006205
元大上證50期近月 元大上證50期 元大上證50 006206
為升期近月 為升期 為升 2231
彩晶期近月 彩晶期 彩晶 6116
胡連期近月 胡連期 胡連 6279
國泰中國A50期近月 國泰中國A50期 國泰中國A50 00636
富邦深100期近月 富邦深100期 富邦深100 00639
小型大立光期近月 小型大立光期 大立光 3008
小型精華期近月 小型精華期 精華 1565
群益深証中小期近月 群益深証中小期 群益深証中小 00643
智邦期近月 智邦期 智邦 2345
樺漢期近月 樺漢期 樺漢 6414
和大期近月 和大期 和大 1536
榮成期近月 榮成期 榮成 1909
聯亞期近月 聯亞期 聯亞 3081
同致期近月 同致期 同致 3552
台燿期近月 台燿期 台燿 6274
環球晶期近月 環球晶期 環球晶 6488
精測期近月 精測期 精測 6510
小型精測期近月 小型精測期 精測 6510
日月光投控期近月 日月光投控期 日月光投控 3711
原相期近月 原相期 原相 3227
小型環球晶期近月 小型環球晶期 環球晶 6488
智擎期近月 智擎期 智擎 4162
泰博期近月 泰博期 泰博 4736
台半期近月 台半期 台半 5425
元大高股息期近月 元大高股息期 元大高股息 0056
台灣高鐵期近月 台灣高鐵期 台灣高鐵 2633
祥碩期近月 祥碩期 祥碩 5269
力旺期近月 力旺期 力旺 3529
台光電期近月 台光電期 台光電 2383
信昌電期近月 信昌電期 信昌電 6173
合晶期近月 合晶期 合晶 6182
大江期近月 大江期 大江 8436
小型祥碩期近月 小型祥碩期 祥碩 5269
宣德期近月 宣德期 宣德 5457
金居期近月 金居期 金居 8358
宏捷科期近月 宏捷科期 宏捷科 8086
神達期近月 神達期 神達 3706
雙鴻期近月 雙鴻期 雙鴻 3324
小型聯發科期近月 小型聯發科期 聯發科 2454
緯穎期近月 緯穎期 緯穎 6669
小型緯穎期近月 小型緯穎期 緯穎 6669
鈊象期近月 鈊象期 鈊象 3293
小型鈊象期近月 小型鈊象期 鈊象 3293
信驊期近月 信驊期 信驊 5274
小型信驊期近月 小型信驊期 信驊 5274
富采期近月 富采期 富采 3714
裕民期近月 裕民期 裕民 2606
台勝科期近月 台勝科期 台勝科 3532
小型國巨期近月 小型國巨期 國巨 2327
小型台積電期近月(一般) 小型台積電期 台積電 2330
小型瑞昱期近月 小型瑞昱期 瑞昱 2379
小型聯詠期近月 小型聯詠期 聯詠 3034
小型穩懋期近月 小型穩懋期 穩懋 3105
小型玉晶光期近月 小型玉晶光期 玉晶光 3406
永豐餘期近月 永豐餘期 永豐餘 1907
精材期近月 精材期 精材 3374
小型上銀期近月 小型上銀期 上銀 2049
小型群聯期近月 小型群聯期 群聯 8299
長興期近月 長興期 長興 1717
正隆期近月 正隆期 正隆 1904
僑威期近月 僑威期 僑威 3078
小型華碩期近月 小型華碩期 華碩 2357
小型南電期近月 小型南電期 南電 8046
超豐期近月 超豐期 超豐 2441
南茂期近月 南茂期 南茂 8150
光罩期近月 光罩期 光罩 2338
威盛期近月 威盛期 威盛 2388
萬海期近月 萬海期 萬海 2615
高端疫苗期近月 高端疫苗期 高端疫苗 6547
力積電期近月 力積電期 力積電 6770
奇鋐期近月 奇鋐期 奇鋐 3017
中磊期近月 中磊期 中磊 5388
漢翔期近月 漢翔期 漢翔 2634
中天期近月 中天期 中天 4128
新唐期近月 新唐期 新唐 4919
小型嘉澤期近月 小型嘉澤期 嘉澤 3533
小型健策期近月 小型健策期 健策 3653
國泰永續高股息期近月 國泰永續高股息期 國泰永續高股息 00878
大亞期近月 大亞期 大亞 1609
金像電期近月 金像電期 金像電 2368
元晶期近月 元晶期 元晶 6443
富邦媒期近月 富邦媒期 富邦媒 8454
合一期近月 合一期 合一 4743
立端期近月 立端期 立端 6245
寶雅期近月 寶雅期 寶雅 5904
小型富邦媒期近月 小型富邦媒期 富邦媒 8454
小型寶雅期近月 小型寶雅期 寶雅 5904
小型力旺期近月 小型力旺期 力旺 3529
世紀鋼期近月 世紀鋼期 世紀鋼 9958
小型台達電期近月 小型台達電期 台達電 2308
小型創意期近月 小型創意期 創意 3443
富邦越南期近月 富邦越南期 富邦越南 00885
群益台ESG低碳50期近月 群益台ESG低碳50期 群益台ESG低碳50 00923
元大美債20年期近月(一般) 元大美債20年期 元大美債20年 00679B
美時期近月 美時期 美時 1795
華紙期近月 華紙期 華紙 1905
小型聚陽期近月 小型聚陽期 聚陽 1477
中興電期近月 中興電期 中興電 1513
小型智邦期近月 小型智邦期 智邦 2345
小型台光電期近月 小型台光電期 台光電 2383
國泰智能電動車期近月 國泰智能電動車期 國泰智能電動車 00893
元大美債1-3期近月 元大美債1-3期 元大美債1-3 00719B
神基期近月 神基期 神基 3005
至上期近月 至上期 至上 8112
小型技嘉期近月 小型技嘉期 技嘉 2376
群益台灣精選高息期近月 群益台灣精選高息期 群益台灣精選高息 00919
復華台灣科技優息期近月 復華台灣科技優息期 復華台灣科技優息 00929
中信高評級公司債期近月 中信高評級公司債期 中信高評級公司債 00772B
小型元大台灣50ETF期近月(一般) 小型元大台灣50ETF期 元大台灣50ETF 0050
小型元大高股息期近月 小型元大高股息期 元大高股息 0056
元大台灣價值高息期近月 元大台灣價值高息期 元大台灣價值高息 00940
小型川湖期近月 小型川湖期 川湖 2059
小型世紀鋼期近月 小型世紀鋼期 世紀鋼 9958
家登期近月 家登期 家登 3680
小型家登期近月 小型家登期 家登 3680
士電期近月 士電期 士電 1503
亞翔期近月 亞翔期 亞翔 6139
廣明期近月 廣明期 廣明 6188
上海商銀期近月 上海商銀期 上海商銀 5876
台塑化期近月 台塑化期 台塑化 6505
達發期近月 達發期 達發 6526
小型奇鋐期近月 小型奇鋐期 奇鋐 3017
小型達發期近月 小型達發期 達發 6526
群益ESG投等債20+期近月 群益ESG投等債20+期 群益ESG投等債20+ 00937B
國泰20年美債期近月 國泰20年美債期 國泰20年美債 00687B
小型雙鴻期近月 小型雙鴻期 雙鴻 3324
世芯-KY期近月 世芯-KY期 世芯-KY 3661
小型世芯-KY期近月 小型世芯-KY期 世芯-KY 3661
保瑞期近月 保瑞期 保瑞 6472
小型保瑞期近月 小型保瑞期 保瑞 6472
統一FANG+期近月 統一FANG+期 統一FANG+ 00757
小型統一FANG+期近月 小型統一FANG+期 統一FANG+ 00757
一詮期近月 一詮期 一詮 2486
台灣虎航期近月 台灣虎航期 台灣虎航 6757
旺矽期近月 旺矽期 旺矽 6223
小型旺矽期近月 小型旺矽期 旺矽 6223
"""

#----------------------------------------------------------------------------------------------------------------------------------------------------
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

def load_stock_codes() -> tuple[dict[str,str], dict[str,str]]:
    """從 StockList 讀取股票代碼和名稱 - 使用 pandas 優化"""
    try:
        # 使用 pandas 快速解析數據
        df = pd.read_csv(
            StringIO(StockList), 
            sep=' ',  # 使用空白字符分隔
            header=None, 
            names=['name', 'code'],
            dtype=str,
            engine='python'
        )
        # 創建字典映射（向量化操作，比循環快得多）
        stock_codes = dict(zip(df['code'], df['name']))
        stock_name_to_codes = dict(zip(df['name'], df['code']))
        return stock_codes, stock_name_to_codes
    except Exception as e:
        WriteMessage(f"加載股票代碼時發生錯誤: {e}", None)
        return {}, {}

def load_future_codes() -> tuple[dict[str,str], dict[str,str]]:
    """從 FutureList 讀取期貨代碼和名稱 - 使用 pandas 優化"""
    try:
        # 使用 pandas 快速解析數據
        df = pd.read_csv(
            StringIO(FutureList), 
            sep=' ',
            header=None, 
            names=['code', 'name'],
            dtype=str,
            engine='python'
        )
        # 創建字典映射（向量化操作）
        future_codes = dict(zip(df['code'], df['name']))
        future_name_to_codes = dict(zip(df['name'], df['code']))
        return future_codes, future_name_to_codes
    except Exception as e:
        WriteMessage(f"加載期貨代碼時發生錯誤: {e}", None)
        return {}, {}

def get_all_items() -> dict[str,Union[StockInfo,FutureInfo]]:
    count = 1 
    all_items = {}
    for code, name in future_codes_to_name.items():
        temp = FutureInfo()
        temp.future_no = code
        temp.future_name = name
        all_items[code] = temp
        count += 1
    for code, name in stock_codes_to_name.items():
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

stock_codes_to_name , stock_name_to_codes = load_stock_codes()
future_codes_to_name ,future_name_to_codes = load_future_codes()
all_stocks = get_all_items()  
spread_map : dict[int,PriceSpreadInfo] = {}
stock_to_spreadmap_index : dict[StockInfo,int] = {}
future_to_spreadmap_index : dict[FutureInfo,int] = {}

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
        
        # 🚀 性能優化：緩存 Treeview item IDs，避免每次都刪除重建
        self.tree_item_cache = {}  # {code: tree_item_id}
        self.last_data_cache = {}  # {code: last_values} - 用於檢測變化
        
        # 🔍 篩選功能變數
        self.filter_type = StringVar(value="全部")  # 類型篩選：全部/股票/期貨
        self.filter_names = []  # 名稱篩選列表
        self.filter_bid_op = StringVar(value="無限制")  # 買進價格操作：無限制/大於/小於
        self.filter_bid_value = StringVar(value="0")
        self.filter_ask_op = StringVar(value="無限制")  # 賣出價格操作
        self.filter_ask_value = StringVar(value="0")
        self.filter_close_op = StringVar(value="無限制")  # 成交價格操作
        self.filter_close_value = StringVar(value="0")
        self.filter_bid_vol_op = StringVar(value="無限制")  # 買量操作
        self.filter_bid_vol_value = StringVar(value="0")
        self.filter_ask_vol_op = StringVar(value="無限制")  # 賣量操作
        self.filter_ask_vol_value = StringVar(value="0")
        self.filter_total_vol_op = StringVar(value="無限制")  # 總量操作
        self.filter_total_vol_value = StringVar(value="0")
        self.filter_enabled = False  # 是否啟用篩選

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
    
    def create_filter_panel(self):
        """創建篩選面板"""
        self.filter_frame = ttk.LabelFrame(self.Quote, text="🔍 篩選條件")
        # 預設隱藏篩選面板
        # self.filter_frame.pack(fill="x", padx=10, pady=5)
        
        # 第一行：類型篩選
        row1 = ttk.Frame(self.filter_frame)
        row1.pack(fill="x", padx=5, pady=3)
        
        ttk.Label(row1, text="類型:").pack(side="left", padx=5)
        type_combo = ttk.Combobox(row1, textvariable=self.filter_type, width=10, state="readonly")
        type_combo['values'] = ("全部", "股票", "期貨")
        type_combo.pack(side="left", padx=5)
        
        # 清除篩選按鈕
        ttk.Button(row1, text="清除篩選", command=self.clear_filter).pack(side="left", padx=10)
        
        # 第二行：名稱篩選
        row2 = ttk.Frame(self.filter_frame)
        row2.pack(fill="x", padx=5, pady=3)
        
        ttk.Label(row2, text="名稱:").pack(side="left", padx=5)
        self.entry_filter_name = ttk.Entry(row2, width=30)
        self.entry_filter_name.pack(side="left", padx=5)
        self.entry_filter_name.bind('<KeyRelease>', self.on_name_filter_change)
        
        ttk.Button(row2, text="添加名稱", command=self.add_name_filter).pack(side="left", padx=5)
        
        # 顯示已選擇的名稱
        self.label_selected_names = ttk.Label(row2, text="已選: 無", foreground="blue")
        self.label_selected_names.pack(side="left", padx=10)
        
        ttk.Button(row2, text="清除名稱", command=self.clear_name_filter).pack(side="left", padx=5)
        
        # 名稱建議列表框（自動完成）
        self.name_suggest_frame = ttk.Frame(self.filter_frame)
        self.name_suggest_listbox = Listbox(self.name_suggest_frame, height=5)
        self.name_suggest_listbox.pack(fill="x")
        self.name_suggest_listbox.bind('<Double-Button-1>', self.select_suggested_name)
        # 預設隱藏
        
        # 第三行：價格篩選
        row3 = ttk.Frame(self.filter_frame)
        row3.pack(fill="x", padx=5, pady=3)
        
        # 買進價格
        ttk.Label(row3, text="買進價:").pack(side="left", padx=5)
        bid_op_combo = ttk.Combobox(row3, textvariable=self.filter_bid_op, width=8, state="readonly")
        bid_op_combo['values'] = ("無限制", "大於", "小於")
        bid_op_combo.pack(side="left", padx=2)
        ttk.Entry(row3, textvariable=self.filter_bid_value, width=10).pack(side="left", padx=2)
        
        # 賣出價格
        ttk.Label(row3, text="賣出價:").pack(side="left", padx=5)
        ask_op_combo = ttk.Combobox(row3, textvariable=self.filter_ask_op, width=8, state="readonly")
        ask_op_combo['values'] = ("無限制", "大於", "小於")
        ask_op_combo.pack(side="left", padx=2)
        ttk.Entry(row3, textvariable=self.filter_ask_value, width=10).pack(side="left", padx=2)
        
        # 成交價格
        ttk.Label(row3, text="成交價:").pack(side="left", padx=5)
        close_op_combo = ttk.Combobox(row3, textvariable=self.filter_close_op, width=8, state="readonly")
        close_op_combo['values'] = ("無限制", "大於", "小於")
        close_op_combo.pack(side="left", padx=2)
        ttk.Entry(row3, textvariable=self.filter_close_value, width=10).pack(side="left", padx=2)
        
        # 買量
        ttk.Label(row3, text="買量:").pack(side="left", padx=5)
        bid_vol_combo = ttk.Combobox(row3, textvariable=self.filter_bid_vol_op, width=8, state="readonly")
        bid_vol_combo['values'] = ("無限制", "大於", "小於")
        bid_vol_combo.pack(side="left", padx=2)
        ttk.Entry(row3, textvariable=self.filter_bid_vol_value, width=10).pack(side="left", padx=2)
        
        # 賣量
        ttk.Label(row3, text="賣量:").pack(side="left", padx=5)
        ask_vol_combo = ttk.Combobox(row3, textvariable=self.filter_ask_vol_op, width=8, state="readonly")
        ask_vol_combo['values'] = ("無限制", "大於", "小於")
        ask_vol_combo.pack(side="left", padx=2)
        ttk.Entry(row3, textvariable=self.filter_ask_vol_value, width=10).pack(side="left", padx=2)
        
        # 總量
        ttk.Label(row3, text="總量:").pack(side="left", padx=5)
        total_vol_combo = ttk.Combobox(row3, textvariable=self.filter_total_vol_op, width=8, state="readonly")
        total_vol_combo['values'] = ("無限制", "大於", "小於")
        total_vol_combo.pack(side="left", padx=2)
        ttk.Entry(row3, textvariable=self.filter_total_vol_value, width=10).pack(side="left", padx=2)

    def toggle_filter(self):
        """切換篩選啟用/停用"""
        self.filter_enabled = not self.filter_enabled
        if self.filter_enabled:
            self.btn_enable_filter.config(text="停用篩選")
            self.label_filter_status.config(text="篩選: 啟用", foreground="green")
            # 顯示篩選面板
            self.filter_frame.pack(fill="x", padx=10, pady=5, before=self.Quote.winfo_children()[2])
            WriteMessage("已啟用報價篩選", GlobalListInformation)
        else:
            self.btn_enable_filter.config(text="啟用篩選")
            self.label_filter_status.config(text="篩選: 停用", foreground="red")
            # 隱藏篩選面板
            self.filter_frame.pack_forget()
            WriteMessage("已停用報價篩選", GlobalListInformation)
    
    def clear_filter(self):
        """清除所有篩選條件"""
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
        self.name_suggest_frame.pack_forget()  # 隱藏建議框
        WriteMessage("已清除所有篩選條件", GlobalListInformation)
    
    def on_name_filter_change(self, event):
        """名稱輸入框變化時顯示建議"""
        search_text = self.entry_filter_name.get().strip().lower()
        
        if not search_text:
            self.name_suggest_frame.pack_forget()
            return
        
        # 搜尋符合的名稱
        suggestions = []
        
        # 從股票名稱中搜尋
        for code, name in stock_codes_to_name.items():
            if search_text in name.lower() or search_text in code.lower():
                suggestions.append(f"{name} ({code})")
        
        # 從期貨名稱中搜尋
        for code, name in future_codes_to_name.items():
            if search_text in name.lower() or search_text in code.lower():
                suggestions.append(f"{name} ({code})")
        
        # 更新建議列表
        self.name_suggest_listbox.delete(0, 'end')
        for suggestion in suggestions[:20]:  # 最多顯示20個建議
            self.name_suggest_listbox.insert('end', suggestion)
        
        if suggestions:
            self.name_suggest_frame.pack(fill="x", padx=5, pady=3)
        else:
            self.name_suggest_frame.pack_forget()
    
    def select_suggested_name(self, event):
        """雙擊選擇建議的名稱"""
        selection = self.name_suggest_listbox.curselection()
        if selection:
            selected_text = self.name_suggest_listbox.get(selection[0])
            self.entry_filter_name.delete(0, 'end')
            self.entry_filter_name.insert(0, selected_text)
            self.add_name_filter()
    
    def add_name_filter(self):
        """添加名稱到篩選列表"""
        name_text = self.entry_filter_name.get().strip()
        if not name_text:
            messagebox.showwarning("警告", "請輸入名稱")
            return
        
        # 提取名稱（去除括號中的代碼）
        if '(' in name_text:
            name = name_text.split('(')[0].strip()
        else:
            name = name_text
        
        if name and name not in self.filter_names:
            self.filter_names.append(name)
            self.update_selected_names_label()
            self.entry_filter_name.delete(0, 'end')
            self.name_suggest_frame.pack_forget()
            WriteMessage(f"已添加篩選名稱: {name}", GlobalListInformation)
    
    def clear_name_filter(self):
        """清除名稱篩選列表"""
        self.filter_names = []
        self.update_selected_names_label()
        WriteMessage("已清除名稱篩選", GlobalListInformation)
    
    def update_selected_names_label(self):
        """更新已選名稱的顯示"""
        if self.filter_names:
            names_text = ", ".join(self.filter_names[:3])
            if len(self.filter_names) > 3:
                names_text += f" ... (共{len(self.filter_names)}個)"
            self.label_selected_names.config(text=f"已選: {names_text}")
        else:
            self.label_selected_names.config(text="已選: 無")
    
    def check_filter(self, item_type, name, bid_price, ask_price, close_price, 
                     bid_volume, ask_volume, total_volume):
        """檢查是否符合篩選條件"""
        if not self.filter_enabled:
            return True
        
        try:
            # 1. 類型篩選
            filter_type = self.filter_type.get()
            if filter_type != "全部":
                if filter_type == "股票" and item_type != "股票":
                    return False
                if filter_type == "期貨" and item_type != "期貨":
                    return False
            
            # 2. 名稱篩選
            if self.filter_names:
                name_match = False
                for filter_name in self.filter_names:
                    if filter_name.lower() in name.lower():
                        name_match = True
                        break
                if not name_match:
                    return False
            
            # 3. 買進價格篩選
            if self.filter_bid_op.get() != "無限制":
                try:
                    threshold = float(self.filter_bid_value.get())
                    if self.filter_bid_op.get() == "大於" and bid_price <= threshold:
                        return False
                    if self.filter_bid_op.get() == "小於" and bid_price >= threshold:
                        return False
                except ValueError:
                    pass
            
            # 4. 賣出價格篩選
            if self.filter_ask_op.get() != "無限制":
                try:
                    threshold = float(self.filter_ask_value.get())
                    if self.filter_ask_op.get() == "大於" and ask_price <= threshold:
                        return False
                    if self.filter_ask_op.get() == "小於" and ask_price >= threshold:
                        return False
                except ValueError:
                    pass
            
            # 5. 成交價格篩選
            if self.filter_close_op.get() != "無限制":
                try:
                    threshold = float(self.filter_close_value.get())
                    if self.filter_close_op.get() == "大於" and close_price <= threshold:
                        return False
                    if self.filter_close_op.get() == "小於" and close_price >= threshold:
                        return False
                except ValueError:
                    pass
            
            # 6. 買量篩選
            if self.filter_bid_vol_op.get() != "無限制":
                try:
                    threshold = int(self.filter_bid_vol_value.get())
                    if self.filter_bid_vol_op.get() == "大於" and bid_volume <= threshold:
                        return False
                    if self.filter_bid_vol_op.get() == "小於" and bid_volume >= threshold:
                        return False
                except ValueError:
                    pass
            
            # 7. 賣量篩選
            if self.filter_ask_vol_op.get() != "無限制":
                try:
                    threshold = int(self.filter_ask_vol_value.get())
                    if self.filter_ask_vol_op.get() == "大於" and ask_volume <= threshold:
                        return False
                    if self.filter_ask_vol_op.get() == "小於" and ask_volume >= threshold:
                        return False
                except ValueError:
                    pass
            
            # 8. 總量篩選
            if self.filter_total_vol_op.get() != "無限制":
                try:
                    threshold = int(self.filter_total_vol_value.get())
                    if self.filter_total_vol_op.get() == "大於" and total_volume <= threshold:
                        return False
                    if self.filter_total_vol_op.get() == "小於" and total_volume >= threshold:
                        return False
                except ValueError:
                    pass
            
            return True
            
        except Exception as e:
            WriteMessage(f"篩選檢查錯誤: {e}", GlobalListInformation)
            return True
    
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
        """使用 pandas 快速加載配對表"""
        try:
            # 使用 pandas 快速解析配對資料
            df = pd.read_csv(
                StringIO(Compare_Map), 
                sep='\\s+',
                header=None, 
                names=['future_name', 'future_short', 'stock_name', 'stock_code'],
                dtype=str,
                engine='python'
            )
            # 轉換為 tuple list (保持兼容性)
            return list(df.itertuples(index=False, name=None))
        except Exception as e:
            WriteMessage(f"加載配對表時發生錯誤: {e}", GlobalListInformation)
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
        """🚀 增量更新報價表格 - 使用 pandas 向量化篩選，超高性能"""
        try:
            # 🚀 步驟 1: 批量收集所有數據到列表（避免逐個處理）
            data_list = []
            
            # 收集期貨資料
            for code, name in future_codes_to_name.items():
                index = future_to_spreadmap_index.get(code)
                if index is not None:
                    spread_info = spread_map[index]
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
            
            # 收集股票資料
            for code, name in stock_codes_to_name.items():
                index = stock_to_spreadmap_index.get(code)
                if index is not None:
                    spread_info = spread_map[index]
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
            
            # 🚀 步驟 2: 轉換為 pandas DataFrame（向量化操作的關鍵）
            if not data_list:
                self.label_quote_count.config(text="無資料")
                return
            
            df = pd.DataFrame(data_list)

            total_count = len(df)
            # 🚀 步驟 3: 使用 pandas 向量化篩選（超快！）
            if self.filter_enabled: 
                mask = pd.Series([True] * len(df))  # 初始全部為 True
                
                # 1. 類型篩選（向量化）
                filter_type = self.filter_type.get()
                if filter_type != "全部":
                    mask &= (df['type'] == filter_type)
                
                # 2. 名稱篩選（向量化）
                if self.filter_names:
                    name_mask = pd.Series([False] * len(df))
                    for filter_name in self.filter_names:
                        name_mask |= df['name'].str.contains(filter_name, case=False, na=False)
                    mask &= name_mask
                
                # 3. 買進價格篩選（向量化）
                if self.filter_bid_op.get() != "無限制":
                    try:
                        threshold = float(self.filter_bid_value.get())
                        if self.filter_bid_op.get() == "大於":
                            mask &= (df['bid_price'] > threshold)
                        elif self.filter_bid_op.get() == "小於":
                            mask &= (df['bid_price'] < threshold)
                    except ValueError:
                        pass
                
                # 4. 賣出價格篩選（向量化）
                if self.filter_ask_op.get() != "無限制":
                    try:
                        threshold = float(self.filter_ask_value.get())
                        if self.filter_ask_op.get() == "大於":
                            mask &= (df['ask_price'] > threshold)
                        elif self.filter_ask_op.get() == "小於":
                            mask &= (df['ask_price'] < threshold)
                    except ValueError:
                        pass
                
                # 5. 成交價格篩選（向量化）
                if self.filter_close_op.get() != "無限制":
                    try:
                        threshold = float(self.filter_close_value.get())
                        if self.filter_close_op.get() == "大於":
                            mask &= (df['close_price'] > threshold)
                        elif self.filter_close_op.get() == "小於":
                            mask &= (df['close_price'] < threshold)
                    except ValueError:
                        pass
                
                # 6. 買量篩選（向量化）
                if self.filter_bid_vol_op.get() != "無限制":
                    try:
                        threshold = int(self.filter_bid_vol_value.get())
                        if self.filter_bid_vol_op.get() == "大於":
                            mask &= (df['bid_volume'] > threshold)
                        elif self.filter_bid_vol_op.get() == "小於":
                            mask &= (df['bid_volume'] < threshold)
                    except ValueError:
                        pass
                
                # 7. 賣量篩選（向量化）
                if self.filter_ask_vol_op.get() != "無限制":
                    try:
                        threshold = int(self.filter_ask_vol_value.get())
                        if self.filter_ask_vol_op.get() == "大於":
                            mask &= (df['ask_volume'] > threshold)
                        elif self.filter_ask_vol_op.get() == "小於":
                            mask &= (df['ask_volume'] < threshold)
                    except ValueError:
                        pass
                
                # 8. 總量篩選（向量化）
                if self.filter_total_vol_op.get() != "無限制":
                    try:
                        threshold = int(self.filter_total_vol_value.get())
                        if self.filter_total_vol_op.get() == "大於":
                            mask &= (df['total_volume'] > threshold)
                        elif self.filter_total_vol_op.get() == "小於":
                            mask &= (df['total_volume'] < threshold)
                    except ValueError:
                        pass
                
                # 應用篩選
                df = df[mask]
                filtered_count = total_count - len(df)
            else:
                filtered_count = 0
            
            # 🚀 步驟 4: 統計
            stock_with_data = len(df[df['type'] == '股票'])
            future_with_data = len(df[df['type'] == '期貨'])

            # 🚀 步驟 5: 批量格式化（向量化字符串操作）
            current_codes = set(df['code'])

            # 使用 pandas 向量化格式化（超快！）
            df['name_short'] = df['name'].str[:10]
            df['bid_price_str'] = df['bid_price'].apply(lambda x: f"{x:.2f}" if x > 0 else "0.00")
            df['ask_price_str'] = df['ask_price'].apply(lambda x: f"{x:.2f}" if x > 0 else "0.00")
            df['close_price_str'] = df['close_price'].apply(lambda x: f"{x:.2f}" if x > 0 else "0.00")
            df['bid_volume_str'] = df['bid_volume'].apply(lambda x: str(x) if x > 0 else "0")
            df['ask_volume_str'] = df['ask_volume'].apply(lambda x: str(x) if x > 0 else "0")
            df['total_volume_str'] = df['total_volume'].apply(lambda x: str(x) if x > 0 else "0")

            # 🚀 步驟 6: 增量更新 GUI
            active_count = 0
            for _, row in df.iterrows():
                code = row['code']
                values = (
                    row['type'],
                    code,
                    row['name_short'],
                    row['bid_price_str'],
                    row['ask_price_str'],
                    row['close_price_str'],
                    row['bid_volume_str'],
                    row['ask_volume_str'],
                    row['total_volume_str']
                )
                
                tree_item = self.tree_item_cache.get(code)
                last_values = self.last_data_cache.get(code)
                
                # 檢查數據是否改變
                if last_values != values:
                    if tree_item and self.quote_tree.exists(tree_item):
                        # 更新現有項目（比刪除重建快得多）
                        self.quote_tree.item(tree_item, values=values)
                    else:
                        # 新增項目
                        tree_item = self.quote_tree.insert("", "end", values=values)
                        self.tree_item_cache[code] = tree_item
                    
                    # 更新緩存
                    self.last_data_cache[code] = values
                
                active_count += 1
            
            # 🚀 移除不再需要的項目（被篩選掉的或不再存在的）
            codes_to_remove = set(self.tree_item_cache.keys()) - current_codes
            for code in codes_to_remove:
                tree_item = self.tree_item_cache.get(code)
                if tree_item and self.quote_tree.exists(tree_item):
                    self.quote_tree.delete(tree_item)
                del self.tree_item_cache[code]
                if code in self.last_data_cache:
                    del self.last_data_cache[code]
            
            # 更新狀態顯示
            if self.filter_enabled and filtered_count > 0:
                status_text = f"顯示: {active_count} | 股票: {stock_with_data} | 期貨: {future_with_data} | 已篩選: {filtered_count}"
            else:
                status_text = f"顯示筆數: {active_count} | 股票有資料: {stock_with_data} | 期貨有資料: {future_with_data}"
            self.label_quote_count.config(text=status_text)
            
        except Exception as e:
            WriteMessage(f"更新表格時發生錯誤: {str(e)}", GlobalListInformation)
    
#----------------------------------------------------------------------------------------------------------------------------------------------------
# 總整理頁面    
class FrameInformation(Frame):
    def __init__(self, root=None):
        Frame.__init__(self)
        self.Information = Frame(self)
        self.Information.pack(fill="both", expand=True)
        self.main_window = root

        self.info_timer_id = None
        
        # 🚀 性能優化：緩存機制
        self.info_tree_cache = {}  # {index: tree_item_id}
        self.info_last_data = {}   # {index: last_values}
        
        # 🔍 篩選功能變數
        self.filter_enabled = False
        self.filter_names = []  # 名稱篩選列表（期貨或股票名稱）
        self.filter_future_to_stock_op = StringVar(value="無限制")  # 期-股差額操作
        self.filter_future_to_stock_value = StringVar(value="0")
        self.filter_stock_to_future_op = StringVar(value="無限制")  # 股-期差額操作
        self.filter_stock_to_future_value = StringVar(value="0")
        
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
        
        # 啟用/停用篩選按鈕
        self.btn_enable_filter = ttk.Button(control_frame, text="啟用篩選", command=self.toggle_filter)
        self.btn_enable_filter.pack(side="left", padx=10, pady=5)
        
        # 篩選狀態顯示
        self.label_filter_status = ttk.Label(control_frame, text="篩選: 停用", foreground="red")
        self.label_filter_status.pack(side="left", padx=5, pady=5)
        
        # 🔍 篩選區域
        self.create_filter_panel()

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
    
    def create_filter_panel(self):
        """創建篩選面板"""
        self.filter_frame = ttk.LabelFrame(self.Information, text="🔍 篩選條件")
        # 預設隱藏篩選面板
        
        # 第一行：名稱篩選
        row1 = ttk.Frame(self.filter_frame)
        row1.pack(fill="x", padx=5, pady=3)
        
        ttk.Label(row1, text="名稱:").pack(side="left", padx=5)
        self.entry_filter_name = ttk.Entry(row1, width=30)
        self.entry_filter_name.pack(side="left", padx=5)
        self.entry_filter_name.bind('<KeyRelease>', self.on_name_filter_change)
        
        ttk.Button(row1, text="添加名稱", command=self.add_name_filter).pack(side="left", padx=5)
        
        # 顯示已選擇的名稱
        self.label_selected_names = ttk.Label(row1, text="已選: 無", foreground="blue")
        self.label_selected_names.pack(side="left", padx=10)
        
        ttk.Button(row1, text="清除名稱", command=self.clear_name_filter).pack(side="left", padx=5)
        ttk.Button(row1, text="清除篩選", command=self.clear_filter).pack(side="left", padx=10)
        
        # 名稱建議列表框（自動完成）
        self.name_suggest_frame = ttk.Frame(self.filter_frame)
        self.name_suggest_listbox = Listbox(self.name_suggest_frame, height=5)
        self.name_suggest_listbox.pack(fill="x")
        self.name_suggest_listbox.bind('<Double-Button-1>', self.select_suggested_name)
        # 預設隱藏
        
        # 第二行：差額篩選
        row2 = ttk.Frame(self.filter_frame)
        row2.pack(fill="x", padx=5, pady=3)
        
        # 期-股差額
        ttk.Label(row2, text="期-股差額:").pack(side="left", padx=5)
        future_to_stock_combo = ttk.Combobox(row2, textvariable=self.filter_future_to_stock_op, width=8, state="readonly")
        future_to_stock_combo['values'] = ("無限制", "大於", "小於")
        future_to_stock_combo.pack(side="left", padx=2)
        ttk.Entry(row2, textvariable=self.filter_future_to_stock_value, width=10).pack(side="left", padx=2)
        
        # 股-期差額
        ttk.Label(row2, text="股-期差額:").pack(side="left", padx=15)
        stock_to_future_combo = ttk.Combobox(row2, textvariable=self.filter_stock_to_future_op, width=8, state="readonly")
        stock_to_future_combo['values'] = ("無限制", "大於", "小於")
        stock_to_future_combo.pack(side="left", padx=2)
        ttk.Entry(row2, textvariable=self.filter_stock_to_future_value, width=10).pack(side="left", padx=2)
    
    def toggle_filter(self):
        """切換篩選啟用/停用"""
        self.filter_enabled = not self.filter_enabled
        if self.filter_enabled:
            self.btn_enable_filter.config(text="停用篩選")
            self.label_filter_status.config(text="篩選: 啟用", foreground="green")
            # 顯示篩選面板
            self.filter_frame.pack(fill="x", padx=10, pady=5, before=self.Information.winfo_children()[2])
            WriteMessage("已啟用整理篩選", GlobalListInformation)
        else:
            self.btn_enable_filter.config(text="啟用篩選")
            self.label_filter_status.config(text="篩選: 停用", foreground="red")
            # 隱藏篩選面板
            self.filter_frame.pack_forget()
            WriteMessage("已停用整理篩選", GlobalListInformation)
    
    def clear_filter(self):
        """清除所有篩選條件"""
        self.filter_names = []
        self.filter_future_to_stock_op.set("無限制")
        self.filter_future_to_stock_value.set("0")
        self.filter_stock_to_future_op.set("無限制")
        self.filter_stock_to_future_value.set("0")
        self.label_selected_names.config(text="已選: 無")
        self.entry_filter_name.delete(0, 'end')
        self.name_suggest_frame.pack_forget()
        WriteMessage("已清除所有篩選條件", GlobalListInformation)
    
    def on_name_filter_change(self, event):
        """名稱輸入框變化時顯示建議"""
        search_text = self.entry_filter_name.get().strip().lower()
        
        if not search_text:
            self.name_suggest_frame.pack_forget()
            return
        
        # 搜尋符合的名稱（期貨和股票）
        suggestions = []
        
        # 從期貨名稱中搜尋
        for code, name in future_codes_to_name.items():
            if search_text in name.lower() or search_text in code.lower():
                suggestions.append(f"{name} ({code})")
        
        # 從股票名稱中搜尋
        for code, name in stock_codes_to_name.items():
            if search_text in name.lower() or search_text in code.lower():
                suggestions.append(f"{name} ({code})")
        
        # 更新建議列表
        self.name_suggest_listbox.delete(0, 'end')
        for suggestion in suggestions[:20]:  # 最多顯示20個建議
            self.name_suggest_listbox.insert('end', suggestion)
        
        if suggestions:
            self.name_suggest_frame.pack(fill="x", padx=5, pady=3)
        else:
            self.name_suggest_frame.pack_forget()
    
    def select_suggested_name(self, event):
        """雙擊選擇建議的名稱"""
        selection = self.name_suggest_listbox.curselection()
        if selection:
            selected_text = self.name_suggest_listbox.get(selection[0])
            self.entry_filter_name.delete(0, 'end')
            self.entry_filter_name.insert(0, selected_text)
            self.add_name_filter()
    
    def add_name_filter(self):
        """添加名稱到篩選列表"""
        name_text = self.entry_filter_name.get().strip()
        if not name_text:
            messagebox.showwarning("警告", "請輸入名稱")
            return
        
        # 提取名稱（去除括號中的代碼）
        if '(' in name_text:
            name = name_text.split('(')[0].strip()
        else:
            name = name_text
        
        if name and name not in self.filter_names:
            self.filter_names.append(name)
            self.update_selected_names_label()
            self.entry_filter_name.delete(0, 'end')
            self.name_suggest_frame.pack_forget()
            WriteMessage(f"已添加篩選名稱: {name}", GlobalListInformation)
    
    def clear_name_filter(self):
        """清除名稱篩選列表"""
        self.filter_names = []
        self.update_selected_names_label()
        WriteMessage("已清除名稱篩選", GlobalListInformation)
    
    def update_selected_names_label(self):
        """更新已選名稱的顯示"""
        if self.filter_names:
            names_text = ", ".join(self.filter_names[:3])
            if len(self.filter_names) > 3:
                names_text += f" ... (共{len(self.filter_names)}個)"
            self.label_selected_names.config(text=f"已選: {names_text}")
        else:
            self.label_selected_names.config(text="已選: 無")
   
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
        """🚀 pandas 向量化更新整理表格 + 篩選"""
        try:
            # 🚀 步驟 1: 批量收集數據到列表
            data_list = []
            
            for index, spread_info in spread_map.items():
                if spread_info.future.future_no and spread_info.stock.stock_no:
                    # 提取數據
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

                    # 計算價差
                    future_to_stock_diff = (future_ask - stock_bid) if (stock_bid > 0 and future_ask > 0) else 0
                    stock_to_future_diff = (stock_ask - future_bid) if (future_bid > 0 and stock_ask > 0) else 0

                    future_name = future_codes_to_name.get(spread_info.future.future_no, "")
                    stock_name = stock_codes_to_name.get(spread_info.stock.stock_no, "")

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
            
            # 🚀 步驟 2: 轉換為 pandas DataFrame
            if not data_list:
                return
            
            df = pd.DataFrame(data_list)
            
            # 🚀 步驟 3: 使用 pandas 向量化篩選
            if self.filter_enabled:
                mask = pd.Series([True] * len(df))
                
                # 1. 名稱篩選（向量化）
                if self.filter_names:
                    name_mask = pd.Series([False] * len(df))
                    for filter_name in self.filter_names:
                        # 搜尋期貨名稱或股票名稱
                        name_mask |= df['future_name'].str.contains(filter_name, case=False, na=False)
                        name_mask |= df['stock_name'].str.contains(filter_name, case=False, na=False)
                    mask &= name_mask
                
                # 2. 期-股差額篩選（向量化）
                if self.filter_future_to_stock_op.get() != "無限制":
                    try:
                        threshold = float(self.filter_future_to_stock_value.get())
                        if self.filter_future_to_stock_op.get() == "大於":
                            mask &= (df['future_to_stock_diff'] > threshold)
                        elif self.filter_future_to_stock_op.get() == "小於":
                            mask &= (df['future_to_stock_diff'] < threshold)
                    except ValueError:
                        pass
                
                # 3. 股-期差額篩選（向量化）
                if self.filter_stock_to_future_op.get() != "無限制":
                    try:
                        threshold = float(self.filter_stock_to_future_value.get())
                        if self.filter_stock_to_future_op.get() == "大於":
                            mask &= (df['stock_to_future_diff'] > threshold)
                        elif self.filter_stock_to_future_op.get() == "小於":
                            mask &= (df['stock_to_future_diff'] < threshold)
                    except ValueError:
                        pass
                
                # 應用篩選
                df = df[mask]
            
            # 🚀 步驟 4: 批量格式化（向量化）
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
            
            # 🚀 步驟 5: 增量更新 GUI
            for _, row in df.iterrows():
                index = row['index']
                values = (
                    row['future_name'],
                    row['stock_name'],
                    row['future_bid_str'],
                    row['future_bid_volume_str'],
                    row['future_ask_str'],
                    row['future_ask_volume_str'],
                    row['future_close_str'],
                    row['stock_bid_str'],
                    row['stock_bid_volume_str'],
                    row['stock_ask_str'],
                    row['stock_ask_volume_str'],
                    row['stock_close_str'],
                    row['future_to_stock_diff_str'],
                    row['stock_to_future_diff_str']
                )
                
                tree_item = self.info_tree_cache.get(index)
                last_values = self.info_last_data.get(index)
                
                if last_values != values:
                    if tree_item and self.info_tree.exists(tree_item):
                        # 更新現有項目
                        self.info_tree.item(tree_item, values=values)
                    else:
                        # 新增項目
                        tree_item = self.info_tree.insert("", "end", values=values)
                        self.info_tree_cache[index] = tree_item
                    
                    # 更新緩存
                    self.info_last_data[index] = values
            
            # 🚀 步驟 6: 移除不再需要的項目
            indices_to_remove = set(self.info_tree_cache.keys()) - current_indices
            for index in indices_to_remove:
                tree_item = self.info_tree_cache.get(index)
                if tree_item and self.info_tree.exists(tree_item):
                    self.info_tree.delete(tree_item)
                del self.info_tree_cache[index]
                if index in self.info_last_data:
                    del self.info_last_data[index]
                    
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
        columns = ("股票名稱","股票代碼", "期貨名稱", "期貨代碼", "正價差" , "逆價差" ,"套利方向", "淨利潤", "總交易成本"  )
        
        self.output_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=25)
        
        # 設定欄位標題和寬度
        column_widths = {
            "股票名稱": 100, "股票代碼": 100, "期貨名稱": 100, "期貨代碼": 100, "正價差": 100 , "逆價差": 100, "套利方向": 100, "淨利潤": 100, "總交易成本": 100
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
                # if spread_info.ArbitrageDirection != None and spread_info.OpportunityScore != 1:
                if spread_info.ArbitrageDirection != None:
                    values = (
                        stock_codes_to_name[spread_info.stock.stock_no] or "",
                        spread_info.stock.stock_no or "",
                        future_codes_to_name[spread_info.future.future_no] or "",
                        spread_info.future.future_no or "",
                        f"{spread_info.Spread_FutureAsk_StockBid:.2f}",
                        f"{spread_info.Spread_StockAsk_FutureBid:.2f}",
                        # str(spread_info.OpportunityScore) or "",
                        spread_info.ArbitrageDirection or "",
                        f"{max(spread_info.PosNetProfit,spread_info.NegNetProfit):.2f}",
                        f"{spread_info.TotalCost:.2f}",
                    )
                    # all_items.append((str(spread_info.OpportunityScore),values))
                    all_items.append(values)
                # 先照機會評級排，再用淨利潤排序
                # all_items.sort(key=lambda t: (int(t[0]),float(t[1][6])), reverse=True)  # 按機會評級和淨利潤排序
                all_items.sort(key=lambda t: (float(t[7])), reverse=True)  # 按淨利潤排序

            for values in all_items:
                self.output_tree.insert("", "end", values=values)
        except Exception as e:
            WriteMessage(f"更新輸出表格時發生錯誤: {str(e)}", GlobalListInformation)

#----------------------------------------------------------------------------------------------------------------------------------------------------
# 📢 公告視窗
class AnnouncementDialog:
    """程式啟動公告視窗"""
    def __init__(self, parent):
        self.dialog = Toplevel(parent)
        self.dialog.title("📢 系統公告")
        self.dialog.geometry("600x450")
        self.dialog.resizable(False, False)
        
        # 設定視窗置中
        self.center_window()
        
        # 設定為模態視窗（必須關閉才能操作主視窗）
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
    
    def center_window(self):
        """視窗置中"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        # 標題區域
        title_frame = ttk.Frame(self.dialog)
        title_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        title_label = ttk.Label(
            title_frame, 
            text="🚀 歡迎使用報價系統 v1.3",
            font=('Arial', 16, 'bold')
        )
        title_label.pack()
        
        # 分隔線
        separator1 = ttk.Separator(self.dialog, orient='horizontal')
        separator1.pack(fill='x', padx=20, pady=10)
        
        # 內容區域（使用 Text widget 以支持多行和滾動）
        content_frame = ttk.Frame(self.dialog)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 創建文字區域和滾動條
        text_scroll = ttk.Scrollbar(content_frame)
        text_scroll.pack(side="right", fill="y")
        
        content_text = Text(
            content_frame,
            wrap="word",
            font=('Microsoft YaHei UI', 10),
            yscrollcommand=text_scroll.set,
            relief="flat",
            bg="#f0f0f0",
            padx=10,
            pady=10
        )
        content_text.pack(side="left", fill="both", expand=True)
        text_scroll.config(command=content_text.yview)
        
        # 公告內容
        announcement = """📌 重要提醒
1. 輸入帳號、密碼，按登入
2. 按連線
3. 必須等到 MessageBox 出現 "Stocks ready!, 可以開始訂閱股票報價"，才可執行報價功能 ( 否則會出現當掉的問題 ) 
4. 報價結束後，可以去整理跟輸出

🎉 更新內容
• v1.1 - 基本的功能
【登入】
    - 登入 : 連接至主伺服器
    - 連線 : 建立報價連線
【報價來源】
    - 開始訂閱報價 : 啟動訂閱報價。
    - 每秒偵測報價變動，並更新有變動的項目
【總整理】
    - 分析報價 : 進行期現套利運算。
【輸出】
    - 先按照機會評級排序，再用淨利潤排序
• v1.2 - 報價頁面的篩選功能與功能優化
【報價來源】
    - 新增名稱篩選（期貨/股票）
    - 新增查詢提示
    - 新增數值篩選
    - 新增股-期差額篩選
    - 篩選面板自動顯示/隱藏
• v1.3 - 整理頁面的篩選功能與公告版
【整理】
    - 新增名稱篩選（期貨/股票）
    - 新增查詢提示
    - 新增期-股差額篩選
    - 新增股-期差額篩選
【公告版】
    - 新增程式啟動公告視窗
    - 告知版本差異
• v1.4 - 修改正價差逆價差公式
【整理】
    - 修改正價差跟逆價差公式
    - 加上總交易成本欄位

👍 祝您交易順利！
"""
        
        content_text.insert("1.0", announcement)
        content_text.config(state="disabled")  # 設定為只讀
        
        # 分隔線
        separator2 = ttk.Separator(self.dialog, orient='horizontal')
        separator2.pack(fill='x', padx=20, pady=10)
        
        # 按鈕區域
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # 不再顯示選項（可選）
        self.dont_show_var = BooleanVar(value=False)
        dont_show_check = ttk.Checkbutton(
            button_frame,
            text="下次不再顯示",
            variable=self.dont_show_var
        )
        dont_show_check.pack(side="left")
        
        # 確認按鈕
        confirm_btn = ttk.Button(
            button_frame,
            text="確認（Enter）",
            command=self.close_dialog,
            width=15
        )
        confirm_btn.pack(side="right")
        
        # 綁定 Enter 鍵
        self.dialog.bind('<Return>', lambda e: self.close_dialog())
        self.dialog.bind('<Escape>', lambda e: self.close_dialog())
        
        # 設定焦點在確認按鈕
        confirm_btn.focus_set()
    
    def close_dialog(self):
        """關閉對話框"""
        # 如果勾選了不再顯示，可以在這裡儲存設定
        if self.dont_show_var.get():
            try:
                # 儲存設定到檔案
                with open('announcement_settings.txt', 'w') as f:
                    f.write('dont_show=True')
            except:
                pass
        
        self.dialog.destroy()
    
    @staticmethod
    def should_show_announcement():
        """檢查是否應該顯示公告"""
        try:
            if os.path.exists('announcement_settings.txt'):
                with open('announcement_settings.txt', 'r') as f:
                    content = f.read()
                    if 'dont_show=True' in content:
                        return False
        except:
            pass
        return True

#----------------------------------------------------------------------------------------------------------------------------------------------------
# 事件        
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

#----------------------------------------------------------------------------------------------------------------------------------------------------
# 主函式
if __name__ == '__main__':
    root = Tk()
    root.title("交易系統 v1-3 - 完整功能")
    root.geometry("1400x900")  # 設定較大的視窗尺寸
    
    # 📢 顯示啟動公告（如果用戶沒有選擇不再顯示）
    if AnnouncementDialog.should_show_announcement():
        AnnouncementDialog(root)
    
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
