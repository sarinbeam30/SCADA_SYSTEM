from bluepy.btle import Scanner, DefaultDelegate
from collections import Counter
import paho.mqtt.client as client
import sys, os, time, threading

ID = sys.argv[0]+str(os.getpid())
mclient = client.Client(ID)

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
    if(message.topic == "Test/devicename"):
        print("Device name: %s" % str(message.payload.decode('utf-8') ))
    elif(message.topic == "Test/nodenumber"):
        print(" Node number: %s" % str(message.payload.decode('utf-8') ))
    elif(message.topic == "Test/distance"):
        val = str( message.payload.decode('utf-8') )
        floatval = float(val)
        print(" Distance in meters: %.2f" % floatval)
        print("")

def TrilaterationLocate(x1,y1,r1,x2,y2,r2,x3,y3,r3):
    A = 2*x2 - 2*x1
    B = 2*y2 - 2*y1
    C = r1**2 - r2**2 - x1**2 + x2**2 - y1**2 + y2**2
    D = 2*x3 - 2*x2
    E = 2*y3 - 2*y2
    F = r2**2 - r3**2 - x2**2 + x3**2 - y2**2 + y3**2
    x = (C*E - F*B) / (E*A - B*D)
    y = (C*D - A*F) / (B*D - A*E)
    return x,y


def scanDevices1():
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
                    # for i in range(20):
                    #     print(" Device RSSI no.%d=%d" % (i,int(dev.rssi)))
                    #     time.sleep(0.1)
                    #     i = i + 1
                    #if(value == "Mi Smart Band 4"):
                    print(" Device RSSI=%d" % (int(dev.rssi)))
                    rssi = dev.rssi
                    ratio = (-49 - rssi)/(10.0 * 2.0)
                    distance = 10**ratio 
                    print(" Distance (m) = %.2f" % distance)
                    print("")
                    time.sleep(3)
                    #else:
                        #pass
    time.sleep(2)

def scanDevices2():
    rssilist = []
    for i in range(5):
        devices = scanner.scan(0.5)
        for dev in devices:
            #print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
            for (adtype, desc, value) in dev.getScanData():
                if(desc == "Complete Local Name"):
                    if(value == "ห้องทำงาน"):
                        #scanner.connect("41:30:28:36:74:86")
                        print("")
                        print(" %s = %s" % (desc, value))
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
                    else:
                        pass
        time.sleep(1)
    print(rssilist)
    print("Mode: ", max(rssilist, key = rssilist.count)) 
    rssilist.clear()



def main():   
    global mclient
    mclient.connect("localhost", port=1883,keepalive=60)
    mclient.subscribe("Test/+")
    print("Broker connected")
    x = threading.Thread(target=scanDevices2)
    x.start()
    mclient.on_message = on_message
    mclient.loop_forever()
    print("End of code")
    

if __name__ == '__main__':
    main()
