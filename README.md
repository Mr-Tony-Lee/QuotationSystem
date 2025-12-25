# CapitalAPI V2.0 - Python Refactored Version

## 專案簡介

本專案為群益 API (Capital API) 的 Python 範例程式重構版本。
原有的單一檔案程式 (`main_3.py`) 已根據物件導向程式設計 (OOP) 原則進行模組化拆分，以提升程式碼的可讀性、維護性與擴展性。

這是一個即時報價與價差監控系統，主要功能包含：
1. **報價來源 (Quote)**：即時訂閱並顯示股票與期貨的報價資訊。
2. **總整理 (Information)**：計算並監控期貨與股票之間的價差 (Spread)，提供套利機會分析。
3. **輸出 (Output)**：篩選並排序有利可圖的價差組合。
4. **登入 (Login)**：管理 API 連線與登入狀態。

## 目錄結構說明

本專案位於 `Module` 資料夾下，結構如下：

```
main.py                   # 主程式  
Module/
├── sk_api.py            # 【核心 API】 封裝 SKCOM.dll 的所有互動與事件處理
├── data_manager.py      # 【資料管理】 負責資料載入、狀態維護與計算邏輯
├── models.py            # 【資料模型】 定義 StockInfo, FutureInfo 等資料結構
├── constants.py         # 【常數定義】 包含大型的商品代碼列表與對照表
├── logger.py            # 【日誌工具】 處理系統訊息與 GUI 顯示 (Thread-safe)
├── SKCOM.dll            # 【元件】 群益 API 元件
└── ui/                  # 【使用者介面】 包含各個分頁的 GUI 實作
    ├── login.py         # 登入與連線分頁
    ├── quote.py         # 報價來源分頁
    ├── information.py   # 總整理分頁
    ├── output.py        # 輸出監控分頁
    └── dialogs.py       # 彈出視窗 (如公告)
```

## 安裝與執行

### 環境需求
- Windows OS
- Python 3.x
- 必要套件: `pandas`, `comtypes`, `tkinter` (內建), `mplfinance`, `matplotlib`
- 必須安裝群益 API 元件並註冊 DLL

### 新增功能-v2.1
- **技術線圖**: 雙擊報價表中的商品，即可開啟專業級 K 線圖 (Dark Theme)。

### 執行方式

請在 `SKDLLPythonTester` 目錄下直接執行 `main.py`：

```bash
cd d:\CapitalAPI_2.13.57_PythonExample\SKDLLPythonTester
python main.py
```

`main.py` 會自動參照 `Module` 資料夾內的模組。請勿刪除或移動 `Module` 資料夾。


## 模組詳細說明

### 1. 核心邏輯層
- **sk_api.py**:
    - `SKClient`: 負責 COM 物件的初始化、登入 (`login`)、連線 (`connect`) 與商品訂閱 (`request_stocks`)。
    - `SKQuoteLibEvents`: 處理報價回傳事件 (`OnNotifyQuoteLONG`)，將資料傳遞給 DataManager。
- **data_manager.py**:
    - `DataManager`: 系統的資料中心。初始時載入 `constants.py` 的對照表。
    - 負責將原始報價更新到 `spread_map` 中 (`update_quote`)，並提供計算後的 DataFrame 給 UI 顯示。

### 2. 資料層
- **models.py**: 定義了 `StockInfo` (股票)、`FutureInfo` (期貨) 與 `PriceSpreadInfo` (價差組合) 類別。
- **constants.py**: 存放 `StockList`, `FutureList` 與配對定義字串。

### 3. 使用者介面層 (UI)
所有 UI 繼承自 `tkinter.Frame`，並透過依賴注入 (Dependency Injection) 取得 `sk_client` 與 `data_manager` 的存取權。
- **Quote (quote.py)**: 顯示原始報價，支援各類篩選。
- **Information (information.py)**: 顯示計算後的價差資訊 (期貨 vs 股票)。
- **Output (output.py)**: 依照利潤排序，顯示最佳套利機會。

---
**開發者注意事項**:
- 若要修改報價邏輯，請查看 `data_manager.py`。
- 若要修改 API 互動方式，請查看 `sk_api.py`。
- 若要修改介面佈局，請查看 `ui/` 資料夾下的對應檔案。
