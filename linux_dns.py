def walkthrough(shutit_session):
	#####################################################################
	# PART I
	#####################################################################

	#####################################################################
	## getaddrinfo - standard C library call... but not everything uses this.
	#####################################################################
	shutit_session.send('strace -e trace=openat -f host google.com',     note='Observe (using a strace) that host does not use nsswitch, just references resolv.conf direct.')
	shutit_session.send('strace -e trace=openat -f ping -c1 google.com', note='ping, by contrast does reference nsswitch.')
	# gai.conf?
	# You can use gai.conf to hack ipv4 over ipv6 without switching ipv6 off.
	# https://community.rackspace.com/products/f/public-cloud-forum/5110/how-to-prefer-ipv4-over-ipv6-in-ubuntu-and-centos

	####################################################################
	# NSSWITCH
	####################################################################
	# Can we ping ok?
	shutit_session.send('ping -c1 google.com',                                                       note='Basic ping on vanilla linux VM to google.com works')
	shutit_session.send('ping -c1 localhost',                                                        note='Basic ping to localhost also works')
	shutit_session.send("sed -i 's/hosts: .*/hosts: files/g' /etc/nsswitch.conf",                    note='Now change nsswitch to only have files rather than "files dns myhostname"')
	shutit_session.send('ping -c1 google.com',                                                       note='google lookup will now fail, as nsswitch does not refer to dns', check_exit=False)
	shutit_session.send('ping -c1 localhost',                                                        note='But localhost still works, because it is handled by the /etc/hosts file (aka "files"')
	shutit_session.send('cat /etc/hosts',                                                            note='/etc/hosts has localhost in it')
	shutit_session.send("sed -i 's/hosts: .*/hosts: dns/g' /etc/nsswitch.conf",                      note='Now change nsswitch to only have dns')
	shutit_session.send('ping -c1 google.com',                                                       note='Google can now be pinged, as dns is in nsswitch config')
	shutit_session.send('ping -c1 localhost',                                                        note='But localhost will fail as /etc/hosts ("files") not referenced by nsswitch', check_exit=False)
	shutit_session.send("sed -i 's/hosts: .*/hosts: files dns myhostname/g' /etc/nsswitch.conf",     note='Finally, revert nsswitch to where it was to restore to original state')


	####################################################################
	# resolvconf
	####################################################################
	# Show resolv.conf is the resolver
	# Change resolv.conf by hand
	shutit_session.send('cat /etc/resolv.conf',                                 note='resolvconf turns /etc/resolv.conf into a symlink to the /run folder.')
	shutit_session.send('ls -l /etc/resolv.conf',                               note='resolvconf turns /etc/resolv.conf into a symlink to the /run folder.')
	shutit_session.send("sed -i 's/^nameserver/#nameserver/' /etc/resolv.conf", note='Take nameserver out of /etc/resolv.conf')
	shutit_session.send('ping -c1 google.com',                                  note='google will fail, no nameserver specified by /etc/resolv.conf', check_exit=False)
	shutit_session.send("sed -i 's/^#nameserver/nameserver/' /etc/resolv.conf", note='put nameserver back')
	shutit_session.send('ping -c1 google.com',                                  note='ping works again')
	shutit_session.send('ln -f -s /run/resolvconf/resolv.conf /etc/resolv.conf',note='restore symlink')

	# So Where does resolvconf get its info from?
	# Plug in a log file triggered whenever the 000resolvconf script gets run
	shutit_session.send("sed -i '2s@^.*@echo I am triggered by ifup > /tmp/000resolvconf.log@' /etc/network/if-up.d/000resolvconf",note='Add a probe within the 000resolvconf file to prove when it is triggered.')
	# Running ifup/ifdown triggers it...
	shutit_session.send('ifdown enp0s8',                note='Bring network interface down')
	shutit_session.send('ls /tmp/000resolvconf.log',    note='File not created on ifdown', check_exit=False)
	shutit_session.send('ifup enp0s8',                  note='Bring up network interface, which triggers probe above')
	shutit_session.send('cat /tmp/000resolvconf.log',   note='File has now been created')
	shutit_session.send('rm /tmp/000resolvconf.log',    note='Remove that file')
	shutit_session.send('systemctl restart networking', note='Restart networking')
	shutit_session.send('cat /tmp/000resolvconf.log',   note='The file is back - it also triggered the script')

	shutit_session.send('''echo 'nameserver 10.10.10.10' | /sbin/resolvconf -a enp0s8.inet''', note='Resolvconf can adds the nameserver to the interface. Normally interface gets this on creation eg from DHCP (see later)')
	# Creates the runtime entry here
	shutit_session.send('cat /run/resolvconf/interface/enp0s8.inet', note='10.10.10.10 should now be seen in the run file for this interface')
	shutit_session.send('resolvconf -u',                             note='Updates the resolv.conf')
	shutit_session.send('cat /etc/resolv.conf',                      note='Resolv.conf before network restart')
	shutit_session.send('systemctl restart networking',              note='Restart networking')
	# Restart networking removes this... so presumably picks up the dns servers from the interface as it's brought up
	shutit_session.send('cat /etc/resolv.conf',                      note='Nameserver we added has gone')
	####################################################################

	####################################################################
	# How does interface know: dhclient? https://jameshfisher.com/2018/02/06/what-is-dhcp
	####################################################################
	shutit_session.send('find /run | grep dh',                                  note='Hunt for dhcp files')
	shutit_session.send('ps -ef | grep dhclient',                               note='Hunt for dhclient processes')
	shutit_session.send('cat /var/lib/dhcp/dhclient.enp0s3.leases',             note='Interface 3 lease')
	shutit_session.send('cat /var/lib/dhcp/dhclient.enp0s8.leases',             note='Interface 8 lease')
	# TODO supercede: https://unix.stackexchange.com/questions/136117/ignore-dns-from-dhcp-server-in-ubuntu?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa
	shutit_session.send('dhclient -r enp0s8 && dhclient -v enp0s8',             note='Recreate the DHCP lease')
	shutit_session.send('cat /etc/resolv.conf',                                 note='resolv.conf as before')
	shutit_session.send('ln -f -s /run/resolvconf/resolv.conf /etc/resolv.conf',note='restore symlink')
	shutit_session.send("sed -i 's/^#supersede.*/supersede domain-name-servers 8.8.8.8, 8.8.4.4;/' /etc/dhcp/dhclient.conf",
		                                                                        note='We can override the dns got from dhcp by setting supersed in the dhclient.conf file')
	shutit_session.send('dhclient -r enp0s8 && dhclient -v enp0s8',             note='Recreate the DHCP lease after supersede added')
	shutit_session.send('cat /etc/resolv.conf',                                 note='dns settings overridden in the resolv.conf')
	shutit_session.send("sed -i 's/^supersede.*/#supersede/' /etc/dhcp/dhclient.conf",
		                                                                        note='Revert the supersede setting')
	shutit_session.send('dhclient -r enp0s8 && dhclient -v enp0s8',             note='Recreate the DHCP lease after supersede removed')
	shutit_session.send('cat /etc/resolv.conf',                                 note='dns settings reverted')
	shutit_session.send('cat /run/resolvconf/interface/enp0s3.dhclient',        note='dhclient settings now in /run')



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
	shutit_session.install('dnsmasq', echo=False)
	shutit_session.send('ps -ef | grep dnsmasq',               note='Check whether dnsmasq running')
	shutit_session.send('ls -lRt /etc/dnsmasq.d',              note='Show dnsmasq config files - not much in there')
	shutit_session.send('systemctl status --no-pager dnsmasq', note='Get status of dnsmasq')
	shutit_session.send('cat /etc/resolv.conf',                note='resolv.conf now points to 127.0.0.1 - dnsmasq has taken over!')
	shutit_session.send('cat /var/run/dnsmasq/resolv.conf',    note='Look at dnsmasq run file for resolv.conf')
	shutit_session.pause_point('now play')

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
