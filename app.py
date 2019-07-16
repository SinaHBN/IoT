import eventlet
import json
from flask import Flask, render_template
from flask_mqtt import Mqtt
from flask_socketio import SocketIO
from flask_bootstrap import Bootstrap
import time
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy
import os
from datetime import datetime
import Adafruit_DHT

eventlet.monkey_patch()

project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "database.db"))

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = database_file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['MQTT_BROKER_URL'] = 'localhost'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_CLIENT_ID'] = 'mqtt-client'
app.config['MQTT_KEEPALIVE'] = 65535
app.config['MQTT_TLS_ENLABLED'] = False
app.config['MQTT_LAST_WILL_TOPIC'] = 'LastWill'
app.config['MQTT_LAST_WILL_MESSAGE'] = 'Bye!'
app.config['MQTT_LAST_WILL_QOS'] = 0


mqtt = Mqtt(app)
socketio = SocketIO(app)
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)


# ______________MODEL______________________________________
class TempAndHum(db.Model):
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    datetime = db.Column(db.String, default=str(time.strftime("%A, %d. %B %Y %I:%M:%S %p")))

def __repr__(self):
    return "<Record: id={0}, temp={1}, hum= {2}, datetime={3}".format(self.id, self.temperature, self.humidity, self.datetime)


# _________________________________________________________


mqtt.subscribe('HumidityTemp')

@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('client_connected')
def handle_client_connect(json):
    print("client connected received: {0}".format(str(json)))


@socketio.on('publishTemp')
def handle_publish_temperature_and_humidity():
    humidity, temperature = Adafruit_DHT.read_retry(11, 4)
    data = str(temperature)+","+str(humidity)
    mqtt.publish("HumidityTemp", data, 0)


@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    print('ON MESSAGE________________________________')
    data = dict(
        topic=message.topic,
        payload=message.payload.decode(),
        qos=message.qos
    )
    tempHum = message.payload.decode().split(",")
    temperature = tempHum[0]
    humidity = tempHum[1]
    db.session.add(TempAndHum(temperature=temperature, humidity=humidity, datetime=str(time.strftime("%A, %d. %B %Y %I:%M:%S %p"))))
    db.session.commit()
    socketio.emit('getTemp', data=data)


@socketio.on('getGraphData')
def handle_get_graph_data():
    query_result = TempAndHum.query.order_by(sqlalchemy.desc(TempAndHum.id)).limit(5).all()
    data = [0 for x in range(5)]
    for i in range(5):
        data[4-i]= str(query_result[i].temperature)+";"+str(query_result[i].humidity)+";"+str(query_result[i].datetime)
    socketio.emit('drawGraph', data=data)



if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, use_reloader=False, debug=True)
