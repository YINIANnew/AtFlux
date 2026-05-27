import socket
import struct
import threading
import time
import select
import json

class STUNClient:
    def __init__(self, config):
        self.config = config
        self.stun_host = config['stun_server']['host']
        self.stun_port = config['stun_server']['port']
        self.socket = None
    
    def create_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.settimeout(5)
    
    def send_stun_request(self):
        transaction_id = b'\x21\x12\xa4\x42\x42\x12\xa4\x42\x42\x12\xa4\x42'
        message_type = struct.pack('!H', 0x0001)
        message_length = struct.pack('!H', 0x0000)
        request = message_type + message_length + transaction_id
        
        try:
            self.socket.sendto(request, (self.stun_host, self.stun_port))
            data, addr = self.socket.recvfrom(1024)
            return self.parse_stun_response(data)
        except Exception as e:
            return None
    
    def parse_stun_response(self, data):
        if len(data) < 20:
            return None
        
        message_type = struct.unpack('!H', data[0:2])[0]
        message_length = struct.unpack('!H', data[2:4])[0]
        
        if message_type != 0x0101:
            return None
        
        attributes = data[20:20 + message_length]
        i = 0
        while i < len(attributes):
            attr_type = struct.unpack('!H', attributes[i:i+2])[0]
            attr_length = struct.unpack('!H', attributes[i+2:i+4])[0]
            attr_value = attributes[i+4:i+4+attr_length]
            
            if attr_type == 0x0001:
                port = struct.unpack('!H', attr_value[2:4])[0]
                ip_bytes = attr_value[4:8]
                ip = socket.inet_ntoa(ip_bytes)
                return (ip, port)
            
            i += 4 + attr_length
        
        return None
    
    def get_external_address(self):
        self.create_socket()
        result = self.send_stun_request()
        self.socket.close()
        return result

class P2PNode:
    def __init__(self, config):
        self.config = config
        self.local_port = config['network']['local_port']
        self.max_packet_size = config['network']['max_packet_size']
        self.connection_timeout = config['network']['connection_timeout']
        self.retry_interval = config['network']['retry_interval']
        
        self.udp_socket = None
        self.tcp_socket = None
        self.external_addr = None
        self.peer_addr = None
        self.connected = False
        self.use_relay = False
        
        self.message_handlers = {}
        self.running = False
        self.thread = None
    
    def init_udp_socket(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.bind(('0.0.0.0', self.local_port))
    
    def init_tcp_socket(self):
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind(('0.0.0.0', self.local_port + 1))
        self.tcp_socket.listen(5)
    
    def discover_external_address(self):
        stun_client = STUNClient(self.config)
        self.external_addr = stun_client.get_external_address()
        return self.external_addr
    
    def send_udp_packet(self, data, addr=None):
        if addr is None:
            addr = self.peer_addr
        if self.udp_socket and addr:
            try:
                self.udp_socket.sendto(data, addr)
                return True
            except Exception as e:
                return False
        return False
    
    def punch_hole(self, peer_external_addr):
        self.peer_addr = peer_external_addr
        
        for i in range(5):
            self.send_udp_packet(b'PUNCH', peer_external_addr)
            time.sleep(0.5)
        
        self.udp_socket.settimeout(3)
        try:
            data, addr = self.udp_socket.recvfrom(1024)
            if data == b'PUNCH_ACK':
                self.peer_addr = addr
                self.connected = True
                self.use_relay = False
                return True
        except socket.timeout:
            return False
        
        return False
    
    def connect_via_relay(self, relay_addr):
        self.peer_addr = relay_addr
        self.use_relay = True
        self.connected = True
        return True
    
    def register_handler(self, message_type, handler):
        self.message_handlers[message_type] = handler
    
    def run(self):
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
    
    def _run_loop(self):
        while self.running:
            try:
                ready, _, _ = select.select([self.udp_socket], [], [], 1)
                if ready:
                    data, addr = self.udp_socket.recvfrom(self.max_packet_size)
                    self._handle_message(data, addr)
            except Exception as e:
                if self.running:
                    pass
    
    def _handle_message(self, data, addr):
        if len(data) < 4:
            return
        
        msg_type = struct.unpack('!I', data[:4])[0]
        payload = data[4:]
        
        if msg_type in self.message_handlers:
            self.message_handlers[msg_type](payload, addr)
    
    def send_message(self, msg_type, payload):
        header = struct.pack('!I', msg_type)
        data = header + payload
        return self.send_udp_packet(data)
    
    def close(self):
        self.running = False
        if self.udp_socket:
            self.udp_socket.close()
        if self.tcp_socket:
            self.tcp_socket.close()

class TCPSession:
    def __init__(self, sock, addr, crypto_manager=None):
        self.socket = sock
        self.addr = addr
        self.crypto_manager = crypto_manager
        self.buffer = b''
        self.running = True
        self.thread = threading.Thread(target=self._recv_loop, daemon=True)
        self.thread.start()
    
    def _recv_loop(self):
        while self.running:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                self.buffer += data
                self._process_buffer()
            except Exception as e:
                break
    
    def _process_buffer(self):
        while len(self.buffer) >= 4:
            length = struct.unpack('!I', self.buffer[:4])[0]
            if len(self.buffer) >= 4 + length:
                msg = self.buffer[4:4+length]
                self.buffer = self.buffer[4+length:]
                if self.crypto_manager:
                    msg = self.crypto_manager.decrypt_with_aes(msg)
                self.on_message(msg)
            else:
                break
    
    def send(self, data):
        if self.crypto_manager:
            data = self.crypto_manager.encrypt_with_aes(data)
        length = struct.pack('!I', len(data))
        self.socket.sendall(length + data)
    
    def on_message(self, msg):
        pass
    
    def close(self):
        self.running = False
        self.socket.close()

class SignalingClient:
    def __init__(self, config):
        self.config = config
        self.signaling_host = config['signaling_server']['host']
        self.signaling_port = config['signaling_server']['port']
        self.socket = None
        self.device_id = None
        self.handlers = {}
    
    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.settimeout(10)
    
    def send(self, action, data):
        message = json.dumps({
            'action': action,
            'device_id': self.device_id,
            'data': data
        }).encode()
        self.socket.sendto(message, (self.signaling_host, self.signaling_port))
    
    def register(self, device_id):
        self.device_id = device_id
        self.send('register', {'device_id': device_id})
    
    def find_peer(self, target_id):
        self.send('find_peer', {'target_id': target_id})
    
    def send_offer(self, target_id, external_addr):
        self.send('offer', {
            'target_id': target_id,
            'external_addr': external_addr
        })
    
    def send_answer(self, target_id, external_addr):
        self.send('answer', {
            'target_id': target_id,
            'external_addr': external_addr
        })
    
    def listen(self):
        while True:
            try:
                data, addr = self.socket.recvfrom(4096)
                message = json.loads(data.decode())
                action = message.get('action')
                if action in self.handlers:
                    self.handlers[action](message.get('data', {}))
            except Exception as e:
                pass
    
    def on(self, action, handler):
        self.handlers[action] = handler