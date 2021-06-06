import serial, time, string, pynmea2, time, os, sys, json
import paho.mqtt.client as mqtt

#Define
ID = sys.argv[0]+str(os.getpid())
mclient = mqtt.Client(ID)
# broker = "192.168.4.38"

MQTT_BROKER_URL = "moose.rmq.cloudamqp.com"
MQTT_BROKER_PORT = 	1883 
MQTT_BROKER_USER = "dxjiwcxy:dxjiwcxy"
MQTT_BROKER_PASSWORD = "RGWpl3vFpw7_Y7Wlb_81VAxuHaaTI2Zk"


#define callback
def on_message(client, userdata, message):
    time.sleep(1)
    print("received message =",str(message.payload.decode("utf-8")))


def main():
    past_location = None
    location_array = [
        {"Latitude": 13.729498674330795, "Longitude": 100.77600523883594},
        {"Latitude": 13.729393542706305, "Longitude": 100.77600523883594},
        {"Latitude": 13.729180437917469, "Longitude": 100.77602278865373},
        {"Latitude": 13.728995746943834, "Longitude": 100.77603448853226},
        {"Latitude": 13.728828104241847, "Longitude": 100.77602278865373},
        {"Latitude": 13.72872865512472,  "Longitude": 100.77602571362337},
        {"Latitude": 13.728612157533872, "Longitude": 100.77601401374484},
        {"Latitude": 13.728606474723072, "Longitude": 100.77583851556695},
        {"Latitude": 13.728583743478541, "Longitude": 100.77549336915041},
        {"Latitude": 13.728589426289888, "Longitude": 100.77535882054737},
        {"Latitude": 13.728592267695511, "Longitude": 100.7751599226124},
        {"Latitude": 13.728578060667068, "Longitude": 100.77508094843236},
        {"Latitude": 13.728640571585755, "Longitude": 100.77504584879678},
        {"Latitude": 13.728748544951516, "Longitude": 100.77503707388789},
        {"Latitude": 13.728811055824774, "Longitude": 100.77503999885752},
        {"Latitude": 13.729044050750987, "Longitude": 100.77505754867532},
        {"Latitude": 13.729191803511094, "Longitude": 100.77503707388789},
        {"Latitude": 13.729308300813997, "Longitude": 100.77503414891825},
        {"Latitude": 13.729424798059041, "Longitude": 100.77505754867532},
        {"Latitude": 13.729376494330324, "Longitude": 100.77505754867532},
        {"Latitude": 13.729464577592882, "Longitude": 100.77505754867532},
        {"Latitude": 13.729583916153882, "Longitude": 100.77508094843236}
    ]

    i=0

    print(len(location_array))
    
    while True:
        port = '/dev/serial0'
        ser = serial.Serial(port,baudrate=9600,timeout=0.5)
        dataout = pynmea2.NMEAStreamReader()
        newdata=ser.readline().decode('UTF-8')
        #print("tetest",newdata.decode('UTF-8'))
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
            else:
                past_location = {"lat":lat,"lng":lng}
            

            # gps = {
            #     "Latitude" : lat,
            #     "Longitude" : lng
            # }
            
            gps = location_array[i]
            print("i : ", i)

            gps_json = json.dumps(gps)
            # gps='Latitude = ' +str(lat) + ' and Longitude = ' +str(lng)
            # print(gps)

            #mqtt
            global mclient
            mclient.username_pw_set(username=MQTT_BROKER_USER, password=MQTT_BROKER_PASSWORD)
            mclient.connect(host=MQTT_BROKER_URL, port=MQTT_BROKER_PORT, keepalive=120)
            # mclient.connect(broker, keepalive=60)
            print("connecting to broker : ",MQTT_BROKER_URL)

            mclient.publish("location", gps_json)#publish
            print("publishing : " + str(gps_json))
            
            mclient.on_message = on_message

            #SET I
            i+=1
            if(i == 21):
                i = 0

            time.sleep(2)

    mclient.loop_forever()

if __name__ == '__main__':
    main()
      # BT_1.setLatitude(13.729085)
      # BT_1.setLongtitude(100.775741)