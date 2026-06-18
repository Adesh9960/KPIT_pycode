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
            "data": frame.data.hex()
        }
    )
if __name__ == "__main__":
    app.run(debug=True)


