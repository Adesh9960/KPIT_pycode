import threading
from decoder import run_decoder

def start(notify_callback: function = None):
    decoder_thread = threading.Thread(target=run_decoder,args=(notify_callback,), daemon=True)
    decoder_thread.start()