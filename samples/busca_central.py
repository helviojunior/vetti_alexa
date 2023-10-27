import socket, re
from time import sleep

def search_vetti() -> dict:
    UDP_PORT = 5000
    SEARCH = b"[T001 ID]"

    interfaces = socket.getaddrinfo(host=socket.gethostname(), port=None, family=socket.AF_INET)
    allips = [
        ip[-1][0] for ip in interfaces
        if ip[-1][0] not in ["127.0.0.1", "::1"]
        ]

    for _ in range(60):

        for ip in allips:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)  # UDP
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(0.2)
            sock.bind((ip,UDP_PORT))
            sock.sendto(SEARCH, ('255.255.255.255', UDP_PORT))
            try:
                data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes

                if isinstance(data, bytes):
                    data = data.decode("UTF-8")


                m = re.search("\[R001.*Mac:([a-fA-F0-9\-]+).*IP:([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}).*Nome:[ \"]{0,2}([^\"]+)", data, re.IGNORECASE)
                if m:
                    return dict(name=m.group(3).strip(), ip=m.group(2), mac=m.group(1))
                    #print(m.group(1))
                    #print(m.group(2).strip())
                else:   
                    print("received unknown message: %s" % data)

            except socket.timeout:
                pass
            sock.close()

        sleep(0.3)

    return None

print(search_vetti())