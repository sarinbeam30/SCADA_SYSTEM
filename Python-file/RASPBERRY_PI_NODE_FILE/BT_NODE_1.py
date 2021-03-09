import requests, json, socket

class IPS_NODE ():
    def __init__(self, IP_address="192.168.4.150",device_name="BT_TAG_1",location="ABC Building", floor=7,room="ECC-804"):
        self.API_ENDPOINT = "http://192.168.4.150:5678/getDATA"
        self.IP_address = IP_address
        self.device_name = device_name
        self.location = location
        self.latitude = 1.1111
        self.longtitude = 2.2222
        self.floor = floor
        self.room = room
        self.x_coord = 1.234
        self.y_coord = 5.678
    
    def setXcoord(self):
        self.x_coord = 9.999
    
    def setYcoord(self):
        self.y_coord = 10.000
    
    def setJsonData(self):
        dummy_data = {
            "DEVICE_NAME" : self.device_name,
            "LOCATION" : self.location,
            "LATITUDE" : self.latitude,
            "LONGTITUDE" : self.longtitude,
            "FLOOR" : self.floor,
            "ROOM" : self.room,
            "X_COORD" : self.x_coord,
            "Y_COORD": self.y_coord,
        }

        json_data = json.dumps(dummy_data)
        print("DATA : " , json_data)
        return json_data
    
    
    def sendDataToServer(self, API_ENDPOINT):
        self.API_ENDPOINT = API_ENDPOINT
        headers = {'Content-type': 'application/json'}
        r = requests.post(url=self.API_ENDPOINT, json=self.setJsonData(), headers=headers)
        print('STATUS_CODE : ' + str(r.status_code))

        # r.text is the content of the response in Unicode
        # pastebin_url = r.text
    
    def sendDataToWebSocket(self):
        s = socket.socket()
        print("Socket sucessfully created")
        port = 12300
        IP_ADDR = "192.168.4.209"
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', port))
        s.listen(5)
        print("socket is listening")

        while True:
            c, addr = s.accept()
            print ('Got connection from', addr )
            c.send(bytes(self.setJsonData(), encoding='utf8'))
            c.close()


if __name__== "__main__":
    BT_1 = IPS_NODE(IP_address="192.168.4.150", device_name="BT_TAG_1", location="ABC Building", floor=7,room="ECC-804")
    # BT_1 = IPS_NODE(IP_address="127.0.0.1", device_name="BT_TAG_1", location="ABC Building", floor=7,room="ECC-804")
    # BT_1.sendDataToWebSocket()
    BT_1.sendDataToServer('https://protected-brook-89084.herokuapp.com/getLocation/')
