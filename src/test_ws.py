import socketio

sio = socketio.Client()

@sio.event
def connect():
    print("Connected")

@sio.on("can_frame")
def handle_can_frame(data):
    print("Received:", data)

@sio.event
def disconnect():
    print("Disconnected")

sio.connect("http://localhost:5000")


sio.emit("message", {"hello": "world"})

sio.wait()
