import bt_common as bt
import json, random, time

print("--- COMPUTER (CENTRAL) ---")
sock = bt.get_sock()
current_passkey = str(random.randint(100000, 999999))
nonce = str(random.randint(1000, 9999))
session_key = None
bonded_device = None
pairing_initiated = False

msg_count = 0

try:
    while True:
        try:
            data, _ = sock.recvfrom(1024)
            msg = json.loads(data.decode())
        except: continue

        if not bonded_device and not pairing_initiated and msg['type'] == "ADVERTISE":
            dev_id = msg['from']
            mode = msg['data']['mode']
            
            print(f"\n[SCAN] Found {dev_id} ({mode}). Sending Pairing Request...")
            bt.send_msg("COMPUTER", "PAIR_REQ", {"target": dev_id, "nonce": nonce})
            pairing_initiated = True
            
            if mode == "just_works":
                session_key = bt.get_hash("000000", nonce)
                bonded_device = dev_id
                print(f"[CONN] Linked to {bonded_device} (Just Works)")
            else:
                print(f"------------------------------------")
                print(f"*** AUTHENTICATION PASSKEY: {current_passkey} ***")
                print(f"------------------------------------")
                print("Waiting for Peripheral to provide cryptographic proof...")

        if msg['type'] == "STK_VERIFY" and not bonded_device:
            expected_hash = bt.get_hash(current_passkey, nonce)
            if msg['data']['hash'] == expected_hash:
                print("\n[SECURE] Passkey Proof Verified! Bond established.")
                bt.send_msg("COMPUTER", "AUTH_OK", {"target": msg['from']})
                session_key = expected_hash
                bonded_device = msg['from']
            else:
                print("\n[ALERT] Incorrect Proof received. Rejecting.")
                bt.send_msg("COMPUTER", "AUTH_FAILED", {"target": msg['from']})
                pairing_initiated = False

        if bonded_device and msg['from'] == bonded_device and msg['type'] == "HEARTBEAT":
            decrypted = bt.crypt(msg['data']['payload'], session_key)
    
            if decrypted.startswith("Heartrate:"):
                print(f"[RX {msg_count+1}/10] {msg['data']['gatt']}: {decrypted}")
                msg_count += 1
            elif "You've been hacked!" in decrypted:
                print(f"[RX {msg_count+1}/10] {msg['data']['gatt']}: {decrypted}")
                print("\n[!!!] SYSTEM COMPROMISED: Malicious HID Input Detected.")
                break
            else:
                print(f"[SNIFF] Dropped invalid packet (Decryption failed/Gibberish)")

            if msg_count >= 10:
                print("\n[INFO] Session limit reached. Disconnecting.")
                break

except KeyboardInterrupt:
    pass
print("Computer Offline.")