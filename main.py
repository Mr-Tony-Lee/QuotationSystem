import comtypes.client 
from tkinter import Tk, ttk
import sys
import os

# 確保可以導入 MainProg 套件
sys.path.append(os.getcwd())

from Module.ui.login import FrameLogin
from Module.ui.quote import Quote
from Module.ui.information import FrameInformation
from Module.ui.output import FrameOutput
from Module.ui.position_page import PositionPage 
from Module.ui.dialogs import AnnouncementDialog
from Module.sk_api import SKClient, SKQuoteLibEvents, SKReplyLibEvent, SKOrderLibEvents
from Module.data_manager import DataManager
from Module.logger import logger

# Global Event Handler references to prevent GC
# Global Event Handler references to prevent GC
sk_quote_event_handler = None
sk_reply_event_handler = None
sk_order_event_handler = None

def main():
    global sk_quote_event_handler, sk_reply_event_handler, sk_order_event_handler
    
    root = Tk()
    root.title("交易系統 v2.1")
    root.geometry("1400x900")
    
    # === UI Beautification: Setup Global Styles ===
    setup_styles()
    
    # Show Announcement
    if AnnouncementDialog.should_show_announcement():
        AnnouncementDialog(root)
    
    # Initialize Core Components
    data_manager = DataManager()
    sk_client = SKClient()
    
    # Dependency Injection
    data_manager.set_sk_client(sk_client)
    
    # Hook up events
    try:
        # Quote Events
        sk_quote_event = SKQuoteLibEvents(data_manager)
        sk_quote_event_handler = comtypes.client.GetEvents(sk_client.skQ, sk_quote_event)
        
        # Reply Events
        sk_reply_event = SKReplyLibEvent()
        sk_reply_event_handler = comtypes.client.GetEvents(sk_client.skR, sk_reply_event)
        
        # Order Events (for Position)
        sk_order_event = SKOrderLibEvents(data_manager)
        sk_order_event_handler = comtypes.client.GetEvents(sk_client.skO, sk_order_event)

    except Exception as e:
        logger.write_message(f"Event Handler Initialization Failed: {e}")

    # Initialize GUI Components
    # Styling for Notebook is handled in setup_styles
    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True, padx=10, pady=10)
    
    login_frame = FrameLogin(sk_client=sk_client)
    root.login_frame = login_frame
    notebook.add(login_frame, text=" 登入 ")  # Added spaces for better look
    
    quote_page = Quote(root=root, sk_client=sk_client, data_manager=data_manager)
    notebook.add(quote_page, text=" 報價來源 ")
    
    info_frame = FrameInformation(root=root, data_manager=data_manager)
    notebook.add(info_frame, text=" 總整理 ")

    output_frame = FrameOutput(root=root, data_manager=data_manager)
    notebook.add(output_frame, text=" 輸出 ")

    position_page = PositionPage(root=root, sk_client=sk_client, data_manager=data_manager)
    notebook.add(position_page, text=" 持倉 ")

    # Start Logger Processing
    # Using root.after in a loop, similar to original process_com_events but cleaner
    logger.set_gui_listbox(login_frame.listInformation)
    
    def process_logger_queue():
        logger.process_queue()
        root.after(100, process_logger_queue)
        
    root.after(100, process_logger_queue)

    root.mainloop()

def setup_styles():
    """設定應用程式的全域樣式"""
    style = ttk.Style()
    
    # 使用 'clam' 作為基礎主題，因為它支援較多的自定義
    try:
        style.theme_use('clam')
    except:
        pass
        
    # 定義色票
    COLOR_BG_MAIN = "#f5f6f7"       # 主背景色 (淡灰)
    COLOR_BG_DARK = "#e1e4e8"       # 深一點的背景 (Tab背景等)
    COLOR_ACCENT = "#0078d7"        # 強調色 (微軟藍)
    COLOR_ACCENT_HOVER = "#1084e3"  # 強調色懸停
    COLOR_TEXT = "#333333"          # 主要文字顏色
    COLOR_TEXT_LIGHT = "#ffffff"    # 反白文字顏色
    
    # 設定字型
    DEFAULT_FONT = ("Microsoft JhengHei UI", 10)
    HEADER_FONT = ("Microsoft JhengHei UI", 10, "bold")
    
    # === 一般控制項設定 ===
    style.configure(".", 
        font=DEFAULT_FONT, 
        background=COLOR_BG_MAIN, 
        foreground=COLOR_TEXT
    )
    
    # === LabelFrame ===
    style.configure("TLabelframe", 
        background=COLOR_BG_MAIN, 
        borderwidth=1, 
        relief="solid"
    )
    style.configure("TLabelframe.Label", 
        font=("Microsoft JhengHei UI", 10, "bold"), 
        foreground=COLOR_ACCENT,
        background=COLOR_BG_MAIN
    )
    
    # === Button ===
    style.configure("TButton", 
        font=("Microsoft JhengHei UI", 10),
        padding=6,
        relief="flat",
        background="#e1e1e1"
    )
    style.map("TButton",
        background=[('active', '#d0d0d0'), ('disabled', '#f0f0f0')],
        foreground=[('disabled', '#a0a0a0')]
    )
    
    # === Notebook (分頁) ===
    style.configure("TNotebook", 
        background=COLOR_BG_DARK, 
        borderwidth=0
    )
    style.configure("TNotebook.Tab", 
        font=("Microsoft JhengHei UI", 11), 
        padding=[15, 5], 
        background=COLOR_BG_DARK,
        foreground="#666666"
    )
    style.map("TNotebook.Tab", 
        background=[('selected', COLOR_BG_MAIN)], 
        foreground=[('selected', COLOR_ACCENT)],
        expand=[('selected', [1, 1, 1, 0])] # remove bottom border for selected
    )
    
    # === Treeview (表格) ===
    style.configure("Treeview", 
        background="white",
        fieldbackground="white",
        font=("Consolas", 10), # 表格數據使用等寬字體較佳
        rowheight=25,
        borderwidth=0
    )
    style.map("Treeview", 
        background=[('selected', COLOR_ACCENT)], 
        foreground=[('selected', 'white')]
    )
    style.configure("Treeview.Heading", 
        font=HEADER_FONT, 
        background="#e1e1e1", 
        foreground="#333333",
        relief="flat",
        padding=5
    )
    style.map("Treeview.Heading",
        background=[('active', '#d0d0d0')]
    )
    
    # === Scrollbar ===
    style.configure("Vertical.TScrollbar", 
        gripcount=0,
        relief="flat",
        background="#cccccc",
        darkcolor="#cccccc",
        lightcolor="#cccccc",
        troughcolor="#f0f0f0",
        bordercolor="#f0f0f0",
        arrowcolor="#333333"
    )


if __name__ == '__main__':
    main()
