import socket
# -*- coding: UTF-8 -*-

UDP_IP = "192.168.0.114"
UDP_PORT = 5000
PASSWD = "1234"
PASSWD2 = "01020304"
AUTH = "[T128 TEC Idx=401 Cmd=3 Par=%s]" % PASSWD
MESSAGE = "[T146 CMDX Id=22 User=%s Part=100000]" % PASSWD2

print("UDP target IP: %s" % UDP_IP)
print("UDP target port: %s" % UDP_PORT)
print("message: %s" % MESSAGE)

sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP

addr = (UDP_IP, UDP_PORT)


#Authenticate
sock.sendto(AUTH.encode(), addr)
sock.recvfrom(1024)

# Send command
sock.sendto(MESSAGE.encode(), addr)

# Receive answer
data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes

if isinstance(data, bytes):
    data = data.decode("UTF-8")

print("received message: %s" % data)

#Auth central
#Cmd: [T128 TEC Idx=401 Cmd=3 Par=1234]
#Res: [R128 TEC Idx=401 Cmd=3 Par=1234]

#Arme Full
#Cmd: [T142 CMDX Id=21 User=01020304 Part=100000]
#Res: [R142 CMDX Id=21 User=01 PART=100000 Err=000000 Stat=AANNNN]

#Desarme
#Cmd: [T146 CMDX Id=22 User=01020304 Part=100000]
#Res: [R146 CMDX Id=22 User=01 PART=100000 Err=000000 Stat=-ANNNN]

# Arme Stay
#Cmd: [T134 CMDX Id=25 User=01020304 Part=100000]
#Res: [R134 CMDX Id=25 User=01 PART=100000 Err=000000 Stat=SANNNN]

# Pega data e hora
#Cmd: [T136 CMD 27]
#Res: [R136 CMD 27 "2023/10/27 16:10:02"]

# Status de conexao
#Cmd: [T129 STAT 5]
#Res: [R129 STAT 5 CID=ethernet GSM=NI Time="2023/10/27 16:11:04" Serv1="conn01.seguranca.com.br" Serv2=""]

# Status do alarme
#Cmd: [T133 CMD 2]

#Res: [R133 CMD 2 (p:-ANNNN)]

# Status do alarme
#Cmd: [T137 CMD 2]
#Res: [R137 CMD 2 (p:SANNNN)]

# ???
#Cmd: [T130 TEC IDX=401 CMD=2]
#Res: [R130 TEC Idx=401 Cmd=2 Part=-ANNNN Par4101=ADBCB67C Par4105=7DB7D4D8 ParA115=120 Stat="0000000000000000000000000000000000000000000000000000000000008100" BatBaixa="0000000000000000000000000000000000000000000000000000000000000000"]

# ???
#Cmd: [T148 TEC IDX=401 CMD=2]
#Res: [R148 TEC Idx=401 Cmd=2 Part=-AAAAA Par4101=BDC0B5C1 Par4105=57211D77 ParA115=120 Stat="0000000000000000000000000000000000000000000000000000000000000104" BatBaixa="0000000000000000000000000000000000000000000000000000000000000000"]

