import struct

class DTPFrame():
    FRAME_HEADER      = "!II"
    FRAME_HEADER_SIZE = 8
    def __init__(self, stream_id, message=b"", ACK=0, NAK=0, SRM=0, FIN=0, CRT=0):
        # STREAM ID
        self.stream_id = stream_id
        # MESSAGE
        self.message = message
        # FLAGS
        self.ACK     = ACK # Acknolwedge
        self.NAK     = NAK # Do not Acknolwedge
        self.SRM     = SRM # Create Stream
        self.FIN     = FIN # End
        self.CRT     = CRT # HANDSHAKE

    def encode(self):
        flags  = (self.CRT << 4) + (self.ACK<<3) + (self.NAK<<2) + (self.SRM << 1) + self.FIN
        header = struct.pack(self.FRAME_HEADER, flags, self.stream_id)
        return header + self.message

    def decode(raw_packet):
        header  = raw_packet[:DTPFrame.FRAME_HEADER_SIZE]
        message = raw_packet[DTPFrame.FRAME_HEADER_SIZE:]
        flags, stream_id = struct.unpack(DTPFrame.FRAME_HEADER, header)
        FIN = flags%2
        flags = flags//2
        SRM = flags%2
        flags = flags//2
        NAK = flags%2
        flags = flags//2
        ACK = flags%2
        flags = flags//2
        CRT = flags%2
        return DTPFrame(stream_id, message, ACK, NAK, SRM, FIN, CRT)
