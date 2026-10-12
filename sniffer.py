from scapy.all import sniff, TCP, IP, Raw
import csv
import os
import time
from datetime import datetime

CSV_FILE = "packets.csv"

# Write CSV header if file doesn't exist
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "src_ip", "dst_ip", "src_port", "dst_port", "type"])

def log_packet(src_ip, dst_ip, src_port, dst_port, ptype):
    """Write packet to CSV with retry — handles Windows file lock conflicts."""
    for attempt in range(5):
        try:
            with open(CSV_FILE, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([datetime.now().isoformat(), src_ip, dst_ip, src_port, dst_port, ptype])
            return  # success
        except PermissionError:
            time.sleep(0.05)  # wait 50ms and retry
    print(f"[!] Could not write packet to CSV after 5 retries (file locked)")

def analyze_packet(packet):
    if IP in packet and TCP in packet:
        try:
            if packet[TCP].flags == 'S':
                print(f"[+] TCP SYN: Incoming connection from {packet[IP].src}")
                log_packet(packet[IP].src, packet[IP].dst,
                           packet[TCP].sport, packet[TCP].dport, "SYN")

            elif Raw in packet and b"503" in packet[Raw].load:
                print(f"[-] PACKET DROPPED: Nginx blocked attack, sent 503 to {packet[IP].dst}")
                log_packet(packet[IP].src, packet[IP].dst,
                           packet[TCP].sport, packet[TCP].dport, "503_BLOCKED")
        except Exception as e:
            print(f"[!] Error in packet handler: {e}")  # never crash Scapy

print("Listening for Network Traffic on Load Balancer (Port 8080)...")
sniff(iface="Software Loopback Interface 1", filter="tcp port 8080", prn=analyze_packet, store=0)
