from tkinter import Frame, Listbox, ttk
from ..logger import logger

class FrameLogin(Frame):
    def __init__(self, master=None, sk_client=None):
        Frame.__init__(self, master)
        self.sk_client = sk_client
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

        # 註冊 listbox 到 logger
        logger.set_gui_listbox(self.listInformation)
        
        # 初始訊息
        logger.write_message("系統初始化完成")
        logger.write_message("請輸入帳號密碼並點擊登入")

    def buttonLogin_Click(self):
        try:
            user_id = self.entry_userid.get().replace(' ', '')
            password = self.entry_password.get().replace(' ', '')
            
            if not user_id or not password:
                logger.write_message("錯誤: 請輸入帳號和密碼")
                return
            
            logger.write_message(f"正在嘗試登入... 帳號: {user_id}")
            
            # 使用 SKClient 進行登入
            if self.sk_client:
                m_nCode = self.sk_client.login(user_id, password)
                
                if m_nCode == 0:
                    self.label_login_status.config(text="已登入", foreground="green")
                    self.btn_connection.config(state="normal")
                    self.labelID["text"] = user_id
                    logger.write_message("登入成功!")
                else:
                    self.label_login_status.config(text="登入失敗", foreground="red")
                    error_msg = self.sk_client.get_return_code_message(m_nCode)
                    logger.write_message(f"登入失敗: {error_msg} (Code: {m_nCode})")
        except Exception as e:
            self.label_login_status.config(text="登入錯誤", foreground="red")
            logger.write_message(f"登入異常: {str(e)}")
    
    def btnConnect_Click(self):
        """建立連線"""
        try:  
            logger.write_message("正在建立連線...")
            if self.sk_client:
                m_nCode = self.sk_client.connect()
                if m_nCode == 0:
                    self.label_connection_status["text"] = "狀態: 已連線"
                    self.label_connection_status["foreground"] = "green"
                    logger.write_message("連線建立成功")
                else:
                    self.label_connection_status["text"] = f"狀態: 連線失敗 (錯誤碼: {m_nCode})"
                    self.label_connection_status["foreground"] = "red"
                    logger.write_message(f"連線失敗，錯誤碼: {m_nCode}")            
        except Exception as e:
            self.label_connection_status.config(text="連線異常", foreground="red")
            logger.write_message(f"連線異常: {str(e)}")
    
    def clear_messages(self):
        """清除所有訊息"""
        self.listInformation.delete(0, 'end')
        # logger.write_message("訊息已清除")
    
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
                logger.write_message("沒有訊息可匯出")
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
                logger.write_message(f"訊息已匯出至: {filename}")
        except Exception as e:
            logger.write_message(f"匯出訊息失敗: {str(e)}")
