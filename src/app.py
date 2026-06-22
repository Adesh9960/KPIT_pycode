import logger.logger as logger
import listener.listener as listener
from uds_client.uds_client import UDS, UDSRoles
import Decoder.decoder_thread as decoder
import isotp
from utils.frontendFieldMapper import build_analytics_packet
from utils.files import zip_folder, delete_file
from flask import Flask, request, jsonify, render_template, send_file
from flask_socketio import SocketIO

uds_client: UDS

app = Flask(
    __name__,
    template_folder="Frontend/templates",
    static_folder="Frontend/static"
)

socketio = SocketIO(app, cors_allowed_origins=["*"])

@app.route("/")
def home():
    return render_template('index.html')

@app.route("/DID/<int:DID>", methods = ["GET"])
def get_DID(DID):
    if uds_client is None: 
        return jsonify({
            "status": "error",
            "message": "UDS client not initialized"
        })
    response = uds_client.readDataByIdentifier(DID)
    return jsonify({
        "status": "success",
        "data": response 
    })

@app.route("/DID", methods = ["POST"])
def set_DID():
    data = request.get_json()
    print(data)
    if uds_client is None: 
        return jsonify({
            "status": "error",
            "message": "UDS client not initialized"
        })
    try:
        uds_client.writeDataByIdentifier(data.get("DID"), data.get("value"))
        return jsonify({
            "status": "success",
            "data": "Data written"
        })
    except Exception as e:
        print(e)
        return jsonify({
            "status": "error",
            "data": "Data could not be written"
        })

@app.route("/download/<file>")
def download(file):
    if file == "logger":
        zip_folder("../data/logger", "../data/all_logs")
        return send_file(
            "../data/all_logs"
        )
    
    if file == "/firmware":
        uds_client.firmwareUpload('../data/firmware/firmware.bin')
        try:
            return send_file(
                "../data/firmware/firmware.bin",
                as_attachment=True
        )
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": "Could not download firmware"
            })

@app.route("/security_access/<int:level>")
def security_access(level):
    try:
        uds_client.security_access(level)
        return jsonify({
            "status": "success",
            "message": "Security Access Granted"
        })
    except Exception as e:
        print(e)
        return jsonify({
            "status": "error",
            "message": "Security Access Failed"
        })

@app.route("/diagnostics_session_control/<int:session>")
def diagnostics_session_control(session):
    try:
        uds_client.diagnostic_session_control(session)
        return jsonify({
            "status": "success",
            "message": "Session Access Granted"
        })
    except Exception as e:
        print(e)
        return jsonify({
            "status": "error",
            "message": "Session Access Failed"
        })

@app.route("/IO_control", methods = ["POST"])
def IO_control():
    data = request.get_json()
    try:
        uds_client.io_control(data.get('DID'), data.get('control_parameter'), data.get('control_state'))
        return jsonify({
            "status": "success",
            "message": "Control changed"
        })
    except Exception as e:
        print(e)
        return jsonify({
            "status": "error",
            "message": "Could not change control"
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
    analytics = build_analytics_packet(frame)
    socketio.emit(
        "analytics",
        analytics
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


