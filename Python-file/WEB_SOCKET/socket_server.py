import socket

s = socket.socket()
print ("Socket successfully created") 

port = 12300

s.bind(('', port))
print("socket bined to %s" %(port))

# put the socket into listening mode  
# listen mode 5 --> 5 connection keep waiting if the server is busy 
# and if a 6th-connection try to connect then connection is refused
s.listen(5)   
print ("socket is listening")

while True:
    # Establish connection with client.
    # Accept a connection. The socket must be bound to an address and listening for connection.
    # return value --> pair(conn, addr) 
    # conn = new socket object usable to send and receive data on the connection
    # addr = the address bound to the socket on the other end of the connection.

    c, addr = s.accept()
    print ('Got connection from', addr )

    # send a thank you message to the client.  
    c.send(b"Thank you for connecting with our web socket")  

    # Close the connection with the client  
    c.close() 