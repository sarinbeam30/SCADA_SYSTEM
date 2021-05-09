from bluepy.btle import Scanner, DefaultDelegate
from collections import Counter
import paho.mqtt.client as client
import sys
import os
import time
import calendar
import datetime
import threading
import json
import socket
import requests
import statistics

ID = sys.argv[0]+str(os.getpid())
mclient = client.Client(ID)
mclient.connect("localhost", port=1883, keepalive=60)

distance_mode = 0.0
node2distance = 0.0
node3distance = 0.0

tempdist2 = 0.0
tempdist3 = 0.0
scanner = Scanner()


class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print("Discovered device", dev.addr)
        elif isNewData:
            print("Received new data from", dev.addr)


def on_message(client, userdata, message):
    global tempdevn
    if(message.topic == "Test/nodenumber"):
        print(" Node number: %s" % str(message.payload.decode('utf-8')))
        locationdict = btscanner.getLocationdict()

    if(message.topic == "Test/devicename"):
        print("Device name: %s" % str(message.payload.decode('utf-8')))
        tempdevn = str(message.payload.decode('utf-8'))

    elif(message.topic == "Test/distancefromnode2"):
        val = str(message.payload.decode('utf-8'))
        floatval = float(val)
        btscanner.setNode2dist(floatval)
        print(" Distance in meters (node2): %.2f" % floatval)
        tempdist2 = floatval
        btscanner.rssilistchecker(floatval, tempdevn, btscanner.getLocationdict())
        print(btscanner.getLocationdict())

    elif(message.topic == "Test/distancefromnode3"):
        val = str(message.payload.decode('utf-8'))
        floatval = float(val)
        btscanner.setNode3dist(floatval)
        print(" Distance in meters (node3): %.2f" % floatval)
        tempdist3 = floatval
        btscanner.rssilistchecker(floatval, tempdevn, btscanner.getLocationdict())
        print(btscanner.getLocationdict())

    elif(message.topic == "Test/timestamp"):
        print(" Timestamp: %s" % str(message.payload.decode('utf-8')))
        print("")


class IPS_NODE ():
    def __init__(self, IP_address="192.168.4.150", device_name="BT_TAG_1", location="ABC Building", floor=7, room="ECC-804"):
        self.API_ENDPOINT = "http://192.168.4.150:5678/getDATA"
        self.IP_address = IP_address
        self.bt_tag_device_name = device_name
        self.bt_tag_owner = 'Admin_BT_TAG_1'
        self.location = location
        self.latitude = 30.0000
        self.longtitude = 52.0000
        self.floor = floor
        self.room = room
        self.x_coord = 0
        self.y_coord = 0

    def setDevice_name(self, name):
        self.device_name = name

    def setBtTagOwner(self, name):
        self.bt_tag_owner = name
    
    def setLatitude(self, latitude):
        self.latitude = latitude
    
    def setLongtitude(self, longtitude):
        self.long = longtitude

    def setXcoord(self, x):
        # self.x_coord = 9.999
        self.x_coord = x

    def setYcoord(self, y):
        #self.y_coord = 10.000
        self.y_coord = y

    def setJsonData(self):
        dummy_data = {
            "BT_TAG_DEVICE_NAME": self.device_name,
            "BT_TAG_OWNER" : self.bt_tag_owner,
            "LOCATION": self.location,
            "LATITUDE": self.latitude,
            "LONGTITUDE": self.longtitude,
            "FLOOR": self.floor,
            "ROOM": self.room,
            "X_COORD": self.x_coord,
            "Y_COORD": self.y_coord,
        }

        json_data = json.dumps(dummy_data)
        print("DATA : ", json_data)
        return json_data

    def sendDataToServer(self, API_ENDPOINT):
        self.API_ENDPOINT = API_ENDPOINT
        headers = {'Content-type': 'application/json'}
        r = requests.post(url=self.API_ENDPOINT,
                          json=self.setJsonData(), headers=headers)
        print("----------*** (BT_TAG_1) SEND DATA TO WEB SERVER LEAW ***----------")
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
            print("----------*** (BT_TAG_1) SEND DATA TO SCADA LEAW ***----------")
            c.close()


class BTScan():
    def __init__(self):
        self.node1distance = 0.0
        self.node2distance = 0.0
        self.node3distance = 0.0
        # self.node2distance = {}
        # self.node3distance = {}
        self.scanner = Scanner()
        self.devicename = ""  # default
        self.sender = IPS_NODE(IP_address="192.168.4.150", device_name=str(self.devicename), location="ABC Building", floor=8, room="ECC-804")

        self.node1x = 0.0
        self.node1y = 0.0
        self.node2x = 2.0
        self.node2y = 0.0
        self.node3x = 2.0
        self.node3y = 2.0

        self.locationdict = {}

    def setNode2dist(self, dist):
        self.node2distance = dist

    def setNode3dist(self, dist):
        self.node3distance = dist

    def setDevicename(self, name):
        self.devicename = name

    def getDevicename(self):
        return self.devicename
    
    def getLocationdict(self):
        return self.locationdict
    
    def resetLocationdict(self):
        self.locationdict = {}
        return self.locationdict

    def TrilaterationLocateX(self, r1, r2, r3):
        A = 2*self.node2x - 2*self.node1x
        B = 2*self.node2y - 2*self.node1y
        C = r1**2 - r2**2 - self.node1x**2 + \
            self.node2x**2 - self.node1y**2 + self.node2y**2
        D = 2*self.node3x - 2*self.node2x
        E = 2*self.node3y - 2*self.node2y
        F = r2**2 - r3**2 - self.node2x**2 + \
            self.node3x**2 - self.node2y**2 + self.node3y**2
        x = (C*E - F*B) / (E*A - B*D)
        y = (C*D - A*F) / (B*D - A*E)
        return x

    def TrilaterationLocateY(self, r1, r2, r3):
        A = 2*self.node2x - 2*self.node1x
        B = 2*self.node2y - 2*self.node1y
        C = r1**2 - r2**2 - self.node1x**2 + \
            self.node2x**2 - self.node1y**2 + self.node2y**2
        D = 2*self.node3x - 2*self.node2x
        E = 2*self.node3y - 2*self.node2y
        F = r2**2 - r3**2 - self.node2x**2 + \
            self.node3x**2 - self.node2y**2 + self.node3y**2
        x = (C*E - F*B) / (E*A - B*D)
        y = (C*D - A*F) / (B*D - A*E)
        return y

    def rssilistchecker(self, rssi, devname, rssidict):
        if(devname in rssidict):
            keyval = rssidict.get(devname)
            if(isinstance(keyval, list)):
                keyval.append(rssi)
            else:
                rssidict[devname] = list((rssi))
        else:
            newlist = [rssi]
            rssidict[devname] = newlist
        return rssidict

    def scanDevices(self):
        while(1):
            rssidict = {}
            for i in range(20):
                devices = self.scanner.scan(0.5)
                for dev in devices:
                    #print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
                    for (adtype, desc, value) in dev.getScanData():
                        if(desc == "Complete Local Name"):
                            # scanner.connect("41:30:28:36:74:86")      
                            print("")
                            print(" %s = %s" % (desc, value))
                            self.devicename = str(value)
                            tempdict = self.rssilistchecker(
                                dev.rssi, value, rssidict)
                            rssidict = tempdict
                            print(" Device addr = ", dev.addr)
                            print(" Device RSSI = %d" % (int(dev.rssi)))

                            # rssilist.append(int(dev.rssi) )
                            rssi = dev.rssi
                            # ratio = (-71 - rssi)/(10.0 * 2.0)
                            # ratio = (-57 - rssi)/(10.0 * 2.0)
                            # distance = 10**ratio
                            # print(" Distance (m) = %.2f" % distance)
                            print("")
            # print(rssidict)
            # self.sender.setXcoord(1)
            # self.sender.setYcoord(2)
            for key in rssidict:
                print(key, ":", rssidict[key])

                dalist = rssidict[key]

                rssi = max(rssidict[key], key=rssidict[key].count)
                rssi2 = statistics.mean(rssidict[key])
                rssi3 = max(dalist)

                # ratio = (-71 - rssi)/(10.0 * 2.0)
                # ratio2 = (-71 - rssi2)/(10.0 * 2.0)
                # ratio3 = (-71 - rssi3)/(10.0 * 2.0)

                if key == "Mi Smart Band 4":
                    ratio = (-60 - rssi)/(10.0 * 2.0)
                    ratio2 = (-60 - rssi2)/(10.0 * 2.0)
                    ratio3 = (-60 - rssi3)/(10.0 * 2.0)

                elif key == "RMX50-5G":
                    ratio = (-78 - rssi)/(10.0 * 2.0)
                    ratio2 = (-78 - rssi2)/(10.0 * 2.0)
                    ratio3 = (-78 - rssi3)/(10.0 * 2.0)

                else:
                    ratio = (-72 - rssi)/(10.0 * 2.0)
                    ratio2 = (-72 - rssi2)/(10.0 * 2.0)
                    ratio3 = (-72 - rssi3)/(10.0 * 2.0)

                distance = 10**ratio
                distance = "{:.2f}".format(distance)

                distance2 = 10**ratio2
                distance2 = "{:.2f}".format(distance2)

                distance3 = 10**ratio3
                distance3 = "{:.2f}".format(distance3)

                print("%s's distance from mode: %.2f" % (key, float(distance)))
                print("%s's distance from mean: %.2f" % (key, float(distance2)))
                print("%s's distance from min : %.2f" % (key, float(distance3)))

                ts = calendar.timegm(time.gmtime())
                readable = datetime.datetime.fromtimestamp(ts).isoformat()
                print(readable)
                print("")

                self.rssilistchecker(distance,key,self.getLocationdict())


            mclient.publish("Test/request", 1)
            print("Requesting node 2 data")
            # mclient.publish("Test/request", 2)
            print("Requesting node 3 data")
            time.sleep(5)

            locationdict = self.getLocationdict()
            for key in locationdict:
            #r1 = node1, r2 = node2, r3 = node3
                rssilist = locationdict[key]
                if len(rssilist) < 3:
                    print("not enough values for calculation")
                else:
                    Xcoord = self.TrilaterationLocateX(float(rssilist[0]), float(rssilist[1]), float(rssilist[2]))
                    Xcoord = "{:.4f}".format(Xcoord)
                    Xcoord = float(Xcoord)
                    self.sender.setXcoord(Xcoord)

                    Ycoord = self.TrilaterationLocateY(float(distance), float(rssilist[1]), float(rssilist[2]))
                    Ycoord = "{:.4f}".format(Ycoord)
                    Ycoord = float(Ycoord)
                    self.sender.setYcoord(Ycoord)

                    print("X: %f, Y: %f of %s" % (Xcoord, Ycoord, str(key)))

                    self.sender.setDevice_name(str(key))  
                    self.sender.sendDataToServer('https://protected-brook-89084.herokuapp.com/getLocation/')
                    self.resetLocationdict()

                    # mclient.publish("Test/request", str("Requesting"))
                    # self.sender.sendDataToWebSocket('https://protected-brook-89084.herokuapp.com/getLocation/') 
                    # if(distance == 0.0):
                    #     print("Node1 distance can't be 0")
                    #     pass
                    # elif(self.node2distance == 0.0):
                    #     print("Node2 distance can't be 0")
                    #     pass
                    # elif(self.node3distance == 0.0):
                    #     print("Node3 distance can't be 0")
                    #     pass
                    # else:
                    #     print("X: %f, Y: %f of %s" % (Xcoord, Ycoord, str(key)))
                        # self.sender.sendDataToWebSocket('https://protected-brook-89084.herokuapp.com/getLocation/')
                        # self.sender.setDevice_name(str(key))
                        # self.sender.sendDataToWebSocket();
                        # pass
            print("\n")
            time.sleep(10)


if __name__ == '__main__':
    btscanner = BTScan()
    mclient.subscribe("Test/+")
    btscanner.setDevicename("RMX50-5G")
    # btscanner.setDevicename("ห้องทำงาน")
    mclient.on_message = on_message
    mclient.loop_start()
    print("Broker connected")
    t1 = threading.Thread(btscanner.scanDevices())
    t1.start()
    # t2 = threading.Thread(target=mclient.loop_forever())
    # time.sleep(1)
    # t2.start()

    # loop_start instead of loop_forever to not jeng
    # print("Broker connected")
