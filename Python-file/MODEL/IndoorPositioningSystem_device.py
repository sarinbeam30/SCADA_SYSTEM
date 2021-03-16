import socket, json, paho.mqtt.client as mqtt, time, sys



class IndoorPositioningSystem_SCADA():
    def __init__(self, IP_address="192.168.4.150", device_name="BT_TAG_1"):
        self.IP_address = IP_address
        self.device_name = device_name

        self.MQTT_BROKER_URL = "192.168.4.150"
        self.MQTT_BROKER_PORT = 1883
        self.ID = 'MQTT'
        self.client = mqtt.Client(self.ID)
        self.client.connect(host=self.MQTT_BROKER_URL, port=self.MQTT_BROKER_PORT, keepalive=60)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        self.message_receive = " "
    

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("**** CONNECT_TO_MQTT_BROKER_SUCCESS ****")
        else:
            print("bad connection Returned code=", rc)
        self.client.subscribe([("TOPIC/BT_TAG_1", 1), ("TOPIC/BT_TAG_2", 1)])

    def on_subscribe(self,client, userdata, mid, granted_qos):
        print("Subscription complete")
    
    def on_message(self, client, userdata, msg):
        # print(str(msg.topic) + " : " + str(msg.payload.decode("utf-8")) )
        print('--- receive message leaw ---')
        self.message_receive = str(msg.payload.decode("utf-8"))
        # print(self.message_receive)
        self.return_payload()
    
    def return_payload(self):
        print("PAYLOAD : " ,self.message_receive)
        return self.message_receive

    def end_MQTT_service(self):
        print('Ending Connection')
        self.client.loop_stop()
        self.client.disconnect()
        time.sleep(3)

    def start_MQTT_service(self):
        # client.connect(host=MQTT_BROKER_URL, port=MQTT_BROKER_PORT, keepalive=60)
        # client.subscribe([("TOPIC/BT_TAG_1", 1), ("TOPIC/BT_TAG_2", 1)])
        # client.on_message = self.MQTT_ON_MESSAGE()
        # client.loop_start()

        # self.client = mqtt.Client(self.ID)
        # self.client.on_message = self.on_message
        # self.client.on_connect = self.on_connect
        self.client.connect(host=self.MQTT_BROKER_URL, port=self.MQTT_BROKER_PORT, keepalive=60)
        self.client.loop_start()
    

    def getDataFromRASPI_SOCKET(self):
        s = socket.socket()
        port = 15000
        IP_ADDR = self.IP_address
        result = -1
        try:
            s.connect((IP_ADDR, port))
            print('**** CONNECT TO WEB SOCKET LEAW ****')
            bytes_text = s.recv(2048)
            string_text = bytes_text.decode("utf-8") 
            json_text = json.dumps(string_text)
            result = string_text
            s.close()
        except Exception as x:
            print(x)
            result = -1
            try: 
                print("SOCKET IS BROKE")
                s.close()
            except:
                print("faulty data")
        print("RESULT TYPE : " , type(result))
        print("JSON_DATA : ", result)
        return result

if __name__ == "__main__":

    while True:
        print('TEST_MAIN_IN_IPS_DEVICE')
        BT_1 = IndoorPositioningSystem_SCADA(IP_address="192.168.4.150", device_name="BT_TAG_1")
        # BT_1 = IndoorPositioningSystem_SCADA(IP_address="127.0.0.1", device_name="BT_TAG_1")
        BT_1.getDataFromRASPI_SOCKET()
        # BT_1.start_MQTT_service()
        # BT_1.end_MQTT_service()
        # BT_1.return_payload()
        time.sleep(5)




