import bt_common as bt
import time, json, sys, threading, random

class Peripheral:
    def __init__(self, mode="just_works"):
        self.id = "HEADPHONES_v1"
        self.mode = mode
        self.bonded = False
        self.session_key = None
        self.nonce = None
        self.running = True

    def send_heartbeat(self):
        count = 0
        while self.running and count < 10:
            if self.bonded:
                raw_data = f"Heartrate: {random.randint(70, 80)} BPM"
                encrypted = bt.crypt(raw_data, self.session_key)
                print(f"  [TX {count+1}/10] Sending Heartbeat...")
                bt.send_msg(self.id, "HEARTBEAT", {"gatt": "HIF", "payload": encrypted})
                count += 1
            time.sleep(2)
        self.running = False

    def run(self):
        sock = bt.get_sock()
        threading.Thread(target=self.send_heartbeat, daemon=True).start()
        print(f"--- PERIPHERAL ({self.mode}) ---")
        
        try:
            while self.running:
                if not self.bonded:
                    bt.send_msg(self.id, "ADVERTISE", {"mode": self.mode})
                    time.sleep(2)
                
                try:
                    data, _ = sock.recvfrom(1024)
                    msg = json.loads(data.decode())
                    
                    if msg['type'] == "RESET":
                        if self.session_key:
                            try:
                                cmd = bt.crypt(msg['data']['payload'], self.session_key)
                                if cmd == "SHUTDOWN":
                                    print("\n[!] AUTHENTICATED DISCONNECT RECEIVED. Shutting down...")
                                    self.running = False
                                    break
                                else:
                                    print(f"\n[?] Malformed Reset Attempt: Decrypted as '{cmd[:10]}...' (Ignored)")
                            except:
                                print("\n[?] Reset packet corrupted or unreadable.")
                        else:
                            print("\n[!] Unauthenticated RESET ignored (No session key).")

                    if msg['type'] == "PAIR_REQ" and msg['data']['target'] == self.id:
                        self.nonce = msg['data']['nonce']
                        if self.mode == "just_works":
                            self.session_key = bt.get_hash("000000", self.nonce)
                            self.bonded = True
                            print("[CONN] Paired with Central.")
                        else:
                            self.do_passkey_entry()
                            
                    if msg['type'] == "AUTH_OK" and msg['data']['target'] == self.id:
                        self.bonded = True
                        print("[CONN] Secure Bond Confirmed.")
                    
                    if msg['type'] == "AUTH_FAILED" and msg['data']['target'] == self.id:
                        print("\n[!] Pairing rejected by Central. Resetting state...")
                        self.nonce = None
                        self.bonded = False
                except: continue
        except KeyboardInterrupt: pass
        print("Peripheral Offline.")

    def do_passkey_entry(self):
        print("\n--- PASSKEY ENTRY MODE (2-Button Simulation) ---")
        print("Controls: 'w' to increment digit, 'd' to confirm and move next.")
        
        passkey = [0] * 6
        for i in range(6):
            confirmed = False
            while not confirmed:
                display = ["*"] * 6
                for j in range(i): display[j] = str(passkey[j])
                display[i] = f"[{passkey[i]}]"
                print(f"\rCurrent Buffer: {' '.join(display)} | Input (w/d): ", end="", flush=True)
                
                cmds = input().lower()
                for char in cmds:
                    if char == 'w':
                        passkey[i] = (passkey[i] + 1) % 10
                    elif char == 'd':
                        confirmed = True
                        break
                
                if not confirmed:
                    display[i] = f"[{passkey[i]}]"
                    print(f"\rCurrent Buffer: {' '.join(display)} | Input (w/d): ", end="", flush=True)

        final_code = "".join(map(str, passkey))
        print(f"\n\n[*] Final Passkey Entered: {final_code}")
        self.session_key = bt.get_hash(final_code, self.nonce)
        bt.send_msg(self.id, "STK_VERIFY", {"hash": self.session_key})

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "just_works"
    Peripheral(mode).run()