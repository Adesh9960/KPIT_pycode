import logger.logger as logger
import listener.listener as listener
from encoder.encoder import encode
from uds_client.uds_client import UDS, UDSRoles
import Decoder.decoder_thread as decoder
import isotp

from flask import Flask, request, jsonify
from flask_socketio import SocketIO


app = Flask(__name__)
socketio = SocketIO(app)

@app.route("/")
def home():
    return "Hello Flask!"


@app.route("/uds", methods = ["POST"])
def uds():
    data = request.get_json()

    print(data)

    return jsonify({
        "status": "success",
        "received": data
    })

@socketio.on("connect")
def handle_connect():
    print("Client connected")

@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected")


def send_realtime_data(frame):
    socketio.emit(
        "can_frame",
        {
            "id": frame.can_id,
            "signals": frame.signals
        }
    )


address = isotp.Address(
    isotp.AddressingMode.Normal_11bits,
    txid=0x22,
    rxid=0x62
)

uds_client = UDS(UDSRoles.USER)
listener.start(address, uds_client.on_response)
logger.start()
decoder.start(send_realtime_data)


if __name__ == "__main__":
    app.run(debug=True)


