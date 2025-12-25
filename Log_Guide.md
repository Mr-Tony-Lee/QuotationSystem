# 系統 Log 檔案說明

本系統提供三種不同層級與用途的 Log 記錄，分別用於系統監控、高獲利追蹤與 API 底層除錯。

## 1. 系統運行日誌 (System Logs)

這是最通用的應用程式日誌，記錄了您在 GUI 介面的「登入」頁籤中所看到的所有訊息。

*   **儲存位置**: `SKDLLPythonTester/Logs/System_YYYYMMDD.log`
*   **檔名格式**: 依日期每日產生一個檔案 (例如 `System_20251225.log`)
*   **內容包含**:
    *   API 連線、斷線狀態
    *   登入成功/失敗訊息
    *   Callback 回報 (Reply, Account, OpenInterest, RealBalance 等)
    *   錯誤與異常訊息
*   **用途**: 用於查詢歷史操作紀錄與系統運行狀態，即使關閉程式，這些紀錄也會被保存。

## 2. 高獲利監控日誌 (High Profit Logs)

專門記錄「輸出」頁面中，淨利潤超過 5000 的套利機會。

*   **儲存位置**: `SKDLLPythonTester/Logs/HighProfit.log`
*   **檔名格式**: 固定為 `HighProfit.log`，新資料會持續附加在檔案尾端。
*   **內容包含**:
    *   觸發時間戳記
    *   符合條件的總筆數
    *   詳細的股票/期貨名稱與淨利潤金額
*   **用途**: 讓使用者在即使不在電腦前時，也能回頭檢視當日出現過的高獲利機會。

## 3. 群益 API 底層日誌 (API Low-level Logs)

由群益 API (SKCOM.dll) 直接產生的除錯日誌，內容由 dll 內部控制。

*   **儲存位置**: `SKDLLPythonTester/Module/CapitalLog_Quote/*.log`
*   **檔名格式**: 通常包含日期與功能名稱 (例如 `20251225_Reply.log`, `20251225_Quote.log`)
*   **內容包含**:
    *   詳細的 TCP/IP 封包收發紀錄
    *   底層 Return Code
    *   連線協議細節
*   **用途**: 僅在發生無法解釋的連線斷線、報價接收異常且系統日誌看不出原因時，提供給開發者或群益客服進行除錯分析。
