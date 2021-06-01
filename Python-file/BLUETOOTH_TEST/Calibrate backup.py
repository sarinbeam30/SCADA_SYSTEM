from bluepy.btle import Scanner, DefaultDelegate, Peripheral
import bluepy.btle as btle
from collections import Counter
import sys, os, time, calendar, datetime, threading, json, socket, requests

results = []
class BTScan():
    def __init__(self):
        self.node1distance = 0.0
        self.scanner = Scanner()
        self.devicename = "" #default

    def setDevicename(self, name):
        self.devicename = name

    def getDevicename(self):
        return self.devicename
    
    def scanDevices(self):
        while(1):
            rssilist = []
            for i in range(100):
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

                                #connecting to the peripheral
                                # try:
                                #     print("[+] Connecting to device %s" % dev.addr)
                                #     device = Peripheral(dev.addr, addrType=btle.ADDR_TYPE_RANDOM)
                                #     print("[+] Device %s connected" % value)
                                # except btle.BTLEException as err:
                                #     print("[-] A connection error has occured: %s" % str(err))

                                print(" Device RSSI = %d" % (int(dev.rssi)))
                                # print(" Peripheral test = %d" % (int(device.rssi)))
                                rssilist.append(int(dev.rssi))
                                rssi = dev.rssi
                                ratio = (-73 - rssi)/(10.0 * 2.0)
                                distance = 10**ratio 
                                print(" Distance (m) = %.2f" % distance)
                                print("")
                            # else:
                            #     pass
                # time.sleep(1)
            # print(rssilist)
            if len(rssilist) == 0:
                self.node1distance = 0.0
            else:
                print("List size: %d" % len(rssilist))
                print("RSSI: ", rssilist)
                print("RSSI mode ", max(rssilist, key = rssilist.count)) 
                results.append(max(rssilist, key = rssilist.count))
                results.append(len(rssilist))
                time.sleep(3)
            
            rssilist.clear() 
            time.sleep(1)
            print(results)

if __name__ == "__main__":
    bts = BTScan()
    bts.setDevicename("RMX50-5G")
    # bts.setDevicename("Jirapat's Galaxy S10+")
    bts.scanDevices()