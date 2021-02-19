import socket
import json

class IndoorPositioningSystem_SCADA():
    def __init__(self, IP_address="192.168.4.150", device_name="BT_TAG_1"):
        self.IP_address = IP_address
        self.device_name = device_name
    
    def getDataFromRASPI(self):
        s = socket.socket()
        port = 12300
        IP_ADDR = self.IP_address
        result = -1
        try:
            s.connect((IP_ADDR, port))
            bytes_text = s.recv(2048)
            string_text = bytes_text.decode("utf-8") 
            json_text = json.dumps(string_text)
            result = json_text
            s.close()
        except Exception as x:
            print(x)
            result = -1
            try: 
                s.close()
            except:
                print("faulty data")
        print("JSON_DATA : ", result)
        return result

if __name__ == "__main__":
    BT_1 = IndoorPositioningSystem_SCADA(IP_address="192.168.4.150", device_name="BT_TAG_1")
    # BT_1 = IndoorPositioningSystem_SCADA(IP_address="127.0.0.1", device_name="BT_TAG_1")
    BT_1.getDataFromRASPI()



