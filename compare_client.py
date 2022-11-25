from dtp_client import DTPSender
from socket import *
import string
import random

def random_string(length, critical=True):
    letters = "abcdefghijklmnopqrstuvwxyz"
    rand_string = ''.join(random.choice(letters) for _ in range(length-1)) + '1' if critical else '0'  
    return rand_string

# CONSTANTS
CRITICAL_FRAGMENTS = 0.3
NUMBER_FRAGMENTS   = 10000
FRAGMENT_LENGTH    = 55000

NUM_CRITICAL_FRAGMENTS = int(NUMBER_FRAGMENTS * CRITICAL_FRAGMENTS)
NUM_ORDINARY_FRAGMENTS = int(NUMBER_FRAGMENTS - NUM_CRITICAL_FRAGMENTS)

# CONFIG
DTP_DST_IP   = "127.0.0.1"
DTP_DST_PORT = 7500
DTP_SRC_IP   = "127.0.0.1"
DTP_SRC_PORT = 7501
TCP_DST_IP   = "127.0.0.1"
TCP_DST_PORT = 7400
TCP_SRC_IP   = "127.0.0.1"
TCP_SRC_PORT = 7401

print(f"""
CONFIG:
    CRITICAL_FRAGMENTS: {CRITICAL_FRAGMENTS}
    NUMBER_FRAGMENTS: {NUMBER_FRAGMENTS}
    FRAGMENT_LENGTH: {FRAGMENT_LENGTH}
""")


# Generate fragments
frag_id = 0
fragments = []
for i in range(NUM_CRITICAL_FRAGMENTS):
    frag = (frag_id, random.randint(6, 10), random_string(FRAGMENT_LENGTH, critical=True))
    fragments.append(frag)
    frag_id += 1
for i in range(NUM_ORDINARY_FRAGMENTS):
    frag = (frag_id, random.randint(0, 5), random_string(FRAGMENT_LENGTH, critical=False))
    fragments.append(frag)
    frag_id += 1
# Randomize
random.shuffle(fragments)

# DTP SEND
# Init sender
print("DTP")
dtpsender = DTPSender(DTP_DST_IP, DTP_DST_PORT, DTP_SRC_IP, DTP_SRC_PORT)
stream_list = []
# Send
for frag_id, priority, block in fragments:
    print(f"SENDING FRAG:{frag_id}")
    s = dtpsender.send_request(block, priority)
    stream_list.append(s)
# Wait
for s in stream_list:
    s.get_response()
dtpsender.close()

# TCP SEND
print("TCP")
tcp_socket = socket(AF_INET, SOCK_STREAM)
tcp_socket.connect((TCP_DST_IP,TCP_DST_PORT))
# tcp_socket.send(fragments[0][2].encode())
# tcp_socket.recv(1024)
# tcp_socket.close()
for frag_id, _, block in fragments:
    print(f"SENDING FRAG:{frag_id}")

    while len(block) > 0:
        b = block[:1024]
        tcp_socket.send(b.encode())
        r = tcp_socket.recv(1024).decode()
        if r == "not ok":
            continue
        block = block[1024:]
tcp_socket.close()