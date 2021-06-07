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
import random

ID = sys.argv[0]+str(os.getpid())
mclient = client.Client(ID)
mclient.connect("localhost", port=1883, keepalive=60)

distance_mode = 0.0
node2distance = 0.0
node3distance = 0.0

tempdist2 = 0.0
tempdist3 = 0.0
scanner = Scanner()

random.seed()


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
        self.bt_tag_owner = '' #change to device_name so that it can be used e.g. ricky_1234
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
        self.longtitude = longtitude

    def setXcoord(self, x):
        # self.x_coord = 9.999
        self.x_coord = x

    def setYcoord(self, y):
        #self.y_coord = 10.000
        self.y_coord = y

    def setLocation(self, location):
        self.location = location
    
    def setFloor(self, floor):
        self.floor = floor
    
    def setRoom(self, room):
        self.room = room

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
        print("----------*** (RPi1) SEND DATA TO WEB SERVER LEAW ***----------")
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

        # while True:
        c, addr = s.accept()
        print ('Got connection from', addr )
        c.send(bytes(self.setJsonData(), encoding='utf8'))
        c.close()
        print("----------*** (BT_TAG_1) SEND DATA TO SCADA LEAW ***----------")

class SingleStateKalmanFilter(object):

    def __init__(self, A, B, C, x, P, Q, R):
        self.A = A  # Process dynamics
        self.B = B  # Control dynamics
        self.C = C  # Measurement dynamics
        self.current_state_estimate = x  # Current state estimate
        self.current_prob_estimate = P  # Current probability of state estimate
        self.Q = Q  # Process covariance
        self.R = R  # Measurement covariance

        self.initA = A  
        self.initB = B  
        self.initC = C  
        self.initcurrent_state_estimate = x  
        self.initcurrent_prob_estimate = P  
        self.initQ = Q 
        self.initR = R 

    def current_state(self):
        return self.current_state_estimate

    def step(self, control_input, measurement):
        # Prediction step
        predicted_state_estimate = self.A * self.current_state_estimate + self.B * control_input
        predicted_prob_estimate = (self.A * self.current_prob_estimate) * self.A + self.Q

        # Observation step
        innovation = measurement - self.C * predicted_state_estimate
        innovation_covariance = self.C * predicted_prob_estimate * self.C + self.R

        # Update step
        kalman_gain = predicted_prob_estimate * self.C * 1 / float(innovation_covariance)
        self.current_state_estimate = predicted_state_estimate + kalman_gain * innovation

        # eye(n) = nxn identity matrix.
        self.current_prob_estimate = (1 - kalman_gain * self.C) * predicted_prob_estimate

    def reset(self):
        self.A = self.initA
        self.B = self.initB
        self.C = self.initC
        self.current_state_estimate = self.initcurrent_state_estimate
        self.current_prob_estimate = self.initcurrent_prob_estimate
        self.Q = self.initQ
        self.R = self.initR

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
        
        self.BT_1 = IPS_NODE(IP_address="192.168.4.150", device_name="BT_TAG_1", location="ECC Building", floor=7,room="ECC-704")
        self.BT_2 = IPS_NODE(IP_address="192.168.4.150", device_name="BT_TAG_2", location="ECC Building", floor=7,room="ECC-704")
        self.BT_3 = IPS_NODE(IP_address="192.168.4.150", device_name="BT_TAG_3", location="ECC Building", floor=7,room="ECC-704")

        self.locationlist = [[13.729085,100.775741,"ECC Building",7,"ECC-704"],
                            [13.72794,100.74748,"Airport Rail Link Lat Krabang",2,"-"],
                            [13.7462,100.5347,"SIAM Paragon",2,"SP-321"]]


        self.node1x = 0.0
        self.node1y = 1.5
        self.node2x = 2.0
        self.node2y = 1.5
        self.node3x = 0.0
        self.node3y = 0.0

        self.locationdict = {}
        # Initialise the Kalman Filter

        A = 1  # No process innovation
        C = 1  # Measurement
        B = 0  # No control input
        Q = 1  # Process covariance
        R = 0.5  # Measurement covariance
        x = 65  # Initial estimate
        P = 1  # Initial covariance

        self.kalman_filter = SingleStateKalmanFilter(A, B, C, x, P, Q, R) 
        
    def setBTtags(self):
        self.BT_1.setBtTagOwner("sarin_beam30")
        # KMITL
        self.BT_1.setLatitude(13.729085)
        self.BT_1.setLongtitude(100.775741)

        self.BT_2.setBtTagOwner("window_1234")
        # KMITL
        self.BT_2.setLatitude(13.729085)
        self.BT_2.setLongtitude(100.775741)

        self.BT_3.setBtTagOwner("ricky_1234")
        # KMITL
        self.BT_3.setLatitude(13.729085)
        self.BT_3.setLongtitude(100.775741)

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

                rssifromkalman_estimates = []
                for i in rssidict[key]:
                    rssifromkalman = self.kalman_filter.step(0,i)
                    rssifromkalman_estimates.append(self.kalman_filter.current_state())
                print(rssifromkalman_estimates)
                rssifromkalman = self.kalman_filter.current_state()

                # ratio = (-71 - rssi)/(10.0 * 2.0)
                # ratio2 = (-71 - rssi2)/(10.0 * 2.0)
                # ratio3 = (-71 - rssi3)/(10.0 * 2.0)

                if key == "Mi Smart Band 4":
                    ratio = (-70 - rssifromkalman)/(10.0 * 2.0)
                    ratio2 = (-57 - rssi2)/(10.0 * 2.0)
                    ratio3 = (-57 - rssi3)/(10.0 * 2.0)

                elif key == "RMX50-5G":
                    ratio = (-82 - rssifromkalman)/(10.0 * 2.0)
                    ratio2 = (-67 - rssi2)/(10.0 * 2.0)
                    ratio3 = (-67 - rssi3)/(10.0 * 2.0)

                elif key == "3T":
                    ratio = (-72 - rssifromkalman)/(10.0 * 2.0)
                    ratio2 = (-60 - rssi2)/(10.0 * 2.0)
                    ratio3 = (-60 - rssi3)/(10.0 * 2.0)

                else:
                    ratio = (-72 - rssifromkalman)/(10.0 * 2.0)
                    ratio2 = (-72 - rssi2)/(10.0 * 2.0)
                    ratio3 = (-72 - rssi3)/(10.0 * 2.0)

                distance = 10**ratio
                distance = "{:.2f}".format(distance)

                distance2 = 10**ratio2
                distance2 = "{:.2f}".format(distance2)

                distance3 = 10**ratio3
                distance3 = "{:.2f}".format(distance3)

                print("%s's distance from kalman: %.2f" % (key, float(distance)))
                print("%s's distance from mean: %.2f" % (key, float(distance2)))
                print("%s's distance from min : %.2f" % (key, float(distance3)))

                ts = calendar.timegm(time.gmtime())
                readable = datetime.datetime.fromtimestamp(ts).isoformat()
                print(readable)
                print("")

                self.rssilistchecker(distance,key,self.getLocationdict())

            self.kalman_filter.reset()
            mclient.publish("Test/request", 1)
            print("Requesting node 2 data")
            # mclient.publish("Test/request", 2)
            print("Requesting node 3 data")
            time.sleep(10)

            locationdict = self.getLocationdict()
            print("PROCEED TO CALCULATION")
            for key in locationdict:
            #r1 = node1, r2 = node2, r3 = node3
                rssilist = locationdict[key]
                if len(rssilist) < 3:
                    print("not enough values for calculation")
                else:
                    print("CALCULATING ", locationdict[key])
                    print("For X coord:", float(rssilist[0]), float(rssilist[1]), float(rssilist[2]))
                    Xcoord = self.TrilaterationLocateX(float(rssilist[0]), float(rssilist[1]), float(rssilist[2]))
                    Xcoord = "{:.4f}".format(Xcoord)
                    Xcoord = float(Xcoord)
                    self.sender.setXcoord(Xcoord)
                    
                    print("For Y coord:", float(rssilist[0]), float(rssilist[1]), float(rssilist[2]))
                    Ycoord = self.TrilaterationLocateY(float(rssilist[0]), float(rssilist[1]), float(rssilist[2]))
                    Ycoord = "{:.4f}".format(Ycoord)
                    Ycoord = float(Ycoord)
                    self.sender.setYcoord(Ycoord)

                    print("X: %f, Y: %f of %s" % (Xcoord, Ycoord, str(key)))

                    # self.sender.setDevice_name(str(key))  
                    if str(key) == "Mi Smart Band 4":
                        choose = random.randrange(0,len(self.locationlist),1)
                        self.BT_1.setLatitude(self.locationlist[choose][0])
                        self.BT_1.setLongtitude(self.locationlist[choose][1])
                        print(self.locationlist[choose][1])
                        self.BT_1.setLocation(self.locationlist[choose][2])
                        self.BT_1.setFloor(self.locationlist[choose][3])
                        self.BT_1.setRoom(self.locationlist[choose][4])

                        self.BT_1.setXcoord(Xcoord)
                        self.BT_1.setYcoord(Ycoord)
                        self.BT_1.setDevice_name(str(key))
                        self.BT_1.sendDataToServer('https://protected-brook-89084.herokuapp.com/getLocation/')
                        # self.BT_1.sendDataToWebSocket()
                        time.sleep(10)

                    elif str(key) == "RMX50-5G":
                        choose = random.randrange(0,len(self.locationlist),1)
                        self.BT_2.setLatitude(self.locationlist[choose][0])
                        print(self.locationlist[choose][1])
                        self.BT_2.setLongtitude(self.locationlist[choose][1])
                        self.BT_2.setLocation(self.locationlist[choose][2])
                        self.BT_2.setFloor(self.locationlist[choose][3])
                        self.BT_2.setRoom(self.locationlist[choose][4])

                        self.BT_2.setXcoord(Xcoord)
                        self.BT_2.setYcoord(Ycoord)
                        self.BT_2.setDevice_name(str(key))
                        self.BT_2.sendDataToServer('https://protected-brook-89084.herokuapp.com/getLocation/')
                        # self.BT_2.sendDataToWebSocket()
                        time.sleep(10)
                    
                    elif str(key) == "3T":
                        choose = random.randrange(0,len(self.locationlist),1)
                        self.BT_3.setLatitude(self.locationlist[choose][0])
                        print(self.locationlist[choose][1])
                        self.BT_3.setLongtitude(self.locationlist[choose][1])
                        self.BT_3.setLocation(self.locationlist[choose][2])
                        self.BT_3.setFloor(self.locationlist[choose][3])
                        self.BT_3.setRoom(self.locationlist[choose][4])

                        self.BT_3.setXcoord(Xcoord)
                        self.BT_3.setYcoord(Ycoord)
                        self.BT_3.setDevice_name(str(key))
                        self.BT_3.sendDataToServer('https://protected-brook-89084.herokuapp.com/getLocation/')
                        # self.BT_3.sendDataToWebSocket()
                        time.sleep(10)

                    else:
                        print("other device")
                        # choose = random.randrange(0,len(self.locationlist),1)
                        # self.sender.setLatitude(self.locationlist[choose][0])
                        # self.sender.setLongtitude(self.locationlist[choose][1])
                        # self.sender.setLocation(self.locationlist[choose][2])
                        # self.sender.setFloor(self.locationlist[choose][3])
                        # self.sender.setRoom(self.locationlist[choose][4])
                        # self.sender.setDevice_name(str(key))  
                        # self.sender.sendDataToServer('https://protected-brook-89084.herokuapp.com/getLocation/')
                    
            self.resetLocationdict()
            print("\n")
            time.sleep(5)



if __name__ == '__main__':
    btscanner = BTScan()
    btscanner.setBTtags()
    print("BT tags set")
    mclient.subscribe("Test/+")
    # btscanner.setDevicename("RMX50-5G")

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
