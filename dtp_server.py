from socket import *
from dtp_frame import DTPFrame
import random

serverPort = 7500
serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind(("", serverPort))
LOSS_RATE = 0.3
AVG_DELAY = 2

print("The server is ready to handle requests")
while True:
    message, clientAddress = serverSocket.recvfrom(1024)
    packet = DTPFrame.decode(message)
    #print(f"FIN={packet.FIN}, SRM={packet.SRM}, NAK={packet.NAK}, ACK={packet.ACK}, CRT={packet.CRT}")
    if packet.CRT == 1:
        print(f"CREATED CONNECTION WITH: {clientAddress}")
        response = DTPFrame(0, message=b"hello", ACK=0, NAK=0, SRM=0, FIN=0, CRT=1)    
    else:
        print(f"Recieved message for stream {packet.stream_id}:")
        print(packet.message)
        ack = 1 if random.random() >= LOSS_RATE else 0

        message = packet.message.decode("ascii").lower().encode("ascii")
        response = DTPFrame(packet.stream_id, message=message, ACK=ack, NAK= not ack, SRM=0, FIN=packet.FIN)
    serverSocket.sendto(response.encode(),clientAddress)