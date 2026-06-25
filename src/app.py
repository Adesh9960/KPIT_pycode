from threading import Lock
from utils.frontendFieldMapper import build_analytics_packet
import logger.logger as logger
import listener.listener as listener
from uds_client.uds_client import UDS, UDSRoles
import Decoder.decoder_thread as decoder
import isotp
from uds_client.UDSError import UDSError
from utils.frontendFieldMapper import build_analytics_packet
from utils.files import zip_folder, delete_file
from utils.updateHistory import history, update_history
from flask import Flask, request, jsonify, render_template, send_file, after_this_request
import os
import logging

latest_analytics = {}
analytics_lock = Lock()
uds_client: UDS

app = Flask(
    __name__,
    template_folder="Frontend/templates",
    static_folder="Frontend/static"
)


class RouteFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        # Suppress logs for this route
        if "GET /live-data" in msg:
            return False
        return True

werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.addFilter(RouteFilter())

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
    print(data.get("DID"), data.get("value"))
    if uds_client is None: 
        return jsonify({
            "status": "error",
            "message": "UDS client not initialized"
        })
    try:
        response = uds_client.writeDataByIdentifier(data.get("DID"), data.get("value"))
        return jsonify(response)
    except Exception as e:
        print(e)
        return jsonify({
            "status": "error",
            "data": "Data could not be written"
        })

@app.route("/download/<file>")
def download(file):
    if file == "logger":
        print("sending logger...")
        zip_folder("../data/logger", "../data/all_logs")
        print("zip created!!")
        @after_this_request
        def cleanup(response):
            delete_file(path)
            return response
        path =  "../data/logger/all_logs.csv"
        return send_file(
           path
        )
    
    if file == "firmware":
        path = '../data/firmware/firmware.bin'
        uds_client.firmwareUpload(path)
        @after_this_request
        def cleanup(response):
            delete_file(path)
            return response
        
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
    print(f"DID : {data.get('DID')}. type: {type(data.get('DID'))}")
    print(f"control parameter: {data.get('control_parameter')}. type: {type(data.get('control_parameter'))}")
    print(f"control state : {data.get('control_state')}. type: {type(data.get('control_state'))}")

    try:
        uds_client.io_control(data.get('DID'), data.get('control_parameter'), data.get('control_state'))
        return jsonify({
            "status": "success",
            "message": "Control changed"
        })
    except UDSError as e:
        print("UDS Error")
        print(e)
        return jsonify({
            "status": "error",
            "message": e.message
        })
    except Exception as e:
        print(e)
        return jsonify({
            "status": "error",
            "message": "Could not change control"
        })


@app.route("/live-data", methods = ["GET"])
def live_data():
    with analytics_lock:
        return jsonify(latest_analytics)


def send_realtime_data(frame):

    analytics = build_analytics_packet(frame)

    if analytics:
        with analytics_lock:
            update_history(analytics)
            latest_analytics.update(analytics)


@app.route("/history-data", methods = ["GET"])
def history_data():
    with analytics_lock:
        return jsonify(history)


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
