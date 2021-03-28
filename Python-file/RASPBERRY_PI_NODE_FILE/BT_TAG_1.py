import requests, json, socket, random, time, sys, os, paho.mqtt.client as client
from datetime import datetime

# MQTT_INITIALIZE
hostname = "192.168.4.150"
port = 1883
ID = sys.argv[0]+str(os.getpid())
mclient = client.Client(ID)
mclient.connect(hostname, port=1883,keepalive=60)

class IPS_NODE ():
    def __init__(self, IP_address="192.168.4.150",device_name="BT_TAG_1",location="ABC Building", floor=7,room="ECC-804"):
        self.API_ENDPOINT = "http://192.168.4.150:5678/getDATA"
        self.IP_address = IP_address
        self.bt_tag_device_name = device_name
        self.bt_tag_owner = 'Admin_BT_TAG_1'
        self.location = location
        self.latitude = 30.0000
        self.longtitude = 52.000
        self.floor = floor
        self.room = room
        self.x_coord = 1.234
        self.y_coord = 5.678
    
    def setBtTagOwner(self, name):
        self.bt_tag_owner = name
    
    def setXcoord(self):
        self.x_coord = (float("{:.3f}".format(random.uniform(0.0, 10.0))))
    
    def setYcoord(self):
        self.y_coord = (float("{:.3f}".format(random.uniform(0.0, 10.0))))
    
    def setJsonData(self):
        dummy_data = {
            "BT_TAG_DEVICE_NAME" : self.bt_tag_device_name,
            "BT_TAG_OWNER" : self.bt_tag_owner,
            "LOCATION" : self.location,
            "LATITUDE" : self.latitude,
            "LONGTITUDE" : self.longtitude,
            "FLOOR" : self.floor,
            "ROOM" : self.room,
            "X_COORD" : self.x_coord,
            "Y_COORD": self.y_coord,
        }

        json_data = json.dumps(dummy_data)
        # print(type(json_data))
        print("DATA : " , json_data)
        return json_data
    
    def sendDataToMQTT(self):
        mclient.publish("TOPIC/BT_TAG_1", self.setJsonData())
        # mclient.publish("TOPIC/BT_TAG_1", str("PAYLOAD--1"))
        print("---- SEND_DATA_TO_MQTT_LEAW ----")
    
    def sendDataToServer(self, API_ENDPOINT):
        self.API_ENDPOINT = API_ENDPOINT
        headers = {'Content-type': 'application/json'}
        r = requests.post(url=self.API_ENDPOINT, json=self.setJsonData(), headers=headers)
        print('STATUS_CODE : ' + str(r.status_code))

        # r.text is the content of the response in Unicode
        # pastebin_url = r.text
    
    def sendDataToWebSocket(self):
        s = socket.socket()
        print(type(self.setJsonData()))
        print("Socket sucessfully created")
        port = 15000
        # IP_ADDR = "192.168.4.19"
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', port))
        s.listen(5)
        print("socket is listening")

        while True:
            c, addr = s.accept()
            print ('Got connection from', addr )
            c.send(bytes(self.setJsonData(), encoding='utf8'))
            c.close()


if __name__== "__main__":

    while True :
        BT_1 = IPS_NODE(IP_address="192.168.4.150", device_name="BT_TAG_1", location="ABC Building", floor=7,room="ECC-804")
        # BT_1 = IPS_NODE(IP_address="127.0.0.1", device_name="BT_TAG_1", location="ABC Building", floor=7,room="ECC-804")
        
        random.seed()
        BT_1.setXcoord()
        BT_1.setYcoord()
        BT_1.setBtTagOwner("sarin_beam30")
        # BT_1.sendDataToMQTT()
        time.sleep(10)

        # BT_1.sendDataToWebSocket()
        # BT_1.sendDataToServer('https://protected-brook-89084.herokuapp.com/getLocation/')
        BT_1.sendDataToServer('http://127.0.0.1:5050/getLocation/')