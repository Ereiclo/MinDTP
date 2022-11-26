from socket import *
from config import *

import random
import time

serverSocket = socket(AF_INET,SOCK_STREAM)
serverSocket.bind((TCP_DST_IP,TCP_DST_PORT))
serverSocket.listen(1)
print("The server is ready to handle requests")



AVG_DELAY = 2
# Fragments consts
LOSS_RATE = 0.3


# Counts
COUNT_ACTUAL_CP      = 0
COUNT_ACTUAL_TP      = 0
START                = 0
# Time
TIME_START           = None 
TIME_FINISH_CRITICAL = None 
TIME_FINISH_TOTAL    = None










connectionSocket, addr = serverSocket.accept()


while True:


    mess = connectionSocket.recv(1024).decode('ascii')

    if not START:
        START       = 1
        TIME_START = time.time()


    message = "" 



    # ack = "ok" if random.random() >= LOSS_RATE else "not ok"

    ack = "ok"

    # print(mess)

    message = ack.encode("ascii")
    connectionSocket.send(message)

    if ack == "not ok":
        continue

    #if mess[-1] == "0" or mess[-1] == "1":
    #    print(COUNT_ACTUAL_TP,COUNT_ACTUAL_CP)

    COUNT_ACTUAL_CP += ((mess[-1] == "1"))
    COUNT_ACTUAL_TP += ((mess[-1] == "1") or (mess[-1] == "0"))


    if COUNT_ACTUAL_CP == NUM_CRITICAL_FRAGMENTS and TIME_FINISH_CRITICAL is None:
        TIME_FINISH_CRITICAL = time.time()
    if COUNT_ACTUAL_TP == NUMBER_FRAGMENTS:
        TIME_FINISH_TOTAL = time.time()
        break



print(COUNT_ACTUAL_CP)
print(COUNT_ACTUAL_TP)


print(f"(TCP) Time elapsed to recieve all critical frames: {TIME_FINISH_CRITICAL - TIME_START}" )
print(f"(TCP) Time elapsed to recieve all frames: {TIME_FINISH_TOTAL - TIME_START}" )

connectionSocket.close()
