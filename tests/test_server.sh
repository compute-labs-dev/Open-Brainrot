#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

test_endpoint() {
    local endpoint=$1
    local method=$2
    local data=$3
    local description=$4
    
    echo -e "${BLUE}Testing: ${description}${NC}"
    
    # Print the curl command for debugging
    echo "Endpoint: http://localhost:5500${endpoint}"
    echo "Data: ${data}"
    
    # Make the API call using curl with verbose output
    response=$(curl -v -X ${method} \
        -H "Content-Type: application/json" \
        -d "${data}" \
        "http://localhost:5500${endpoint}" 2>&1)
    
    # Print the full response
    echo -e "${BLUE}Response:${NC}"
    echo "$response"
    
    # Check if curl command was successful
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Success: API call completed${NC}"
    else
        echo -e "${RED}Error: API call failed${NC}"
    fi
    
    # Add a separator between tests
    echo -e "\n${BLUE}----------------------------------------${NC}\n"
}


echo -e "${BLUE}Testing text generation with all voices${NC}"

read -r -d '' text << 'EOF'
This is an example of a Daily Digest. In this example, we are going to be talking about the latest news in the world of AI and Machine Learning. Subscribe to our channel to get more videos like this one!
EOF

# Escape the text for JSON
json_text=$(printf '%s' "$text" | jq -R -s '.')

# Test the generate_multiple endpoint with multiple voices at once
# echo -e "${BLUE}Testing generate_multiple endpoint${NC}"
# test_endpoint "/generate" "POST" "{
#     \"text\": ${json_text},
#     \"voices\": [\"donald_trump\", \"walter_cronkite\", \"southpark_eric_cartman\", \"keanu_reeves\", \"fireship\"],
#     \"model\": \"o3mini\",
#     \"video\": \"minecraft\"
# }" "Generating multiple videos with different voices simultaneously"

# Test the generate endpoint with a specific digest_id
echo -e "${BLUE}Testing generate endpoint with digest_id${NC}"
test_endpoint "/generate" "POST" "{
    \"text\": \"This is a test with a specific digest_id\",
    \"model\": \"o3mini\", 
    \"voices\": [\"donald_trump\"],
    \"video\": \"minecraft\",
    \"digest_id\": \"bed3b9e4-e6bb-42e8-9a75-2d9075acc3ad\"
}" "Generating a video with a specific digest_id"

echo -e "\n${GREEN}All tests completed!${NC}"

