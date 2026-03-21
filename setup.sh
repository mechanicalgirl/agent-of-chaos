#!/bin/bash

CHAOS_LEVEL=${1:-medium}  # low, medium, high
LOG="/var/log/setup_manifest.txt"
echo "=== Setup Manifest ===" > $LOG
echo "Generated: $(date)" >> $LOG
echo "" >> $LOG

log() {
    echo "$1" | tee -a $LOG
}

log "=== Agent of Chaos Setup Manifest ==="
log "Generated: $(date)"
log "Chaos Level: $CHAOS_LEVEL"
log ""

# === CHAOS BEGINS HERE ===
log ""
log "=== Chaos Level: $CHAOS_LEVEL ==="

case $CHAOS_LEVEL in
    low)
        # minimal chaos
        ;;
    medium)
        # moderate chaos
        ;;
    high)
        # maximum chaos
        ;;
esac

# deliberately break something
# log ""
# log "=== Intentional Chaos ==="
# chmod 000 /etc/dovecot/dovecot.conf
# log "dovecot.conf: permissions set to 000"

# scatter some files
# log ""
# log "=== Scattered Files ==="
# echo "TODO: ask Dave about the mail relay config" > /opt/notes-2011.txt
# log "created: /opt/notes-2011.txt"

