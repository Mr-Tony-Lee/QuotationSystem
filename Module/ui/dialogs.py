from tkinter import Toplevel, Text, BooleanVar
from tkinter import ttk
import os

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
            text="🚀 歡迎使用報價系統 v2.0 (Refactored)",
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
• v2.0 - OOP 重構版本
    - 模組化程式碼結構
    - 分離邏輯與界面
    - 提升維護性

• v1.3 - 整理頁面的篩選功能與公告版
【整理】
    - 新增名稱篩選（期貨/股票）
    - 新增查詢提示
    - 新增期-股差額篩選
    - 新增股-期差額篩選
【公告版】
    - 新增程式啟動公告視窗
    - 告知版本差異

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
