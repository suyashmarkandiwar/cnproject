from scapy.all import sniff, TCP, IP, Raw

def analyze_packet(packet):
    if IP in packet and TCP in packet:
        # Detect incoming requests (TCP SYN)
        if packet[TCP].flags == 'S':
            print(f"[+] TCP SYN: Incoming connection from {packet[IP].src}")
        
        # Detect Nginx dropping the packet (HTTP 503 Service Unavailable)
        elif Raw in packet and b"503" in packet[Raw].load:
            print(f"[-] PACKET DROPPED: Nginx blocked attack, sent 503 to {packet[IP].dst}")

print("Listening for Network Traffic on Load Balancer (Port 8080)...")
# Listen on port 8080 where your load test hits
sniff(iface="Software Loopback Interface 1", filter="tcp port 8080", prn=analyze_packet, store=0)