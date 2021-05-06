import requests, json, socket, random, time, sys, os, paho.mqtt.client as client
from datetime import datetime

# MQTT_INITIALIZE
hostname = "192.168.4.150"
port = 1883
ID = sys.argv[0]+str(os.getpid())
# mclient = client.Client(ID)
# mclient.connect(hostname, port=1883,keepalive=60)

class IPS_NODE ():
    def __init__(self, IP_address="192.168.4.171",device_name="BT_TAG_2",location="ABC Building", floor=7,room="ECC-804"):
        self.API_ENDPOINT = "http://192.168.4.150:5678/getDATA"
        self.IP_address = IP_address
        self.bt_tag_device_name = device_name
        self.bt_tag_owner = 'Admin_BT_TAG_2'
        self.location = location
        self.latitude = 45.000
        self.longtitude = 49.000
        self.floor = floor
        self.room = room
        self.x_coord = 2.222
        self.y_coord = 2.222
    
    def setBtTagOwner(self, name):
        self.bt_tag_owner = name
    
    def setLatitude(self, latitude):
        self.latitude = latitude
    
    def setLongtitude(self, longtitude):
        self.longtitude = longtitude
    
    def setXcoord(self):
        random.seed(datetime.now())
        self.x_coord = float("{:.3f}".format(random.uniform(0.0, 3.0)))
    
    def setYcoord(self):
        random.seed(datetime.now())
        self.y_coord = float("{:.3f}".format(random.uniform(0.0, 3.0)))

    def setLocation(self, location):
        self.location = location
    
    def setFloor(self, floor):
        self.floor = floor
    
    def setRoom(self, room):
        self.room =room

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
        # print("DATA : " , json_data)
        return json_data

    def sendDataToMQTT(self):
        # mclient.publish("TOPIC/BT_TAG_2", str("PAYLOAD--2"))
        # mclient.publish("TOPIC/BT_TAG_2", self.setJsonData())
        print("---- SEND_DATA_TO_MQTT_LEAW ----")
    
    def sendDataToServer(self, API_ENDPOINT):
        try:
            self.API_ENDPOINT = API_ENDPOINT
            headers = {'Content-type': 'application/json'}
            r = requests.post(url=self.API_ENDPOINT, json=self.setJsonData(), headers=headers)
            print("----------*** (BT_TAG_2) SEND DATA TO WEB SERVER LEAW ***----------")
            print('STATUS_CODE : ' + str(r.status_code))
        except ConnectionResetError:
            print("----------*** (BT_TAG_2) CONNECTION RESET BY PEER ***----------")

        # r.text is the content of the response in Unicode
        # pastebin_url = r.text
    
    def sendDataToWebSocket(self):
        s = socket.socket()
        print("Socket sucessfully created")
        port = 15000
        IP_ADDR = "192.168.4.19"
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', port))
        s.listen(5)
        print("socket is listening")

        # while True:
        c, addr = s.accept()
        print ('Got connection from', addr )
        c.send(bytes(self.setJsonData(), encoding='utf8'))
        c.close()
        print("----------*** (BT_TAG_2) SEND DATA TO SCADA LEAW ***----------")


if __name__== "__main__":

    while True:
        BT_2 = IPS_NODE(IP_address="192.168.4.171", device_name="BT_TAG_2", location="ECC Building", floor=8,room="ECC-804")
        # BT_2 = IPS_NODE(IP_address="127.0.0.1", device_name="BT_TAG_1", location="ABC Building", floor=7,room="ECC-804")
        
        random.seed()
        BT_2.setXcoord()
        BT_2.setYcoord()
        BT_2.setBtTagOwner("window_1234")

        # KMITL
        BT_2.setLatitude(13.7291)
        BT_2.setLongtitude(100.7756)
        BT_2.setLocation("ECC Building")
        BT_2.setFloor(7)
        BT_2.setRoom("ECC-704")
        
        print("[BT_2] LA : ", BT_2.latitude)
        print("[BT_2] LONG : ", BT_2.longtitude)
        # BT_2.sendDataToRabbitMQTT()
        # BT_2.sendDataToWebSocket()
        # BT_2.sendDataToServer('https://protected-brook-89084.herokuapp.com/getLocation/')
        BT_2.sendDataToServer('http://127.0.0.1:8080/getLocation/')
        time.sleep(30)