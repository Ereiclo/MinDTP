from socket import *
from config import *
import time
from dtp_frame import DTPFrame
import random

serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind((DTP_DST_IP, DTP_DST_PORT))
LOSS_RATE = 0

# Counts
COUNT_ACTUAL_CP      = 0
COUNT_ACTUAL_TP      = 0
START                = 0
# Time
TIME_START           = None 
TIME_FINISH_CRITICAL = None 
TIME_FINISH_TOTAL    = None
streams_confirmed = {}
print("The server is ready to handle requests")
while True:
    message, clientAddress = serverSocket.recvfrom(1024)
    if not START:
        START       = 1
        print("STARTED TIMER")
        TIME_START = time.time()

    packet = DTPFrame.decode(message)
    if packet.CRT == 1:
        print(f"CREATED CONNECTION WITH: {clientAddress}")
        response = DTPFrame(0, message=b"hello", ACK=0, NAK=0, SRM=0, FIN=0, CRT=1)    
    else:
        #print(f"Recieved message for stream {packet.stream_id}:")
        #print(packet.message)
        message = "" 
        ack = 1 if random.random() >= LOSS_RATE else 0
        if not ack:
            message = "not ok".encode("ascii")
        else:
            message = "ok".encode("ascii")
            #if packet.FIN:
            #    print(packet.message.decode("ascii")[-1] == "1")

            if packet.stream_id not in streams_confirmed:
                if packet.FIN:
                    COUNT_ACTUAL_CP += ((packet.message.decode("ascii")[-1] == "1"))
                    streams_confirmed[packet.stream_id] = True 
                    COUNT_ACTUAL_TP += 1 

        response = DTPFrame(packet.stream_id, message=message, ACK=ack, NAK= not ack, SRM=0, FIN=packet.FIN)
    serverSocket.sendto(response.encode(),clientAddress)
    if COUNT_ACTUAL_CP == NUM_CRITICAL_FRAGMENTS and TIME_FINISH_CRITICAL is None:
        TIME_FINISH_CRITICAL = time.time()
    if COUNT_ACTUAL_TP == NUMBER_FRAGMENTS:
        TIME_FINISH_TOTAL = time.time()
        break



print(f"(DTP) Time elapsed to recieve all critical frames: {TIME_FINISH_CRITICAL - TIME_START}" )
print(f"(DTP) Time elapsed to recieve all frames: {TIME_FINISH_TOTAL - TIME_START}" )


while True:

    message, clientAddress = serverSocket.recvfrom(1024)
    ack = 1
    response = DTPFrame(packet.stream_id, message=message, ACK=ack, NAK= not ack, SRM=0, FIN=1)
    serverSocket.sendto(response.encode(),clientAddress)
 

