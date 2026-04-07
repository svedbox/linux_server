#!/usr/bin/env python3
#coding:utf-8
#----------------------------svedbox-----------------------------------#
#-----Monitoring services of server and send telegram messages---------#
#-----about problems---------------------------------------------------#
#----------------------------------------------------------------------#
#----------------------------------------------------------------------#

#--------Modules-------#
import os
import configparser
import requests
import subprocess
import re
import psutil
import psycopg2
import pwd
import logging
#--------Variables of paths--------------------------#
script_path = os.path.realpath(__file__)
script_owner = pwd.getpwuid(os.stat(script_path).st_uid).pw_name
home_dir = os.path.expanduser(f'/home/{script_owner}')
workpath = os.path.join(home_dir, '.monitoring')
configpath = '/etc/monitoring.conf'
logpath = '/var/log/monitoring.log'
#----Creating work dir-----------------#
#if not (os.path.exists(workpath)):
#    d = os.makedirs(workpath)
#----Creating log file---------#
if not (os.path.exists(logpath)):
    file = open(logpath, 'w+')
    file.write('')
    file.close()
    file = open('/etc/logrotate.d/monitoring', 'w+')
    file.write('/var/log/monitoring.log {rotate 7; daily; compress; delaycompress; missingok; notifempty}')
    file.close()
#----Logging-------------------#
logging.basicConfig(filename=logpath, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Program is run')
#----Creating conf file---------#
if not (os.path.exists(configpath)):
    config = configparser.ConfigParser(allow_no_value=True)
    ttoken = input ('Enter your telegram token -')
    tchatid = input ('Enter your telegram chatid -')
    config.add_section("Main")
    config.set('Main', 'token', ttoken)
    config.set('Main', 'chatid', tchatid)
    config.set('Main', 'block_total', 0)
    with open(configpath, "w") as config_file:
        config.write(config_file)
#--------Reading conf file-------------#
config = configparser.ConfigParser()
config.read(configpath)
token = config.get('Main','token')
chatid = config.get('Main','chatid')
f2btotal = int(config.get('Main','block_total'))
#---------Variables-------------------------#
boturl = "https://api.telegram.org/bot"
boturl2 = "/sendMessage?chat_id="
boturl3 = "&text="
boturlf =  boturl + token + boturl2 + chatid + boturl3

#-------Mon Fail2ban  brutforce-------------------------
try:
    f2bcom = "fail2ban-client status"
    f2bres = subprocess.run(f2bcom, shell=True, capture_output=True, text=True)
    f2bres_lines = f2bres.stdout.splitlines()
    f2bres_line = (f2bres_lines[2])
    f2bj = f2bres_line[14:]
    f2bitems = [item.strip() for item in f2bj.split(',')]
    f2bitem_set = set(f2bitems)
    f2btot = 0
    for jail in f2bitem_set:
        comm = "fail2ban-client status " + jail
        f2bcomm = subprocess.run(comm, shell=True, capture_output=True, text=True)
        f2bcommr = f2bcomm.stdout.splitlines()
        curr = f2bcommr[6]
        currc = int(curr[24:])
        print (currc, " - ", jail)
        f2btot = f2btot + currc
    if f2btot == f2btotal:
        pass
    else:
        if f2btot >= 20:
            requests.post( boturlf + 'Server has brutforce !!!' )
            logging.error('Server has brutforce !!!')
            f2btots = str(f2btot)
            config = configparser.ConfigParser()
            config.read(configpath)
            config.set('Main', 'block_total', f2btots)
            with open(configpath, "w") as config_file:
                config.write(config_file)
        elif f2btot == 0:
            requests.post( boturlf + 'Brutforce finished' )
            logging.info('Brutforce finished ')
            f2btots = str(f2btot)
            config = configparser.ConfigParser()
            config.read(configpath)
            config.set('Main', 'block_total', f2btots)
            with open(configpath, "w") as config_file:
                config.write(config_file)
        else:
            f2btots = str(f2btot)
            config = configparser.ConfigParser()
            config.read(configpath)
            config.set('Main', 'block_total', f2btots)
            with open(configpath, "w") as config_file:
                config.write(config_file)

except:
    pass
#-------Mon Power if use raspberry pi--------------------------------
#try:
#    powmes = "Problem with POWER and Temperature !!!"
#    powcom = "vcgencmd get_throttled"
#    pow80000 = "Soft temperature limit has occured!"
#    powresult = subprocess.run(powcom, shell=True, capture_output=True, text=True)
#    powres = (powresult.stdout).strip()
#    if powres != 'throttled=0x0':
#        requests.post( boturlf + powmes + powres )
#        logging.error('Problem with POWER and Temperature !!! '+ powres)
#        print ('Checking power -', '\033[1;31;40m FAIL \033[0m', powres )
#    else: print ('Checking power -', '\033[1;32;40m OK \033[0m')
#except:
#    pass
#-------Mon ZRAID---------------------------------
try:
    raidmes = "Raid has a problem !!!"
    raidcom = "mdadm --detail /dev/md0"
    raidzcom = "zpool status"
    result = subprocess.run(raidcom, shell=True, capture_output=True, text=True)
    zresult = subprocess.run(raidzcom, shell=True, capture_output=True, text=True)
    raidres = (result.stdout)
    zraidres = (zresult.stdout)
    lines = raidres.splitlines()
    zlines = zraidres.splitlines()
#---------------------for zfs raidz-----------
    for line in zlines:
        if "state:" in line:
            resline = line
    reslineclr = resline.strip()
    if reslineclr != 'state: ONLINE' :
        requests.post( boturlf + raidmes )
        logging.error('Checking RAID - FAIL')
        print ('Checking RAID -', '\033[1;31;40m FAIL \033[0m')
    else: print ('Checking RAID -', '\033[1;32;40m OK \033[0m')
except:
    logging.error('Checking RAID - RAID is not running')
    print ('\033[1;31;40m RAID Array is not running \033[0m')
    requests.post( boturlf + 'RAID Array is not running' )
#---------Determine ps status processes-----------------
def proc_stat(proc_name):
    proci_com = "systemctl status "+ proc_name
    proci = subprocess.run(proci_com, shell=True, capture_output=True, text=True)
    proci_lines = proci.stdout.splitlines()
    for line in proci_lines:
        if "Active: active" in line:
            return True
    else: return False
#----Status services-----------------------------
servset = { 'opendht', 'rustdesk-hbbs', 'rustdesk-hbbr', 'signaling', 'syncthing', 'wg-quick@wg0','crowdsec', 'coturn', \
'janus', 'nats-server', 'notify_push', 'ntpsec', 'crowdsec-firewall-bouncer', 'mariadb', \
'sshd', 'shadowsocks-libev', 'nftables', 'nginx', 'coolwsd', 'postgresql', \
'redis-server', 'ddclient', 'ntpd', 'openhab', 'fail2ban', 'minidlna', 'suricata'}
for serv in servset:
    proc_name = serv
    if proc_stat(proc_name):
        print ('Checking ', proc_name, ' -', '\033[1;32;40m OK \033[0m')
    else:
        requests.post( boturlf + "The process " + proc_name + " is not running." )
        logging.error('Checking ' + proc_name + ' - FAIL')
        print ('Checking ', proc_name, ' -', '\033[1;31;40m FAIL \033[0m')

#----------------------------------------------------
logging.info('Program is end')
#------------------------END-----------------------------#
