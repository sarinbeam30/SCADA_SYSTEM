from bluepy.btle import Scanner, DefaultDelegate
import paho.mqtt.publish as publish
import paho.mqtt.client as client
import time, datetime, calendar, json, socket, sys, os, threading
#hostname = "192.168.1.101"
hostname = "192.168.4.150"
port = 1883

nodename = "Node 3"

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
        print("Device request: %s" % str(message.payload.decode('utf-8') ))
        if(str(message.payload.decode('utf-8')) == "2"):
            print("Request: %s" % str(message.payload.decode('utf-8') ))
            devn = btscanner.getDevicename()
            node = nodename
            dist = btscanner.getDistance()
            time = btscanner.getCurrentTime()
            btscan = BTScanOther()
            btscan.sendtoNode1(devn, node, dist, time)
            print("Data sent to node1")
        else:
            pass

class BTScanOther():
    def __init__(self):
        # self.tokenname = "ห้องทำงาน"
        self.node3distance = 0.0
        self.devicename = "ห้องทำงาน"
        self.scanner = Scanner()
        self.ts = ""

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
        mclient.publish("Test/distancefromnode3",float(dist))
        mclient.publish("Test/timestamp", str(time))
        # mclient.publish("Test/devicename", str(self.devicename))
        # mclient.publish("Test/nodenumber", str(nodename))
        # mclient.publish("Test/distancefromnode2",float(self.node2distance))
        # mclient.publish("Test/timestamp", str(readable))

    
    def scanDevices(self):
        while(1):
            rssilist = []
            for i in range(2):
                devices = self.scanner.scan(0.5)
                for dev in devices:
                    #print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
                    for (adtype, desc, value) in dev.getScanData():
                        if(desc == "Complete Local Name"):
                            if(value == self.devicename):
                                #scanner.connect("41:30:28:36:74:86")
                                print("")
                                print(" %s = %s" % (desc, value))
                                self.devicename = str(value)
                                # for i in range(20):
                                #     print(" Device RSSI no.%d=%d" % (i,int(dev.rssi)))
                                #     time.sleep(0.1)
                                #     i = i + 1
                                #if(value == "Mi Smart Band 4"):
                                print(" Device addr = ", dev.addr)
                                print(" Device RSSI = %d" % (int(dev.rssi)))
                                rssilist.append(int(dev.rssi))
                                rssi = dev.rssi
                                ratio = (-49 - rssi)/(10.0 * 2.0)
                                distance = 10**ratio 
                                print(" Distance (m) = %.2f" % distance)
                                print("")
                                # else:
                                #     pass
                time.sleep(1)
            print(rssilist)
            if len(rssilist) == 0:
                pass
            else:
                rssi = max(rssilist, key = rssilist.count)
                ratio = (-49 - rssi)/(10.0 * 2.0)
                distance = 10**ratio 
                self.node3distance =  "{:.4f}".format(distance)
            print("Distance: ", self.node3distance) 

            # self.sendtoNode1(str(self.devicename), str(nodename), float(self.node2distance), str(readable))
            # print("Data sent to Node 1")

            rssilist.clear()
            time.sleep(1) 

def scanDevices():
    devices = scanner.scan(5.0)
    for dev in devices:
        #print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
        for (adtype, desc, value) in dev.getScanData():
            if(desc == "Complete Local Name"):
                if(value == ""):
                    pass
                else:
                    print("")
                    print(" %s = %s" % (desc, value))
                    print(" Device RSSI=%d" % int(dev.rssi))
                    #if(value == "Mi Smart Band 4"):
                    rssi = dev.rssi
                    ratio = (-49 - rssi)/(10.0 * 2.0)
                    distance = 10**ratio 
                    print(" Distance (m) = %.2f" % distance)
                    print("")
                    publish.single("Test/devicename", str(value), hostname=hostname, port=port)
                    publish.single("Test/nodenumber", str(nodename), hostname=hostname, port=port)
                    publish.single("Test/distancefromnode3",float(distance), hostname=hostname, port=port)
                    time.sleep(3)
                    #else:
                        #pass
    time.sleep(2)

if __name__ == "__main__":
    # btscanner.setDevicename("RMX50-5G")
    btscanner = BTScanOther()
    btscanner.setDevicename("ห้องทำงาน")

    mclient.subscribe("Test/request")
    mclient.on_message = on_message
    mclient.loop_start()
    print("Connected to Test/request")
    t1 = threading.Thread(btscanner.scanDevices())
    t1.start()