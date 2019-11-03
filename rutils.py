#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
import os
import fcntl
import subprocess
import re
import datetime
import time
pt_pid =  re.compile("\([0-9]+\)")

# rutils.killtasks(int(pid))
def killtasks(pid):
	pids = getallpids(pid)
	os.kill(pid,9)
	for pid in pids:
		os.kill(pid,9)
	return 0

def get_installpath():
	return os.path.dirname(os.path.abspath(__file__))

def get_resource():
	fn = open(get_installpath() + "/spool/config/jobinfo","r")
	maxcpus,maxmemK,maxjobid = map(int,fn.read().strip().split())
	return maxcpus,maxmemK,maxjobid

class Lock(object):
	def __init__(self):
		self.lockfile = get_installpath() + "/spool/config/lockfile"
		self.f = None
	def get(self):
		if not os.path.isfile(self.lockfile):
			sys.stderr.write("[ERROR] '%s' not exist!\n"%self.lockfile)
			return 1
		self.f = open(self.lockfile,"r")
		fcntl.flock(self.f.fileno(),fcntl.LOCK_EX)
		return 0
	def release(self):
		if self.f == None:
			sys.stderr.write("[ERROR] please open the '%s' first!\n"%self.lockfile)
			return 1
		fcntl.flock(self.f.fileno(),fcntl.LOCK_UN)
		self.f.close()
		return 0 

def getallpids(pid):
	exitstatus, outtext = subprocess.getstatusoutput("/bin/pstree -p %d"%pid)
	allpids = pt_pid.findall(outtext)
	pids = []
	for tmppid in allpids:
		tmppid = int(tmppid[1:-1])
		if tmppid == pid:continue
		else: pids.append(tmppid)
	return pids
def getallstat(cpid,pcpu,xs,stat,pmem,rsz,runcmd):
	otherids = getallpids(cpid)
	for pid in otherids:
		ret = getpidstat(pid)
		if ret is None:continue
		else:
			t_cpid,t_pcpu,t_xs,t_stat,t_pmem,t_rsz,t_runcmd = ret
		pcpu += t_pcpu
		xs += t_xs
		pmem += t_pmem
		rsz += t_rsz
	return pcpu,xs,pmem,rsz 
def getpidstat(pid):
	cmd = "/bin/ps -q %d -o pid,pcpu,cputime,stat,%%mem,rsz,args"%pid
	exitstatus, outtext = subprocess.getstatusoutput(cmd)
	arr = outtext.strip().split("\n")
	if len(arr) == 2:
		subarr = arr[1].strip().split(None,6) # # PID %CPU     TIME STAT %MEM   RSZ COMMAND
		cpid = int(subarr[0]);  pcpu = float(subarr[1]); 
		### tm_year=1900, tm_mon=1, tm_mday=1, tm_hour=0, tm_min=0, tm_sec=21, tm_wday=0, tm_yday=1, tm_isdst=-1
		### timeArray = time.strptime('1-00:00:21', "%d-%H:%M:%S")
		try:
			x = time.strptime(subarr[2],"%H:%M:%S"); 
			xs = datetime.timedelta(hours=x.tm_hour,minutes=x.tm_min,seconds=x.tm_sec).total_seconds()
		except:
			try:
				x = time.strptime(subarr[2],"%d-%H:%M:%S");
				xs = datetime.timedelta(days=x.tm_yday,hours=x.tm_hour,minutes=x.tm_min,seconds=x.tm_sec).total_seconds()
			except:
				raise;
		stat = subarr[3]; pmem = float(subarr[4]); rsz = int(subarr[5]); 
		runcmd = subarr[6]
		#xs = datetime.timedelta(days=x.tm_mday,hours=x.tm_hour,minutes=x.tm_min,seconds=x.tm_sec).total_seconds()
		return cpid,pcpu,xs,stat,pmem,rsz,runcmd ## 对主进程， submitcmd.strip() == runcmd[9:].strip() 
	else:
		return None
"""
import datetime
import time
x = time.strptime("01:20:40","%H:%M:%S")
xs = datetime.timedelta(hours=x.tm_hour,minutes=x.tm_min,seconds=x.tm_sec).total_seconds() 
4840.0
str(datetime.timedelta(seconds=xs)) 
'1:20:40'
"""
def runcheck(taskid,username,cwd,shdir,shcmd,pid):
	shdircmd = shdir + "/" + shcmd
	shout = shdircmd + ".o%s"%taskid
	sherr = shdircmd + ".e%s"%taskid
	shpid = shdircmd + ".p%s"%taskid
	submitcmd = """cd %s && /usr/bin/sh %s 1>%s 2>%s & echo $!>%s"""%(cwd,shdircmd,shout,sherr,shpid)
	#pid = int(file(shpid,"r").read().strip())
	ret = getpidstat(pid)
	if ret is None: return None
	else:
		if ret[-1][9:].strip() != submitcmd.strip(): return None
		pcpu,xs,pmem,rsz = getallstat(*ret)
		return pid,pcpu,xs,pmem,rsz

def runcmd(taskid,username,cwd,shdir,shcmd):
	#taskid,username,cwd,shdir,shcmd,askcpu,askmem,status,cpu_active, mem_active,time_active,pid
	## su - rongzhengqin -c 'cd /home/rongzhengqin/simpbs && sh /home/rongzhengqin/simpbs/test.sh 1>xx.o 2>xx.e &  echo $! > xx.pid '
	shdircmd = shdir + "/" + shcmd
	shout = shdircmd + ".o%s"%taskid
	sherr = shdircmd + ".e%s"%taskid
	shpid = shdircmd + ".p%s"%taskid
	cmd = """su - %s -c 'cd %s && /usr/bin/sh %s 1>%s 2>%s & echo $!>%s'"""%(username,cwd,shdircmd,shout,sherr,shpid)
	os.system(cmd)
	pid = int(open(shpid,"r").read().strip())
	return pid

def mem_h2k(mem):
	if mem.endswith("M"):
		mem = int(mem[0:-1]) * 1024
	elif mem.endswith("G"):
		mem = int(mem[0:-1]) * 1024 * 1024
	else:
		try:
			mem = int(mem)
		except: mem = 2048
	return mem

def mem_print(mem):
	mem = float(mem)
	if mem > 1048576: # > G
		memprint = mem / 1048576 
		code = "G"
	elif mem > 1024:
		memprint = mem / 1024
		code = "M"
	else:
		memprint = mem
		code = "K"
	return "%.1f%s"%(memprint,code)


if __name__ == "__main__":
	print(mem_h2k("12M"))
	print(mem_h2k("12G"))
	print(mem_h2k("123K"))
	print(mem_print(12313))
	print(mem_print(2231123))
	print(mem_print(123))
