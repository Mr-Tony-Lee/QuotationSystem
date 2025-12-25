from tkinter import Frame, Listbox, ttk, BooleanVar, Checkbutton
from ..logger import logger
import json
import os

class FrameLogin(Frame):
    def __init__(self, master=None, sk_client=None):
        Frame.__init__(self, master)
        self.sk_client = sk_client
        self.config_file = "login_config.json"
        
        self.FrameLogin = Frame(self)
        self.FrameLogin.pack(fill="both", expand=True)
        self.createWidgets()
        self._load_credentials()
        
    def createWidgets(self):
        # 使用者ID
        # === 登入區塊 ===
        login_group = ttk.LabelFrame(self.FrameLogin, text="登入設定", style="TLabelframe")
        login_group.pack(fill="x", padx=15, pady=10)
        ttk.Label(login_group, text="UserID:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_userid = ttk.Entry(login_group, width=20)
        self.entry_userid.grid(row=0, column=1, padx=5, pady=5)
        
        # 密碼
        ttk.Label(login_group, text="Password:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.entry_password = ttk.Entry(login_group, width=20, show="*")
        self.entry_password.grid(row=1, column=1, padx=5, pady=5)

        # 記住我選項
        self.var_remember = BooleanVar()
        self.chk_remember = ttk.Checkbutton(login_group, text="記住帳號密碼", variable=self.var_remember)
        self.chk_remember.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # 登入按鈕
        self.btn_login = ttk.Button(login_group, text="登入", command=self.buttonLogin_Click)
        self.btn_login.grid(row=0, column=2, rowspan=2, padx=15, pady=5)
        
        # === 連線控制區塊 ===
        connection_group = ttk.LabelFrame(self.FrameLogin, text="連線控制", style="TLabelframe")
        connection_group.pack(fill="x", padx=15, pady=10)
        
        # 連線按鈕
        self.btn_connection = ttk.Button(connection_group, text="建立連線", command=self.btnConnect_Click)
        self.btn_connection.grid(row=0, column=0, padx=10, pady=10)
        self.btn_connection.config(state="disabled")
        
        # === 狀態顯示區塊 ===
        status_group = ttk.LabelFrame(self.FrameLogin, text="連線狀態", style="TLabelframe")
        status_group.pack(fill="x", padx=15, pady=10)
        
        # 登入狀態
        ttk.Label(status_group, text="登入狀態:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.label_login_status = ttk.Label(status_group, text="未登入", foreground="red")
        self.label_login_status.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        # 連線狀態
        ttk.Label(status_group, text="連線狀態:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.label_connection_status = ttk.Label(status_group, text="未連線", foreground="red")
        self.label_connection_status.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        # === 訊息顯示區塊 ===
        message_group = ttk.LabelFrame(self.FrameLogin, text="系統訊息", style="TLabelframe")
        message_group.pack(fill="both", expand=True, padx=15, pady=10)
        
        # 創建訊息框和滾動條
        message_frame = ttk.Frame(message_group)
        message_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 訊息列表框
        self.listInformation = Listbox(message_frame, height=15, font=("Consolas", 9), relief="flat", borderwidth=1, selectbackground="#0078d7")
        self.listInformation.pack(side="left", fill="both", expand=True)
        
        # 滾動條
        scrollbar = ttk.Scrollbar(message_frame, orient="vertical", command=self.listInformation.yview)
        scrollbar.pack(side="right", fill="y")
        self.listInformation.config(yscrollcommand=scrollbar.set)
        
        # 清除訊息按鈕
        btn_frame = ttk.Frame(message_group)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(btn_frame, text="清除訊息", command=self.clear_messages).pack(side="left")
        ttk.Button(btn_frame, text="匯出訊息", command=self.export_messages).pack(side="left", padx=5)
        
        # 警告標籤
        ttk.Label(btn_frame, text="(注意: 記住密碼功能會將密碼儲存於本地檔案)", foreground="gray", font=("Microsoft JhengHei UI", 8)).pack(side="right", padx=5)


        # ID 標籤（用於全域變數）
        self.labelID = ttk.Label(status_group, text="")
        self.labelID.grid(row=0, column=2, sticky="w", padx=20, pady=2)

        # 註冊 listbox 到 logger
        logger.set_gui_listbox(self.listInformation)
        
        # 初始訊息
        logger.write_message("系統初始化完成")
        logger.write_message("請輸入帳號密碼並點擊登入")

    def _load_credentials(self):
        """讀取儲存的帳號密碼"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    if config.get('remember', False):
                        self.var_remember.set(True)
                        self.entry_userid.insert(0, config.get('user_id', ''))
                        self.entry_password.insert(0, config.get('password', ''))
                        logger.write_message("已載入儲存的帳號密碼")
            except Exception as e:
                logger.write_message(f"讀取設定檔失敗: {e}")

    def _save_credentials(self, user_id, password):
        """儲存帳號密碼"""
        try:
            config = {}
            if self.var_remember.get():
                config = {
                    'remember': True,
                    'user_id': user_id,
                    'password': password
                }
            else:
                config = {'remember': False}
                
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            logger.write_message(f"儲存設定檔失敗: {e}")

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
                    
                    # 儲存或清除帳號密碼
                    self._save_credentials(user_id, password)
                    
                    # Auto-fetch account info
                    logger.write_message("正在自動取得帳號資訊...")
                    # Ensure Order API is initialized
                    self.sk_client.initialize_order_api()
                    self.sk_client.get_user_account()
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
