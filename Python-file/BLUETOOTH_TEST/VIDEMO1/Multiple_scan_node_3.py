from bluepy.btle import Scanner, DefaultDelegate
import paho.mqtt.publish as publish
import paho.mqtt.client as client
import time
import datetime
import calendar
import json
import socket
import sys
import os
import threading
#hostname = "192.168.1.101"
#hostname = "192.168.4.150"
home = "192.168.1.38"
beam = "192.168.1.102"
beam2 = "192.168.1.107"
ecc704 = "192.168.4.150"
port = 1883

nodename = "Node 3"

ID = sys.argv[0]+str(os.getpid())
mclient = client.Client(ID)
mclient.connect(ecc704, port=1883, keepalive=60)

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
    if(message.topic == "Test/request"):
        # print("Device request: %s" % str(message.payload.decode('utf-8') ))
        if(str(message.payload.decode('utf-8')) == "1"):
            distancedict = btscanner.getdistancedict()
            time.sleep(1)
            for key in distancedict:
                print("Request: %s" % str(message.payload.decode('utf-8')))
                devn = key
                node = nodename
                dist = distancedict[key]
                print(devn, "'s distance: ", dist)
                currtime = btscanner.getCurrentTime()
                btscanner.sendtoNode1(devn, node, dist, currtime)
                print("%s distance:%.2f sent to node1" % (devn, dist))
                time.sleep(1)
        btscanner.cleardicts()

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

class BTScanOther():
    def __init__(self):
        self.node3distance = 0.0
        self.devicename = ""
        self.scanner = Scanner()
        self.ts = ""
        self.rssidict = {}
        self.distancedict = {}

        A = 1  # No process innovation
        C = 1  # Measurement
        B = 0  # No control input
        Q = 0.03  # Process covariance
        R = 0.2  # Measurement covariance
        x = 60  # Initial estimate
        P = 2  # Initial covariance

        self.kalman_filter = SingleStateKalmanFilter(A, B, C, x, P, Q, R) 

    def getrssidict(self):
        return self.rssidict

    def getdistancedict(self):
        return self.distancedict

    def cleardicts(self):
        self.rssidict = {}
        self.distancedict = {}

    def getDevicename(self):
        return self.devicename

    def getDistance(self):
        return self.node3distance

    def getCurrentTime(self):
        ts = calendar.timegm(time.gmtime())
        readable = datetime.datetime.fromtimestamp(ts).isoformat()
        print(readable)
        return str(readable)

    def setDevicename(self, name):
        self.devicename = name

    def sendtoNode1(self, devname, nodename, dist, time):
        mclient.publish("Test/devicename", str(devname))
        mclient.publish("Test/nodenumber", str(nodename))
        mclient.publish("Test/distancefromnode3", float(dist))
        mclient.publish("Test/timestamp", str(time))
        # mclient.publish("Test/devicename", str(self.devicename))
        # mclient.publish("Test/nodenumber", str(nodename))
        # mclient.publish("Test/distancefromnode2",float(self.node2distance))
        # mclient.publish("Test/timestamp", str(readable))

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
            self.rssidict = {}
            for i in range(30):
                devices = self.scanner.scan(0.5)
                for dev in devices:
                    #print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
                    for (adtype, desc, value) in dev.getScanData():
                        if(desc == "Complete Local Name"):
                            if(value == self.devicename): 
                                print("")
                                print(" %s = %s" % (desc, value))
                                tempdict = self.rssilistchecker(
                                    dev.rssi, value, self.rssidict)
                                self.rssidict = tempdict
                                print(" Device addr = ", dev.addr)
                                print(" Device RSSI = %d" % (int(dev.rssi)))
                                rssi = dev.rssi
                                # ratio = (-71 - rssi)/(10.0 * 2.0)
                                # ratio = (-52 - rssi)/(10.0 * 2.0)
                                # distance = 10**ratio
                                # print(" Distance (m) = %.2f" % distance)
                                print("")
                                # else:
                                #     pass
            for key in self.rssidict:
                # print(key, ":", self.rssidict[key])
                rssi = max(self.rssidict[key], key=self.rssidict[key].count)

                print(key, ":", self.rssidict[key])
                rssifromkalman_estimates = []
                for i in self.rssidict[key]:
                    rssifromkalman = self.kalman_filter.step(60,i)
                    rssifromkalman_estimates.append(self.kalman_filter.current_state())
                print("Kalman estimation: ", rssifromkalman_estimates)
                rssifromkalman = self.kalman_filter.current_state()
                # ratio = (-71 - rssi)/(10.0 * 2.0)
                if (key == "Mi Smart Band 4"):
                    ratio = (-69 - rssifromkalman)/(10.0 * 2.0)
                    distance = 10**ratio
                    distance = "{:.2f}".format(distance)
                    print("%s's distance: %.2f" % (key, float(distance)))
                    self.distancedict[key] = float(distance)
                    print()
                elif(key == "RMX50-5G"):
                    ratio = (-73 - rssifromkalman)/(10.0 * 2.0)
                    distance = 10**ratio
                    distance = "{:.2f}".format(distance)
                    print("%s's distance: %.2f" % (key, float(distance)))
                    self.distancedict[key] = float(distance)
                    print()
                elif(key == "3T"):
                    ratio = (-77 - rssifromkalman)/(10.0 * 2.0)
                    distance = 10**ratio
                    distance = "{:.2f}".format(distance)
                    print("%s's distance: %.2f" % (key, float(distance)))
                    self.distancedict[key] = float(distance)
                    print()
                else:
                    ratio = (-64 - rssifromkalman)/(10.0 * 2.0)
                    distance = 10**ratio
                    distance = "{:.2f}".format(distance)
                    print("%s's distance: %.2f" % (key, float(distance)))
                    self.distancedict[key] = float(distance)
                    print()
                self.kalman_filter.reset()
            time.sleep(1)


if __name__ == "__main__":
    btscanner = BTScanOther()
    # btscanner.setDevicename("ห้องทำงาน")
    btscanner.setDevicename("3T")

    mclient.subscribe("Test/request")
    mclient.on_message = on_message
    mclient.loop_start()
    print("Connected to Test/request")
    t1 = threading.Thread(btscanner.scanDevices())
    t1.start()
