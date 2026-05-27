import socket
import json
import threading
import time
import os

class SignalingServer:
    def __init__(self, config):
        self.config = config
        self.host = config['signaling_server']['host']
        self.port = config['signaling_server']['port']
        self.socket = None
        self.running = False
        self.clients = {}
        self.whitelist = []
        self.lock = threading.Lock()
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        
        self.load_whitelist()
    
    def load_whitelist(self):
        try:
            whitelist_path = os.path.join(self.base_dir, 'config', 'whitelist.json')
            with open(whitelist_path, 'r') as f:
                data = json.load(f)
                self.whitelist = data.get('devices', [])
        except Exception as e:
            self.whitelist = []
    
    def save_whitelist(self):
        try:
            whitelist_path = os.path.join(self.base_dir, 'config', 'whitelist.json')
            with open(whitelist_path, 'w') as f:
                json.dump({'devices': self.whitelist}, f, indent=2)
        except Exception as e:
            pass
    
    def add_to_whitelist(self, device_id):
        with self.lock:
            if device_id not in self.whitelist:
                self.whitelist.append(device_id)
                self.save_whitelist()
    
    def is_whitelisted(self, device_id):
        return device_id in self.whitelist
    
    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        
        self.running = True
        
        thread = threading.Thread(target=self._listen_loop, daemon=True)
        thread.start()
        
        while self.running:
            time.sleep(1)
    
    def _listen_loop(self):
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
                self._handle_message(data, addr)
            except Exception as e:
                if self.running:
                    pass
    
    def _handle_message(self, data, addr):
        try:
            message = json.loads(data.decode())
            action = message.get('action')
            device_id = message.get('device_id')
            payload = message.get('data', {})
            
            if action == 'register':
                self._handle_register(device_id, addr)
            
            elif action == 'find_peer':
                self._handle_find_peer(device_id, payload)
            
            elif action == 'offer':
                self._handle_offer(device_id, payload)
            
            elif action == 'answer':
                self._handle_answer(device_id, payload)
            
            elif action == 'add_whitelist':
                self._handle_add_whitelist(device_id, payload)
            
            elif action == 'query_whitelist':
                self._handle_query_whitelist(device_id, addr)
        
        except json.JSONDecodeError:
            pass
        except Exception as e:
            pass
    
    def _handle_register(self, device_id, addr):
        with self.lock:
            self.clients[device_id] = {
                'addr': addr,
                'last_seen': time.time()
            }
        
        response = {
            'action': 'registered',
            'data': {'success': True}
        }
        self._send_response(addr, response)
    
    def _handle_find_peer(self, device_id, payload):
        target_id = payload.get('target_id')
        
        with self.lock:
            if target_id in self.clients:
                peer_info = self.clients[target_id]
                response = {
                    'action': 'peer_found',
                    'data': {
                        'device_id': target_id,
                        'addr': peer_info['addr']
                    }
                }
                self._send_response(self.clients[device_id]['addr'], response)
            else:
                response = {
                    'action': 'peer_found',
                    'data': {'error': 'Peer not online'}
                }
                self._send_response(self.clients[device_id]['addr'], response)
    
    def _handle_offer(self, device_id, payload):
        target_id = payload.get('target_id')
        external_addr = payload.get('external_addr')
        
        with self.lock:
            if target_id in self.clients:
                response = {
                    'action': 'offer_received',
                    'data': {
                        'from_device_id': device_id,
                        'external_addr': external_addr
                    }
                }
                self._send_response(self.clients[target_id]['addr'], response)
    
    def _handle_answer(self, device_id, payload):
        target_id = payload.get('target_id')
        external_addr = payload.get('external_addr')
        
        with self.lock:
            if target_id in self.clients:
                response = {
                    'action': 'answer_received',
                    'data': {
                        'from_device_id': device_id,
                        'external_addr': external_addr
                    }
                }
                self._send_response(self.clients[target_id]['addr'], response)
    
    def _handle_add_whitelist(self, device_id, payload):
        new_device_id = payload.get('device_id')
        if new_device_id:
            self.add_to_whitelist(new_device_id)
            response = {
                'action': 'whitelist_added',
                'data': {'success': True}
            }
            with self.lock:
                if device_id in self.clients:
                    self._send_response(self.clients[device_id]['addr'], response)
    
    def _handle_query_whitelist(self, device_id, addr):
        response = {
            'action': 'whitelist_query',
            'data': {'devices': self.whitelist}
        }
        self._send_response(addr, response)
    
    def _send_response(self, addr, response):
        try:
            message = json.dumps(response).encode()
            self.socket.sendto(message, addr)
        except Exception as e:
            pass
    
    def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()

if __name__ == '__main__':
    import sys
    sys.path.insert(0, '../')
    
    config_path = os.path.join(os.path.dirname(__file__), '../config/app.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    server = SignalingServer(config)
    server.start()