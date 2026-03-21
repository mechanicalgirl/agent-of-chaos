#!/bin/bash
service postfix restart
service dovecot start
exec /usr/sbin/sshd -D
