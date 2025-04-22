#!/bin/bash
# Script to check subdomains from a list and output only active ones to a file

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <domain_name> [subdomain_list_file] [output_file]"
    echo "Example: $0 example.com subdomains.txt active_subdomains.txt"
    echo "If no subdomain list file is provided, 'list.txt' will be used"
    echo "If no output file is provided, 'active_subdomains.txt' will be used"
    exit 1
fi

DOMAIN=$1
SUBDOMAIN_FILE=${2:-list.txt}
OUTPUT_FILE=${3:-active_subdomains.txt}

if [ ! -f "$SUBDOMAIN_FILE" ]; then
    echo "Error: Subdomain list file '$SUBDOMAIN_FILE' not found"
    exit 1
fi

echo "Checking subdomains for $DOMAIN using list from $SUBDOMAIN_FILE..."
echo "Only active subdomains will be saved to $OUTPUT_FILE"
echo "-------------------------------------------------------------"

# Create or clear the output file
> "$OUTPUT_FILE"

# Counter for active subdomains
active_count=0

# Loop through each subdomain in the file
while read subdomain; do
    # Skip empty lines
    [ -z "$subdomain" ] && continue
    
    # Construct full domain name
    FULL_DOMAIN="${subdomain}.${DOMAIN}"
    
    # Use host command to resolve domain
    host_result=$(host "$FULL_DOMAIN" 2>&1)
    
    # Check if the host command was successful and domain is active
    if echo "$host_result" | grep -q "has address"; then
        ip=$(echo "$host_result" | grep "has address" | head -1 | awk '{print $NF}')
        echo -e "[\033[0;32mACTIVE\033[0m] $FULL_DOMAIN ($ip)"
        
        # Write the active subdomain to the output file (with optional IP address)
        echo "$FULL_DOMAIN,$ip" >> "$OUTPUT_FILE"
        
        # Increment the counter
        ((active_count++))
    fi
done < "$SUBDOMAIN_FILE"

echo "-------------------------------------------------------------"
echo "Found $active_count active subdomains and saved to $OUTPUT_FILE"
