#!/bin/bash

if [ `ps -ef | grep "python.*celery.*$1" | wc -l` -lt 2 ]
then
    echo '['`date`'] Celery processes appear to be down, restarting:' >&2
    rm -rf /tmp/namecheap.lock
    /etc/init.d/celeryd restart
else
    echo '['`date`'] Celery processes appear to running, no restart required.' >&2
fi
