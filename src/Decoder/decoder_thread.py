import threading
from decoder import run_decoder

def start():
    decoder_thread = threading.Thread(target=run_decoder, daemon=True)
    decoder_thread.start()