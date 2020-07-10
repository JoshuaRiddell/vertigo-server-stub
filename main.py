#!/usr/bin/env python3

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, send, emit
import threading
from time import sleep
from flask_cors import CORS
from dummy_coordinates import gps_coordinates

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config["TEMPLATES_AUTO_RELOAD"] = True
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


@app.route('/')
def hello_world():
    return render_template("base.html")


param_values = {
    "seabed_height": 0.0,
    "surface_depth": 0.0,
    "track": 0.0,
}


@app.route('/annotation/videoPoint', methods=["POST"])
def add_video_point():
    content = request.json
    print("videoPoint:" + str(content))
    return jsonify(isError=False, message="Success", statusCode=200)


@app.route('/annotation/videoRectangle', methods=["POST"])
def add_video_rectangle():
    content = request.json
    print("videoRectangle:" + str(content))
    return jsonify(isError=False, message="Success", statusCode=200)


@app.route('/annotation/videoFrame', methods=["POST"])
def add_video_frame():
    content = request.json
    print("videoFrame:" + str(content))
    return jsonify(isError=False, message="Success", statusCode=200)


@socketio.on('json', namespace="/control/mode")
def control_mode(json):
    "Handle change of mode controlled by frontend."
    mode = json.get("mode")
    if mode is None or mode not in ["surface", "seabed", "manual", "stable"]:
        return

    print("Mode set to " + mode)
    socketio.emit("json", {"mode": mode}, namespace="/control/mode")


@socketio.on('json', namespace="/session/state")
def session_state(json):
    "Handle change of session state controlled by frontend."
    active = json.get("active")
    paused = json.get("paused")

    if type(active) != type(True) or type(paused) != type(True):
        return

    print("Session state set to active:" +
          str(active) + " paused:" + str(paused))
    socketio.emit("json", {"active": active,
                           "paused": paused}, namespace="/session/state")


@socketio.on('json', namespace="/control/parameters")
def control_parameters(json):
    "Handle change of parameter setpoint by frontend."
    if type(json) != type([]):
        return
    for param in json:
        handle_parameter_change(param)


def handle_parameter_change(param):
    name = param.get("name")
    value = float(param.get("value"))

    if name not in param_values.keys():
        return

    print("Parameter " + name + " changed to " + str(value))
    param_values[name] = value


def publish_function():
    param_state = param_values.copy()

    i = 0
    coordinates_index = 0
    while True:
        for key in param_state.keys():
            param_state[key] += (param_values[key] - param_state[key]) * 0.5

        msg = []
        for key in param_state.keys():
            msg.append({
                "name": key,
                "value": param_state[key],
                "unit": "m"
            })
        socketio.emit("json", msg, namespace="/control/parameters")
        socketio.emit("json", [
            {
                "name": "depth",
                "value": i,
                "unit": "m"
            },
            {
                "name": "depth",
                "value": i/10,
                "unit": "km"
            }
        ], namespace="/status/updates")

        # send gps coordinates
        if coordinates_index < len(gps_coordinates):
            socketio.emit(
                "json", gps_coordinates[coordinates_index], namespace="/surface/gps")
            coordinates_index += 1
        else:
            coordinates_index = 0
            i = 0

        i += 0.4

        sleep(1)


if __name__ == '__main__':
    t = threading.Thread(target=publish_function)
    t.start()
    socketio.run(app, host="0.0.0.0")
