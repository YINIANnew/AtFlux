import os
import sys
import json
import time
import threading
import argparse

current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from common.network import P2PNode, SignalingClient, TCPSession
from common.crypto import CryptoManager, WhitelistManager
from common.file_share import FileShareManager, FileShareProtocol
from common.remote_desktop import ScreenCapture, InputSimulator, RemoteDesktopProtocol

class AtFluxClient:
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '../config/app.json')
        self.config = self._load_config(config_path)
        self.crypto_manager = CryptoManager(self.config)
        self.whitelist_manager = WhitelistManager(self.config)
        self.p2p_node = P2PNode(self.config)
        self.signaling_client = SignalingClient(self.config)
        self.file_share_manager = None
        self.remote_desktop = None
        
        self.device_id = self.crypto_manager.generate_device_id()
        self.connection_mode = None
        self.temp_key = None
        self.peer_device_id = None
        self.connected = False
        
        self._setup_handlers()
    
    def _load_config(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            return {}
    
    def _setup_handlers(self):
        self.signaling_client.on('registered', self._on_registered)
        self.signaling_client.on('peer_found', self._on_peer_found)
        self.signaling_client.on('offer_received', self._on_offer_received)
        self.signaling_client.on('answer_received', self._on_answer_received)
        self.signaling_client.on('whitelist_query', self._on_whitelist_query)
    
    def _on_registered(self, data):
        pass
    
    def _on_peer_found(self, data):
        if 'error' in data:
            return
        
        if self.connection_mode == 'whitelist':
            external_addr = self.p2p_node.discover_external_address()
            self.signaling_client.send_offer(data['device_id'], external_addr)
    
    def _on_offer_received(self, data):
        if self.connection_mode == 'whitelist':
            if not self.whitelist_manager.is_whitelisted(data['from_device_id']):
                return
            
            external_addr = self.p2p_node.discover_external_address()
            self.signaling_client.send_answer(data['from_device_id'], external_addr)
            
            self.peer_device_id = data['from_device_id']
            self._attempt_p2p_connection(data['external_addr'])
    
    def _on_answer_received(self, data):
        self.peer_device_id = data['from_device_id']
        self._attempt_p2p_connection(data['external_addr'])
    
    def _on_whitelist_query(self, data):
        pass
    
    def _attempt_p2p_connection(self, peer_addr):
        self.p2p_node.init_udp_socket()
        
        success = self.p2p_node.punch_hole(peer_addr)
        
        if success:
            self.connected = True
            self._start_tcp_session()
        else:
            self.p2p_node.connect_via_relay(self.config['signaling_server']['host'], 
                                            self.config['signaling_server']['port'])
    
    def _start_tcp_session(self):
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            tcp_socket.connect((self.p2p_node.peer_addr[0], self.p2p_node.local_port + 1))
            self.tcp_session = TCPSession(tcp_socket, self.p2p_node.peer_addr, self.crypto_manager)
            
            self.file_share_manager = FileShareManager(self.config, self.tcp_session)
        
        except Exception as e:
            pass
    
    def start_with_temp_key(self, key):
        self.connection_mode = 'temp_key'
        self.temp_key = key
        self._connect_with_key()
    
    def start_with_whitelist(self):
        self.connection_mode = 'whitelist'
        
        self.signaling_client.connect()
        self.signaling_client.register(self.device_id)
        
        listen_thread = threading.Thread(target=self.signaling_client.listen, daemon=True)
        listen_thread.start()
        
        time.sleep(1)
        
        for device_id in self.whitelist_manager.get_all_devices():
            self.signaling_client.find_peer(device_id)
            time.sleep(1)
    
    def _connect_with_key(self):
        pass
    
    def add_to_whitelist(self, device_id):
        self.whitelist_manager.add_device(device_id)
    
    def remove_from_whitelist(self, device_id):
        self.whitelist_manager.remove_device(device_id)
    
    def list_shared_files(self, path=''):
        if not self.file_share_manager:
            return
        
        result = self.file_share_manager.list_directory(path)
        print(json.dumps(result, indent=2))
    
    def download_file(self, remote_path, local_path):
        if not self.file_share_manager:
            return
        
        data, error = self.file_share_manager.download_file(remote_path)
        if error:
            return
        
        try:
            with open(local_path, 'wb') as f:
                f.write(data)
        except Exception as e:
            pass
    
    def upload_file(self, local_path, remote_name):
        if not self.file_share_manager:
            return
        
        try:
            with open(local_path, 'rb') as f:
                data = f.read()
            
            error = self.file_share_manager.upload_file(remote_name, data)
        
        except Exception as e:
            pass
    
    def start_remote_desktop(self):
        if not self.tcp_session:
            return
        
        self.remote_desktop = RemoteDesktopProtocol(self.tcp_session, self.crypto_manager)
        
        screen_capture = ScreenCapture(self.config)
        screen_capture.start(callback=self._on_frame_captured)
        
        input_simulator = InputSimulator()
        
        def handle_input():
            while self.connected:
                try:
                    cmd = input()
                    parts = cmd.strip().split()
                    if not parts:
                        continue
                    
                    if parts[0] == 'move':
                        x, y = map(int, parts[1].split(','))
                        self.remote_desktop.send_mouse_move(x, y)
                    elif parts[0] == 'click':
                        button = parts[1] if len(parts) > 1 else 'left'
                        pressed = parts[2] != 'up' if len(parts) > 2 else True
                        self.remote_desktop.send_mouse_click(button, pressed)
                    elif parts[0] == 'key':
                        key_code = int(parts[1]) if len(parts) > 1 else 0
                        pressed = parts[2] != 'up' if len(parts) > 2 else True
                        self.remote_desktop.send_key_event(key_code, pressed)
                    elif parts[0] == 'exit':
                        break
                except Exception as e:
                    pass
        
        input_thread = threading.Thread(target=handle_input, daemon=True)
        input_thread.start()
    
    def _on_frame_captured(self, frame):
        if self.remote_desktop:
            compressed = ScreenCapture(self.config).compress_frame(frame)
            if compressed:
                self.remote_desktop.send_frame(compressed)

def main():
    parser = argparse.ArgumentParser(description='AtFlux - P2P Cross-Network Collaboration Tool')
    parser.add_argument('--mode', choices=['whitelist', 'temp_key'], default='whitelist')
    parser.add_argument('--key', help='Temporary key')
    parser.add_argument('--device-id', help='Target device ID')
    parser.add_argument('--add-whitelist', help='Add device to whitelist')
    parser.add_argument('--remove-whitelist', help='Remove device from whitelist')
    parser.add_argument('--list-files', action='store_true')
    parser.add_argument('--download', nargs=2, metavar=('remote_path', 'local_path'))
    parser.add_argument('--upload', nargs=2, metavar=('local_path', 'remote_name'))
    parser.add_argument('--remote-desktop', action='store_true')
    
    args = parser.parse_args()
    
    client = AtFluxClient()
    
    if args.add_whitelist:
        client.add_to_whitelist(args.add_whitelist)
        return
    
    if args.remove_whitelist:
        client.remove_from_whitelist(args.remove_whitelist)
        return
    
    if args.mode == 'whitelist':
        client.start_with_whitelist()
    elif args.mode == 'temp_key':
        if not args.key:
            return
        client.start_with_temp_key(args.key)
    
    time.sleep(2)
    
    if args.list_files:
        client.list_shared_files()
    
    if args.download:
        client.download_file(args.download[0], args.download[1])
    
    if args.upload:
        client.upload_file(args.upload[0], args.upload[1])
    
    if args.remote_desktop:
        client.start_remote_desktop()
    
    while True:
        time.sleep(1)

if __name__ == '__main__':
    import socket
    main()