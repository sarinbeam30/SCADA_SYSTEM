import paho.mqtt.client as mqtt
import time, sys

########### -------------- MQTT SECTION ------------------ ****************
# MQTT Initialize
MQTT_BROKER_URL = "192.168.4.150"
MQTT_BROKER_PORT = 1883
MQTT_BROKER_SSL = 27758
MQTT_BROKER_USER = "odbyktmn"
MQTT_BROKER_PWD = "9esnfcLYs5wF"

ID = 'MQTT'
client = mqtt.Client(ID)

def on_connect(client, userdata, rc):
    print("SUB LEAW")
   
def on_message(client, userdata, msg):
    print(str(msg.topic) + " : " + str(msg.payload.decode('utf-8')) )

def on_disconnect():
    print('Disconnected from MQTT broker, reconnecting...')
    client.loop_stop(force=False)
    if rc != 0:
        print("Unexpected disconnection.")
    else:
        print("Disconnected")

def connect_to_mqtt_broker():
    # client.username_pw_set(username=MQTT_BROKER_USER, password=MQTT_BROKER_PWD)
    client.connect(host=MQTT_BROKER_URL, port=MQTT_BROKER_PORT, keepalive=60)
    print("CONNECT_TO_BROKER_SUCCESS")
    client.subscribe([("TOPIC/BT_TAG_1", 1), ("TOPIC/BT_TAG_2", 1)])
    client.on_message = on_message
    client.loop_forever()

    

def main():
    connect_to_mqtt_broker()
    print("KO TEST NOI")

while True:
    time.sleep(2)
    main()