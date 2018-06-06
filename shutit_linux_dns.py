# Generated by shutit skeleton
import random
import datetime
import logging
import string
import os
import inspect
from shutit_module import ShutItModule


class shutit_linux_dns(ShutItModule):

	def build(self, shutit):
		vagrant_image = shutit.cfg[self.module_id]['vagrant_image']
		vagrant_provider = shutit.cfg[self.module_id]['vagrant_provider']
		gui = shutit.cfg[self.module_id]['gui']
		memory = shutit.cfg[self.module_id]['memory']
		shutit.build['vagrant_run_dir'] = os.path.dirname(os.path.abspath(inspect.getsourcefile(lambda:0))) + '/vagrant_run'
		shutit.build['module_name'] = 'shutit_linux_dns_' + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
		shutit.build['this_vagrant_run_dir'] = shutit.build['vagrant_run_dir'] + '/' + shutit.build['module_name']
		shutit.send(' command rm -rf ' + shutit.build['this_vagrant_run_dir'] + ' && command mkdir -p ' + shutit.build['this_vagrant_run_dir'] + ' && command cd ' + shutit.build['this_vagrant_run_dir'])
		shutit.send('command rm -rf ' + shutit.build['this_vagrant_run_dir'] + ' && command mkdir -p ' + shutit.build['this_vagrant_run_dir'] + ' && command cd ' + shutit.build['this_vagrant_run_dir'])
		if shutit.send_and_get_output('vagrant plugin list | grep landrush') == '':
			shutit.send('vagrant plugin install landrush')
		shutit.send('vagrant init ' + vagrant_image)
		shutit.send_file(shutit.build['this_vagrant_run_dir'] + '/Vagrantfile','''Vagrant.configure("2") do |config|
  config.landrush.enabled = true
  config.vm.provider "virtualbox" do |vb|
    vb.gui = ''' + gui + '''
    vb.memory = "''' + memory + '''"
  end

  config.vm.define "linuxdns1" do |linuxdns1|
    linuxdns1.vm.box = ''' + '"' + vagrant_image + '"' + '''
    linuxdns1.vm.hostname = "linuxdns1.vagrant.test"
    config.vm.provider :virtualbox do |vb|
      vb.name = "shutit_linux_dns_1"
    end
  end
end''')

		# machines is a dict of dicts containing information about each machine for you to use.
		machines = {}
		machines.update({'linuxdns1':{'fqdn':'linuxdns1.vagrant.test'}})

		try:
			pw = open('secret').read().strip()
		except IOError:
			pw = ''
		if pw == '':
			shutit.log("""You can get round this manual step by creating a 'secret' with your password: 'touch secret && chmod 700 secret'""",level=logging.CRITICAL)
			pw = shutit.get_env_pass()
			import time
			time.sleep(10)

		# Set up the sessions
		shutit_sessions = {}
		for machine in sorted(machines.keys()):
			shutit_sessions.update({machine:shutit.create_session('bash', walkthrough=True)})
		# Set up and validate landrush
		for machine in sorted(machines.keys()):
			shutit_session = shutit_sessions[machine]
			shutit_session.send('cd ' + shutit.build['this_vagrant_run_dir'])
			# Remove any existing landrush entry.
			shutit_session.send('vagrant landrush rm ' + machines[machine]['fqdn'])
			# Needs to be done serially for stability reasons.
			try:
				shutit_session.multisend('vagrant up --provider ' + shutit.cfg['shutit-library.virtualization.virtualization.virtualization']['virt_method'] + machine_name,{'assword for':pw,'assword:':pw})
			except NameError:
				shutit_session.multisend('vagrant up ' + machine,{'assword for':pw,'assword:':pw},timeout=99999)
			if shutit_session.send_and_get_output("vagrant status 2> /dev/null | grep -w ^" + machine + " | awk '{print $2}'") != 'running':
				shutit_session.pause_point("machine: " + machine + " appears not to have come up cleanly")
			ip = shutit_session.send_and_get_output('''vagrant landrush ls 2> /dev/null | grep -w ^''' + machines[machine]['fqdn'] + ''' | awk '{print $2}' ''')
			machines.get(machine).update({'ip':ip})
			shutit_session.login(command='vagrant ssh ' + machine)
			shutit_session.login(command='sudo su - ')
			# Correct /etc/hosts
			shutit_session.send(r'''cat <(echo $(ip -4 -o addr show scope global | grep -v 10.0.2.15 | head -1 | awk '{print $4}' | sed 's/\(.*\)\/.*/\1/') $(hostname)) <(cat /etc/hosts | grep -v $(hostname -s)) > /tmp/hosts && mv -f /tmp/hosts /etc/hosts''')
			# Correct any broken ip addresses.
			if shutit_session.send_and_get_output('''vagrant landrush ls | grep ''' + machine + ''' | grep 10.0.2.15 | wc -l''') != '0':
				shutit_session.log('A 10.0.2.15 landrush ip was detected for machine: ' + machine + ', correcting.',level=logging.WARNING)
				# This beaut gets all the eth0 addresses from the machine and picks the first one that it not 10.0.2.15.
				while True:
					ipaddr = shutit_session.send_and_get_output(r'''ip -4 -o addr show scope global | grep -v 10.0.2.15 | head -1 | awk '{print $4}' | sed 's/\(.*\)\/.*/\1/' ''')
					if ipaddr[0] not in ('1','2','3','4','5','6','7','8','9'):
						time.sleep(10)
					else:
						break
				# Send this on the host (shutit, not shutit_session)
				shutit.send('vagrant landrush set ' + machines[machine]['fqdn'] + ' ' + ipaddr)
			# Check that the landrush entry is there.
			shutit.send('vagrant landrush ls | grep -w ' + machines[machine]['fqdn'])
		# Gather landrush info
		for machine in sorted(machines.keys()):
			ip = shutit.send_and_get_output('''vagrant landrush ls 2> /dev/null | grep -w ^''' + machines[machine]['fqdn'] + ''' | awk '{print $2}' ''')
			machines.get(machine).update({'ip':ip})



		for machine in sorted(machines.keys()):
			shutit_session = shutit_sessions[machine]
			shutit_session.run_script(r'''#!/bin/sh
# See https://raw.githubusercontent.com/ianmiell/vagrant-swapfile/master/vagrant-swapfile.sh
fallocate -l ''' + shutit.cfg[self.module_id]['swapsize'] + r''' /swapfile
ls -lh /swapfile
chown root:root /swapfile
chmod 0600 /swapfile
ls -lh /swapfile
mkswap /swapfile
swapon /swapfile
swapon -s
grep -i --color swap /proc/meminfo
echo "
/swapfile none            swap    sw              0       0" >> /etc/fstab''')
			shutit_session.multisend('adduser person',{'Enter new UNIX password':'person','Retype new UNIX password:':'person','Full Name':'','Phone':'','Room':'','Other':'','Is the information correct':'Y'})

		for machine in sorted(machines.keys()):
			shutit_session = shutit_sessions[machine]
			#shutit_session.send('apt install -y curl strace nmap telnet && curl -s https://s3.amazonaws.com/download.draios.com/stable/install-sysdig | bash',background=True,wait=False,block_other_commands=False)
			shutit_session.install('curl strace nmap telnet',echo=False)
			shutit_session.send('curl -s https://s3.amazonaws.com/download.draios.com/stable/install-sysdig | bash',echo=False)

			#####################################################################
			# PART I
			#####################################################################

			####################################################################
			# NSSWITCH
			####################################################################
			# Can we ping ok?
			shutit_session.send('ping -c1 google.com', note='Basic ping to google.comm works')
			shutit_session.send('ping -c1 localhost', note='Basic ping to localhost works')
			shutit_session.send("""sed -i 's/hosts: .*/hosts: files/g' /etc/nsswitch.conf""", note='Change nsswitch to only have files')
			shutit_session.send('ping -c1 google.com', note='google lookup will now fail', check_exit=False)
			shutit_session.send('ping -c1 localhost', note='But localhost still works, presumably because it is handled by "files"')
			shutit_session.send("sed -i 's/hosts: .*/hosts: dns/g' /etc/nsswitch.conf", note='Change nsswitch to only have dns')
			shutit_session.send('ping -c1 google.com', note='Google can now be pinged')
			shutit_session.send('ping -c1 localhost', note='But localhost will fail', check_exit=False)
			shutit_session.send("""sed -i 's/hosts: .*/hosts: files dns myhostname/g' /etc/nsswitch.conf""")

			#####################################################################
			## getaddrinfo - standard C library?
			#####################################################################
			# gai.conf?
			# https://jameshfisher.com/2018/02/03/what-does-getaddrinfo-do
			# BUT WAIT THERE'S STILL MORE! After our process has its DNS responses, it does more work. It starts by reading /etc/gai.conf, the Configuration for getaddrinfo(3). The function call has its very own configuration file! Luckily, mine is only comments.
			# Not everything uses gai - eg ping vs host - tho that 
			# 'Makes sense - a strace of host shows it 'just' goes to /etc/resolv.conf, while ping (for example) looks up nsswitch.' (and gai.conf) etc
			# Can use gai.conf to hack ipv4 over ipv6 without switching ipv6 off.
			# https://community.rackspace.com/products/f/public-cloud-forum/5110/how-to-prefer-ipv4-over-ipv6-in-ubuntu-and-centos
			# eg JAVA has its own dns lookup?
			shutit_session.send('strace -e trace=openat -f host google.com',note='Host does not use nsswitch, just resolv.conf.')
			# ping references nsswitch
			shutit_session.send('strace -e trace=openat -f ping -c1 google.com', note='Ping does use nsswitch.')

			####################################################################
			# resolvconf
			####################################################################
			# Show resolv.conf is the resolver
			# Change resolv.conf by hand
			shutit_session.send('ls -l /etc/resolv.conf',note='resolvconf turns /etc/resolv.conf into a symlink to the /run folder.')
			shutit_session.send("sed -i 's/^nameserver/#nameserver/' /etc/resolv.conf", note='Take nameserver out of /etc/resolv.conf')
			shutit_session.send('ping -c1 google.com', note='google will fail, no nameserver specified by /etc/resolv.conf', check_exit=False)
			shutit_session.send("sed -i 's/^#nameserver/nameserver/' /etc/resolv.conf", note='put nameserver back')
			shutit_session.send('ping -c1 google.com', note='ping works again')

			# So Where does resolvconf get its info from?
			# Plug in a log file triggered whenever the 000resolvconf script gets run
			shutit_session.send("""sed -i '2s@^.*@echo I am triggered by ifup > /tmp/000resolvconf.log@' /etc/network/if-up.d/000resolvconf""")
			# Running ifup/ifdown triggers it...
			shutit_session.send('ifdown enp0s8', note='Bring network interface down')
			shutit_session.send('ls /tmp/000resolvconf.log', note='File not created on ifdown', check_exit=False)
			shutit_session.send('ifup enp0s8')
			shutit_session.send('cat /tmp/000resolvconf.log')
			# Remove it
			shutit_session.send('rm /tmp/000resolvconf.log')
			# Restart networking
			shutit_session.send('systemctl restart networking')
			# The file is back - it also triggered the script
			shutit_session.send('cat /tmp/000resolvconf.log')

			# Resolvconf adds the nameserver to the interface. Normally interface gets this on creation
			shutit_session.send('''echo 'nameserver 10.10.10.10' | /sbin/resolvconf -a enp0s8.inet''')
			# Creates the runtime entry here
			shutit_session.send('''cat /run/resolvconf/interface/enp0s8.inet''')
			# Updates the resolv.conf
			shutit_session.send('resolvconf -u')
			shutit_session.send('cat /etc/resolv.conf')
			# Restart networking removes this... so presumably picks up the dns servers from the interface as it's brought up
			shutit_session.send('systemctl restart networking')
			shutit_session.send('cat /etc/resolv.conf')
			####################################################################

			####################################################################
			# How does interface know 
			# dhclient? https://jameshfisher.com/2018/02/06/what-is-dhcp
			####################################################################
			shutit_session.send('find /run | grep dh')
			shutit_session.send('ps -ef | grep dhclient')
			shutit_session.send('cat /var/lib/dhcp/dhclient.enp0s3.leases')
			shutit_session.send('cat /var/lib/dhcp/dhclient.enp0s8.leases')
			# TODO supercede: https://unix.stackexchange.com/questions/136117/ignore-dns-from-dhcp-server-in-ubuntu?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa
			shutit_session.send('dhclient -r enp0s8 && dhclient -v enp0s8',note='Recreate the DHCP lease')
			shutit_session.send('cat /etc/resolv.conf', note='resolv.conf as before')
			shutit_session.send('''sed -i 's/^#supersede.*/supersede domain-name-servers 8.8.8.8, 8.8.4.4;/' /etc/dhcp/dhclient.conf''')
			shutit_session.send('dhclient -r enp0s8 && dhclient -v enp0s8',note='Recreate the DHCP lease after supersede added')
			shutit_session.send('cat /etc/resolv.conf',note='dns settings overridden')
			shutit_session.send('''sed -i 's/^supersede.*/#supersede/' /etc/dhcp/dhclient.conf''')
			shutit_session.send('dhclient -r enp0s8 && dhclient -v enp0s8',note='Recreate the DHCP lease after supersede removed')
			shutit_session.send('cat /etc/resolv.conf',note='dns settings reverted')
			shutit_session.pause_point('''dhclient: cat /etc/dhcp/dhclient.conf
domain home
nameserver 10.0.2.2
			change the conf to not get dns?''')
			shutit_session.send('cat /run/resolvconf/interface/enp0s3.dhclient')

			#####################################################################
			# PART II
			#####################################################################


			#####################################################################
			## Start systemd-resolved - seems different in vagrant?
			####################################################################
			#shutit_session.send('systemctl enable systemd-resolved')
			#shutit_session.send('systemctl start systemd-resolved')
			#shutit_session.send('cat /etc/resolv.conf')
			##https://wiki.ubuntu.com/OverrideDNSServers

			#####################################################################
			## Install NetworkManager? More about interfaces than anything else
			####################################################################
			#shutit_session.install('network-manager')
			#shutit_session.send('ls /etc/NetworkManager')
			#shutit_session.send('cat /etc/NetworkManager/NetworkManager.conf')
			

			####################################################################
			# Install dnsmasq? See what's changed?
			####################################################################
			shutit_session.install('dnsmasq')
			# dnsmasq running
			shutit_session.send('ps -ef | grep dnsmasq')
			# Nothing in here.
			shutit_session.send('ls -lRt /etc/dnsmasq.d')
			shutit_session.send('systemctl status dnsmasq')
			# resolv.conf now points to 127.0.0.1 - dnsmasq has taken over.
			shutit_session.send('cat /etc/resolv.conf')
			shutit_session.send('cat /var/run/dnsmasq/resolv.conf')
			shutit_session.pause_point('cat /var/run/dnsmasq/resolv.conf')

			# https://foxutech.com/how-to-configure-dnsmasq/
			#Local Caching using NetworkManager
			#Set this in /etc/NetworkManager/NetworkManager.conf:
			#[main]
			#dns=dnsmasq
			#and restart network-manager service.

			#root@linuxdns1:/etc# ls -lRt | grep 15:28
			#drwxr-xr-x 2 root root    4096 Jun  1 15:28 rc0.d
			#drwxr-xr-x 2 root root    4096 Jun  1 15:28 rc1.d
			#drwxr-xr-x 2 root root    4096 Jun  1 15:28 rc2.d
			#drwxr-xr-x 2 root root    4096 Jun  1 15:28 rc3.d
			#drwxr-xr-x 2 root root    4096 Jun  1 15:28 rc4.d
			#drwxr-xr-x 2 root root    4096 Jun  1 15:28 rc5.d
			#drwxr-xr-x 2 root root    4096 Jun  1 15:28 rc6.d
			#drwxr-xr-x 2 root root    4096 Jun  1 15:28 insserv.conf.d
			#drwxr-xr-x 3 root root    4096 Jun  1 15:28 default
			#drwxr-xr-x 2 root root    4096 Jun  1 15:28 init.d
			#drwxr-xr-x 2 root root    4096 Jun  1 15:28 dnsmasq.d
			#lrwxrwxrwx 1 root root  17 Jun  1 15:28 K01dnsmasq -> ../init.d/dnsmasq
			#lrwxrwxrwx 1 root root  17 Jun  1 15:28 K01dnsmasq -> ../init.d/dnsmasq
			#lrwxrwxrwx 1 root root  17 Jun  1 15:28 S02dnsmasq -> ../init.d/dnsmasq
			#lrwxrwxrwx 1 root root  14 Jun  1 15:28 S03cron -> ../init.d/cron
			#lrwxrwxrwx 1 root root  15 Jun  1 15:28 S03rsync -> ../init.d/rsync
			#lrwxrwxrwx 1 root root  17 Jun  1 15:28 S02dnsmasq -> ../init.d/dnsmasq
			#lrwxrwxrwx 1 root root  14 Jun  1 15:28 S03cron -> ../init.d/cron
			#lrwxrwxrwx 1 root root  15 Jun  1 15:28 S03rsync -> ../init.d/rsync
			#lrwxrwxrwx 1 root root  17 Jun  1 15:28 S02dnsmasq -> ../init.d/dnsmasq
			#lrwxrwxrwx 1 root root  14 Jun  1 15:28 S03cron -> ../init.d/cron
			#lrwxrwxrwx 1 root root  15 Jun  1 15:28 S03rsync -> ../init.d/rsync
			#lrwxrwxrwx 1 root root  17 Jun  1 15:28 S02dnsmasq -> ../init.d/dnsmasq
			#lrwxrwxrwx 1 root root  14 Jun  1 15:28 S03cron -> ../init.d/cron
			#lrwxrwxrwx 1 root root  15 Jun  1 15:28 S03rsync -> ../init.d/rsync
			#lrwxrwxrwx 1 root root  17 Jun  1 15:28 K01dnsmasq -> ../init.d/dnsmasq
			#drwxr-xr-x 2 root root 4096 Jun  1 15:28 system.d
			#drwxr-xr-x 2 root root 4096 Jun  1 15:28 update.d
			#drwxr-xr-x 2 root root 4096 Jun  1 15:28 multi-user.target.wants
			#lrwxrwxrwx 1 root root 35 Jun  1 15:28 dnsmasq.service -> /lib/systemd/system/dnsmasq.service

			####################################################################
			# Install NCSD?
			####################################################################
			# The answer is that local processes don't know to connect to /var/run/nscd/socket. Or rather, some do, and some don't. The processes that do know about /var/run/nscd/socket are those linked against glibc and using getaddrinfo from that library.  Only GNU's implementation of the C standard library has the knowledge of /var/run/nscd/socket. If your process is linked against a different libc (e.g. musl), or if your process uses a different runtime (e.g. the Go runtime), it knows nothing of /var/run/nscd/socket. This is your first reason for not using nscd.

			####################################################################
			# Install landrush
			####################################################################

		return True


	def get_config(self, shutit):
		shutit.get_config(self.module_id,'vagrant_image',default='ubuntu/xenial64')
		shutit.get_config(self.module_id,'vagrant_provider',default='virtualbox')
		shutit.get_config(self.module_id,'gui',default='false')
		shutit.get_config(self.module_id,'memory',default='1024')
		shutit.get_config(self.module_id,'swapsize',default='2G')
		return True

def module():
	return shutit_linux_dns(
		'git.shutit_linux_dns.shutit_linux_dns', 3614408475.0001,
		description='',
		maintainer='',
		delivery_methods=['bash'],
		depends=['shutit.tk.setup','shutit-library.virtualization.virtualization.virtualization','tk.shutit.vagrant.vagrant.vagrant']
	)

