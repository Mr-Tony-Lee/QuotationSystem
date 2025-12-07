import queue
import datetime

class Logger:
    def __init__(self):
        self.com_event_queue = queue.Queue()
        self.gui_listbox = None
        self.log_callback = None

    def set_gui_listbox(self, listbox):
        self.gui_listbox = listbox

    def set_callback(self, callback):
        self.log_callback = callback

    def write_message(self, message, list_info=None):
        """安全的訊息寫入函數 - 使用隊列機制避免 COM 事件衝突"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # 將消息放入隊列
        # param: (event_type, message, listbox_reference)
        # list_info argument is kept for compatibility but we prefer using registered listbox
        target_listbox = list_info if list_info else self.gui_listbox
        self.com_event_queue.put(('message', formatted_message, target_listbox))

    def process_queue(self):
        """處理隊列中的消息，這個方法應該由 GUI 主線程定時調用"""
        try:
            while True:
                try:
                    event_type, message, listbox = self.com_event_queue.get_nowait()
                    if event_type == 'message':
                        if listbox is not None and listbox.winfo_exists():
                            listbox.insert('end', message)
                            listbox.see('end')
                        elif self.log_callback:
                            self.log_callback(message)
                except queue.Empty:
                    break
        except Exception as e:
            print(f"Error processing event queue: {e}")

# Global logger instance
logger = Logger()
