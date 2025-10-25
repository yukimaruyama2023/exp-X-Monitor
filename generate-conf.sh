#!/bin/bash
set -euo pipefail

if [ -d conf ] ; then
	echo "Config already exists"
	exit 1
fi

cp -r conf.template conf

find conf -name netdata.conf | while read f ; do
	echo "=== $f ==="
	sed -i "s|XXXXXXXX_CONF_ROOT|`pwd`/conf|" $f 
	echo
done

