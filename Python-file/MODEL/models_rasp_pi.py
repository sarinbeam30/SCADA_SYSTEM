class Connection(object):
    def __init__(self, address, devices = [],redis_client=None):
        self.address = address
        self.client = None #Client(address)
        self.devices = devices
        self.run = True
        self.pub=redis_client
    def addDevice(self, d):
        self.devices.append(d)

    def stop(self):
        self.run = False

    def start(self, threadName = None):
        try:
            import asyncio
            print('connect')
            self.client = Client(address)
            self.client.connect()
            print('after connect')
            root = self.client.get_root_node()
            loop=asyncio.get_event_loop()
            redis_host='redis://redis'
            pub= loop.run_until_complete(aioredis.create_redis(redis_host))
            print('create redis client ok')
            while self.run:
                sleep(0.01)

                for device in self.devices:
                    #print("In device:", device.name)
                    for tag in device.tags:
                        l=["0:Objects", "2:"+device.address, "2:"+tag.address]
                        print(l)
                        obj = root.get_child(l)
                        value = obj.get_value()

                        res = loop.run_until_complete(pub.set('tag:'+str(tag.name), value))
                        tag.updateValue(value)                    
        finally:
            self.client.disconnect()
def create_testdevice(dev_id):
    tag_offset=(dev_id-1)*4
    device = Device("Meter_Plane_%d" %dev_id,"Meter%d" %dev_id,[])
    tag = Tag(tag_offset+1, "Meter_Plane_%d.Volt" %dev_id, "Volt")
    device.addTag(tag)
    tag = Tag(tag_offset+2, "Meter_Plane_%d.Current" %dev_id, "Current")
    device.addTag(tag)
    tag = Tag(tag_offset+3, "Meter_Plane_%d.kW" %dev_id, "kW")
    device.addTag(tag)
    tag = Tag(tag_offset+4, "Meter_Plane_%d.kWh" %dev_id, "kWh")
    device.addTag(tag)
    return device

import phue 
class Phillip_Hue_Connection(Connection):
    def __init__(self, address, port = None, devices = [], redis_client=None):
        Connection.__init__(self, address, devices, redis_client)
        self.port = port
        self.client = None #phue.Bridge() #socket.socket()
        self.write_dict = {}
        self.device_dict = {}
        self.mapping = False
        self.pub = None
        self.loop = None
        self.item = None
    
    def write_out(self):	
        if self.pub == None or self.loop == None:
            return		
        from tag.models import Tag
        # t=Tag.objects.get(full_name=tag)
        for tn in self.write_dict:
            if not self.write_dict[tn][0]:
                continue
            temp = self.write_dict[tn]
            t=Tag.objects.get(full_name=tn)
            print("get to set tag", t)
            print(tn)
            print(self.write_dict[tn])
            value = temp[1]
            result = False
            if t.address in ['on','brightness','color']:
                addr = t.device.address
                result = self.setBulb(addr,t.address,value)
            if result:
                res = self.loop.run_until_complete(self.pub.set('tag:'+str(t.full_name), value)) #await 
                print(t.name+" : "+str(value))
            self.write_dict[tn] = [False, 0]
            #sleep(0.1)

from drivers.extra_driver.SaijoLan import AirItemLan as SaijoAir
class Saijo_Air_Connection(Connection):
    def __init__(self, devices = [], redis_client=None):
        Connection.__init__(self, None, devices, redis_client)
        self.client = {}
        self.write_dict = {}
        self.device_dict = {}
        self.mapping = False
        self.pub = None
        self.loop = None
        self.item = None
		
    def write_out(self):	
        if self.pub == None or self.loop == None:
            return		
        from tag.models import Tag
        # t=Tag.objects.get(full_name=tag)
        for tn in self.write_dict:
            if not self.write_dict[tn][0]:
                continue
            temp = self.write_dict[tn]
            t=Tag.objects.get(full_name=tn)
            print("get to set tag", t)
            print(tn)
            print(self.write_dict[tn])
            value = temp[1]
            result = False
            if t.address == "powerStat":
                addr = t.device.address
                result = self.client[addr].setOnOff(int(value))
            elif t.address == "setTemp":
                addr = t.device.address
                result = self.client[addr].setTemp(float(value))
            elif t.address == "fan":
                addr = t.device.address
                result = self.client[addr].setFan(int(value))
            elif t.address == "setHum":
                addr = t.device.address
                result = self.client[addr].setRH(int(value))
            elif t.address == "mode":
                addr = t.device.address
                result = self.client[addr].setMode(int(value))
            elif t.address == "lp":
                addr = t.device.address
                result = self.client[addr].setLP(int(value))
            if result:
                res = self.loop.run_until_complete(self.pub.set('tag:'+str(t.full_name), value)) #await 
                print(t.name+" : "+str(value))
            self.write_dict[tn] = [False, 0]
            #sleep(0.1)

from drivers.extra_driver.SaijoLan import AirItemLan as SaijoAir
class Saijo_Air_Connection(Connection):
    def __init__(self, devices = [], redis_client=None):
        Connection.__init__(self, None, devices, redis_client)
        self.client = {}
        self.write_dict = {}
        self.device_dict = {}
        self.mapping = False
        self.pub = None
        self.loop = None
        self.item = None

import string
from drivers.extra_driver.IndoorPositioningSystem_device import IndoorPositioningSystem_SCADA
class IndoorPositioingSystemDevice_Connection(Connection):
    def __init__(self, IP_address, device_name, location, latitude, longtitude, \
        floor, room, x_coord, y_coord,  devices=[], redis_client=None):
        
        Connection.__init__(self, IP_address, devices, redis_client)
        self.device_name = device_name
        self.location = location
        self.latitude = latitude
        self.longtitude = longtitude
        self.floor = floor
        self.room = room
        self.x_coord = x_coord
        self.y_coord = y_coord

        self.client = {}
        self.write_dict = {}
        self.device_dict = {}
        self.mapping = False
        self.pub = None
        self.loop = None
        self.item = None
    
    def WriteTag(self,tag,value):
        if self.mapping:
            tag = self.mappingTag(tag)
        print(tag)
        print(value)
        if tag not in self.write_dict:
            return
        self.write_dict[tag] = [True, value]
        print("set write out to : ",tag," value ",value)

    # keep in case need to swap tag to webscoket
    def mappingTag(self, tag):
        my_map = {
                 }
        if tag in my_map:
            return my_map[tag]
        return 0

    def write_out(self):  
        import asyncio
        if self.pub == None or self.loop == None:
            return
        
        from tag.models import Tag
        for tn in self.write_dict:
            if not self.write_dict[tn][0]:
                continue

            temp = self.write_dict[tn]
            t=Tag.objects.get(full_name=tn)
            print("get to set tag", t)
            print(tn)
            print(self.write_dict[tn])
            value = temp[1]
            result = False

            if t.address == "device_name":
                addr = t.device.address
                self.client[addr].setDeviceName(string(value))
            
            if t.address == "location":
                addr = t.device.address
                self.client[addr].setLocation(string(value))
            
            if t.address == "latitude":
                addr = t.device.address
                self.client[addr].setLatitude(float(value))
            
            if t.address == "longtitude":
                addr = t.device.address
                self.client[addr].setLongtitude(float(value))
            
            if t.address == "floor":
                addr = t.device.address
                self.client[addr].setFloor(int(value))
            
            if t.address == "room":
                addr = t.device.address
                self.client[addr].setRoom(string(value))
            
            if t.address == "x_ccord":
                addr = t.device.address
                self.client[addr].setXCoord(float(value))

            if t.address == "y_ccord":
                addr = t.device.address
                self.client[addr].setYCoord(float(value))		
            self.write_dict[tn] = [False, 0]
    
    def start(self, threadName = None):
        try:
            import asyncio
            print('connect')
            redis_host='redis://redis'
            loop=asyncio.get_event_loop()
            pub= loop.run_until_complete(aioredis.create_redis(redis_host))
            res = loop.run_until_complete(pub.auth('ictadmin')) #await 
            print('create redis client ok')
            
            self.loop = loop
            self.pub = pub

            self.client = {} # IndoorPositioingDeviceSystem

            device_dict = {}
            for device in self.devices:
                d_id = device.address
                temp = {}
                for tag in device.tags:
                    addr = tag.address
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0]
                device_dict[d_id] = temp
                # ASK P'NAME
                self.client[d_id] = IndoorPositioningSystem_SCADA(IP_address="192.168.4.150", device_name="BT_TAG_1")
                self.client[d_id].on_connect()
            
            print("finish set device_dict")
            print(device_dict)
            print(self.write_dict)
            
            self.device_dict = device_dict

            #asyncio.ensure_future(self.client.loop_forever()) #self.client.loop_start()

            count = 0
            while self.run:
                loop.run_until_complete(asyncio.sleep(1))
                temp = self.write_out() # check anything to write first

                count += 1
                if count % 10 != 1:
                    continue

                oldData = {}

                for d in self.device_dict:
                    l = self.client[d]
                    data = l.readValue()
                    for t in self.device_dict[d]:
                        if t not in data:
                            continue
                        if t in oldData and oldData[t] == data[t]:
                            continue
                        oldData[t] = data[t]
                        tag = self.device_dict[d][t]
                        value = data[t]

                        if value != None:
                            if self.mapping:
                                name = self.mappingTag(tag.full_name)
                                res = loop.run_until_complete(pub.set('tag:'+str(name), value))
                            else:
                                res = loop.run_until_complete(pub.set('tag:'+str(tag.full_name), value)) #await 
                            print(tag.name+" : "+str(value))
                
        finally:
            pub.close()
            print("End")

@app.task
def IndoorPositioingSystemDevice_driver(port_id = 5):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop = asyncio.get_event_loop()

    # ASK P'NAME
    conn_1 = IndoorPositioingSystemDevice_Connection([])

    print("Start")

    for d in devices:
        device_1 = Device(d.name,d.address,[])

        for t in d.device_tag.all():
            #tag = Tag(t.id, t.full_name, t.address, scale = t.scale, tag_type = t.type)
            device_1.addTag(t)
            #print("Add tag", t, tag)

        conn_1.addDevice(device_1)

    pool=MP(tags=n,modbus=conn_1)
	
    asyncio.ensure_future(pool.connect())
    
    asyncio.ensure_future(conn_1.start())

    while True:
        #print('main loop')
        loop.run_until_complete(asyncio.sleep(1)) 
        #m.ReadAll()
    print("good bye naja.")