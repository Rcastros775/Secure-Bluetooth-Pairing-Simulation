import socket, struct, json, hashlib

MCAST_GRP = '224.1.1.1'
MCAST_PORT = 5007

def get_hash(passkey, nonce):
    return hashlib.sha256(f"{passkey}{nonce}".encode()).hexdigest()

def crypt(text, key):
    """Simple XOR to simulate encryption/decryption. Actual encryption uses Elliptic Curve Diffie Hellman"""
    return "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(text))

def send_msg(sender_id, msg_type, data):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    payload = json.dumps({"from": sender_id, "type": msg_type, "data": data})
    sock.sendto(payload.encode(), (MCAST_GRP, MCAST_PORT))

def get_sock():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', MCAST_PORT))
    mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.settimeout(0.5)
    return sock