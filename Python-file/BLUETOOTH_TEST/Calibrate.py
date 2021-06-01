from bluepy.btle import Scanner, DefaultDelegate, Peripheral
import bluepy.btle as btle
from collections import Counter
import sys, os, time, calendar, datetime, threading, json, socket, requests

results = []
kalman_results = []

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
    def __init__(self, mp):
        self.node1distance = 0.0
        self.scanner = Scanner()
        self.measured_power = mp
        self.devicename = "" #default

        A = 1  # No process innovation
        C = 1  # Measurement
        B = 0  # No control input
        Q = 1  # Process covariance
        R = 1  # Measurement covariance
        x = 64  # Initial estimate
        P = 2  # Initial covariance

        self.kalman_filter = SingleStateKalmanFilter(A, B, C, x, P, Q, R) 

    def setDevicename(self, name):
        self.devicename = name

    def getDevicename(self):
        return self.devicename
    
    def scanDevices(self):
        while(1):
            rssilist = []
            for i in range(20):
                devices = self.scanner.scan(0.5)
                for dev in devices:
                    for (adtype, desc, value) in dev.getScanData():
                        if(desc == "Complete Local Name"):
                            if(value == self.devicename):
                                print("")
                                print(" %s = %s" % (desc, value))
                                self.devicename = str(value)
                                print(" Device addr = ", dev.addr)
                                print(" Device RSSI = %d" % (int(dev.rssi)))
                                rssilist.append(int(dev.rssi))
                                rssi = dev.rssi
                                ratio = (self.measured_power - rssi)/(10.0 * 2.0)
                                distance = 10**ratio 
                                print(" Distance (m) = %.2f" % distance)
                                print("")
            if len(rssilist) == 0:
                self.node1distance = 0.0
            else:
                print("List size: %d" % len(rssilist))
                print("RSSI: ", rssilist)
                print("RSSI mode ", max(rssilist, key = rssilist.count))
                results.append("from mode") 
                results.append(max(rssilist, key = rssilist.count))


                
                rssifromkalman_estimates = []
                for i in rssilist:
                    self.kalman_filter.step(0,i)
                    rssifromkalman_estimates.append(self.kalman_filter.current_state())
                print(rssifromkalman_estimates)

                results.append("from kalman") 
                results.append(rssifromkalman_estimates[-1])
                results.append("sample size") 
                results.append(len(rssilist))
                time.sleep(3)
            
            rssilist = []
            time.sleep(1)
            print(results)
            self.kalman_filter.reset()

if __name__ == "__main__":
    bts = BTScan(-64)
    bts.setDevicename("Mi Smart Band 4")
    bts.scanDevices()