import serial, pynmea2

if __name__ == '__main__':
  past_location = None
  port = '/dev/serial0'
  ser = serial.Serial(port,baudrate=9600,timeout=0.5)
  dataout = pynmea2.NMEAStreamReader()
  newdata=ser.readline().decode('UTF-8')
  #print("tetest",newdata.decode('UTF-8'))
  print("Waiting for GPS")
  if newdata[0:6] == '$GPRMC':
      newmsg=pynmea2.parse(newdata)
      lat=newmsg.latitude
      lng=newmsg.longitude

      if lat == 0.0 and lng == 0.0:
          if past_location is None:
              lat = 13.729512166
              lng = 100.775583
          else:
              lat = past_location["lat"]
              lng = past_location["lng"]
              print("From sensor: ", lat, " ", lng)
      else:
          past_location = {"lat":lat,"lng":lng}
          print("From sensor: ", lat, " ", lng)
  print("error")


