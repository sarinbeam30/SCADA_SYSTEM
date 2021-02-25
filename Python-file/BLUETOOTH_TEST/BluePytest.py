from bluepy.btle import Scanner, DefaultDelegate
import time

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print("Discovered device", dev.addr)
        elif isNewData:
            print("Received new data from", dev.addr)

scanner = Scanner()
#devices = scanner.scan(3.0)

while(1):
    devices = scanner.scan(5.0)
    for dev  in devices:
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
                    print(" Distance = %f" % distance)
                    #else:
                        #pass
    time.sleep(2)
