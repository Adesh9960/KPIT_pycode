import logger.logger as logger
import listener.listener as listener
from encoder.encoder import encode
from uds_client.uds_client import UDS, UDSRoles
import Decoder.decoder_thread as decoder
import isotp

from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO


app = Flask(
    __name__,
    template_folder="Frontend/templates",
    static_folder="Frontend/static"
)

socketio = SocketIO(app, cors_allowed_origins=["*"])

@app.route("/")
def home():
    return render_template('index.html')


@app.route("/DID", methods = ["POST"])
def send_DID():
    data = request.get_json()
    
    return jsonify({
        "status": "success",
        "received": data
    })
@app.route("/DID", methods = ["GET"])
def get_DID():
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
    print("Send realitme called")
    print(frame)
    socketio.emit(
        "analytics",
        {
            "speed": frame["signals"]["Speed"],
            "rpm": frame["signals"]["RPM"]
        }
    )

if __name__ == "__main__":
    address = isotp.Address(
    isotp.AddressingMode.Normal_11bits,
    txid=0x22,
    rxid=0x62
    )
    uds_client = UDS(UDSRoles.USER)
    listener.start(address, uds_client.on_response)
    decoder.start(send_realtime_data)
    logger.start()
    app.run()


