from django.db import models
from scada.celeryconf import app
from time import sleep
from asgiref.sync import async_to_sync
import aioredis
from pprint import pprint
import json
import logging
import random
logging.getLogger().propagate=False
# Create your models here.
@app.task
def test(c):
    for x in range(c):
        print(x)
        sleep(1)
    return c
def test_select_queue():
    test.apply_async([5],queue='worker1')
    test.apply_async([5],queue='celery')

@app.task
def test_serial_port(text,port_name):
    import serial
    ser = serial.Serial(port_name)
    ser.write(text.encode())
    ser.close()

def test_serialport_worker():
    test_serial_port.apply_async(['1234567890123456','/dev/ttyUSB1'],queue='worker1')

@app.task
def simulator():
    from time import sleep
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    channel=get_channel_layer()
    count=0
    while True:
        print('test sim 1 sec count %d' %count)
        async_to_sync(channel.group_send)('chat_test',{'type':'chat_message','message':'count='+str(count)})
        count+=1
        sleep(1)



from opcua import Client
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
channel=get_channel_layer()
# basic class water down mimic objects that got from Django
class Tag(object):
    def __init__(self, set_id, name, address, value = 0, scale = 1, tag_type = None):
        self.id = set_id
        self.name = name
        self.address = address
        self.value = value
        self.scale = scale
        self.tag_type = tag_type

    def updateValue(self,value):
        # Update value to itself and print out value
        # represent sent data to websocket

        self.value = value

        #print("    TAG id: ", self.id, "name:", self.name, "new value:", self.value)
        import json 
        data={'type':'notify_tag','tag':str(self.name),
        'value':str(self.value)}
        async_to_sync(channel.group_send)('tag_'+str(self.name),{'type':'chat_message',
            'message':json.dumps(data)})

class Device(object):
    def __init__(self, name, address, tags = []):
        self.name = name
        self.address = address
        self.tags = tags

    def addTag(self, tag):
        self.tags.append(tag)

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


@app.task
def opcclient_driver():
    print('setting opc')
    
    # set up connections devices & tags 

    conn_1 = Connection("opc.tcp://opcserver:4840/testScada/server_1/",[])
    
    #device = Device("Meter_Plane_1","Meter1",[])
    #
    #tag = Tag(1, "Meter_Plane_1.Volt", "Volt")
    #device.addTag(tag)
    #tag = Tag(2, "Meter_Plane_1.Current", "Current")
    #device.addTag(tag)
    #tag = Tag(3, "Meter_Plane_1.kW", "kW")
    #device.addTag(tag)
    #tag = Tag(4, "Meter_Plane_1.kWh", "kWh")
    #device.addTag(tag)

    #conn_1.addDevice(device)

    #device_2 = Device("Meter_Plane_2","Meter2",[])
    #
    #tag = Tag(5, "Meter_Plane_2.Volt", "Volt")
    #device_2.addTag(tag)
    #tag = Tag(6, "Meter_Plane_2.Current", "Current")
    #device_2.addTag(tag)
    #tag = Tag(7, "Meter_Plane_2.kW", "kW")
    #device_2.addTag(tag)
    #tag = Tag(8, "Meter_Plane_2.kWh", "kWh")
    #device_2.addTag(tag)

    #conn_1.addDevice(device_2)
    for x in range(500):
        dev =create_testdevice(x+1)
        conn_1.addDevice(dev)
    conn_1.start()
    
def find_opc_path(node = None, name_list = [], path = [], dic = None):
    if dic == None:
        dic = {}
        for name in name_list:
            dic[name] = None
    if node == None:
        return {}

    for n in node.get_children():
        node_name = n.get_browse_name().to_string()
        newPath = path[:]+[node_name]
        if node_name in name_list:
            dic[node_name] = newPath[:]
        else:
            find_opc_path(n, name_list, newPath, dic)        

    return dic
    
def opc_child_of(node, parent = "None"):
    node_name = node.get_browse_name().to_string()
    print(node_name+" child of "+parent)

    for n in node.get_children():
        opc_child_of(n, node_name)
        
class OPC_UA_Connection(Connection):
    def __init__(self, address, devices = [], redis_client=None):
        Connection.__init__(self, address, devices, redis_client)
        self.write_dict = {}
        self.device_dict = {}
        self.mapping = False
		
    def WriteTag(self,tag,value):
        if self.mapping:
            tag = self.mappingTag(tag)
        if tag not in self.write_dict:
            return
        self.write_dict[tag] = [True, value]
        print("set write out to : ",tag," value ",value)

    # keep in case need to swap tag to webscoket
    def mappingTag(self, tag):
        my_map = {"plc_minipanel_1.Potentiometer_2":"Twido_LightControl.Switch_Array_2",
                  "plc_minipanel_1.Potentiometer_1":"Twido_LightControl.Switch_Array_1",
                    "plc_minipanel_1.LED1_write":"Switch_control.LightStatus1",
                    "plc_minipanel_1.LED2_write":"Switch_control.LightStatus2",
                    "plc_minipanel_1.Button1":"Switch_control.SwitchStatus1",
                    "plc_minipanel_1.Button2":"Switch_control.SwitchStatus2",
                    "Switch_control.LightStatus1":"plc_minipanel_1.LED1_write",
                    "Switch_control.LightStatus2":"plc_minipanel_1.LED2_write",
                 }
        if tag in my_map:
            return my_map[tag]
        return 0
		
    def write_out(self):			
        from tag.models import Tag
        
        root = self.client.get_root_node()
        
        for tn in self.write_dict:
            if not self.write_dict[tn][0]:
                continue
            temp = self.write_dict[tn]
            t=Tag.objects.get(full_name=tn)
            path = self.tag_path[t.address] + [self.tag_path[t.address][-1]]
            print("get to set tag", t)
            print(path)
            print(self.write_dict[tn])
            value = int(temp[1])
            try:
                obj = root.get_child(path)
                value = obj.set_data_value(value)
                self.write_dict[tn] = [False, 0]
                sleep(0.1)
            except:
                print("Not working on "+tn)

    def start(self, threadName = None):
        try:
            import asyncio
            print('connect')
            self.client.connect()
            print('after connect')
            root = self.client.get_root_node()
            loop=asyncio.get_event_loop()
            redis_host='redis://redis'
            loop=asyncio.get_event_loop()
            pub= loop.run_until_complete(aioredis.create_redis(redis_host))
            res = loop.run_until_complete(pub.auth('ictadmin')) #await 
            print('create redis client ok')
            
            tag_list = []
            tag_dict = {}
            for device in self.devices:
                for tag in device.tags:
                    addr = tag.address
                    tag_dict[addr] = tag 
                    tag_list.append(addr)
                    self.write_dict[tag.full_name] = [False, 0]
            
            self.tag_path = find_opc_path(node = root.get_child(["0:Objects"]), name_list = tag_list, path = ["0:Objects"], dic = None)
            print("got path")
            print(self.tag_path)
                
            while self.run:
                loop.run_until_complete(asyncio.sleep(1))
                self.write_out()

                for addr in self.tag_path:
                    path = self.tag_path[addr] + [self.tag_path[addr][-1]]
                    tag = tag_dict[addr]
                    print(addr)
                    obj = root.get_child(path)
                    value = obj.get_value()

                    res = loop.run_until_complete(pub.set('tag:'+str(tag.full_name), value))
                    #tag.updateValue(value)  
                    print(tag.name+" : "+str(value))
        finally:
            self.client.disconnect()

from drivers.datapool import GenericPool
class ReplayWorker():
    def __init__(self,replayer):
        import asyncio
        self.replayer=replayer
        self.pool = GenericPool(self.replay_callback)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.pool.connect())
        #from tag.models import Tag
        #for tag in Tag.objects.filter(device__port__id=self.port.id):
        #loop.run_until_complete(self.pool.sub_key('PSUBSCRIBE simcommand:*',self.replay_callback))
        #self.pool.psubscribe('simcommand:*')
        asyncio.ensure_future(self.redis_receive_loop()) # res = loop.run_until_complete(self.redis_receive_loop())
        print('finish')

    async def replay_callback(self,channel):
        while await channel.wait_message():
            print('get something')
            msg = await channel.get(encoding='utf-8')
         
            import json 
            tag=channel.name.decode()
            key=tag[7:]
            print('key',key)
            name=tag[7:]
            print('name',name)
            value=msg
            print('value',value)
            #if type(value)==type(bytes()):
            #    value=value.decode()
            #await self.pool.pub.set('tag:'+name,value)

    async def redis_receive_loop(self):
        self.sub = await aioredis.create_redis(
            'redis://redis')
        self.pub = await aioredis.create_redis(
            'redis://redis')
        await self.pub.auth('ictadmin')
        await self.sub.auth('ictadmin')
        #send to channel group
        print('redis_receive_loop start')
        res = await self.sub.psubscribe('simcommand:*')
        ch = res[0]
        while (await ch.wait_message()):
            msg = await ch.get()
            print(msg)
            s=msg[0][4:]
            value=msg[1]
            print('get data')
            print('ch.name',ch.name)
            print("Got Message:", msg)
            nel = msg[0].decode()
            u_id = nel.split(":")[1]
            data = msg[1].decode()
            data = json.loads(data)
            print(u_id, data)
            self.replayer.command(data, u_id)
            #TODO: send to channel group
            #json.loads()
            #tag=s.decode()
            #value=value.decode()
            #await self.pub.set('tag:'+tag,value) 

class Data_Replay_Connection(object):
    def __init__(self, redis_client=None):
        #self.logTemplate = logTemplate
        #self.client = Client(address)
        self.Rchannel = {}
        self.devices = [] #devices
        self.run = True
        self.pub=redis_client
        self.target = "start"

        # self.Rchannel = {u_id_1 : { log_id_1 : {st:time, et:time, nt:time, status:status }, log_id_2 : {st:time, et:time, nt:time, status:status } }, 
        #                  u_id_2 : { log_id_2 : {st:time, et:time, nt:time, status:status } } }
    def addDevice(self, d):
        self.devices.append(d)

    def stop(self):
        self.run = False

    def command(self, data, u_id = '1'):
        from datetime import datetime, timedelta
        print("got data", data)
        print("from", u_id)

        # {"type":"command","command":"start","template_id":"1","st":"","et":""}
        if "type" not in data or data["type"] != "command" or "command" not in data or "template_id" not in data:
            return
        
        if u_id not in self.Rchannel:
            self.Rchannel[u_id] = {}

        t_id = int(data["template_id"])

        def checkInChannel(ch = {}, u_id = None, log_id = None):
            if u_id not in ch:
                return False
            if log_id not in ch[u_id]:
                return False
            return True

        if data["command"] == "start":
            self.target = "play"
            et = None
            st = None
            if "et" not in data or data["et"] in ["", None]:
                et = datetime.now()
            else:
                et = datetime.strptime(data["et"], '%Y-%m-%d %H:%M:%S')

            if "st" not in data or data["st"] in ["", None]:
                st = et - timedelta(hours = 1)
            else:
                st = datetime.strptime(data["st"], '%Y-%m-%d %H:%M:%S')
                self.timerun = st

            #from tag.models import  LogData, LogDataChar, LogDataInt, LogDataFloat, LogDataBoolean, LogDataPoint
            #from tag.models import  Tag as DB_Tag

            # self.Rchannel = {u_id_1 : { log_id_1 : {st:time, et:time, nt:time, status:status }, log_id_2 : {st:time, et:time, nt:time, status:status } }, 
            #                  u_id_2 : { log_id_2 : {st:time, et:time, nt:time, status:status } } }

            print("command start from : ", u_id, " template id : ", t_id)
            print("time start-end")
            print(st,et)

        elif data["command"] == "resume":
            self.target = "play"
            if not checkInChannel(self.Rchannel, u_id, t_id):
                return
            target = self.Rchannel[u_id][t_id]
            if target["status"] == "pause":
                target["status"] == "play"
        elif data["command"] == "pause":
            self.target = "pause"
            if not checkInChannel(self.Rchannel, u_id, t_id):
                return
            if target["status"] == "play":
                target["status"] == "pause"
        elif data["command"] == "stop":
            self.target = "stop"
            if not checkInChannel(self.Rchannel, u_id, t_id):
                return
            target["status"] == "stop"

    def start(self, threadName = None):
        try:
            import asyncio
            from datetime import datetime, timedelta
            print('connect')
            #self.client.connect()
            print('after connect')
            redis_host='redis://redis'
            loop=asyncio.get_event_loop()
            pub= loop.run_until_complete(aioredis.create_redis(redis_host))
            res = loop.run_until_complete(pub.auth('ictadmin')) #await 
            print('create redis client ok')

            self.timerun = datetime.now() 
            t = datetime.now()
            c  = 0
            while self.run:
                loop.run_until_complete(asyncio.sleep(3))
                #self.timerun = datetime.now() - timedelta(days = 1)
                tn = datetime.now()
                if self.target == "play":
                    self.timerun += tn - t
                    res = loop.run_until_complete(pub.set('simtag:1:Test_Robot.Work_Count', c))
                    x = random.randint(2700,2800)
                    res = loop.run_until_complete(pub.set('simtag:1:Test_Robot.Temperature', x/100))
                    TRstr = str(self.timerun)
                    res = loop.run_until_complete(pub.set('simtag:1:Htime', TRstr.split(".")[0]))
                    c += 1
                    x = """for device in self.devices:
                    if 1 == 2:
                        res = loop.run_until_complete(pub.set('simtag:'+str(tag.name), value))
                        tag.updateValue(value)     """   
                t = tn


        finally:
            pass
            #self.client.disconnect()

@app.task
def replay_driver(port_id = 8):
    print('setting mqtt')
    import asyncio
    loop=asyncio.get_event_loop()

    conn_1 = Data_Replay_Connection() #(port.detail["address"],port.detail["port"],[],login,pw)
		
    pool=ReplayWorker(conn_1)
	
    #asyncio.ensure_future(pool.redis_receive_loop())
    print("start listener")
    asyncio.ensure_future(conn_1.start())
    print("start streamer")

    while True:
        #print('main loop')
        loop.run_until_complete(asyncio.sleep(1)) 
        #m.ReadAll()
    print("good bye naja.")

class Excel_Replay_Connection(object):
    def __init__(self, redis_client=None):
        #self.logTemplate = logTemplate
        #self.client = Client(address)
        self.Rchannel = {}
        self.devices = [] #devices
        self.run = True
        self.pub=redis_client
        self.target = "start"

        # self.Rchannel = {u_id_1 : { log_id_1 : {st:time, et:time, nt:time, status:status }, log_id_2 : {st:time, et:time, nt:time, status:status } }, 
        #                  u_id_2 : { log_id_2 : {st:time, et:time, nt:time, status:status } } }
    def addDevice(self, d):
        self.devices.append(d)

    def stop(self):
        self.run = False

    def command(self, data, u_id = '1'):
        from datetime import datetime, timedelta
        print("got data", data)
        print("from", u_id)

        # {"type":"command","command":"start","template_id":"1","st":"","et":""}
        if "type" not in data or data["type"] != "command" or "command" not in data or "template_id" not in data:
            return
        
        if u_id not in self.Rchannel:
            self.Rchannel[u_id] = {}

        t_id = int(data["template_id"])

        def checkInChannel(ch = {}, u_id = None, log_id = None):
            if u_id not in ch:
                return False
            if log_id not in ch[u_id]:
                return False
            return True

        if data["command"] == "start":
            self.target = "play"
            et = None
            st = None
            if "et" not in data or data["et"] in ["", None]:
                et = datetime.now()
            else:
                et = datetime.strptime(data["et"], '%Y-%m-%d %H:%M:%S')

            if "st" not in data or data["st"] in ["", None]:
                st = et - timedelta(hours = 1)
            else:
                st = datetime.strptime(data["st"], '%Y-%m-%d %H:%M:%S')
                self.timerun = st

            #from tag.models import  LogData, LogDataChar, LogDataInt, LogDataFloat, LogDataBoolean, LogDataPoint
            #from tag.models import  Tag as DB_Tag

            # self.Rchannel = {u_id_1 : { log_id_1 : {st:time, et:time, nt:time, status:status }, log_id_2 : {st:time, et:time, nt:time, status:status } }, 
            #                  u_id_2 : { log_id_2 : {st:time, et:time, nt:time, status:status } } }

            print("command start from : ", u_id, " template id : ", t_id)
            print("time start-end")
            print(st,et)

        elif data["command"] == "resume":
            self.target = "play"
            if not checkInChannel(self.Rchannel, u_id, t_id):
                return
            target = self.Rchannel[u_id][t_id]
            if target["status"] == "pause":
                target["status"] == "play"
        elif data["command"] == "pause":
            self.target = "pause"
            if not checkInChannel(self.Rchannel, u_id, t_id):
                return
            if target["status"] == "play":
                target["status"] == "pause"
        elif data["command"] == "stop":
            self.target = "stop"
            if not checkInChannel(self.Rchannel, u_id, t_id):
                return
            target["status"] == "stop"

    def start(self, threadName = None):
        try:
            import asyncio
            from datetime import datetime, timedelta
            import dateutil.parser
            from time import sleep
            import xlrd
            from os.path import join, dirname, abspath, isfile
            print('connect')
            #self.client.connect()
            print('after connect')
            redis_host='redis://redis'
            loop=asyncio.get_event_loop()
            pub= loop.run_until_complete(aioredis.create_redis(redis_host))
            res = loop.run_until_complete(pub.auth('ictadmin')) #await 
            print('create redis client ok')


            def get_excel_sheet_object(fname, idx=0):
                if not isfile(fname):
                    print ('File doesn\'t exist: ', fname)

                # Open the workbook and 1st sheet
                xl_workbook = xlrd.open_workbook(fname)
                xl_sheet = xl_workbook.sheet_by_index(0)
                print (40 * '-' + 'nRetrieved worksheet: %s' % xl_sheet.name)

                return xl_sheet

            x = get_excel_sheet_object("./drivers/extra_driver/report_example.xlsx")

            tagList = ["Htime"]

            pos = 1
            while True:
                try:
                    Ntag = x.cell_value(5, pos)
                except:
                    Ntag = ''
                #print(pos)
                #print(Ntag)
                if Ntag == '':
                    break
                tagList.append(Ntag)
                pos += 1

            print(tagList)
            colMax = pos - 1

            pos = 5
            Otime = datetime.now()
            Htime = None

            while self.run:
                loop.run_until_complete(asyncio.sleep(0.1))
                
                pos += 1
                try:
                    tempData = x.cell_value(pos, 0)
                except:
                    tempData = ''
                if tempData == '':
                    pos = 5
                    Otime = datetime.now()
                    Htime = None
                    continue

                Htime = dateutil.parser.parse(tempData, yearfirst = True)

                if pos == 6: # first row
                    Ntime = datetime.now()
                    diff = Ntime - Otime
                    Otime = Ntime
                    Rtime = Htime + diff

                while Rtime < Htime:
                    Ntime = datetime.now()
                    diff = Ntime - Otime
                    Rtime += diff
                    Otime = Ntime 

                print("time: "+tempData)
                res = loop.run_until_complete(pub.set('tag:Htime', tempData))


                col = 1
                while col <= colMax:
                    value = x.cell_value(pos, col)
                    res = loop.run_until_complete(pub.set('tag:'+tagList[col], value))
                    print("\t"+tagList[col]+" : "+str(value))
                    col += 1
                


        finally:
            pass
            #self.client.disconnect()

@app.task
def excel_replay_driver(port_id = 8):
    print('setting mqtt')
    import asyncio
    loop=asyncio.get_event_loop()

    conn_1 = Excel_Replay_Connection() #(port.detail["address"],port.detail["port"],[],login,pw)
		
    #pool=ReplayWorker(conn_1)
	
    #asyncio.ensure_future(pool.redis_receive_loop())
    print("start listener")
    asyncio.ensure_future(conn_1.start())
    print("start streamer")

    while True:
        #print('main loop')
        loop.run_until_complete(asyncio.sleep(1)) 
        #m.ReadAll()
    print("good bye naja.")

from drivers.modbus_rtu.modbus_umodbus import device_tcp

class ModBusTCP_Connection(Connection):
    def __init__(self, address, port = "0", devices = [],redis_client=None):
        Connection.__init__(self, address, devices, redis_client)
        self.port = port
        self.client = device_tcp()

    def start(self, threadName = None):
        try:
            import asyncio
            print('connect')
            #root = self.client.get_root_node()
            self.client.config(device_id=1, socket_ip=self.address, 
                               socket_port=self.port, signed_type=True)
            self.client.connect()
            print('after connect')
            redis_host='redis://redis'
            loop=asyncio.get_event_loop()
            pub= loop.run_until_complete(aioredis.create_redis(redis_host))
            print('create redis client ok')
            while self.run:
                sleep(0.01)

                for device in self.devices:
                    #print("In device:", device.name)
                    d_id = int(device.address)
                    self.client.device_id = d_id
                    for tag in device.tags:
                        value = self.client.read_input_registers(start_register_address=int(tag.address), number_of_registers=1)                   
                        #print(value)
                        #obj = root.get_child(l)
                        #value = obj.get_value()
                        if value != None:
                            value = value[0]*tag.scale
                            res = loop.run_until_complete(pub.set('tag:'+str(tag.name), value))
                            tag.updateValue(value) 
                            print(tag.name+" : "+str(value)) 
                        sleep(0.5)                  
        
        finally:
            print("End")
            #self.client.disconnect()

def check_type(name):
    note = { "Discrete Output Coils": "OC",
             "Discrete Input Contacts": "IC",
             "Analog Input Registers": "IR",
             "Analog Output Holding Registers": "OHR",
           }
    if name in note:
        return note[name]
    return ""

def _cal_block(temp):
    s, e = None, 0
    for i in temp:
        if s == None or s > i:
            s = i
        if e < i:
            e = i
    return s, e - s + 1
    
def cal_block(temp):
    result = []
    data = []
    #s, e = None, 0
    for i in temp:
        i = int(i)
        if data == []:
            data.append(i)
        else:
            ins = False
            for d in range(len(data)):
                if data[d] > i:
                    data.insert(d, i)
                    ins = True
                    break
            if not ins:
                data.append(i)
    block = []
    for d in data:
        if d < 0:
            continue
        if block == []:
            block.append(d)
        else:
            if block[-1] - block[0] >= 50 or d - block[-1] > 10:
                result.append(_cal_block(block))
                block = [d]
            else:
                block.append(d)
    result.append(_cal_block(block))
    return result #s, e - s + 1
            
class ModBusTCP_DB_Connection(Connection):
    def __init__(self, address, port = "0", devices = [],redis_client=None):
        Connection.__init__(self, address, devices, redis_client)
        self.port = int(port)
        self.client = device_tcp()
        self.write_dict = {}
        self.mapping = False
		
    def WriteTag(self,tag,value):
        if self.mapping:
            tag = self.mappingTag(tag)
        if tag not in self.write_dict:
            return
        self.write_dict[tag] = [True, value]
        print("set write out to : ",tag," value ",value)

    # keep in case need to swap tag to webscoket
    def mappingTag(self, tag):
        my_map = {"plc_minipanel_1.Potentiometer_2":"Twido_LightControl.Switch_Array_2",
                  "plc_minipanel_1.Potentiometer_1":"Twido_LightControl.Switch_Array_1",
                  "plc_minipanel_1.LED1_write":"Switch_control.LightStatus1",
                  "plc_minipanel_1.LED2_write":"Switch_control.LightStatus2",
                  "plc_minipanel_1.Button1":"Switch_control.SwitchStatus1",
                  "plc_minipanel_1.Button2":"Switch_control.SwitchStatus2",
                  "Switch_control.LightStatus1":"plc_minipanel_1.LED1_write",
                  "Switch_control.LightStatus2":"plc_minipanel_1.LED2_write",
                 }
        if tag in my_map:
            return my_map[tag]
        return 0
		
    def write_out(self):			
        from tag.models import Tag
        # t=Tag.objects.get(full_name=tag)
    		
        # do write back here
        ##rr = self.modbus.write_coil(int(t.address), int(value), unit=int(t.device.address))
        for tn in self.write_dict:
            if not self.write_dict[tn][0]:
                continue
            temp = self.write_dict[tn]
            t=Tag.objects.get(full_name=tn)
            print("get to set tag", t)
            print(tn)
            print(self.write_dict[tn])
            value = int(float(temp[1])/t.scale)
            self.client.connect()
            if t.type in ["Discrete Input Contacts","Discrete Output Coils"]: # still only work for this 2
                self.client.device_id = int(t.device.address) # this line may nee to move outside
                x = self.client.write_coil(int(t.address), value)
                self.write_dict[tn] = [False, 0]
            elif t.type in ["Analog Output Holding Registers"]: 
                self.client.device_id = int(t.device.address) # this line may nee to move outside
                x = self.client.write_register(int(t.address), value)
                self.write_dict[tn] = [False, 0]
            self.client.disconnect()

    def start(self, threadName = None):
        try:
            import asyncio
            print('connect')
            #root = self.client.get_root_node()
            self.client.config(device_id=1, socket_ip=self.address, 
                               socket_port=self.port, signed_type=True)
            self.client.connect()
            print('after connect')
            redis_host='redis://redis'
            loop=asyncio.get_event_loop()
            pub= loop.run_until_complete(aioredis.create_redis(redis_host))
            res = loop.run_until_complete(pub.auth('ictadmin')) #await 
            print('create redis client ok')
            
            device_dict = {}
            #print(self.devices)
            for device in self.devices:
                d_id = int(device.address)
                #print(device.tags)
                temp = {"OC":{}, "IC":{}, "IR":{}, "OHR":{}}
                for tag in device.tags:
                    #print(tag.name)
                    #print(tag.tag_type)
                    ct = check_type(tag.type)
                    #print(ct)
                    if ct in temp:
                        addr = int(tag.address)
                        temp[ct][addr] = tag 
                        self.write_dict[tag.full_name] = [False, 0]
                device_dict[d_id] = temp
                
            #temp = device["OHR"]
            #dataBlockOHR = cal_block(temp)

            print("finish set device_dict")
            print(device_dict)
            print(self.write_dict)
                
            while self.run:
                sleep(0.1)

                for d_id in device_dict:
                    temp = self.write_out() # clear write out first
                    #print("check write out")
                    #print("In device:", d_id)
                    self.client.device_id = d_id
                    device = device_dict[d_id]
                    if len(device["IC"]) > 0:
                        temp = device["IC"]
                        for i in temp:
                            tag = temp[i]
                            self.client.connect()
                            value = self.client.read_coils(start_coil_address=int(tag.address), number_of_coils=1)
                            self.client.disconnect()                   
                            #print(value)
                            #obj = root.get_child(l)
                            #value = obj.get_value()
                            if value != None and type(value) in (tuple, list):
                                value = int(value[0]*tag.scale)
                                if self.mapping:
                                    name = self.mappingTag(tag.full_name)
                                    res = loop.run_until_complete(pub.set('tag:'+str(name), value))
                                else:
                                    res = loop.run_until_complete(pub.set('tag:'+str(tag.full_name), value)) #await 
                                #res = loop.run_until_complete(pub.set('tag:'+str(tag.name), value))
                                #tag.updateValue(value) 
                                print(tag.name+" : "+str(value)) 
                            #sleep(0.1) 
                    if len(device["OC"]) > 0:
                        temp = device["OC"]
                        for i in temp:
                            tag = temp[i]
                            self.client.connect()
                            value = self.client.read_coils(start_coil_address=int(tag.address), number_of_coils=1)  
                            self.client.disconnect()                 
                            #print(value)
                            #obj = root.get_child(l)
                            #value = obj.get_value()
                            if value != None and type(value) in (tuple, list):
                                value = int(value[0]*tag.scale)
                                if self.mapping:
                                    name = self.mappingTag(tag.full_name)
                                    res = loop.run_until_complete(pub.set('tag:'+str(name), value))
                                else:
                                    res = loop.run_until_complete(pub.set('tag:'+str(tag.full_name), value)) #await 
                                #res = loop.run_until_complete(pub.set('tag:'+str(tag.name), value))
                                #tag.updateValue(value) 
                                print(tag.name+" : "+str(value)) 
                            #sleep(0.1) 
                        notNow = """start, size = cal_block(temp)
                        values = self.client.read_coils(start_coil_address= start, number_of_coils= size)
                        if values != None:
                            for i in range(len(values)):
                                target = start + i
                                if target in temp:
                                    value = values[i]*temp[target].scale
                                    res = loop.run_until_complete((pub.set('tag:'+str(temp[target].full_name), value))) #await 
                                    #res = loop.run_until_complete(pub.set('tag:'+str(temp[target].name), value))
                                    #tag.updateValue(value) 
                        sleep(0.25) """
                    if len(device["OHR"]) > 0:
                        temp = device["OHR"]
                        dataBlockOHR = cal_block(temp)
                        for block in dataBlockOHR:
                            self.client.connect()
                            values = self.client.read_holding_registers(start_register_address=block[0], number_of_registers=block[1])
                            self.client.disconnect()
                            try: #if values != None and type(value) in (tuple, list):
                                for p in range(len(values)):
                                    pos = p + block[0]
                                    if pos in temp:
                                        tag = temp[pos]
                                        value = int(values[p]*tag.scale)
                                        if self.mapping:
                                            name = self.mappingTag(tag.full_name)
                                            res = loop.run_until_complete(pub.set('tag:'+str(name), value))
                                        else:
                                            res = loop.run_until_complete(pub.set('tag:'+str(tag.full_name), value)) #await 
                                        print(tag.name+" : "+str(value)) 
                            except:
                                print("something not right")
                    if len(device["IR"]) > 0:
                        temp = device["IR"]
                        dataBlockOHR = cal_block(temp)
                        for block in dataBlockOHR:
                            self.client.connect()
                            values = self.client.read_input_registers(start_register_address=block[0], number_of_registers=block[1])
                            self.client.disconnect()

                            print("read block "+str(block))
                            print("got value "+str(values)+":"+str(type(values)))
                            try :#if values != None and type(value) == list:
                                print("in it with "+str(temp))
                                for p in range(len(values)):
                                    pos = p + block[0]
                                    if pos in temp:
                                        tag = temp[pos]
                                        print(tag)
                                        value = int(values[p]*tag.scale)
                                        if self.mapping:
                                            name = self.mappingTag(tag.full_name)
                                            res = loop.run_until_complete(pub.set('tag:'+str(name), value))
                                        else:
                                            res = loop.run_until_complete(pub.set('tag:'+str(tag.full_name), value)) #await 
                                        print(tag.name+" : "+str(value)) 
                            except:
                                print("something not right")                
        
        finally:
            pub.close()
            print("End")
            #self.client.disconnect()
 
          
import paho.mqtt.client as mqtt
class MQTT_DB_Connection(Connection):
    def __init__(self, address, port = 1883, devices = [], topic = "", tranFunction = None, login = '', pw = '', redis_client=None):
        Connection.__init__(self, address, devices, redis_client)
        self.port = port
        self.client = mqtt.Client()
        self.write_dict = {}
        self.device_dict = {}
        self.login = login
        self.topic = topic
        self.pw = pw
        self.tranFunction = tranFunction
        #self.mapping = False
		
    def WriteTag(self,tag,value):
        if self.mapping:
            tag = self.mappingTag(tag)
        if tag not in self.write_dict:
            return
        self.write_dict[tag] = [True, value]
        print("set write out to : ",tag," value ",value)

    # keep in case need to swap tag to webscoket
    def mappingTag(self, tag):
        my_map = {}
        if tag in my_map:
            return my_map[tag]
        return 0
		
    def write_out(self):			
        from tag.models import Tag
        # t=Tag.objects.get(full_name=tag)
        
        print("no write out yet")
        
        # return # pass
    		
        # nowNow = """
        # do write back here
        ##rr = self.modbus.write_coil(int(t.address), int(value), unit=int(t.device.address))
        for tn in self.write_dict:
            if not self.write_dict[tn][0]:
                continue
            temp = self.write_dict[tn]
            t=Tag.objects.get(full_name=tn)
            print("get to set tag", t)
            print(tn)
            print(self.write_dict[tn])
            value = int(temp[1])
            if t.type in ["Discrete Input Contacts","Discrete Output Coils"]: # still only work for this 2
                #self.client.device_id = int(t.device.address) # this line may nee to move outside
                #x = self.client.write_coil(int(t.address), value)
                self.write_dict[tn] = [False, 0]
                sleep(0.1)
            #"""

    def start(self, threadName = None):
        try:
            import asyncio
            print('connect')
            #self.client.connect()
            print('after connect')
            #root = self.client.get_root_node()
            #self.client.config(device_id=1, socket_ip=self.address, 
            #                   socket_port=self.port, signed_type=True)
            redis_host='redis://redis'
            loop=asyncio.get_event_loop()
            pub= loop.run_until_complete(aioredis.create_redis(redis_host))
            res = loop.run_until_complete(pub.auth('ictadmin')) #await 
            print('create redis client ok')
            
            device_dict = {}
            #print(self.devices)
            for device in self.devices:
                d_id = device.address
                temp = {}
                for tag in device.tags:
                    addr = tag.address
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0]
                device_dict[d_id] = temp

            print("finish set device_dict")
            print(device_dict)
            print(self.write_dict)
            
            self.device_dict = device_dict
            
            def update_tags(data = {}):
                if "ID" in data and data['ID'] in self.device_dict:
                    device = self.device_dict[data['ID']]
                    for d in data:
                        if d in device:
                            tag = device[d]
                            res = loop.run_until_complete(pub.set('tag:'+str(tag.full_name), data[d])) 
                            print(tag.name+" : "+str(data[d]))
                else:
                    for d in self.device_dict:
                        dev = self.device_dict[d]
                        for t in dev:
                            if t in data:
                                tag = dev[t]
                                res = loop.run_until_complete(pub.set('tag:'+str(tag.full_name), data[t])) 
                                print(tag.name+" : "+str(data[t]))
            def on_connect(client, userdata, flags, rc):
                print("Connected With Result Code "+str(rc))

            def on_message(client, userdata, message):
                data = str(message.payload.decode())
                print("Message Recieved:"+str(message.payload.decode()))
                print(self.tranFunction)
                result = self.tranFunction(data)
                print(result)
                update_tags(result)
            
            self.client.on_connect = on_connect
            self.client.on_message = on_message
            if self.login not in [None, ''] and self.pw not in [None, '']:
                self.client.username_pw_set(self.login,self.pw)
            self.client.connect(self.address, int(self.port))
            
            self.client.subscribe(self.topic, qos=1)
            
            asyncio.ensure_future(self.client.loop_forever()) #self.client.loop_start()
                
            while self.run:
                sleep(0.01)           
        
        finally:
            #self.client.loop_stop()
            pub.close()
            print("End")
            #self.client.disconnect()

#import paho.mqtt.client as mqtt
class MQTT_Multi_Connection(Connection):
    def __init__(self, address, port, devices = [], login = '', pw = '', redis_client=None):
        Connection.__init__(self, address, devices, redis_client)
        self.client = mqtt.Client()
        self.port = port
        self.write_dict = {}
        self.device_dict = {}
        self.login = login
        self.topic = []
        self.topicDic = {}
        self.pw = pw
        self.mapping = False
		
    def WriteTag(self,tag,value):
        if self.mapping:
            tag = self.mappingTag(tag)
        if tag not in self.write_dict:
            return
        self.write_dict[tag] = [True, value]
        print("set write out to : ",tag," value ",value)

    # keep in case need to swap tag to webscoket
    def mappingTag(self, tag):
        my_map = {}
        if tag in my_map:
            return my_map[tag]
        return 0
		
    def write_out(self):			
        from tag.models import Tag
        # t=Tag.objects.get(full_name=tag)
        
        print("no write out yet")
        
        # return # pass
    		
        # nowNow = """
        # do write back here
        ##rr = self.modbus.write_coil(int(t.address), int(value), unit=int(t.device.address))
        for tn in self.write_dict:
            if not self.write_dict[tn][0]:
                continue
            temp = self.write_dict[tn]
            t=Tag.objects.get(full_name=tn)
            print("get to set tag", t)
            print(tn)
            print(self.write_dict[tn])
            value = int(temp[1])
            if t.type in ["Discrete Input Contacts","Discrete Output Coils"]: # still only work for this 2
                #self.client.device_id = int(t.device.address) # this line may nee to move outside
                #x = self.client.write_coil(int(t.address), value)
                self.write_dict[tn] = [False, 0]
                sleep(0.1)
            #"""
    
    def tag_tree(self, topic = {}, tags = [], sub = False):
        if not sub:
            for tag in tags:
                if tag.type in ["JSON_RAW", "LIST_RAW"]:
                    topic[tag.name] = {}
            for tag in tags:
                if tag.type not in ["JSON_RAW", "LIST_RAW"]:
                    try:
                        JS = json.loads(tag.address)
                        if JS['tag'] in topic:
                            if tag.type not in ["JSON_SubValue", "LIST_SubValue"]:
                                if JS['key'] not in topic[JS['tag']]:
                                    topic[JS['tag']][JS['key']] = [{'tag':tag, 'type':tag.type}]
                                else:
                                    topic[JS['tag']][JS['key']].append({'tag':tag, 'type':tag.type})
                            else:
                                if JS['key'] not in topic[JS['tag']]:
                                    topic[JS['tag']][JS['key']] = [{'tag':tag, 'type':tag.type, 'sub':self.tag_tree({}, tags, tag.name)}]
                                else:
                                    topic[JS['tag']][JS['key']].append({'tag':tag, 'type':tag.type, 'sub':self.tag_tree({}, tags, tag.name)})
                    except:
                        print("Cannot load tag: "+tag.name)
        else:
            for tag in tags:
                try:
                    JS = json.loads(tag.address)
                    if JS['tag'] == sub:
                        if tag.type not in ["JSON_SubValue", "LIST_SubValue"]:
                            if JS['key'] not in topic:
                                topic[JS['key']] = [{'tag':tag, 'type':tag.type}]
                            else:
                                topic[JS['key']].append({'tag':tag, 'type':tag.type})
                        else:
                            if JS['key'] not in topic:
                                topic[JS['key']] = [{'tag':tag, 'type':tag.type, 'sub':self.tag_tree({}, tags, tag.name)}]
                            else:
                                topic[JS['key']].append({'tag':tag, 'type':tag.type, 'sub':self.tag_tree({}, tags, tag.name)})
                except:
                    print("Cannot load tag: "+tag.name)
        return topic

    def start(self, threadName = None):
        try:
            import asyncio
            print('connect')
            #self.client.connect()
            print('after connect')
            #root = self.client.get_root_node()
            #self.client.config(device_id=1, socket_ip=self.address, 
            #                   socket_port=self.port, signed_type=True)
            redis_host='redis://redis'
            loop=asyncio.get_event_loop()
            pub= loop.run_until_complete(aioredis.create_redis(redis_host))
            res = loop.run_until_complete(pub.auth('ictadmin')) #await 
            print('create redis client ok')
            
            device_dict = {}
            self.topic = [] # topic of list
            self.topicDic = {} # topic pair with tag
            self.nameDevice = {}
            self.device_address = {} # device address detail
            self.devicePairTag = {} # pair up topic tag with other tag
            #print(self.devices)
            for device in self.devices:
                d_id = device.name
                temp = {}
                temp_tp = {}
                tempDPT = {}
                try:
                    dvJS = json.loads(device.address)
                    self.device_address[d_id] = dvJS
                    device.address = dvJS
                except:
                    print("Cannot device load: "+d_id)
                for tag in device.tags:
                    addr = tag.name
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0]
                    if tag.type in ["JSON_RAW", "LIST_RAW"]:
                        tp = None
                        try:
                            tpJS = json.loads(tag.address)
                            tp = tpJS["topic"]
                            if tp not in self.topic:
                                self.topic.append(tp)
                            temp_tp[tp] = tag 
                            #temp_dpt[tp] = []
                        except:
                            tp = None
                            print("Cannot tag load: "+tag.full_name)
                #for tag in device.tags:  # double loop for add tag to topic
                #    pass
                tempDPT = self.tag_tree(tempDPT, device.tags)
                device_dict[d_id] = temp
                self.topicDic[d_id] = temp_tp 
                self.nameDevice[d_id] = device
                self.devicePairTag[d_id] = tempDPT

            print("finish set device_dict")
            print(device_dict)
            print(self.write_dict)
            print(self.topic)
            print(self.topicDic)
            print(self.devicePairTag)
            
            self.device_dict = device_dict

            def macth_list(dev, tag, data):
                Rvalue = {}
                print("in macth")
                print(dev.address)
                try:
                    dvJS = dev.address
                    #print(1)
                    tpJS = json.loads(tag.address)
                    #print(2)
                    if "key_list" not in tpJS or tpJS["key_list"] == "order":
                        key_list = False
                    else:
                        key_list = tpJS["key_list"]
                    split = tpJS["split"]
                    #print(3)
                    Ldata = data.split(split)
                    #print(4)
                    if not key_list:
                        for l in range(len(data)):
                            Rvalue[l] = Ldata[l]
                    else:
                        for l in range(len(key_list)):
                            Rvalue[key_list[l]] = Ldata[l]
                    #print(5) 
                    #print(Rvalue)
                    for addr in dvJS:
                        if addr not in Rvalue or dvJS[addr] != Rvalue[addr]:
                            Rvalue = -1
                            break
                    #print(6)
                    #print(Rvalue)
                except e:
                    print(e)
                    return -1
                print(Rvalue)
                return Rvalue

            def macth_json(dev, tag, data):
                Rvalue = {}
                print("in macth")
                print(dev.address)
                try:
                    dvJS = dev.address
                    Rvalue = json.loads(data)
                    for addr in dvJS:
                        if addr not in Rvalue or dvJS[addr] != Rvalue[addr]:
                            Rvalue = -1
                            break
                except e:
                    print(e)
                    return -1
                return Rvalue

            def update_sub_list(data = "", sTag = {}):
                try:
                    if type(data) not in [str, list]:
                        return
                    tag = sTag['tag']
                    tpJS = json.loads(tag.address)
                    if "key_list" not in tpJS or tpJS["key_list"] == "order":
                        key_list = False
                    else:
                        key_list = tpJS["key_list"]
                    split = tpJS["split"]
                    Ldata = data
                    if type(data) == str:
                        Ldata = data.split(split)
                    sub = sTag['sub']
                    result = {}
                    if not key_list:
                        for l in range(len(data)):
                            result[l] = Ldata[l]
                    else:
                        for l in range(len(key_list)):
                            result[key_list[l]] = Ldata[l]
                    for pair in sub:
                        for tPair in sub[pair]:
                            cond = {}
                            JS = json.loads(tPair["tag"].address)
                            if "condition" in JS:
                                cond = JS["condition"]
                            print(tPair)
                            print(cond)
                            for con in cond:
                                if con not in result or cond[con] != result[con]:
                                    continue
                            print("pass")
                            #tPair = pairing[pair]
                            #tPair = sub[s]
                            if pair in result:
                                if  tPair["type"] == "LIST_SubValue":
                                    res = loop.run_until_complete(pub.set('tag:'+str(tPair["tag"].full_name), result[pair])) 
                                    print(tPair["tag"].name+" : "+str(result[pair]))
                                    update_sub_list(result[pair], tPair)
                                elif tPair["type"] == "JSON_SubValue":
                                    res = loop.run_until_complete(pub.set('tag:'+str(tPair["tag"].full_name), str(result[pair]))) 
                                    print(tPair["tag"].name+" : "+str(result[pair]))
                                    update_sub_json(result[pair], tPair)
                                else:
                                    res = loop.run_until_complete(pub.set('tag:'+str(tPair["tag"].full_name), result[pair])) 
                                    print(tPair["tag"].name+" : "+str(result[pair]))

                except e:
                    print(e) 

            def update_sub_json(data = "", sTag = {}):
                try:
                    if type(data) not in [str, dict]:
                        return
                    tag = sTag['tag']
                    result = data
                    if type(data) == str:
                        result = json.loads(data)
                    sub = sTag['sub']
                    for pair in sub:
                        for tPair in sub[pair]:
                            cond = {}
                            JS = json.loads(tPair["tag"].address)
                            if "condition" in JS:
                                cond = JS["condition"]
                            print(tPair)
                            print(cond)
                            for con in cond:
                                if con not in result or cond[con] != result[con]:
                                    continue
                            print("pass")
                            #tPair = pairing[pair]
                            #tPair = sub[s]
                            if pair in result:
                                if  tPair["type"] == "LIST_SubValue":
                                    res = loop.run_until_complete(pub.set('tag:'+str(tPair["tag"].full_name), result[pair])) 
                                    print(tPair["tag"].name+" : "+str(result[pair]))
                                    update_sub_list(result[pair], tPair)
                                elif tPair["type"] == "JSON_SubValue":
                                    res = loop.run_until_complete(pub.set('tag:'+str(tPair["tag"].full_name), str(result[pair]))) 
                                    print(tPair["tag"].name+" : "+str(result[pair]))
                                    update_sub_json(result[pair], tPair)
                                else:
                                    res = loop.run_until_complete(pub.set('tag:'+str(tPair["tag"].full_name), result[pair])) 
                                    print(tPair["tag"].name+" : "+str(result[pair]))

                except e:
                    print(e) 
            
            def update_tags(data = {}, topic = ""):
                if topic not in self.topic:
                    return

                #print("in topic")
                print(data)
                #print(topic)
                
                for d_name in self.topicDic:
                    if topic not in self.topicDic[d_name]:
                        continue
                    device = self.nameDevice[d_name]
                    tag = self.topicDic[d_name][topic]
                    print(device)
                    print(tag)
                    result = -1
                    if tag.type == "JSON_RAW":
                        print("in json")
                        result = macth_json(device, tag, data)
                    elif tag.type == "LIST_RAW":
                        print("in list")
                        result = macth_list(device, tag, data)
                    print(result)
                    if result != -1:
                        res = loop.run_until_complete(pub.set('tag:'+str(tag.full_name), str(data))) 
                        print(tag.name+" : "+str(data))
                        pairing = self.devicePairTag[d_name][tag.name]
                        #print("pairing")
                        #print(pairing)
                        for pair in pairing:
                            #print("pair")
                            #print(pair)
                            for tPair in pairing[pair]:
                                #print("tPair")
                                #print(tPair)
                                cond = {}
                                JS = json.loads(tPair["tag"].address)
                                if "condition" in JS:
                                    cond = JS["condition"]
                                #print(tPair)
                                #print(cond)
                                pas = True
                                for con in cond:
                                    if con not in result or cond[con] != result[con]:
                                        pas = False
                                if not pas:
                                    continue
                                print("pass")
                                #tPair = pairing[pair]
                                if pair in result:
                                    if  tPair["type"] == "LIST_SubValue":
                                        res = loop.run_until_complete(pub.set('tag:'+str(tPair["tag"].full_name), result[pair])) 
                                        print(tPair["tag"].name+" : "+str(result[pair]))
                                        update_sub_list(result[pair], tPair)
                                    elif tPair["type"] == "JSON_SubValue":
                                        res = loop.run_until_complete(pub.set('tag:'+str(tPair["tag"].full_name), str(result[pair])))
                                        print(tPair["tag"].name+" : "+str(result[pair]))
                                        update_sub_json(result[pair], tPair)
                                    else:
                                        res = loop.run_until_complete(pub.set('tag:'+str(tPair["tag"].full_name), result[pair])) 
                                        print(tPair["tag"].name+" : "+str(result[pair]))
                        break
                    print("")
                

            def on_connect(client, userdata, flags, rc):
                print("Connected With Result Code "+str(rc))
                topic = []
                for t in self.topic:
                    topic.append((t,1))
                self.client.subscribe(topic)

            def on_subscribe(client, userdata, mid, granted_qos):
                print("Subscibe With granted_qos Code "+str(granted_qos))
                print("in on subscribe callback result "+str(mid))

            def on_message(client, userdata, message):
                data = str(message.payload.decode())
                print("Message Recieved:"+str(message.payload.decode()))
                print("from topic:"+str(message.topic))
                #print(self.tranFunction)
                #result = [] #self.tranFunction(data)
                #print(result)
                update_tags(data, message.topic)
            
            self.client.on_connect = on_connect
            self.client.on_message = on_message
            self.client.on_subscribe = on_subscribe
            if self.login not in [None, ''] and self.pw not in [None, '']:
                self.client.username_pw_set(self.login,self.pw)
            self.client.connect(self.address, int(self.port))
            
            asyncio.ensure_future(self.client.loop_forever()) #self.client.loop_start()
                
            while self.run:
                sleep(0.01)           
        
        finally:
            #self.client.loop_stop()
            pub.close()
            print("End")
            #self.client.disconnect()            
            
import msgpack
import socket
import ast 
import datetime
def decode_datetime(obj):
    if b'__datetime__' in obj:
        obj = datetime.datetime.strptime(obj["as_str"], "%Y%m%dT%H:%M:%S.%f")
    return obj
def ext_hook(code, data):
    if code == -1:
        if len(data) == 4:
            secs = int.from_bytes(data, byteorder='big', signed=True)
            nsecs = 0;
        elif len(data) == 8:
            data = int.from_bytes(data, byteorder='big', signed=False)
            secs = data & 0x00000003ffffffff;
            nsecs = data >> 34;
        elif len(data) == 12:
            import struct

            nsecs, secs = struct.unpack('!Iq', data)
        else:
            raise AssertionError("Not reached");

        return datetime.datetime.utcfromtimestamp(secs + nsecs / 1e9)

    else:
        return msgpack.ExtType(code, data)

#msgpack.unpack(data, ext_hook=ext_hook)
class Socket_MsgPack_Connection(Connection):
    def __init__(self, address, port = 1883, devices = [], redis_client=None):
        Connection.__init__(self, address, devices, redis_client)
        self.port = int(port)
        self.client = socket.socket()
        self.write_dict = {}
        self.device_dict = {}
        self.mapping = False
		
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
        my_map = {}
        if tag in my_map:
            return my_map[tag]
        return 0
		
    def write_out(self):			
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
            value = int(temp[1])
            #if t.type in ["Discrete Input Contacts","Discrete Output Coils"]: # still only work for this 2
            #    self.client.device_id = int(t.device.address) # this line may nee to move outside
            #    x = self.client.write_coil(int(t.address), value)
            print(['set',t.name,str(value)])
            x = self.sending_to(['set',t.name,str(value)])
            self.write_dict[tn] = [False, 0]
            #sleep(0.1)
    		
    def sending_to(self, data):
        temp = ""
        try:
            self.client = socket.socket()
            self.client.connect((self.address, self.port))
            x = msgpack.packb(data, use_bin_type=True)
            print(data)
            print(x)
            self.client.send(x)
            print(2)
            re = self.client.recv(1024)
            print("got")
            print(re)
            temp = msgpack.unpackb(re, ext_hook=ext_hook, raw=False) # unpackb(re, object_hook=decode_datetime, use_list=False, raw=False)
            print("tran got")
            print(temp)
            x = msgpack.packb('exit', use_bin_type=True)
            self.client.send(x)
            self.client.close()
        except:
            #print(e)
            self.client.close()
            temp = "error"
            
        return temp

    def start(self, threadName = None):
        try:
            import asyncio
            print('connect')
            redis_host='redis://redis'
            loop=asyncio.get_event_loop()
            pub= loop.run_until_complete(aioredis.create_redis(redis_host))
            res = loop.run_until_complete(pub.auth('ictadmin')) #await 
            print('create redis client ok')
            
            device_dict = {}
            for device in self.devices:
                d_id = device.address
                temp = {}
                for tag in device.tags:
                    addr = tag.address
                    #temp[tag.name] = tag 
                    self.write_dict[tag.full_name] = [False, 0]
                    device_dict[tag.name] = tag

            print("finish set device_dict")
            print(device_dict)
            print(self.write_dict)
            
            self.device_dict = device_dict
            tagKeys = list(self.device_dict.keys())
            
            #asyncio.ensure_future(self.client.loop_forever()) #self.client.loop_start()
                
            while self.run:
                loop.run_until_complete(asyncio.sleep(1))
                temp = self.write_out() # check anything to write first
                
                
                count = 0
                while count < len(tagKeys):
                    s = count
                    count += 10
                    if count > len(tagKeys):
                        count = len(tagKeys)
                    temp = tagKeys[s:count]
                    print(temp)
                    temp = ['get'] + temp
                    x = self.sending_to(temp)
                    print(temp)
                    print(x)
                    reData = x[2]
                    for i in reData:
                        tag = self.device_dict[i]
                        if reData[i] == None or type(reData[i]) == str:
                            continue
                        value = reData[i]*tag.scale
                        if self.mapping:
                            name = self.mappingTag(tag.full_name)
                            res = loop.run_until_complete(pub.set('tag:'+str(name), value))
                        else:
                            res = loop.run_until_complete(pub.set('tag:'+str(tag.full_name), value)) #await 
                        print(tag.name+" : "+str(value))
                    
                    
        
        finally:
            pub.close()
            print("End")

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

    def setBulb(self,addr,key,value):
        result = False
        if addr not in self.item:
            return result
        bulb = self.item[addr]
        try:
            if key == 'on':
                value = int(value)
                s = False if value in [b'0',0,'0',False] else True
                bulb.on = s
                result = True
            elif key == 'brightness':
                s = int(value)
                if s > 254: s = 254
                elif s < 0: s = 0
                bulb.brightness = s
                result = True
            elif key == 'color':
                value = value.decode()
                temp = []
                if value[0] == "#":
                    temp.append(int(value[5:7],16))
                    temp.append(int(value[3:5],16))
                    temp.append(int(value[1:3],16))
                else:
                    s = int(value)
                    for i in range(3):
                        temp += [(s % 256)/256]
                        s //= 256
                bulb.xy = self.RGBtoCIE(temp[2],temp[1],temp[0])
                result = True
        except Exception as e:
            print(e)
            result = False
        return result

    def RGBtoCIE(self,r,g,b):
        X = (0.412453*r + 0.357580*g + 0.180423*b)
        Y = (0.212671*r + 0.715160*g + 0.072169*b)
        Z = (0.019334*r + 0.119193*g + 0.950227*b)
        if X+Y+Z == 0:
                x = 0
                y = 0
        else:
                x = X / (X + Y + Z)
                y = Y / (X + Y + Z)
        return x,y

    def start(self, threadName = None):
        try:
            import asyncio
            print('connect')
            redis_host='redis://redis'
            loop=asyncio.get_event_loop()
            pub= loop.run_until_complete(aioredis.create_redis(redis_host))
            res = loop.run_until_complete(pub.auth('ictadmin')) #await 
            print('create redis client ok')
            import json
            import urllib3
            username = "To12WiQhfurMCjoRJjUo0qtblfJjKkDGIbh-8UD8"
            url = 'https://%s/api/' %(self.address)
            http = urllib3.PoolManager(cert_reqs='CERT_NONE',assert_hostname=False)
            h={}#{"authorization":"Token f2b5c1c068c610e3b09ca32f34fb7c14f252fc1f"}
            data={"devicetype":"scada_driver2hue"}
            r = http.request('POST', url, headers=h, body=json.dumps(data))
            ans = json.loads(r.data.decode())[0]

            if "error" in ans:
                raise Exception(str(ans["error"]["description"]))
            elif "success" in ans:
                username = ans["success"]["username"]
            else:
                raise Exception(str(ans))

            self.client = phue.Bridge(self.address, username)
            x = """
            if self.port in [None,"-"]:
                self.client = phue.Bridge(self.address, "To12WiQhfurMCjoRJjUo0qtblfJjKkDGIbh-8UD8")
            else:
                self.client = phue.Bridge(self.address, "To12WiQhfurMCjoRJjUo0qtblfJjKkDGIbh-8UD8")"""
            
            self.loop = loop
            self.pub = pub
            self.item = self.client.get_light_objects('name')
            self.sitem = self.client.sensors

            device_dict = {}
            for device in self.devices:
                d_id = device.address
                temp = {}
                for tag in device.tags:
                    addr = tag.address
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0]
                device_dict[d_id] = temp

            print("finish set device_dict")
            print(device_dict)
            print(self.write_dict)
            
            self.device_dict = device_dict
            tagKeys = list(self.device_dict.keys())
            
            #asyncio.ensure_future(self.client.loop_forever()) #self.client.loop_start()
                
            tagOldValue = {}
            count = 0
            while self.run:
                loop.run_until_complete(asyncio.sleep(0.5))
                temp = self.write_out() # check anything to write first
                
                #count += 1
                #if count % 3600 != 1:
                #    continue

                self.item = self.client.get_light_objects('name')
                item = self.item
                sitem = self.client.sensors_by_name
                
                for d in self.device_dict:
                    if d not in item and d not in ['sensor', 'Sensor']:
                        continue
                    
                    for t in self.device_dict[d]:
                        tag = self.device_dict[d][t]
                        tagFN = tag.full_name
                        tagAdd = tag.address
                        value = None
                        if d in item:
                            l = item[d]
                            if t == 'on':
                                value = 1 if l.on else 0
                            elif t == 'brightness':
                                value = l.brightness
                        elif tagAdd in sitem:
                            s = sitem[tagAdd].state
                            if 'daylight' in s:
                                value = s['daylight']
                            else:
                                for k in s:
                                    if k != 'lastupdated':
                                        value = s[k]
                                        break
                            if type(value) == bool:
                                value = 1 if value else 0

                        if value != None:
                            value = value*tag.scale
                            if tag.type == "int":
                                value = int(value)
                            if tagFN in tagOldValue and tagOldValue[tagFN] == value:
                                continue
                            
                            tagOldValue[tagFN] = value
                            if self.mapping:
                                name = self.mappingTag(tagFN)
                                res = loop.run_until_complete(pub.set('tag:'+str(name), value))
                            else:
                                res = loop.run_until_complete(pub.set('tag:'+str(tagFN), value)) #await 
                            print(tag.name+" : "+str(value))
                                   
        
        finally:
            pub.close()
            print("End")

@app.task
def phillip_hue_driver(port_id = 5):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)

    conn_1 = Phillip_Hue_Connection(port.detail["address"],port.detail["port"],[])

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

            self.client = {} # SaijoAir

            device_dict = {}
            for device in self.devices:
                d_id = device.address
                temp = {}
                for tag in device.tags:
                    addr = tag.address
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0]
                device_dict[d_id] = temp
                self.client[d_id] = SaijoAir(device.address)

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
                if count % 7200 != 1:
                    continue

                nope = """{ 'currentTemp' : self.tempC,
                 'setTemp' : self.tempS,
                 'currentHum' : self.rhC,
                 'setHum' : self.rhS,
                 'mode' : self.modeA,
                 'powerStat' : self.powerStat,
                 'fan' : self.fan,
                 'lp' : self.lp,
                 'last update' : self.lastUpdate}"""
                
                for d in self.device_dict:
                    l = self.client[d]
                    data = l.readValue()
                    for t in self.device_dict[d]:
                        if t not in data:
                            continue
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
def saijo_lan_driver(port_id = 5):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)

    conn_1 = Saijo_Air_Connection([])

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

from drivers.extra_driver.DaikinLan import AirItemLan as DaikinAir
from drivers.extra_driver.DaikinLan import getUUID as DaikinUUID
class Daikin_Air_Connection(Connection):
    def __init__(self, devices = [], redis_client=None):
        Connection.__init__(self, None, devices, redis_client)
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
        if self.pub == None or self.loop == None:
            return		
        from tag.models import Tag
        # t=Tag.objects.get(full_name=tag)
        total = {}
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
            addr = t.device.address
            if t.address in ["setTemp", "setHum"]:
                value = int(value)
            else:
                value = int(value)

            if addr not in total:
                total[addr] = {}
            total[addr][t.address] = value

            res = self.loop.run_until_complete(self.pub.set('tag:'+str(t.full_name), value)) #await 
            print(t.name+" : "+str(value))
            self.write_dict[tn] = [False, 0]
            #sleep(0.1)
        for d in total:
            data = total[d]
            print("setting", d)
            print(data)
            self.client[d].command(data)

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

            self.client = {} # DaikinAir
            my_uuid = DaikinUUID()

            from tag.models import  Device as Rdevice
            device_dict = {}
            #serial_number
            for device in self.devices:
                d_id = device.address
                temp = {}
                for tag in device.tags:
                    addr = tag.address
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0]
                device_dict[d_id] = temp
                rd = Rdevice.objects.get(name = device.name, address = device.address)
                serial = rd.serial_number
                self.client[d_id] = DaikinAir(device.address,serial,my_uuid)

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
                if count % 15 != 1:
                    continue

                nope = """{ 'currentTemp' : self.tempC,
                 'setTemp' : self.tempS,
                 'currentHum' : self.rhC,
                 'setHum' : self.rhS,
                 'mode' : self.modeA,
                 'powerStat' : self.powerStat,
                 'fan' : self.fan,
                 'lp' : self.lp,
                 'last update' : self.lastUpdate}"""
                
                for d in self.device_dict:
                    l = self.client[d]
                    data = l.getInfo()
                    for t in self.device_dict[d]:
                        if t not in data:
                            continue
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
def Daikin_lan_driver(port_id = 5):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)

    conn_1 = Daikin_Air_Connection([])

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

from pyHS100 import SmartPlug as TPLinkSP
class TPLink_Connection(Connection):
    def __init__(self, devices = [], redis_client=None):
        Connection.__init__(self, None, devices, redis_client)
        self.client = {}
        self.write_dict = {}
        self.device_dict = {}
        self.mapping = False
        self.pub = None
        self.loop = None
        self.item = ["on","energy"]
		
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
        if self.pub == None or self.loop == None:
            return		
        from tag.models import Tag
        # t=Tag.objects.get(full_name=tag)
        for tn in self.write_dict:
            if not self.write_dict[tn][0]:
                continue
            temp = self.write_dict[tn]
            t=Tag.objects.get(full_name=tn)
            if t.address not in ["on"]:
                self.write_dict[tn] = [False, 0]
                continue
            print("get to set tag", t)
            value = int(self.write_dict[tn][1])
            d_id = t.device.address
            self.client[d_id].state = "ON" if value == 1 else "OFF"
            result = True
            if result:
                res = self.loop.run_until_complete(self.pub.set('tag:'+str(t.full_name), value)) #await 
                print(t.name+" : "+str(value))
            self.write_dict[tn] = [False, 0]
            #sleep(0.1)

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

            self.client = {} # SaijoAir

            device_dict = {}
            for device in self.devices:
                d_id = device.address
                temp = {}
                for tag in device.tags:
                    addr = tag.address
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0]
                device_dict[d_id] = temp
                self.client[d_id] = TPLinkSP(device.address)

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
                if count % 30 != 1:
                    continue

                
                for d in self.device_dict:
                    l = self.client[d]
                    for t in self.device_dict[d]:
                        if t not in self.item:
                            continue
                        tag = self.device_dict[d][t]
                        value = None # data[t]

                        if t == "on":
                            value = 1 if l.is_on else 0
                        elif t == "energy":
                            value = l.current_consumption()

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
def TPLink_driver(port_id = 5):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)

    conn_1 = TPLink_Connection([])

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

from drivers.extra_driver.cbfood_inspect_cam.cbfood_camera import FoodInspector
import serial
serial_parity_dict = {
    None : serial.PARITY_NONE,
    "none" : serial.PARITY_NONE,
    "serial.parity_none" : serial.PARITY_NONE,
    1 : serial.PARITY_ODD,
    "odd" : serial.PARITY_ODD,
    "serial.parity_odd" : serial.PARITY_ODD,
    "even" : serial.PARITY_EVEN,
    0 : serial.PARITY_EVEN,
    "serial.parity_even" : serial.PARITY_ODD,
}
class Food_Inspector_Connection(Connection):
    def __init__(self, port = None, baudrate=9600, parity=serial.PARITY_NONE, timeout=None, devices = [], redis_client=None):
        Connection.__init__(self, "", devices, redis_client)
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.parity = parity
        self.client = None #phue.Bridge() #socket.socket()
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
        if self.pub == None or self.loop == None:
            return		
        from tag.models import Tag
        # t=Tag.objects.get(full_name=tag)
        for tn in self.write_dict:
            if not self.write_dict[tn][0]:
                continue
            self.write_dict[tn] = [False, 0]
            temp = """
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
            #sleep(0.1)"""



    def start(self, threadName = None):
        try:
            import asyncio
            print('connect')
            redis_host='redis://redis'
            loop=asyncio.get_event_loop()
            pub= loop.run_until_complete(aioredis.create_redis(redis_host))
            res = loop.run_until_complete(pub.auth('ictadmin')) #await 
            print('create redis client ok')
            
            self.client = FoodInspector(port=self.port, baud=self.baudrate, parity=self.parity, timeout=self.timeout)
            self.client.connect()
            
            self.loop = loop
            self.pub = pub

            device_dict = {}
            for device in self.devices:
                d_id = device.address
                temp = {}
                for tag in device.tags:
                    addr = tag.address
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0]
                device_dict[d_id] = temp

            print("finish set device_dict")
            print(device_dict)
            print(self.write_dict)
            
            self.device_dict = device_dict
            tagKeys = list(self.device_dict.keys())
            
            #asyncio.ensure_future(self.client.loop_forever()) #self.client.loop_start()
                
            count = 0
            while self.run:
                loop.run_until_complete(asyncio.sleep(1))
                temp = self.write_out() # check anything to write first
                
                #count += 1
                #if count % 3600 != 1:
                #    continue
                
                for d in self.device_dict:

                    for t in self.device_dict[d]:
                        value = self.client.capture_request()

                        if value != 1: #None:
                            if value == None:
                                value = "timeout"
                            if self.mapping:
                                name = self.mappingTag(tag.full_name)
                                res = loop.run_until_complete(pub.set('tag:'+str(name), value))
                            else:
                                res = loop.run_until_complete(pub.set('tag:'+str(tag.full_name), value)) #await 
                            print(tag.name+" : "+str(value))
                                   
        
        finally:
            self.client.disconnect()
            pub.close()
            print("End")

@app.task
def Food_Inspector_driver(port_id = 5):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)

    # class Food_Inspector_Connection(Connection):
    # def __init__(self, port = None, baudrate=9600, parity=serial.PARITY_NONE, timeout=None, devices = [], redis_client=None):
    p = port.detail["parity"].lower()
    parity = serial.PARITY_NONE
    if p in serial_parity_dict:
        parity = serial_parity_dict[p]
    timeout = None
    try:
        timeout = float(port.detail["parity"])
    except:
        timeout = None
    conn_1 = Food_Inspector_Connection(port.detail["port"], port.detail["baudrate"], parity=parity, timeout = timeout,  devices = [], redis_client=None)

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

class Foobot_Connection(Connection):
    def __init__(self, user = None, api_key = None, devices = [], redis_client=None):
        Connection.__init__(self, "", devices, redis_client)
        self.user = user
        self.api_key = api_key
        self.client = None #phue.Bridge() #socket.socket()
        self.write_dict = {}
        self.device_dict = {}
        self.mapping = False
        self.pub = None
        self.loop = None
        self.item = ['time', 'pm', 'tmp', 'hum', 'co2', 'voc', 'allpollu']
		
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
        if self.pub == None or self.loop == None:
            return		
        from tag.models import Tag
        # t=Tag.objects.get(full_name=tag)
        for tn in self.write_dict:
            if not self.write_dict[tn][0]:
                continue
            self.write_dict[tn] = [False, 0]
            temp = """
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
            #sleep(0.1)"""

    def requestFoobot(self, uuid):
        #uuid = c["uuid"]
        device_url = "https://api.foobot.io/v2/device/%s/datapoint/0/last/0/" %(uuid)
        headers = {'X-API-KEY-TOKEN': self.api_key , 'Accept': 'application/json;charset=UTF-8'}
        import requests
        import json
        r = requests.get(device_url, headers=headers)
        print(r.content)
        print(r.status_code)

        content = eval(r.content.decode().replace('null','None').replace('true','True').replace('false','False'))

        pprint(content)

        return content


    def start(self, threadName = None):
        try:
            import asyncio
            print('connect')
            redis_host='redis://redis'
            loop=asyncio.get_event_loop()
            pub= loop.run_until_complete(aioredis.create_redis(redis_host))
            res = loop.run_until_complete(pub.auth('ictadmin')) #await 
            print('create redis client ok')

            get_url = "https://api.foobot.io/v2/owner/%s/device/" %(self.user)
            headers = {'X-API-KEY-TOKEN': self.api_key , 'Accept': 'application/json;charset=UTF-8'}
            import requests
            import json
            r = requests.get(get_url, headers=headers)
            
            print(r.content)
            print(r.status_code)

            content = eval(r.content.decode().replace('null','None').replace('true','True').replace('false','False'))

            pprint(content)

            uuid_list = {} 
            for c in content:
                uuid_list[c["name"]] = c["uuid"]
            
            self.loop = loop
            self.pub = pub

            device_dict = {}
            for device in self.devices:
                d_id = device.address
                temp = {}
                for tag in device.tags:
                    addr = tag.address
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0]
                device_dict[d_id] = temp

            print("finish set device_dict")
            print(device_dict)
            print(self.write_dict)
            
            self.device_dict = device_dict
            # tagKeys = list(self.device_dict.keys())
            
            #asyncio.ensure_future(self.client.loop_forever()) #self.client.loop_start()
                
            count = 0
            while self.run:
                loop.run_until_complete(asyncio.sleep(1))
                temp = self.write_out() # check anything to write first
                tn = datetime.datetime.now()
                
                if count != 0 and tn.minute % 15 != 0:
                    count += 1
                    continue
                
                count += 1
                for d in self.device_dict:
                    if d not in uuid_list:
                        continue
                    temp = uuid_list[d]
                    data = self.requestFoobot(temp)

                    for tag in self.device_dict[d]:                        
                        if tag in self.item:
                            ttag = self.device_dict[d][tag]
                            pos = [i for i,x in enumerate(data["sensors"]) if x == tag][0]
                            value = data["datapoints"][0][pos]
                            if value == None:
                                value = "timeout"
                            if self.mapping:
                                name = self.mappingTag(ttag.full_name)
                                res = loop.run_until_complete(pub.set('tag:'+str(name), value))
                            else:
                                res = loop.run_until_complete(pub.set('tag:'+str(ttag.full_name), value)) #await 
                            print(ttag.name+" : "+str(value))
                                   
        
        finally:
            self.client.disconnect()
            pub.close()
            print("End")

@app.task
def Foobot_driver(port_id = 5):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)

    # class Foobot_Connection(Connection):
    # def __init__(self, user = None, api_key = None, devices = [], redis_client=None):

    conn_1 = Foobot_Connection(port.detail["user"], port.detail["api_key"],  devices = [], redis_client=None)

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

from drivers.extra_driver.Netatmo import *
class Netatmo_Connection(Connection):
    def __init__(self, user = None, password = None, client_id = None, client_secret = None, devices = [], redis_client=None):
        Connection.__init__(self, "", devices, redis_client)
        self.user = user
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.refresh_token = None
        self.client = None #phue.Bridge() #socket.socket()
        self.write_dict = {}
        self.device_dict = {}
        self.mapping = False
        self.pub = None
        self.loop = None
        self.item = ['time', 'pm', 'tmp', 'hum', 'co2', 'voc', 'allpollu']
		
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
        if self.pub == None or self.loop == None:
            return		
        from tag.models import Tag
        # t=Tag.objects.get(full_name=tag)
        for tn in self.write_dict:
            if not self.write_dict[tn][0]:
                continue
            self.write_dict[tn] = [False, 0]
            temp = """
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
            #sleep(0.1)"""


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

            self.client = NetatmoAccount(user = self.user, password = self.password, client_id = self.client_id, client_secret = self.client_secret, scope = ["read_station"])

            device_dict = {}
            for device in self.devices:
                d_id = device.address
                temp = {}
                for tag in device.tags:
                    addr = tag.address
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0]
                device_dict[d_id] = temp

            print("finish set device_dict")
            print(device_dict)
            print(self.write_dict)
            
            self.device_dict = device_dict
            # tagKeys = list(self.device_dict.keys())
            
            #asyncio.ensure_future(self.client.loop_forever()) #self.client.loop_start()
                
            count = 0
            while self.run:
                loop.run_until_complete(asyncio.sleep(1))
                temp = self.write_out() # check anything to write first
                tn = datetime.datetime.now()
                
                if count != 0 and tn.minute % 15 != 0:
                    count += 1
                    continue
                
                count += 1
                self.client.retrieve_devices()
                for d in self.device_dict:
                    if d not in self.client.devices:
                        continue
                    data = self.client[d].status()
                    for tag in self.device_dict[d]:
                        ttag = self.device_dict[d][tag]
                        value = data[tag]
                        if self.mapping:
                            name = self.mappingTag(ttag.full_name)
                            res = loop.run_until_complete(pub.set('tag:'+str(name), value))
                        else:
                            res = loop.run_until_complete(pub.set('tag:'+str(ttag.full_name), value))
                        print(ttag.name+" : "+str(value))
                                   
        
        finally:
            self.client.disconnect()
            pub.close()
            print("End")

@app.task
def Netatmo_driver(port_id = 5):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)

    # class Foobot_Connection(Connection):
    # def __init__(self, user = None, api_key = None, devices = [], redis_client=None):

    #conn_1 = Netatmo_Connection(port.detail["user"], port.detail["api_key"],  devices = [], redis_client=None)
    conn_1 = Netatmo_Connection(port.detail["user"], port.detail["password"], port.detail["client_id"], port.detail["client_secret"],  devices = [], redis_client=None)

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


import broadlink
from drivers.extra_driver.DaikinSkyair import DaikinSkyair
BL = None #broadlink.rm(host=('192.168.2.27',80), mac="78:0F:77:B9:41:C3", devtype="RM2")
from drivers.BroadLinkCode import remote_code
class Broadlink_Connection(Connection):
    def __init__(self, address, port = None, mac = None, broadlinkType = None, devices = [], redis_client=None):
        Connection.__init__(self, address, devices, redis_client)
        self.port = port
        self.mac = mac
        self.broadlinkType = broadlinkType
        self.client = None #phue.Bridge() #socket.socket()
        #self.client = broadlink.rm(host=(self.address,self.port), mac=self.mac, devtype=self.broadlinkType)
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
        self.write_dict[tag] = [True, value, self.write_dict[tag][2]]
        print("set write out to : ",tag," value ",value)

    # keep in case need to swap tag to webscoket
    def mappingTag(self, tag):
        my_map = {
                 }
        if tag in my_map:
            return my_map[tag]
        return 0

    def sentRemote(self, dev, tType, addr, value, oldV):
        print("got ", dev, tType, addr, value, oldV)
        #value = int(value)
        #print("pair with ", remote_code)
        if dev not in remote_code or addr not in remote_code[dev]:
            return False
        code = remote_code[dev][addr]
        print(code)
        if dev == "Daikin_Main_Remote" and self.dsk != None:
            if addr == "status":
                if value in [0,'0',b'0']:
                    self.dsk.turnOff()
                else:
                    self.dsk.turnOn()
            elif addr == "temperature":
                value = int(float(value))
                self.dsk.setTemperature(value)
            elif addr == "fanlevel":
                value = int(float(value))
                self.dsk.setFanLevel(value)
            elif addr == "mode":
                value = int(float(value))
                self.dsk.setModeLevel(value)
            else:
                return False
        elif tType == "single":
            self.client.send_data(code)
        elif tType == "toggle":
            if value in [0,'0',b'0']:
                self.client.send_data(code[0])
            else:
                self.client.send_data(code[1])
        elif tType == "multiple":
            if value in code:
                self.client.send_data(code[value])
            else:
                return False
        elif tType == "step":
            if value in [0,'0',b'0']:
                self.client.send_data(code[0])
            elif value in [1,'1',b'1']:
                self.client.send_data(code[1])
            elif value > oldV:
                self.client.send_data(code[1])
            else:
                self.client.send_data(code[0])
        return True
		
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
            value = int(float(temp[1]))
            result = False
            addr = t.device.address
            result = self.sentRemote(addr, t.type, t.address, value, temp[2])
            if result:
                res = self.loop.run_until_complete(self.pub.set('tag:'+str(t.full_name), value)) #await 
                print(t.name+" : "+str(value))
            if t.type != "step":
                self.write_dict[tn] = [False, 0, 0]
            else:
                self.write_dict[tn] = [False, 0, value]

    def start(self, threadName = None):
        try:
            import asyncio
            print('connect')
            redis_host='redis://redis'
            loop=asyncio.get_event_loop()
            pub= loop.run_until_complete(aioredis.create_redis(redis_host))
            res = loop.run_until_complete(pub.auth('ictadmin')) #await 
            print('create redis client ok')
            if self.port in [None,"-"]:
                self.port = 80
            else:
                self.port = int(self.port)
                
            print(self.address,self.port,self.mac,self.broadlinkType)
            host = (self.address,self.port)
            self.client = broadlink.rm(host=host, mac=self.mac, devtype=self.broadlinkType)
            temp = self.client.auth()
            print(temp)

            self.dsk = None
            #self.client.enter_learning()
            #self.client.sweep_frequency()
            
            self.loop = loop
            self.pub = pub
            #self.item = self.client.get_light_objects('name')

            device_dict = {}
            for device in self.devices:
                d_id = device.name #address
                #JS = json.loads(d_id)
                temp = {}
                for tag in device.tags:
                    addr = tag.name
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0, 0]
                    if tag.type in ["step","multiple"]:
                        value = int((int(tag.max) + int(tag.min))/2)
                        res = self.loop.run_until_complete(self.pub.set('tag:'+str(tag.full_name), value)) #await 
                        print(tag.name+" : "+str(value))
                    elif addr == "connection":
                        value = 1
                        res = self.loop.run_until_complete(self.pub.set('tag:'+str(tag.full_name), value)) #await 
                        print(tag.name+" : "+str(value))
                device_dict[d_id] = temp

            if "Daikin_Main_Remote" in device_dict:
                self.dsk = DaikinSkyair(self.client)

            print("finish set device_dict")
            print(device_dict)
            print(self.write_dict)
            
            self.device_dict = device_dict
            tagKeys = list(self.device_dict.keys())
            
            #asyncio.ensure_future(self.client.loop_forever()) #self.client.loop_start()
                
            count = 0
            while self.run:
                loop.run_until_complete(asyncio.sleep(0.2))
                temp = self.write_out() # check anything to write first
                                          
                                   
        
        finally:
            pub.close()
            print("End")

@app.task
def broadlink_driver(port_id = 5):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)

    #def __init__(self, address, port = None, mac = None, broadlinkType = None, devices = [], redis_client=None):
    conn_1 = Broadlink_Connection(port.detail["address"],port.detail["port"],port.detail["mac"],port.detail["broadlinkType"],[])

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

from drivers.Miio_Connector import findIt

class Miio_Connection(Connection):
    def __init__(self, address = None, devices = [], redis_client=None):
        Connection.__init__(self, address, devices, redis_client)
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
        self.write_dict[tag] = [True, value, self.write_dict[tag][2]]
        print("set write out to : ",tag," value ",value)

    # keep in case need to swap tag to webscoket
    def mappingTag(self, tag):
        my_map = {
                 }
        if tag in my_map:
            return my_map[tag]
        return 0

    def sentMiio(self, dev, addr, value, oldV):
        print("got ", dev, addr, value, oldV)
        #value = int(value)
        #print("pair with ", remote_code)
        if dev not in self.client:
            return False
        miiobject = self.client[dev]
        print(miiobject)
        if addr == "onoff":
            if value:
                miiobject.on()
            else:
                miiobject.off()
        elif addr == "set_target_humidity":
            miiobject.set_target_humidity(value)
        return True
		
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
            value = int(temp[1])
            result = False
            addr = t.device.address
            result = self.sentMiio(addr, t.address, value, temp[2])
            if result:
                res = self.loop.run_until_complete(self.pub.set('tag:'+str(t.full_name), value)) #await 
                print(t.name+" : "+str(value))
            self.write_dict[tn] = [False, 0, 0]

    def start(self, threadName = None):
        try:
            import asyncio
            print('connect')
            redis_host='redis://redis'
            loop=asyncio.get_event_loop()
            pub= loop.run_until_complete(aioredis.create_redis(redis_host))
            res = loop.run_until_complete(pub.auth('ictadmin')) #await 
            print('create redis client ok')

            self.client = findIt()
            if self.client == {}:
                from miio.airhumidifier import AirHumidifier
                self.client["192.168.2.13"] = AirHumidifier('192.168.2.13',"fe017238d8a532ea6d4058cc5aa5672d")
            print(self.client)
            
            self.loop = loop
            self.pub = pub

            device_dict = {}
            for device in self.devices:
                d_id = device.address
                #JS = json.loads(d_id)
                temp = {}
                for tag in device.tags:
                    addr = tag.address
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0, 0]
                    value = int(tag.min)
                    res = self.loop.run_until_complete(self.pub.set('tag:'+str(tag.full_name), value)) #await 
                    print(tag.name+" : "+str(value))
                device_dict[d_id] = temp

            print("finish set device_dict")
            print(device_dict)
            print(self.write_dict)
            
            self.device_dict = device_dict
            
            #asyncio.ensure_future(self.client.loop_forever()) #self.client.loop_start()
                
            count = 0
            while self.run:
                loop.run_until_complete(asyncio.sleep(0.2))
                temp = self.write_out() # check anything to write first
                                          
                                   
        
        finally:
            pub.close()
            print("End")

#from task_manager.models import scada_task
@app.task #(bind=True,base=scada_task,abortable=True)
def Miio_driver(port_id = 5):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)

    #class Miio_Connection(Connection):
    #def __init__(self, address = None, devices = [], redis_client=None):
    conn_1 = Miio_Connection(None,[])

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


@app.task
def tcp_modbus_client_driver():
    print('setting modbus tcp')
    
    # set up connections devices & tags 
 
    device = { # device Example from Django
      "id": 1,
      "device_tag": [
        {
          "id": 2,
          "chat_room": "Tower_Pump_System.Pump2.Pressure",
          "tag_type": 0,
          "name": "Pump2.Pressure",
          "full_name": "Tower_Pump_System.Pump2.Pressure",
          "address": "1",
          "value_type": "float",
          "type": "Analog Output Holding Registers",
          "scale": 0.2,
          "expression": None,
          "logable": False,
          "is_display": True,
          "device": 1
        },
        {
          "id": 1,
          "chat_room": "Tower_Pump_System.Pump1.Pressure",
          "tag_type": 0,
          "name": "Pump1.Pressure",
          "full_name": "Tower_Pump_System.Pump1.Pressure",
          "address": "0",
          "value_type": "float",
          "type": "Analog Output Holding Registers",
          "scale": 0.2,
          "expression": None,
          "logable": False,
          "is_display": True,
          "device": 1
        }
      ],
      "serial_number": "001",
      "name": "Tower_Pump_System",
      "address": "1",
      "geom": {
        "type": "Point",
        "coordinates": [
          11217929.919275,
          1543267.1838485
        ]
      },
      "interval": 1000,
      "port": 1
    }

    port = { # Port Example from Django
      "id": 1,
      "protocol": {
        "id": 1,
        "name": "ModbusTCP",
        "detail": {
          "port": "int",
          "address": "str"
        },
        "type": [
          {
            "type": "Discrete Output Coils",
            "value_type": ""
          },
          {
            "type": "Discrete Input Contacts",
            "value_type": ""
          },
          {
            "type": "Analog Input Registers",
            "value_type": ""
          },
          {
            "type": "Analog Output Holding Registers",
            "value_type": ""
          }
        ]
      },
      "name": "TCPtoVecon",
      "detail": {
        "port": 8899,
        "address": "192.168.2.66"
      }
    }

    conn_1 = ModBusTCP_Connection(port["detail"]["address"],port["detail"]["port"],[])

    print("Start")
   
    device_1 = Device(device["name"],device["address"],[])
    
    for t in device["device_tag"]:
        tag = Tag(t["id"], t["full_name"], t["address"], scale = t["scale"])
        print("add tag")
        print(tag)
        device_1.addTag(tag)

    conn_1.addDevice(device_1)
    
    conn_1.start()

def get_from_DB(port_id):
    from tag.models import  Device, Port
    from tag.models import  Tag as DB_Tag

    #port_id = 5
    print("get port id :",port_id)
    port = Port.objects.get(id = port_id)

    print("get port:",port)

    devices = Device.objects.filter(port = port)

    print("get devices:",devices)
	
    tag_name = DB_Tag.objects.filter(device__port=port).values_list('full_name',flat=True)
    # this is for test concept
    #temp_it = DB_Tag.objects.filter(full_name = "Switch_control.LightStatus1").values_list('full_name',flat=True)
    #temp_it_2 = DB_Tag.objects.filter(full_name = "Switch_control.LightStatus2").values_list('full_name',flat=True)
    #tag_name = tag_name.union(temp_it, temp_it_2)

    print("get tag_name:",tag_name)

    return port, devices, tag_name
@app.task
def tcp_modbus_client_driver_2():
    print('setting modbus tcp')

    port ,devices ,n = get_from_DB(port_id = 2)

    conn_1 = ModBusTCP_DB_Connection(port.detail["address"],port.detail["port"],[])

    print("Start")
   
    for d in devices:
        device_1 = Device(d.name,d.address,[])
    
        for t in d.device_tag.all():
            tag = Tag(t.id, t.full_name, t.address, scale = t.scale, tag_type = t.type)
            device_1.addTag(tag)

        conn_1.addDevice(device_1)
    
    conn_1.start()

@app.task
def tcp_modbus_client_driver_3():
    print('setting modbus tcp')

    port ,devices ,n = get_from_DB(port_id = 4)

    conn_1 = ModBusTCP_DB_Connection(port.detail["address"],port.detail["port"],[])

    print("Start")
   
    for d in devices:
        device_1 = Device(d.name,d.address,[])
    
        for t in d.device_tag.all():
            tag = Tag(t.id, t.full_name, t.address, scale = t.scale, tag_type = t.type)
            device_1.addTag(tag)

        conn_1.addDevice(device_1)
    
    conn_1.start()

@app.task
def tcp_modbus_client_driver_rw(port_id = 5):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)

    conn_1 = ModBusTCP_DB_Connection(port.detail["address"],port.detail["port"],[])

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
    
#class Socket_MsgPack_Connection(Connection):
#    def __init__(self, address, port = 1883, devices = [], redis_client=None):
@app.task
def socket_msgpack_client_driver_rw(port_id = 6):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)

    conn_1 = Socket_MsgPack_Connection(port.detail["address"],port.detail["port"],[])

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
    
    conn_1.start() #asyncio.ensure_future(conn_1.start())

    while True:
        #print('main loop')
        loop.run_until_complete(asyncio.sleep(1)) 
        #m.ReadAll()
    print("good bye naja.")
    
@app.task
def tcp_modbus_client_driver_rw_2(port_id = 7):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)

    conn_1 = ModBusTCP_DB_Connection(port.detail["address"],port.detail["port"],[])

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
    
# 001,ABCDEFGHIJKLMNO,3,H,20181122,095030,01,0000000,0000000,10.32,20.34,55.55,0,E,27.5,55,27.5,OK,#						
 
def MQTT_AbotIoT_decode(data):
    try:
        text = [0] + data.split(',')
        #temp = {}
    
        temp = { 'ID' : text[1],
                 'Customer_name'        : text[2],         'Motor_efficiency_Current'   : float(text[10]),
                 'Motor_number'         : text[3],         'Motor_efficiency_Volt'      : float(text[11]),
                 'level_password'       : text[4],         'Motor_efficiency_Power'     : float(text[12]),  
                 'Date'                 : text[5],         'Joint_movement_counter'     : text[13],   
                 'Time'                 : text[6],         'Faults_status'              : text[14],   
                 'IO_status'            : text[7],         'Temp'                       : float(text[15]),   
                 'Counter_number_of_function' : text[8],   'Hummidity'                  : int(text[16]),    
                 'Motor_position'       : text[9],         'Dust_PM'                    : float(text[17]), 
                 'Status message'       : text[18],                  
               }
        
    except x:
        print(x)
        temp = {}
    return temp

def MQTT_AbotIoT_encode(data):
    return ""

def MQTT_ICTLora_Subscribe_Decode(mqtt_sub_message):
    """ This function is used to decode a subscribed message into topic's dictionary which contain all tags of lora device.
        @argument : mqtt_sub_message (mqtt subscribe message)
        @return : topic_dict (dictionary of a given subscribed topic)
    """
    topic_dict = {}
    # Split comma as for each value field in LoRa message
    # split_comma = [( : ), ( : ), ...]
    split_comma = mqtt_sub_message.split(",")
    for i in range(len(split_comma)):
        try:
            # Split colon as for dictionary format within LoRa message
            # split_colon = [key, value]
            split_colon = split_comma[i].split(":")
            key   = split_colon[0]
            value = split_colon[1]

            # Update dictionary of LoRa device
            topic_dict.update({key:value})
        except Exception as e:
            print(e)

    return topic_dict
    
mqtt_decode_dict = {"AbotIoT" : MQTT_AbotIoT_decode,
                    "MQTT_ICTLora_Subscribe_Decode" : MQTT_ICTLora_Subscribe_Decode,
                    }
                    
mqtt_encode_dict = {"AbotIoT" : MQTT_AbotIoT_encode,
                    "MQTT_ICTLora_Subscribe_Decode" : MQTT_ICTLora_Subscribe_Decode,
                    }


@app.task
# class MQTT_DB_Connection(Connection):
#     def __init__(self, address, port = 1883, devices = [], topic = "", tranFunction = None, redis_client=None):
def mqtt_client_driver(port_id = 8):
    print('setting mqtt')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)
    
    func = mqtt_decode_dict[port.detail["function"]]
    
    if "login" not in port.detail or "password" not in port.detail or port.detail["login"] in [None, ""] or port.detail["password"] in [None, ""]:
        login = ""
        pw = ""
    else:
        login = port.detail["login"] 
        pw = port.detail["password"] 

    conn_1 = MQTT_DB_Connection(port.detail["address"],port.detail["port"],[],port.detail["topic"],func,login,pw)

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
   
@app.task
#class MQTT_Multi_Connection(Connection):
#    def __init__(self, address, devices = [], login = '', pw = '', redis_client=None):
def multi_mqtt_client_driver(port_id = 8):
    print('setting mqtt')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)
    
    #func = mqtt_decode_dict[port.detail["function"]]
    
    if "login" not in port.detail or "password" not in port.detail or port.detail["login"] in [None, "", "-"] or port.detail["password"] in [None, "", "-"]:
        login = ""
        pw = ""
    else:
        login = port.detail["login"] 
        pw = port.detail["password"] 

    conn_1 = MQTT_Multi_Connection(port.detail["address"],port.detail["port"],[],login,pw)

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
        
@app.task
# class OPC_UA_Connection(Connection):
#     def __init__(self, address, devices = [], redis_client=None):
def opc_ua_client_driver(port_id = 8):
    print('setting mqtt')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)
    
    conn_1 = OPC_UA_Connection(port.detail["address"],[])

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

from drivers.extra_driver.LGWebOS import LGTVWebOS
class LG_WEBOS_Connection(Connection):
    def __init__(self, address, port = 3000, mac = None, key = None, devices = [], redis_client=None):
        Connection.__init__(self, address, devices, redis_client)
        self.port = port
        self.mac = mac
        self.key = key
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

            if t.address == "on":
                addr = t.device.address
                if int(value):
                    self.client[addr].on()
                    asyncio.ensure_future(self.client[addr].run_loop(self.wrapper_callback(self.pub, self.device_dict[addr])))
                else:
                    asyncio.get_event_loop().run_until_complete(self.client[addr].off())
            elif t.address == "volume":
                addr = t.device.address
                asyncio.get_event_loop().run_until_complete(self.client[addr].audioSetVolume(int(value)))
            elif t.address == "mute":
                addr = t.device.address
                asyncio.get_event_loop().run_until_complete(self.client[addr].mute(int(value)))
            elif t.address == "channel":
                addr = t.device.address
                if int(value) > self.client[addr].channel:
                    asyncio.get_event_loop().run_until_complete(self.client[addr].inputChannelUp())
                else:
                    asyncio.get_event_loop().run_until_complete(self.client[addr].inputChannelDown())
            #if result:
            #    res = self.loop.run_until_complete(self.pub.set('tag:'+str(t.full_name), value)) #await 
            #    print(t.name+" : "+str(value))
            self.write_dict[tn] = [False, 0]
            #sleep(0.1)
    
    def wrapper_callback(self, pub, device):
        
        async def write_tag_callback(address, value):
            if address not in device:
                return
            full_name = device[address].full_name
            await pub.set('tag:'+str(full_name), value)
        
        return write_tag_callback

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

            self.client = {} # LG WEBOS

            device_dict = {}
            for device in self.devices:
                d_id = device.address
                temp = {}
                for tag in device.tags:
                    addr = tag.address
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0]
                device_dict[d_id] = temp
                self.client[d_id] = LGTVWebOS(self.mac, device.address, self.port, self.key)
                asyncio.ensure_future(self.client[d_id].run_loop(self.wrapper_callback(pub, device_dict[d_id])))

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
                if count % 30 != 1:
                    continue
                
                for d in self.device_dict:
                    l = self.client[d]
                    data = l.readValue()
                    for t in self.device_dict[d]:
                        if t not in data:
                            continue
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
def lg_webos_driver(port_id = 5):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)

    conn_1 = LG_WEBOS_Connection(port.detail["addr"],port.detail["port"],port.detail["mac"],port.detail["key"],[])

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

from drivers.extra_driver.Dyson import DysonFAN
class DysonFAN_Connection(Connection):
    def __init__(self, address, serial, username,password,language,devices = [], redis_client=None):
        Connection.__init__(self, address, devices, redis_client)
        self.serial = serial
        self.username = username
        self.password = password
        self.language = language
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
            if t.address == "speed":
                addr = t.device.address
                self.client[addr].setFan_speed(int(value))
            if t.address == "oscillation":
                addr = t.device.address
                self.client[addr].setOscillation(int(value))
            if t.address == "nightmode":
                addr = t.device.address
                self.client[addr].nightmode(int(value))
            if t.address == "timer":
                addr = t.device.address
                self.client[addr].setTimer(int(value))
            #if result:
            #    res = self.loop.run_until_complete(self.pub.set('tag:'+str(t.full_name), value)) #await 
            #    print(t.name+" : "+str(value))
            self.write_dict[tn] = [False, 0]
            #sleep(0.1)

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

            self.client = {} # LG WEBOS

            device_dict = {}
            for device in self.devices:
                d_id = device.address
                temp = {}
                for tag in device.tags:
                    addr = tag.address
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0]
                device_dict[d_id] = temp
                self.client[d_id] = DysonFAN(self.serial, device.address, self.username, self.password,self.language)
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
def DysonFAN_driver(port_id = 5):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)

    conn_1 = DysonFAN_Connection(port.detail["Address"],port.detail["Serial"],port.detail["Username"],port.detail["Password"],port.detail["Language"],[])

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

import string
from drivers.extra_driver.IndoorPositioningSystem_device import IndoorPositioningSystem_SCADA
class IndoorPositioningSystemDevice_Connection(Connection):
    def __init__(self, devices=[], redis_client=None):
        
        Connection.__init__(self, "", "", redis_client)
        self.devices = devices

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
            
            if t.address == "x_coord":
                addr = t.device.address
                self.client[addr].setXCoord(string(value))

            if t.address == "y_coord":
                addr = t.device.address
                self.client[addr].setYCoord(string(value))		
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
                d_name = device.name
                temp = {}
                for tag in device.tags:
                    addr = tag.address
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0]
                device_dict[d_id] = temp
                # ASK P'NAME
                self.client[d_id] = IndoorPositioningSystem_SCADA(IP_address=d_id, device_name=d_name)
                #self.client[d_id].on_connect()
            
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
                    #print("(Count = " + str(count) + " ) Ko Check Noi")
                    continue

                oldData = {}

                for d in self.device_dict:
                    l = self.client[d]
                    # print("PAYLOAD_1 : " + str(l.message_receive))

                    # l.start_MQTT_service()
                    # print("PAYLOAD_2 : " + str(l.message_receive))
                    # # print("PAYLOAD_3 : " + str(l.on_message()))
                    # print("PAYLOAD_4 : " + str(l.return_payload()))
                    # l.end_MQTT_service()

                    data_from_rasi_pi = l.getDataFromRASPI_SOCKET()
                    print("(models.py) TYPE OF DATA : " + str(type(data_from_rasi_pi)))
                    print(data_from_rasi_pi)
                    
                    if data_from_rasi_pi == -1:
                        continue
                    data = json.loads(data_from_rasi_pi)
                    for t in self.device_dict[d]:
                        if t not in data:
                            continue
                        if t in oldData and oldData[t] == data[t]:
                            continue

                        oldData[t] = data[t]
                        tag = self.device_dict[d][t]
                        print("TAG : " , tag)
                        value = data[t]

                        if value != None:
                            if self.mapping:
                                name = self.mappingTag(tag.full_name)
                                print("NAME_TAG : " + str(name))

                                res = loop.run_until_complete(pub.set('tag:'+str(name), value))
                            else:
                                res = loop.run_until_complete(pub.set('tag:'+str(tag.full_name), value)) #await 
                            print(tag.name+" : "+str(value))
                
        finally:
            pub.close()
            print("End")

@app.task
def IndoorPositioningSystemDevice_driver(port_id = 5):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop = asyncio.get_event_loop()
    print('setting modbus tcp')

    port ,devices ,n = get_from_DB(port_id = port_id)

    # ASK P'NAME
    conn_1 = IndoorPositioningSystemDevice_Connection([])

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




from drivers.extra_driver.gateopener import *



class Gateopener_Connection(Connection):
    def __init__(self, address, devices = [], redis_client=None):
        Connection.__init__(self, address, devices, redis_client)
        self.client = {}
        self.write_dict = {}
        self.device_dict = {}
        self.mapping = False
        self.pub = None
        self.loop = None
        self.item = None
        self.set_pos = 0
		
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
            
            """
            # These are write-type tags for v0.1 of gateopener driver
            if t.address == "set_pos":
                addr = t.device.address
                self.set_pos = int(value)
            elif t.address == "cmd_set_pos":
                addr = t.device.address
                self.client[addr].set_pos(int(self.set_pos))
            elif t.address == "cmd_reset_pos":
                addr = t.device.address
                self.client[addr].reset_pos()
            elif t.address == "cmd_stop":
                addr = t.device.address
                self.client[addr].force_stop()
            """
            
            # These are write-type tags for v0.2 of gateopener driver
            if t.address == "write_set_pos":
                addr = t.device.address
                self.set_pos = int(value)
                
            elif t.address == "set_pos":
                addr = t.device.address
                self.client[addr].set_pos(int(self.set_pos))
                
            elif t.address == "reset_pos":
                addr = t.device.address
                if int(value) != 0:
                    self.client[addr].reset_pos()
                    
            elif t.address == "stop":
                addr = t.device.address
                if int(value) != 0:
                    self.client[addr].force_stop()
                
            elif t.address == "full_close":
                addr = t.device.address
                self.client[addr].close_full()
                if int(value) != 0:
                    self.client[addr].force_stop()
                    
            elif t.address == "full_open":
                addr = t.device.address
                if int(value) != 0:
                    self.client[addr].open_full()
                    
            elif t.address == "manual_close":
                addr = t.device.address
                if int(value) != 0:
                    self.client[addr].close_manual()
                else:
                    self.client[addr].stop_manual()
                    
            elif t.address == "manual_open":
                addr = t.device.address
                if int(value) != 0:
                    self.client[addr].open_manual()
                else:
                    self.client[addr].stop_manual()    
            
            res = self.loop.run_until_complete(self.pub.set('tag:'+str(t.full_name), value)) #await 
            print(t.name+" : "+str(value))
            self.write_dict[tn] = [False, 0]
            #sleep(0.1)

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

            self.client = {}

            device_dict = {}
            for device in self.devices:
                d_id = device.address
                temp = {}
                for tag in device.tags:
                    addr = tag.address
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0]
                device_dict[d_id] = temp
                self.client[d_id] = Sonoff_Gateopener()
                self.client[d_id].config(ip_address=self.address)

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
                if count % 5 != 1:
                    continue
                
                for d in self.device_dict:
                    l = self.client[d]
                    data = l.read_all_tag()
                    print(data)
                    for t in self.device_dict[d]:
                        if t not in data:
                            continue
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
def gateopener_driver(port_id = 5):
    print('setting modbus tcp')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)

    conn_1 = Gateopener_Connection(port.detail["Address"],[])

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







from drivers.extra_driver.onvif_cctv import *



class Onvif_CCTV_Connection(Connection):
    def __init__(self, devices = [], redis_client=None):
        Connection.__init__(self, None, devices, redis_client)
        self.client = {}
        self.write_dict = {}
        self.device_dict = {}
        self.mapping = False
        self.pub = None
        self.loop = None
        self.item = None
        self.set_pos = 0
		
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
            
            if t.address == "move_up":
                addr = t.device.address
                if int(value) != 0:
                    self.client[addr].continuous_move('up')
                elif int(value) == 0:
                    self.client[addr].continuous_stop('y')
                    print("send ptz stop axis-y")

            elif t.address == "move_down":
                addr = t.device.address
                if int(value) != 0:
                    self.client[addr].continuous_move('down')
                elif int(value) == 0:
                    self.client[addr].continuous_stop('y')
                    print("send ptz stop axis-y")

            elif t.address == "move_left":
                addr = t.device.address
                if int(value) != 0:
                    self.client[addr].continuous_move('left')
                elif int(value) == 0:
                    self.client[addr].continuous_stop('x')
                    print("send ptz stop axis-x")

            elif t.address == "move_right":
                addr = t.device.address
                if int(value) != 0:
                    self.client[addr].continuous_move('right')
                elif int(value) == 0:
                    self.client[addr].continuous_stop('x')
                    print("send ptz stop axis-x")
                    
            elif t.address == "move_stop":
                addr = t.device.address
                if int(value) != 0:
                    self.client[addr].continuous_stop('x')
                    self.client[addr].continuous_stop('y')

            elif t.address == "zoom_in":
                addr = t.device.address
                if int(value) != 0:
                    self.client[addr].continuous_zoom('in')
                elif int(value) == 0:
                    self.client[addr].continuous_zoom_stop()

            elif t.address == "zoom_out":
                addr = t.device.address
                if int(value) != 0:
                    self.client[addr].continuous_zoom('out')
                elif int(value) == 0:
                    self.client[addr].continuous_zoom_stop()

            res = self.loop.run_until_complete(self.pub.set('tag:'+str(t.full_name), value)) #await 
            print(t.full_name+" : "+str(value))
            self.write_dict[tn] = [False, 0]
            #sleep(0.1)

    def start(self, threadName = None):
        try:
            import asyncio
            import datetime

            print('connect')
            redis_host='redis://redis'
            loop=asyncio.get_event_loop()
            pub = loop.run_until_complete(aioredis.create_redis(redis_host))
            res = loop.run_until_complete(pub.auth('ictadmin')) #await 
            print('create redis client ok')
            
            self.loop = loop
            self.pub = pub

            self.client = {}

            device_dict = {}
            for device in self.devices:
                d_id = device.address
                temp = {}
                for tag in device.tags:
                    addr = tag.address
                    temp[addr] = tag 
                    self.write_dict[tag.full_name] = [False, 0]
                device_dict[d_id] = temp
                self.client[d_id] = Onvif_Camera_Driver()
                self.client[d_id].config(ip_address=device.address, port=80, auth_user='admin', auth_pwd='Smarthome', onvif_user='onvif', onvif_pwd='scadatest1234')
                self.client[d_id].continuous_stop('x')
                self.client[d_id].continuous_stop('y')
                self.client[d_id].continuous_zoom_stop()

            print("finish set device_dict")
            print(device_dict)
            print(self.write_dict)
            
            self.device_dict = device_dict
            
            #asyncio.ensure_future(self.client.loop_forever()) #self.client.loop_start()

            # variable for datetime() scheduling for image snapshoot, rtsp timeout
            ret = False
            count = 0
            rtsp_fail_count = 0
            tick_max = 60
            schedule_period = 1
            ref_date  = datetime.datetime.now()
            ref_tick = ref_date.second
            update_tick_flag = False

            oldData = {}
            while self.run:
                loop.run_until_complete(asyncio.sleep(0.1))
                count+=1
                temp = self.write_out() # check anything to write first

                for d in self.device_dict:
                    l = self.client[d]
                    
                    # read ptz and status tag 
                    data = l.read_all_tag()
                    # read image
                    ret, image_base64 = l.snapshot_image(encode_flag=True)

                    # time diff calculation for scheduling
                    current_date  = datetime.datetime.now()
                    current_tick = current_date.second
                    diff_tick = current_tick - ref_tick
                    if diff_tick < 0:
                        diff_tick += tick_max

                    for t in self.device_dict[d]:
                        if t == 'image' and diff_tick >= schedule_period:
                            print('set image tag schedule!')
                            update_tick_flag = True
                            if ret:
                                rtsp_fail_count = 0
                                
                                # fullname extraction
                                # I don't know how to get tag's fullname without using self.device_dict[d]
                                tmp_fn = str(self.device_dict[d][t])
                                tmp_fn = tmp_fn.split('.')[:-1]
                                tag_fullname = tmp_fn[0] + '.' + tmp_fn[1] + '.' + tmp_fn[2]
                                """
                                tag_fullname = ''
                                for part in tmp_fn:
                                    tag_fullname = tag_fullname + part + '.'
                                tag_fullname = tag_fullname[:-1]
                                """
                                res = loop.run_until_complete(pub.set('tag:'+str(tag_fullname), image_base64)) #await
                                print(tag_fullname+' : '+str('capture complete')+str(' at time : ')+str(datetime.datetime.now()))
                                
                            else:
                                rtsp_fail_count += 1
                                if rtsp_fail_count >= 10:
                                    print("rtsp snap connect timeout")
                                    self.client[d_id].rtsp_reconnect()
                                    rtsp_fail_count = 0
                    
                        if t not in data:
                            continue

                        tag = self.device_dict[d][t]
                        value = data[t]
                        if d not in oldData:
                            oldData[d] = {}
                        if t not in oldData[d]:
                            oldData[d][t] = value
                        elif oldData[d][t] == value:
                            continue
                        else:
                            oldData[d][t] = value
                        
                        if value != None:
                            if self.mapping:
                                name = self.mappingTag(tag.full_name)
                                res = loop.run_until_complete(pub.set('tag:'+str(name), value))
                                print(tag.name+" : "+str(value))
                            else:
                                res = loop.run_until_complete(pub.set('tag:'+str(tag.full_name), value)) #await
                                print(tag.name+" : "+str(value))
                        
                    # update tick when diff tick >= period, update here to prevent error when there are many image tag
                    if update_tick_flag:
                        ref_date = datetime.datetime.now()
                        ref_tick = ref_date.second
                        update_tick_flag = False
                    
        finally:
            pub.close()
            print("End")

@app.task
def onvif_cctv_driver(port_id = 5):
    print('setting onvif cctv')
    from drivers.worker import ModbusPool as MP
    import asyncio
    loop=asyncio.get_event_loop()

    port ,devices ,n = get_from_DB(port_id = port_id)

    conn_1 = Onvif_CCTV_Connection([])

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





from drivers.canopen.canopen_worker import *
# from drivers.worker import *
# from alert.models import *
# from drivers.gige.worker import *
# #from drivers.another_driver import *

