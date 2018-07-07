def walkthrough(shutit_session):
	#####################################################################
	# PART I
	#####################################################################

	#####################################################################
	## getaddrinfo - standard C library call... but not everything uses this.
	#####################################################################
	shutit_session.send('strace -e trace=open -f host google.com',     note='Observe (using a strace) that host does not use nsswitch, just references resolv.conf direct.')
	shutit_session.send('strace -e trace=open -f ping -c1 google.com', note='ping, by contrast does reference nsswitch.')
	# gai.conf? You can use gai.conf (for example) to hack ipv4 over ipv6 without switching ipv6 off.
	# https://community.rackspace.com/products/f/public-cloud-forum/5110/how-to-prefer-ipv4-over-ipv6-in-ubuntu-and-centos

	####################################################################
	# NSSWITCH
	####################################################################
	shutit_session.send('ping -c1 google.com',                                                       note='Basic ping on vanilla linux VM to google.com works')
	shutit_session.send('ping -c1 localhost',                                                        note='Basic ping to localhost also works')
	shutit_session.send('ping -c1 linuxdns1',                                                        note='Basic ping to myhostname also works')
	shutit_session.send("sed -i 's/hosts: .*/hosts: files/g' /etc/nsswitch.conf",                    note='Now change nsswitch to only have files rather than "files dns myhostname"')
	shutit_session.send('ping -c1 google.com', check_exit=False,                                     note='google lookup will now fail, as nsswitch does not refer to dns')
	shutit_session.send('host google.com',                                                           note='But host still works - it does not care about nsswitch.')
	shutit_session.send('ping -c1 localhost',                                                        note='And localhost still works, because it is handled by the /etc/hosts file (aka "files")')
	shutit_session.send('cat /etc/hosts',                                                            note='/etc/hosts has localhost in it')
	shutit_session.send("sed -i 's/hosts: .*/hosts: dns/g' /etc/nsswitch.conf",                      note='Now change nsswitch to only have dns')
	shutit_session.send('ping -c1 google.com',                                                       note='Google can now be pinged, as dns is in nsswitch config')
	shutit_session.send('ping -c1 localhost', check_exit=False,                                      note='But localhost will fail as /etc/hosts ("files") not referenced by nsswitch')
	shutit_session.send('ping -c1 linuxdns1', check_exit=False,                                      note='But my hostname will fail as /etc/hosts and /etc/hostname ("myhostname") not referenced by nsswitch')
	shutit_session.send("sed -i 's/hosts: .*/hosts: files dns myhostname/g' /etc/nsswitch.conf",     note='Finally, revert nsswitch to where it was to restore to original state')


	####################################################################
	# resolv.conf
	####################################################################
	# Show resolv.conf is the resolver
	# Change resolv.conf by hand
	shutit_session.send('cat /etc/resolv.conf',                                 note='Contents of /etc/resolv.conf')
	shutit_session.send('ls -l /etc/resolv.conf',                               note='resolvconf turns /etc/resolv.conf into a symlink to the /run folder.')
	shutit_session.send("sed -i 's/^nameserver/#nameserver/' /etc/resolv.conf", note='Take nameserver out of /etc/resolv.conf')
	shutit_session.send('ping -c1 google.com', check_exit=False,                note='google will fail, no nameserver specified by /etc/resolv.conf')
	shutit_session.send("sed -i 's/^#nameserver/nameserver/' /etc/resolv.conf", note='put nameserver back')
	shutit_session.send('ping -c1 google.com',                                  note='ping works again')
	shutit_session.send('ln -f -s /run/resolvconf/resolv.conf /etc/resolv.conf',note='restore symlink')
	shutit_session.send('ping -c1 google', check_exit=False,                    note='Pinging just google fails')
	shutit_session.send('echo search com >> /etc/resolv.conf',                  note='add com to search domain')
	shutit_session.send('ping -c1 google',                                      note='Pinging just google now works')
	shutit_session.send("sed -i '$d' /etc/resolv.conf",                         note='Revert /etc/resolv.conf')

	#####################################################################
	# PART II
	#####################################################################

	# This is now for ubuntu
	shutit_session.send('echo nameserver 10.10.10.10 >> /etc/resolv.conf', note='Add a nameserver by hand')
	shutit_session.send('cat /etc/resolv.conf',                            note='Resolv.conf before network restart')
	shutit_session.send('systemctl restart networking',                    note='Restart networking')
	shutit_session.send('cat /etc/resolv.conf',                            note='Resolv.conf after network restart')


	# Can be 'hacked' with resolvconf -u
	# So Where does resolvconf get its info from?
	shutit_session.send('''echo 'nameserver 10.10.10.10' | /sbin/resolvconf -a enp0s8.inet''', note='Resolvconf can adds the nameserver to the interface. Normally interface gets this on creation eg from DHCP (see later)')
	# Creates the runtime entry here
	shutit_session.send('cat /run/resolvconf/interface/enp0s8.inet', note='10.10.10.10 should now be seen in the run file for this interface')
	shutit_session.send('resolvconf -u',                             note='Updates the resolv.conf')
	shutit_session.send('cat /etc/resolv.conf',                      note='Resolv.conf before network restart')
	shutit_session.send('systemctl restart networking',              note='Restart networking')
	# Type=oneshot
	# EnvironmentFile=-/etc/default/networking
	# ExecStartPre=-/bin/sh -c '[ "$CONFIGURE_INTERFACES" != "no" ] && [ -n "$(ifquery --read-environment --list --exclude=lo)" ] && udevadm settle'
	# ExecStart=/sbin/ifup -a --read-environment
	# ExecStop=/sbin/ifdown -a --read-environment --exclude=lo
	# RemainAfterExit=true

	# ifdown is called first - this triggers a dhclient reset
	# exclude is a trick to stop this ssh session from being killed off
	shutit_session.send('/sbin/ifdown -a --read-environment --exclude=enp0s3')
	shutit_session.send('/sbin/ifup -a --read-environment')

# Also of interest here:
	# https://unix.stackexchange.com/questions/339189/undocumented-read-environment-in-ifup-ifdown-ifquery
	# https://access.redhat.com/solutions/27166 - what does ifup do that ifconfig does not
	# [Service]



	####################################################################
	# How does interface know: dhclient (see above)? https://jameshfisher.com/2018/02/06/what-is-dhcp
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
	# PART III
	#####################################################################
	#####################################################################
	## Install NetworkManager.
	####################################################################
	shutit_session.install('network-manager',                          note='NetworkManager installed, which acts as a hub for all network activity and control.')
# The following network interfaces were found in /etc/network/interfaces
# which means they are currently configured by ifupdown:
# - enp0s8
# If you want to manage those interfaces with NetworkManager instead
# remove their configuration from /etc/network/interfaces.
	shutit_session.send('ls /etc/NetworkManager',                      note='dispatcher.d runs whenever interfaces under its control are updated, conf.d contains your conf files')
	shutit_session.send('cat /etc/NetworkManager/NetworkManager.conf', note='Note that dns=dnsmasq')
	shutit_session.send('systemctl start NetworkManager')
	####################################################################
	# Install dnsmasq? See what's changed?
	####################################################################
	shutit_session.send('ps -ef | grep dnsmasq',               note='Check whether dnsmasq running - it should not be', check_exit=False)
	shutit_session.install('dnsmasq', echo=False)
	shutit_session.send('ps -ef | grep dnsmasq',               note='Check whether dnsmasq running - it should be')
	shutit_session.send('ls -lRt /etc/dnsmasq.d',              note='Show dnsmasq config files - not much in there')
	shutit_session.send('systemctl status --no-pager dnsmasq', note='Get status of dnsmasq')
	shutit_session.send('cat /etc/resolv.conf',                note='resolv.conf now points to 127.0.0.1 - dnsmasq has taken over!')
	shutit_session.send('cat /var/run/dnsmasq/resolv.conf',    note='Look at dnsmasq run file for resolv.conf')
	# TODO: set dnsmasq to log queries with log-queries
	shutit_session.send("sed -i 's/#log-queries/log-queries/g' /etc/dnsmasq.conf")
	shutit_session.send('systemctl restart dnsmasq')
	shutit_session.send('ping -c1 bbc.co.uk')
	shutit_session.send("kill -SIGUSR1 <(cat /var/log/)")
	shutit_session.send('grep -w dnsmasq /var/log/syslog')
#root@linuxdns1:~# grep -w dnsmasq /var/log/syslog 
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: time 1530630488
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: cache size 150, 0/5 cache insertions re-used unexpired cache entries.
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: queries forwarded 2, queries answered locally 0
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: queries for authoritative zones 0
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: server 10.0.2.2#53: queries sent 2, retried or failed 0
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: Host                                     Address                        Flags      Expires
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: linuxdns1                      172.28.128.8                             4FRI   H
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: ip6-localhost                  ::1                                      6FRI   H
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: ip6-allhosts                   ff02::3                                  6FRI   H
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: ip6-localnet                   fe00::                                   6FRI   H
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: ip6-mcastprefix                ff00::                                   6FRI   H
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: ip6-loopback                   ::1                                      6F I   H
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: ip6-allnodes                   ff02::1                                  6FRI   H
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: bbc.co.uk                      151.101.64.81                            4F         Tue Jul  3 15:11:41 2018
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: bbc.co.uk                      151.101.192.81                           4F         Tue Jul  3 15:11:41 2018
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: bbc.co.uk                      151.101.0.81                             4F         Tue Jul  3 15:11:41 2018
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: bbc.co.uk                      151.101.128.81                           4F         Tue Jul  3 15:11:41 2018
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]:                                151.101.64.81                            4 R  NX    Tue Jul  3 15:34:17 2018
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: localhost                      127.0.0.1                                4FRI   H
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: <Root>                         19036   8   2                            SF I
#Jul  3 15:08:08 ubuntu-xenial dnsmasq[15697]: ip6-allrouters                 ff02::2                                  6FRI   H
	shutit_session.pause_point('now play')


	#####################################################################
	# PART IV
	#####################################################################

	#####################################################################
	## Start systemd-resolved - seems different in vagrant?
	####################################################################
	#shutit_session.send('systemctl enable systemd-resolved')
	#shutit_session.send('systemctl start systemd-resolved')
	#shutit_session.send('cat /etc/resolv.conf')
	##https://wiki.ubuntu.com/OverrideDNSServers

	####################################################################
	# Install NCSD?
	####################################################################
	# The answer is that local processes don't know to connect to /var/run/nscd/socket. Or rather, some do, and some don't. The processes that do know about /var/run/nscd/socket are those linked against glibc and using getaddrinfo from that library.  Only GNU's implementation of the C standard library has the knowledge of /var/run/nscd/socket. If your process is linked against a different libc (e.g. musl), or if your process uses a different runtime (e.g. the Go runtime), it knows nothing of /var/run/nscd/socket. This is your first reason for not using nscd.

	####################################################################
	# Install landrush
	####################################################################

#The next part is the fun one, where you find out some lying piece of shit service
#is silently replacing resolve.conf with garbage and/or running a local DNS proxy
#with an opaque configuration that it redirects every request through.
#Or this one piece of software using some insane mechanism that completely
#ignores resolv.conf and also is bypassing your system libc.
#Or you try to keep a consistent first nameserver in resolv.conf by using
#openresolve (eg. set a name_servers in resolveconf.conf so that it gets
#prepended to your network manager's selections) to prevent bullshit hijacking,
#but now nothing works because the network you connected to has a captive portal
#resolvable only by the third address it supplied with DHCP option 6, and libc
#only supports three name servers.
#Or..
#It was never fun, but I hate what DNS resolution has become.



#This is a good write-up. I think there are a couple of things you could add,
#because the POSIX DNS API is actually a little more complex than this, even.
#
#(First, to pick a nit: What you're describing has nothing to do with Linux.
#The specification is POSIX, and the implementation is GNU. All of this applies
#equally to GNU/Windows, aka WSL or "bash on Windows", where there is no Linux
#component.)
#
#GNU libc provides three different name resolution APIs. There is the low-level
#DNS resolver library (RESOLVER(3)) which implements a BSD specification, there
#is gethostbyname (GETHOSTBYNAME(3)) and its related functions which implement
#an obsolete POSIX specification, and there is getaddrinfo (GETADDRINFO(3))
#which is the modern POSIX API for name resolution.
#
#Applications fall into one of maybe three categories. Maybe two. It's
#subjective. The first is older applications which still use the obsolete
#gethostbyname() API. The second is newer applications that use getaddrinfo().
#Both of those will go through the GNU libc NSS service, so they'll parse
#/etc/nsswitch.conf, and from there they might use /etc/hosts, /etc/resolv.conf,
#/etc/hostname, and they might also use multicast DNS or an NSS caching service
#like nscd or sssd. The getaddrinfo API will also consult /etc/gai.conf to order
#address results according to system preference.
#
#The third group of applications (or second group, depending on your point of
#view) is applications that don't use the POSIX NSS APIs at all. This includes
#the "host" utility, because "host" is actually one of the applications included
#with ISC BIND, and it is intended specifically to interface with DNS directly,
#and not the system NSS API. It also includes applications like Firefox which
#bypass NSS and implement their own DNS API for performance reasons. And it
#includes applications which need access to records other than A and AAAA
#records. Such applications will need to use the resolver library or their own
#DNS client library to access MX or TXT records.
#
#I also want to note that "ping localhost" should not fail when nsswitch refers
#only to DNS. A DNS server is required by RFC to resolve the name "localhost".
#The DNS service that you're using is not compliant with standards, due to a
#configuration error.
#
#And, finally, that the documentation for gethostbyname indicates that it will
#fall back to a DNS server on 127.0.0.1, just like ISC's "host" application.
#The documentation for getaddrinfo does not contain such a note, but I suspect
#that it will do the same since those are both part of GNU libc's NSS API.
#
#Thanks for the write-up. I hope this helps.


###############
# IFUP
###############
	#shutit_session.send('strace -f ifup -a --read-environment',      note='What does ifup actually do?')
# Accesses these files:
# root@linuxdns1:~# grep open\( out | grep etc | sed 's/^[0-9]*\(.*\)/\1/' | sort -u
#   open("/etc/ld.so.cache", O_RDONLY|O_CLOEXEC) = 3
#   open("/etc/network/if-pre-up.d/ethtool", O_RDONLY) = 3
#   open("/etc/network/if-pre-up.d/ifenslave", O_RDONLY) = 3
#   open("/etc/network/if-pre-up.d", O_RDONLY|O_NONBLOCK|O_DIRECTORY|O_CLOEXEC) = 3
#   open("/etc/network/if-pre-up.d/vlan", O_RDONLY) = 3
#   open("/etc/network/if-up.d/000resolvconf", O_RDONLY) = 3
#   open("/etc/network/if-up.d/ethtool", O_RDONLY) = 3
#   open("/etc/network/if-up.d/ifenslave", O_RDONLY) = 3
#   open("/etc/network/if-up.d/ip", O_RDONLY) = 3
#   open("/etc/network/if-up.d/openssh-server", O_RDONLY) = 3
#   open("/etc/network/if-up.d", O_RDONLY|O_NONBLOCK|O_DIRECTORY|O_CLOEXEC) = 3
#   open("/etc/network/if-up.d/upstart", O_RDONLY) = 3
#   open("/etc/network/interfaces.d/50-cloud-init.cfg", O_RDONLY) = 4
#   open("/etc/network/interfaces.d", O_RDONLY|O_NONBLOCK|O_DIRECTORY|O_CLOEXEC) = 4
#   open("/etc/network/interfaces", O_RDONLY) = 3

# Also accesses these files:
#  open("//lib/charset.alias", O_RDONLY|O_NOFOLLOW) = -1 ENOENT (No such file or directory)
#  open("/lib/lsb/init-functions.d/01-upstart-lsb", O_RDONLY) = 3
#  open("/lib/lsb/init-functions.d/20-left-info-blocks", O_RDONLY) = 3
#  open("/lib/lsb/init-functions.d/40-systemd", O_RDONLY) = 3
#  open("/lib/lsb/init-functions.d/50-ubuntu-logging", O_RDONLY) = 3
#  open("/lib/lsb/init-functions.d/99-plymouth", O_RDONLY) = 3
#  open("/lib/lsb/init-functions.d", O_RDONLY|O_NONBLOCK|O_DIRECTORY|O_CLOEXEC) = 3
#  open("/lib/lsb/init-functions", O_RDONLY) = 3
#  open("/lib/x86_64-linux-gnu/libc.so.6", O_RDONLY|O_CLOEXEC) = 3
#  open("/lib/x86_64-linux-gnu/libdl.so.2", O_RDONLY|O_CLOEXEC) = 3
#  open("/lib/x86_64-linux-gnu/libgcrypt.so.20", O_RDONLY|O_CLOEXEC) = 3
#  open("/lib/x86_64-linux-gnu/libgpg-error.so.0", O_RDONLY|O_CLOEXEC) = 3
#  open("/lib/x86_64-linux-gnu/liblzma.so.5", O_RDONLY|O_CLOEXEC) = 3
#  open("/lib/x86_64-linux-gnu/libpcre.so.3", O_RDONLY|O_CLOEXEC) = 3
#  open("/lib/x86_64-linux-gnu/libply.so.4", O_RDONLY|O_CLOEXEC) = 3
#  open("/lib/x86_64-linux-gnu/libpthread.so.0", O_RDONLY|O_CLOEXEC) = 3
#  open("/lib/x86_64-linux-gnu/librt.so.1", O_RDONLY|O_CLOEXEC) = 3
#  open("/lib/x86_64-linux-gnu/libselinux.so.1", O_RDONLY|O_CLOEXEC) = 3
#  open("/proc/cmdline", O_RDONLY)   = 6
#  open("/proc/filesystems", O_RDONLY) = 3
#  open("/proc/self/stat", O_RDONLY|O_CLOEXEC) = 3
#  open("/run/network/ifstate.enp0s3", O_RDWR|O_CREAT|O_APPEND, 0666) = 3
#  open("/run/network/ifstate.enp0s8", O_RDWR|O_CREAT|O_APPEND, 0666) = 3
#  open("/run/network/ifstate.lo", O_RDWR|O_CREAT|O_APPEND, 0666) = 3
#  open("/sys/fs/kdbus/0-system/bus", O_RDWR|O_NOCTTY|O_CLOEXEC) = -1 ENOENT (No such file or directory)

#root@linuxdns1:~# grep '^[0-9]*  execve' out | sed 's/^[0-9]*\(.*\)/\1/' 
#  execve("/sbin/ifup", ["ifup", "-a", "--read-environment"], [/* 16 vars */]) = 0
#  execve("/bin/sh", ["/bin/sh", "-c", "/bin/run-parts --exit-on-error /"...], [/* 9 vars */]) = 0
#  execve("/bin/run-parts", ["/bin/run-parts", "--exit-on-error", "/etc/network/if-pre-up.d"], [/* 9 vars */] <unfinished ...>
#  execve("/etc/network/if-pre-up.d/ethtool", ["/etc/network/if-pre-up.d/ethtool"], [/* 9 vars */]) = 0
#  execve("/etc/network/if-pre-up.d/ifenslave", ["/etc/network/if-pre-up.d/ifensla"...], [/* 9 vars */]) = 0
#  execve("/etc/network/if-pre-up.d/vlan", ["/etc/network/if-pre-up.d/vlan"], [/* 9 vars */]) = 0
#  execve("/bin/sh", ["/bin/sh", "-c", "/bin/run-parts --exit-on-error /"...], [/* 9 vars */]) = 0
#  execve("/bin/run-parts", ["/bin/run-parts", "--exit-on-error", "/etc/network/if-up.d"], [/* 9 vars */]) = 0
#  execve("/etc/network/if-up.d/000resolvconf", ["/etc/network/if-up.d/000resolvco"...], [/* 9 vars */]) = 0
#  execve("/etc/network/if-up.d/ethtool", ["/etc/network/if-up.d/ethtool"], [/* 9 vars */]) = 0
#  execve("/bin/sed", ["sed", "-n", "\n/^IF_ETHERNET_PAUSE_[A-Za-z0-9_"...], [/* 9 vars */]) = 0
#  execve("/bin/sed", ["sed", "-n", "\n/^IF_HARDWARE_IRQ_COALESCE_[A-Z"...], [/* 9 vars */]) = 0
#  execve("/bin/sed", ["sed", "-n", "\n/^IF_HARDWARE_DMA_RING_[A-Za-z0"...], [/* 9 vars */] <unfinished ...>
#  execve("/bin/sed", ["sed", "-n", "\n/^IF_OFFLOAD_[A-Za-z0-9_]*=/ {\n"...], [/* 9 vars */] <unfinished ...>
#  execve("/etc/network/if-up.d/ifenslave", ["/etc/network/if-up.d/ifenslave"], [/* 9 vars */]) = 0
#  execve("/etc/network/if-up.d/ip", ["/etc/network/if-up.d/ip"], [/* 9 vars */]) = 0
#  execve("/etc/network/if-up.d/openssh-server", ["/etc/network/if-up.d/openssh-ser"...], [/* 9 vars */]) = 0
#  execve("/etc/network/if-up.d/upstart", ["/etc/network/if-up.d/upstart"], [/* 9 vars */]) = 0
#  execve("/bin/run-parts", ["run-parts", "--lsbsysinit", "--list", "/lib/lsb/init-functions.d"], [/* 9 vars */]) = 0
#  execve("/bin/systemctl", ["systemctl", "-p", "LoadState", "show", "upstart.service"], [/* 9 vars */]) = 0
#  execve("/bin/readlink", ["readlink", "-f", "/etc/network/if-up.d/upstart"], [/* 9 vars */]) = 0
#  execve("/bin/plymouth", ["plymouth", "--ping"], [/* 9 vars */]) = 0
	####################################################################
