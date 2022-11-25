import struct
import socket
import heapq
from dtp_frame import DTPFrame
from threading import Thread, Lock, Semaphore

class DTPBlockStream():
    STATUS_READY     = 1
    STATUS_COMPLETE  = 2
    STATUS_RESET     = 3

    def __init__(self, stream_id, block_message):
        self.stream_id = stream_id
        self.status    = self.STATUS_READY
        self.message   = block_message
        self.response  = ""
        self.mutex     = Lock()
        self.start     = True
        self.mutex.acquire()

    def __lt__(self, other):
        return self.stream_id < other.stream_id

    def get_next_frame(self, message_size):
        message = bytes(self.message[:message_size-DTPFrame.FRAME_HEADER_SIZE], 'ascii')
        SRM = self.start
        FIN = len(self.message[message_size-DTPFrame.FRAME_HEADER_SIZE:]) == 0
        frame = DTPFrame(self.stream_id, message=message, ACK=0, NAK=0, SRM=SRM, FIN=FIN)
        self.start = False
        return frame

    def confirm_next_frame(self, message_size):
        self.message = self.message[message_size-DTPFrame.FRAME_HEADER_SIZE:]
        if len(self.message) == 0:
            self.set_complete()

    def add_response(self, response):
        self.response+=response

    def set_complete(self):
        self.status    = self.STATUS_COMPLETE
        self.mutex.release()

    def set_reset(self):
        self.status    = self.STATUS_RESET
        self.mutex.release()

    def get_response(self):
        self.mutex.acquire()
        return self.response

    def is_completed(self):
        return self.status == self.STATUS_COMPLETE

class DTPSender():
    MESSAGE_SIZE = 1024
    TYPE_CLIENT  = 0
    TYPE_SERVER  = 1
    CONNECTION_TIMEOUT = 2

    def __init__(self, dst_ip, dst_port, src_ip, src_port, conntype=TYPE_CLIENT):
        self.active = True
        # UDP  Config
        self.dst_ip       = dst_ip
        self.dst_port     = dst_port
        self.src_ip       = src_ip
        self.src_port     = src_port
        # QUIC Config
        self.conntype     = conntype
        self.sid          = conntype # Client initiated even. Server initiated odd
        self.streams      = {}
        self.squeue       = []
        self.next_stream = None
        self.next_stream_priority = None
        # Init UDP
        self.sock         = socket.socket(socket.AF_INET,    # Internet
                                       socket.SOCK_DGRAM) # UDP
        self.sock.bind((self.src_ip, self.src_port))
        # MUTEX config
        self.mutex_streams = Lock()
        self.mutex_queue   = Lock()
        self.mutex_next   = Lock()
        # SEMAPHORE config
        self.sempahore_queue     = Semaphore(value=0)
        self.sempahore_sender    = Semaphore(value=0)
        self.sempahore_scheduler = Semaphore(value=1)

        # Quic Handshake
        self.handshake()

        # Scheduler in background
        self.scheduler_thread = Thread(target=self.scheduler)
        # Sender in background
        self.sender_thread = Thread(target=self.sender)
        # Start threads
        self.sender_thread.start()
        self.scheduler_thread.start()

    def add_stream_to_queue(self, stream, priority):
        # TODO: improve scheduling
        self.mutex_queue.acquire()    # PROTECT QUEUE
        heapq.heappush(self.squeue, (-priority,stream))
        self.sempahore_queue.release()# Increase count queue
        self.mutex_queue.release()    # RELEASE QUEUE


    def get_next_stream_from_queue(self):
        # TODO: improve scheduling
        self.mutex_queue.acquire()
        negpriority, stream,  = heapq.heappop(self.squeue)
        self.mutex_queue.release()
        return stream, -negpriority

    def sender(self):
        while True:
            # print("send")
            # # Wait for SENDER    (set by scheduler)
            self.sempahore_sender.acquire()
            if not self.active:
                break
            # >>> Consume next (send and recieve) <<<
            self.mutex_next.acquire()     # PROTECT NEXT

            # -% SEND AND RECIEVE %-
            # Get message
            frame = self.next_stream.get_next_frame(self.MESSAGE_SIZE)
            message = frame.encode()
            # Send
            #print("DEBUG: MESSAGE SIZE:", len(message))
            self.sock.sendto(message, ((self.dst_ip, self.dst_port)))
            #print(f"Sending SID:{self.next_stream.stream_id} ...")
            # Recieve
            self.sock.settimeout(self.CONNECTION_TIMEOUT)
            try:
                response = self.sock.recv(self.MESSAGE_SIZE+2)
                response_frame = DTPFrame.decode(response)
                if response_frame.ACK:
                    self.next_stream.add_response(response_frame.message.decode("ascii"))
                    self.next_stream.confirm_next_frame(self.MESSAGE_SIZE)
                    #print(f"Recieved ACK response SID:{self.next_stream.stream_id}")
                elif response_frame.NAK:
                    #print(f"Recieved NAK response SID:{self.next_stream.stream_id}")
                    pass
                else:
                    #print(f"Recieved unexpected response SID:{self.next_stream.stream_id}")
                    pass
            except:
                print(f"Timeout SID:{self.next_stream.stream_id}")
            # If not complete, add back to queue
            if self.next_stream.is_completed():  
                #print(f"Sending completed SID:{self.next_stream.stream_id}")
                pass
            else:
                self.add_stream_to_queue(self.next_stream, self.next_stream_priority)
                #print(f"Sending incomplete SID:{self.next_stream.stream_id}")
            # ------------------
            
            self.mutex_next.release()     # RELEASE NEXT
            # Awake scheduler
            self.sempahore_scheduler.release()

    def scheduler(self):
        while True:
            # Wait dor SCHEDULER (set by sender)

            self.sempahore_scheduler.acquire()
            if not self.active:
                    break
            # Wait for user input

            self.sempahore_queue.acquire()

            if not self.active:
                    break
 
            # >>> Consume queue <<<
            self.mutex_next.acquire()
            self.next_stream, self.next_stream_priority = self.get_next_stream_from_queue()
            self.mutex_next.release()
            # Awake sender
            self.sempahore_sender.release()

    def handshake(self):
        # Send Hello/Crypto (SIMULATION)
        message = DTPFrame(0, message=b"hello", ACK=0, NAK=0, SRM=0, FIN=0, CRT=1)
        self.sock.sendto(message.encode(), (self.dst_ip, self.dst_port))
        response = self.sock.recv(self.MESSAGE_SIZE)
        return True
    
    def send_request(self, block_message, priority):
        # $ --- MUTEX ACQUIRE --- $
        self.mutex_streams.acquire()
        # $ --------------------- $

        # >>> CRITICAL SECTION START <<<
        # Get stream id
        sid = self.sid
        self.sid += 2
        # Create stream  
        stream = DTPBlockStream(sid, block_message)
        self.streams[sid] = stream
        # >>> CRITICAL SECTION END   <<<

        # $ --- MUTEX RELEASE --- $
        self.mutex_streams.release()
        # $ --------------------- $
        
        # Produce for scheduler
        self.add_stream_to_queue(stream, priority)      

        # Return stream obj
        return stream


    def close(self):
        self.active = False
        self.sempahore_sender.release()
        self.sempahore_scheduler.release()
        self.sempahore_queue.release()
        #print("quito los sems")
        self.sender_thread.join()
        self.scheduler_thread.join()
        #print("terminaron las threads")
        print("CLOSING CONNECTION")


    
if __name__ == "__main__":
    dst_ip   = "127.0.0.1"
    dst_port = 7500
    src_ip   = "127.0.0.1"
    src_port = 7501
    sender = DTPSender(dst_ip, dst_port, src_ip, src_port)
    msg1 = sender.send_request("Mensaje 1", 1)
    msg2 = sender.send_request("Mensaje 2 LARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXTLARGETEXT", 2)
    msg3 = sender.send_request("Mensaje 3", 10)
    print("M1")
    print(msg1.get_response())
    print("M2")
    print(msg2.get_response())
    print("M3")
    print(msg3.get_response())
    sender.close()



