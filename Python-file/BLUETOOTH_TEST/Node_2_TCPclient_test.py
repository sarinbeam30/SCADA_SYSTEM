import socket
import sys

HOST, PORT = "192.168.4.150", 20000
data = " ".join(sys.argv[1:])

# Create a socket (SOCK_STREAM means a TCP socket)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
if __name__ == "__main__":
    print("test")
    try:
        # Connect to server and send data
        sock.connect((HOST, PORT))
        sock.sendall(data + "\n")

        # Receive data from the server and shut down
        received = sock.recv(1024)
    finally:
        sock.close()
    print("Sent:     {}".format(data))
    print("Received: {}".format(received))