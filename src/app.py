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
import time
import json

latest_analytics = {}
analytics_lock = Lock()
uds_client: UDS

current_session = 1
current_security_level = 0
app = Flask(
    __name__,
    template_folder="Frontend/templates",
    static_folder="Frontend/static"
)
start_time_flag: float = 0
prev_count: int = 0

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
    try:
        uds_client.diagnostic_session_control(1)
        uds_client.security_access(0)
        return render_template('index.html')
    except Exception as e:
        print(e)
        return jsonify({
            "status": "error",
            "message": "Session Access Failed"
        })
    

@app.route("/DID/<int:DID>", methods = ["GET"])
def get_DID(DID):
    if uds_client is None: 
        return jsonify({
            "status": "error",
            "message": "UDS client not initialized"
        })
    try:
        response = uds_client.readDataByIdentifier(DID)
        return jsonify({
            "status": "success",
            "data": response 
        })
    except UDSError as e:
        print(e)
        return jsonify({
            "status": "error",
            "message": e.message
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
@app.route("/DTC", methods = ["GET"])
def get_all_DTC():
    try:
        response = uds_client.read_dtcs()
        return jsonify(response)
    except UDSError as e:
        print(e)
        return jsonify({
            "status": "error",
            "message": e.message
        })
@app.route("/DTC", methods=["DELETE"])
def clearDTC():
    try:
        response = uds_client.clear_all_dtcs()
        return jsonify(response)
    except UDSError as e:
        print(e)
        return jsonify({
            "status": "error",
            "message": e.message
        })
    
@app.route("/download/<file>")
def download(file):
    if file == "logger":
        print("sending logger...")
        zip_folder("../data/logger", "../data/all_logs")
        print("zip created!!")
       
        path = os.path.dirname(os.getcwd())
        path =  os.path.join(path, 'data', 'all_logs.zip')
        response = send_file(
           path,
           as_attachment=True,
           conditional=False
        )
        response.direct_passthrough = False
        print(response.direct_passthrough)
        print("registering cleanup")
        @response.call_on_close
        def cleanup():
            try:
                os.remove(path)
                print("Zip deleted.")
            except Exception as e:
                print(f"Cleanup failed: {e}")
        return response
    
    if file == "firmware":
        path = os.path.join(os.path.dirname(os.getcwd()), 'data', 'firmware', 'firmware.bin')
        try:
            uds_client.firmwareUpload(path)
            response = send_file(
                path,
                as_attachment=True,
                conditional=False
            )
            response.direct_passthrough = False

            @response.call_on_close
            def cleanup():
                try:
                    os.remove(path)
                    print("firmware duplicate deleted.")
                except Exception as e:
                    print(f"Cleanup failed: {e}")
            return response
        except UDSError as e:
            print(e)
            return jsonify({
                "status": "error",
                "message": e.message
            })
        except Exception as e:
            print(e)
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
    stats = listener.get_stats()
    with analytics_lock:
        global start_time_flag
        global prev_count
        latest_analytics["error_frames"] = stats.error_frames
        delta_time = time.monotonic() - start_time_flag
        latest_analytics["message_speed"] = round((stats.rx_frames - prev_count) / delta_time, 2)
        prev_count = stats.rx_frames
        start_time_flag = time.monotonic()
        return jsonify(latest_analytics)


def send_realtime_data(frame):
    analytics = build_analytics_packet(frame)

    with analytics_lock:
        update_history(analytics)
        latest_analytics.update(analytics)


@app.route("/history-data", methods = ["GET"])
def history_data():
    with analytics_lock:
        history_json = json.dumps(
            {key: list(value) for key, value in history.items()},
            indent=4
        )
        return history_json

@app.route("/state", methods= ["GET"])
def get_state():
    return {
        "status": "success",
        "current_session": current_session,
        "current_security_level": current_security_level
    }

if __name__ == "__main__":
    address = isotp.Address(
    isotp.AddressingMode.Normal_11bits,
    txid=0x22,
    rxid=0x62
    )
    uds_client = UDS(UDSRoles.USER)
    listener.start(address, uds_client.on_response)
    start_time_flag = time.monotonic()
    decoder.start(send_realtime_data)
    logger.start()
    app.run()
