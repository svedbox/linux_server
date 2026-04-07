#!/bin/bash

set -e  # Exit immediately if any command fails
mkdir -p /home/pi/geoban

#US_LIST_URL="https://www.ipdeny.com/ipblocks/data/countries/us.zone"
US_LIST_URL="https://www.ipdeny.com/ipblocks/data/aggregated/us-aggregated.zone"
US_ZONE="/home/pi/geoban/us.zone"

echo "Downloading US zone file..."
if ! wget -q -O "$US_ZONE" "$US_LIST_URL"; then
    echo "Failed to download US zone file"
    exit 1
fi

if [ ! -s "$US_ZONE" ]; then
    echo "US zone file is empty or missing!"
    exit 1
fi


# Read IPs from the file and add to the array
while read -r line; do
    ip_list+=("$line")
done < "$US_ZONE"

echo "Flushing nftables..."
nft flush ruleset
nft add table inet filter
nft add chain inet filter input { type filter hook input priority 0 \; policy drop \; }
nft add rule inet filter input iif "lo" accept
nft add rule inet filter input ct state established,related accept
nft add rule inet filter input ip saddr 192.168.0.0/24 accept

# Create a whitelist set in nftables
nft add set inet filter whitelist { type ipv4_addr \; flags interval \; }

echo "Adding IPs to whitelist in batches..."

batch_size=20000  # Adjust if needed
batch=()

for ip in "${ip_list[@]}"; do
    batch+=("$ip")
    if [[ ${#batch[@]} -ge $batch_size ]]; then
        batch_str=$(IFS=,; echo "${batch[*]}")  # Convert array to comma-separated string
        nft add element inet filter whitelist { $batch_str }
        batch=()
    fi
done

# Add remaining IPs in the last batch
if [[ ${#batch[@]} -gt 0 ]]; then
    batch_str=$(IFS=,; echo "${batch[*]}")
    nft add element inet filter whitelist { $batch_str }
fi

echo "Applying firewall rules..."
nft add rule inet filter input ip saddr @whitelist tcp dport 60023 ct count over 2 drop
nft add rule inet filter input ip saddr @whitelist tcp dport 60023 accept
nft add rule inet filter input ip saddr @whitelist tcp dport 80 accept
nft add rule inet filter input ip saddr @whitelist tcp dport 443 accept
nft add rule inet filter input ip saddr @whitelist tcp dport 60025 accept
nft add rule inet filter input ip saddr @whitelist tcp dport 5349 accept
nft add rule inet filter input ip saddr @whitelist udp dport 5349 accept
nft add rule inet filter input ip saddr @whitelist udp dport 3478 accept
nft add rule inet filter input ip saddr @whitelist udp dport 60025 accept
nft add rule inet filter input ip saddr @whitelist udp dport 60024 accept
nft add rule inet filter input ip saddr 10.10.200.0/24 ip daddr 192.168.0.0/24 accept

echo "Configuring NAT..."
nft add table ip nat
nft add chain ip nat POSTROUTING { type nat hook postrouting priority srcnat \; policy accept \; }
nft add rule ip nat POSTROUTING oifname "eth0" ip saddr 10.10.200.0/24 masquerade

echo "Restarting fail2ban..."
systemctl restart fail2ban &  # Run in background to prevent freezing
systemctl restart crowdsec &
echo "*** Done ***"
