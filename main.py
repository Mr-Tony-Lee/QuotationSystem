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
    root.title("交易系統 v2.0 - Refactored")
    root.geometry("1400x900")
    
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
    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True, padx=10, pady=10)
    
    login_frame = FrameLogin(sk_client=sk_client)
    root.login_frame = login_frame
    notebook.add(login_frame, text="登入")
    
    quote_page = Quote(root=root, sk_client=sk_client, data_manager=data_manager)
    notebook.add(quote_page, text="報價來源")
    
    info_frame = FrameInformation(root=root, data_manager=data_manager)
    notebook.add(info_frame, text="總整理")

    output_frame = FrameOutput(root=root, data_manager=data_manager)
    notebook.add(output_frame, text="輸出")

    position_page = PositionPage(root=root, sk_client=sk_client, data_manager=data_manager)
    notebook.add(position_page, text="持倉")

    # Start Logger Processing
    # Using root.after in a loop, similar to original process_com_events but cleaner
    logger.set_gui_listbox(login_frame.listInformation)
    
    def process_logger_queue():
        logger.process_queue()
        root.after(100, process_logger_queue)
        
    root.after(100, process_logger_queue)

    root.mainloop()

if __name__ == '__main__':
    main()
