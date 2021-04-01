from bluepy.btle import Scanner, DefaultDelegate
import paho.mqtt.publish as publish
import paho.mqtt.client as client
import time, datetime, calendar, json, socket, sys, os, threading
#hostname = "192.168.1.101"
hostname = "192.168.4.150"
port = 1883

nodename = "Node 2"

ID = sys.argv[0]+str(os.getpid())
mclient = client.Client(ID)
mclient.connect(hostname, port=1883,keepalive=60)

scanner = Scanner()


class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)
    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print("Discovered device", dev.addr)
        elif isNewData:
            print("Received new data from", dev.addr)

def on_message(client,userdata,message):
    if(message.topic == "Test/request"):
        # print("Device request: %s" % str(message.payload.decode('utf-8') ))
        distancedict = btscanner.getrssidict()
        if(str(message.payload.decode('utf-8')) == "1"):
            for key in distancedict:
                print("Request: %s" % str(message.payload.decode('utf-8') ))
                devn = key
                node = nodename
                dist = distancedict[key]
                time = btscanner.getCurrentTime()
                btscanner.sendtoNode1(devn, node, dist, time)
                print("%s distance:%.2f sent to node1" % devn, dist)
                time.sleep(1)
        else:
            pass

class BTScanOther():
    def __init__(self):
        self.node2distance = 0.0
        self.devicename = ""
        self.scanner = Scanner()
        self.ts = ""
        self.rssidict = {}

    def getrssidict(self):
        return self.rssidict

    def getDevicename(self):
        return self.devicename

    def getDistance(self):
        return self.node2distance

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
        mclient.publish("Test/distancefromnode2",float(dist))
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
            for i in range(20):
                devices = self.scanner.scan(0.5)
                for dev in devices:
                    #print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
                    for (adtype, desc, value) in dev.getScanData():
                        if(desc == "Complete Local Name"):
                            print("")
                            print(" %s = %s" % (desc, value))
                            tempdict = self.rssilistchecker(dev.rssi, value, self.rssidict)
                            self.rssidict = tempdict
                            print(" Device addr = ", dev.addr)
                            print(" Device RSSI = %d" % (int(dev.rssi)))
                            rssi = dev.rssi
                            ratio = (-71 - rssi)/(10.0 * 2.0)
                            distance = 10**ratio 
                            print(" Distance (m) = %.2f" % distance)
                            print("")
                            # else:
                            #     pass
            for key in self.rssidict:
                print(key, ":", self.rssidict[key])
                rssi = max(self.rssidict[key], key = self.rssidict[key].count)
                ratio = (-71 - rssi)/(10.0 * 2.0)
                distance = 10**ratio 
                distance = "{:.2f}".format(distance)
                print("%s's distance: %.2f\n" % (key,float(distance)))
                self.rssidict[key] = float(distance)
                # self.sendtoNode1()
            time.sleep(1) 


if __name__ == "__main__":
    btscanner = BTScanOther()
    # btscanner.setDevicename("ห้องทำงาน")
    btscanner.setDevicename("RMX50-5G")

    mclient.subscribe("Test/request")
    mclient.on_message = on_message
    mclient.loop_start()
    print("Connected to Test/request")
    t1 = threading.Thread(btscanner.scanDevices())
    t1.start()