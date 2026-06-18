import socketio

sio = socketio.Client()

@sio.event
def connect():
    print("Connected")

@sio.event
def disconnect():
    print("Disconnected")

sio.connect("http://localhost:5000")

sio.emit("message", {"hello": "world"})

sio.wait()
