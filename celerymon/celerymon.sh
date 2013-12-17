#!/bin/bash

if [ `ps -ef | grep "python.*celery.*worker.*$1" | wc -l` -lt 2 ]
then
    echo '['`date`'] Celery processes appear to be down, restarting:' >&2
    rm -rf /tmp/namecheap.lock
    /etc/init.d/celeryd restart
else
    echo '['`date`'] Celery processes appear to running, no restart required.' >&2
fi

if [ `ps -ef | grep "python.*celerybeat.*$2" | wc -l` -lt 2 ]
then
    echo '['`date`'] Celerybeat process appears to be down, restarting: ' >&2
    /etc/init.d/celerybeat restart
else
    echo '['`date`'] Celerybeat process appears to be running, no restart required.' >&2
fi

