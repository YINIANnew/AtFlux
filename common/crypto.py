import os
import json
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import hashlib

class CryptoManager:
    def __init__(self, config):
        self.config = config
        self.rsa_key_size = config['encryption']['rsa_key_size']
        self.aes_key_size = config['encryption']['aes_key_size']
        self.iv_size = config['encryption']['iv_size']
        self.private_key = None
        self.public_key = None
        self.aes_key = None
        
    def generate_rsa_key_pair(self):
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.rsa_key_size,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        return self.private_key, self.public_key
    
    def serialize_public_key(self, public_key=None):
        if public_key is None:
            public_key = self.public_key
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def deserialize_public_key(self, key_bytes):
        return serialization.load_pem_public_key(key_bytes, backend=default_backend())
    
    def encrypt_with_rsa(self, data, public_key=None):
        if public_key is None:
            public_key = self.public_key
        return public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    def decrypt_with_rsa(self, encrypted_data):
        return self.private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    def generate_aes_key(self):
        self.aes_key = os.urandom(self.aes_key_size // 8)
        return self.aes_key
    
    def set_aes_key(self, key):
        self.aes_key = key
    
    def encrypt_with_aes(self, data):
        iv = os.urandom(self.iv_size)
        cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        padding_length = self.iv_size - (len(data) % self.iv_size)
        padded_data = data + bytes([padding_length] * padding_length)
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        return iv + encrypted
    
    def decrypt_with_aes(self, encrypted_data):
        iv = encrypted_data[:self.iv_size]
        ciphertext = encrypted_data[self.iv_size:]
        cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        padding_length = padded_data[-1]
        return padded_data[:-padding_length]
    
    def generate_device_id(self):
        import platform
        import uuid
        hardware_info = f"{platform.machine()}-{platform.processor()}-{uuid.getnode()}"
        return hashlib.sha256(hardware_info.encode()).hexdigest()
    
    def hash_data(self, data):
        return hashlib.sha256(data).hexdigest()
    
    def verify_hash(self, data, expected_hash):
        return self.hash_data(data) == expected_hash

class WhitelistManager:
    def __init__(self, config):
        self.config = config
        self.whitelist_path = config['whitelist']['local_path']
        self.devices = []
        self.load_whitelist()
    
    def load_whitelist(self):
        try:
            if os.path.exists(self.whitelist_path):
                with open(self.whitelist_path, 'r') as f:
                    data = json.load(f)
                    self.devices = data.get('devices', [])
        except Exception as e:
            self.devices = []
    
    def save_whitelist(self):
        try:
            with open(self.whitelist_path, 'w') as f:
                json.dump({'devices': self.devices}, f, indent=2)
        except Exception as e:
            pass
    
    def add_device(self, device_id):
        if device_id not in self.devices:
            self.devices.append(device_id)
            self.save_whitelist()
    
    def remove_device(self, device_id):
        if device_id in self.devices:
            self.devices.remove(device_id)
            self.save_whitelist()
    
    def is_whitelisted(self, device_id):
        return device_id in self.devices
    
    def get_all_devices(self):
        return self.devices.copy()