num_memcacheds = [1,5,10]

conf_root = f"./conf"

for num_memcached in num_memcacheds:
	netdata_conf = f"{conf_root}/{num_memcached}mcd/netdata.conf"
	subprocess.run(f"netdata -c {netdata_conf}".split())

	######################

