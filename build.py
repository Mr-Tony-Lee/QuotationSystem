import PyInstaller.__main__
import os

# 確保輸出目錄存在
if not os.path.exists('dist'):
    os.makedirs('dist')

# 定義 PyInstaller 參數
params = [
    'main.py',                      # 主程式入口
    '--name=CapitalTester',         # 輸出檔名
    '--onedir',                     # 輸出為目錄 (方便 Debug 與放置 DLL)
    '--noconsole',                  # 隱藏主控台視窗 (GUI 程式)
    '--clean',                      # 清除快取
    '--add-binary=Module/SKCOM.dll;.', # 加入 SKCOM.dll 到根目錄 (Windows 使用 ;)
    # '--add-data=login_config.json;.', # 如果需要預設設定檔可開啟，但通常是執行時產生
    '--hidden-import=pandas',       # 強制加入隱藏依賴
    '--hidden-import=comtypes',
    '--hidden-import=comtypes.client',
    '--hidden-import=comtypes.gen',
    # 排除不必要的巨型套件
    '--exclude-module=torch',
    '--exclude-module=tensorflow',
    '--exclude-module=tensorboard',
    '--exclude-module=sklearn',
    '--exclude-module=scipy',
    '--exclude-module=matplotlib',
    '--exclude-module=IPython',
    '--exclude-module=jedi',
    '--exclude-module=PIL',  # 如果沒用到圖片處理也可排除
]

print("開始打包執行檔...")
PyInstaller.__main__.run(params)
print("打包完成！請查看 dist/CapitalTester 資料夾")
