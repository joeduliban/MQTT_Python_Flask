from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import threading

app = Flask(__name__)
socketio = SocketIO(app)

# Configuration MQTT (identique à votre code précédent)
TTN_USERNAME = "joe-valentin-isib-test-lora@ttn"
TTN_PASSWORD = "NNSXS.MRNEVXPTLWEG75MMWK6EYO4JZ5DV3JX644IOM7A.UW3AJHVDETRSWMBZLJDLINTFNVCI4FEIEX4UBXOKXSI3NPFC4MJQ"
TTN_BROKER = "eu1.cloud.thethings.network"
TTN_PORT = 1883

DEVICES = {
    "joe-valentin-node-1": "Device Alpha",
    "joe-valentin-node-2": "Device Beta"
}

messages = []

def process_ttn_payload(payload_json):
    try:
        if 'uplink_message' in payload_json:
            uplink = payload_json['uplink_message']
            decoded_payload = uplink.get('decoded_payload', {})
            timestamp_str = uplink.get('received_at', datetime.now().isoformat())
            
            device_id = payload_json.get('end_device_ids', {}).get('device_id', 'Unknown')
            device_name = DEVICES.get(device_id, device_id)
            
            if isinstance(decoded_payload.get('payload'), str):
                values = decoded_payload['payload'].split(',')
                
                if len(values) == 3:
                    return {
                        'device_name': device_name,
                        'device_id': device_id,
                        'temperature': float(values[0]),
                        'humidity': float(values[1]),
                        'light': float(values[2]),
                        'timestamp': timestamp_str
                    }
            
            return None
    except Exception as e:
        print(f"Erreur de traitement des données TTN: {e}")
        return None

def mqtt_connect():
    def on_connect(client, userdata, flags, rc):
        print(f"Connecté avec le code de résultat {rc}")
        
        for device_id in DEVICES.keys():
            topics = [
                f"v3/{TTN_USERNAME}/devices/{device_id}/up",
                f"v3/{TTN_USERNAME}/up"
            ]
            
            for topic in topics:
                client.subscribe(topic)
                print(f"Abonnement au topic: {topic}")
    
    def on_message(client, userdata, msg):
        try:
            payload_str = msg.payload.decode('utf-8')
            payload_json = json.loads(payload_str)
            
            device_id = payload_json.get('end_device_ids', {}).get('device_id')
            if device_id in DEVICES:
                sensor_data = process_ttn_payload(payload_json)
                
                if sensor_data:
                    messages.append(sensor_data)
                    
                    if len(messages) > 50:
                        messages.pop(0)
                    
                    # Envoi en temps réel via SocketIO
                    socketio.emit('new_sensor_data', sensor_data)
                    print(f"Données reçues: {sensor_data}")
        
        except Exception as e:
            print(f"Erreur de traitement du message: {e}")
    
    client = mqtt.Client(
        client_id="",
        protocol=mqtt.MQTTv311
    )
    
    client.username_pw_set(TTN_USERNAME, TTN_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    
    client.connect(TTN_BROKER, TTN_PORT, keepalive=60)
    client.loop_start()

@app.route('/')
def index():
    return render_template('sensor_dashboard.html')

if __name__ == '__main__':
    mqtt_thread = threading.Thread(target=mqtt_connect)
    mqtt_thread.start()
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)