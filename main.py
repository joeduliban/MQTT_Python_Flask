from flask import Flask, render_template, jsonify
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import threading

app = Flask(__name__)

# Liste globale pour stocker les messages
messages = []

# Configuration MQTT
TTN_USERNAME = "joe-valentin-isib-test-lora@ttn"
TTN_PASSWORD = "NNSXS.MRNEVXPTLWEG75MMWK6EYO4JZ5DV3JX644IOM7A.UW3AJHVDETRSWMBZLJDLINTFNVCI4FEIEX4UBXOKXSI3NPFC4MJQ"
TTN_BROKER = "eu1.cloud.thethings.network"
TTN_PORT = 1883
DEVICE_ID = "joe-valentin-node-2"

def process_ttn_payload(payload_json):
    """
    Traitement spécifique des payloads de The Things Network
    """
    try:
        # Vérifier si c'est un uplink message
        if 'uplink_message' in payload_json:
            uplink = payload_json['uplink_message']
            
            # Récupérer le payload décodé
            decoded_payload = uplink.get('decoded_payload', {})
            
            # Récupérer le timestamp
            timestamp_str = uplink.get('received_at', datetime.now().isoformat())
            
            # Si le payload est une chaîne de caractères
            if isinstance(decoded_payload.get('payload'), str):
                # Diviser la chaîne par des virgules
                values = decoded_payload['payload'].split(',')
                
                # Vérifier qu'on a bien 3 valeurs
                if len(values) == 3:
                    return {
                        'temperature': float(values[0]),
                        'humidity': float(values[1]),
                        'light': float(values[2]),
                        'timestamp': timestamp_str
                    }
            
            # Si le payload est déjà un dictionnaire
            elif isinstance(decoded_payload, dict):
                return {
                    'temperature': decoded_payload.get('temperature', 'N/A'),
                    'humidity': decoded_payload.get('humidity', 'N/A'),
                    'light': decoded_payload.get('light', 'N/A'),
                    'timestamp': timestamp_str
                }
        
        # Si aucun traitement n'a abouti
        return {
            'temperature': 'N/A',
            'humidity': 'N/A',
            'light': 'N/A',
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"Erreur de traitement des données TTN: {e}")
        return {
            'temperature': 'Erreur',
            'humidity': 'Erreur',
            'light': 'Erreur',
            'timestamp': datetime.now().isoformat()
        }

def mqtt_connect():
    def on_connect(client, userdata, flags, rc):
        print(f"Connecté avec le code de résultat {rc}")
        
        # Topics possibles
        topics = [
            f"v3/{TTN_USERNAME}/devices/{DEVICE_ID}/up",
            f"v3/{TTN_USERNAME}/up"
        ]
        
        for topic in topics:
            client.subscribe(topic)
            print(f"Abonnement au topic: {topic}")

    def on_message(client, userdata, msg):
        try:
            # Décodage du payload
            payload_str = msg.payload.decode('utf-8')
            payload_json = json.loads(payload_str)
            
            # Traitement des données de capteurs
            sensor_data = process_ttn_payload(payload_json)
            
            # Ajouter à la liste des messages
            messages.append(sensor_data)
            
            # Limiter la liste à 50 derniers messages
            if len(messages) > 50:
                messages.pop(0)
            
            print(f"Données reçues: {sensor_data}")
        
        except Exception as e:
            print(f"Erreur de traitement du message: {e}")

    client = mqtt.Client(
        client_id="",  # ID aléatoire
        protocol=mqtt.MQTTv311
    )
    
    client.username_pw_set(TTN_USERNAME, TTN_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    
    client.connect(TTN_BROKER, TTN_PORT, keepalive=60)
    client.loop_start()

@app.route('/')
def index():
    return render_template('sensor_dashboard.html', messages=messages)

@app.route('/data')
def get_data():
    return jsonify(messages)

if __name__ == '__main__':
    # Démarrer la connexion MQTT dans un thread
    mqtt_thread = threading.Thread(target=mqtt_connect)
    mqtt_thread.start()
    
    app.run(debug=True, host='0.0.0.0', port=5000)