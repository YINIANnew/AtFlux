import os
import json
import struct
import hashlib

class FileShareManager:
    def __init__(self, config, session):
        self.config = config
        self.session = session
        self.shared_root = config['file_share']['default_root']
        self.max_file_size = config['file_share']['max_file_size']
        self.buffer_size = config['file_share']['buffer_size']
        
        os.makedirs(self.shared_root, exist_ok=True)
    
    def set_shared_root(self, path):
        if os.path.isdir(path):
            self.shared_root = os.path.abspath(path)
            return True
        return False
    
    def list_directory(self, path=''):
        full_path = os.path.join(self.shared_root, path)
        
        if not full_path.startswith(self.shared_root):
            return {'error': 'Access denied'}
        
        if not os.path.exists(full_path):
            return {'error': 'Path not found'}
        
        if not os.path.isdir(full_path):
            return {'error': 'Not a directory'}
        
        items = []
        for name in os.listdir(full_path):
            item_path = os.path.join(full_path, name)
            is_dir = os.path.isdir(item_path)
            items.append({
                'name': name,
                'type': 'directory' if is_dir else 'file',
                'size': os.path.getsize(item_path) if not is_dir else 0,
                'mtime': os.path.getmtime(item_path)
            })
        
        return {'items': items}
    
    def get_file_info(self, file_path):
        full_path = os.path.join(self.shared_root, file_path)
        
        if not full_path.startswith(self.shared_root):
            return {'error': 'Access denied'}
        
        if not os.path.exists(full_path):
            return {'error': 'File not found'}
        
        if os.path.isdir(full_path):
            return {'error': 'Not a file'}
        
        file_size = os.path.getsize(full_path)
        file_hash = self._calculate_hash(full_path)
        
        return {
            'name': os.path.basename(full_path),
            'size': file_size,
            'hash': file_hash,
            'mtime': os.path.getmtime(full_path)
        }
    
    def _calculate_hash(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(self.buffer_size), b''):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def download_file(self, file_path):
        full_path = os.path.join(self.shared_root, file_path)
        
        if not full_path.startswith(self.shared_root):
            return None, 'Access denied'
        
        if not os.path.exists(full_path):
            return None, 'File not found'
        
        if os.path.isdir(full_path):
            return None, 'Not a file'
        
        file_size = os.path.getsize(full_path)
        if file_size > self.max_file_size:
            return None, 'File too large'
        
        with open(full_path, 'rb') as f:
            data = f.read()
        
        return data, None
    
    def upload_file(self, file_name, data):
        full_path = os.path.join(self.shared_root, file_name)
        
        if not full_path.startswith(self.shared_root):
            return 'Access denied'
        
        if os.path.isdir(full_path):
            return 'Target is directory'
        
        if len(data) > self.max_file_size:
            return 'File too large'
        
        try:
            with open(full_path, 'wb') as f:
                f.write(data)
            return None
        except Exception as e:
            return str(e)
    
    def handle_request(self, request):
        try:
            request_data = json.loads(request)
            action = request_data.get('action')
            
            if action == 'list':
                path = request_data.get('path', '')
                result = self.list_directory(path)
            
            elif action == 'info':
                file_path = request_data.get('path', '')
                result = self.get_file_info(file_path)
            
            elif action == 'download':
                file_path = request_data.get('path', '')
                data, error = self.download_file(file_path)
                if error:
                    result = {'error': error}
                else:
                    file_hash = hashlib.sha256(data).hexdigest()
                    return {
                        'type': 'file_data',
                        'path': file_path,
                        'size': len(data),
                        'hash': file_hash,
                        'data': data
                    }
            
            elif action == 'upload':
                file_name = request_data.get('name', '')
                file_data = request_data.get('data', b'')
                if isinstance(file_data, str):
                    file_data = bytes.fromhex(file_data)
                error = self.upload_file(file_name, file_data)
                if error:
                    result = {'error': error}
                else:
                    result = {'success': True}
            
            else:
                result = {'error': 'Unknown action'}
            
            return json.dumps(result)
        
        except Exception as e:
            return json.dumps({'error': str(e)})

class FileShareProtocol:
    LIST_DIR = 0x01
    GET_FILE_INFO = 0x02
    DOWNLOAD_FILE = 0x03
    UPLOAD_FILE = 0x04
    
    def __init__(self, session, crypto_manager):
        self.session = session
        self.crypto_manager = crypto_manager
    
    def send_request(self, request_type, data):
        header = struct.pack('!II', request_type, len(data))
        message = header + data
        if self.crypto_manager:
            message = self.crypto_manager.encrypt_with_aes(message)
        self.session.send(message)
    
    def parse_response(self, data):
        if self.crypto_manager:
            data = self.crypto_manager.decrypt_with_aes(data)
        
        if len(data) < 8:
            return None, None
        
        response_type = struct.unpack('!I', data[:4])[0]
        payload_length = struct.unpack('!I', data[4:8])[0]
        payload = data[8:8+payload_length]
        
        return response_type, payload