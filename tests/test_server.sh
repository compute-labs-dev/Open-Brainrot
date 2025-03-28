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

echo -e "${BLUE}Testing Daily Digests Generation${NC}"

# April 9th Digest
read -r -d '' april_9_digest << 'DIGEST9'
### Daily Digest (Apr 9, 2025) – AI, Compute, & Web3

🌎 **Macro:**
• 🇺🇸 **White House** confirms **104% tariffs** on China went into effect at noon, with threat of additional **50%**.
• 🇨🇦 Canada imposes **25% tariffs** on some US-made cars in retaliation to American auto industry tariffs.
• 🇰🇷 South Korea announces it will not retaliate against US tariffs, seeks new trade agreement instead.

💻 **Technology & Infrastructure:**
• **Apple** flies five planes loaded with iPhones to bypass US tariffs, plans to shift production to India.
• **RedStone** launches "**Bolt**" oracle on **MegaETH**, delivering price data updates every **2.4 milliseconds**.
• **Samsung** reports slight **0.2%** Q1 operating profit decline despite tariff concerns, lifted by memory chip sales.

🤖 **AI & Research:**
• **Google** rolls out **Project Astra** capabilities in **Gemini Live**, enabling real-time visual AI conversations.
• **Runway** releases **Gen-4 Turbo**, producing **10-second videos** in just **30 seconds** across all plans.
• **Amazon** introduces **Nova Sonic** speech model that understands natural pauses and handles conversation interruptions.

🪙 **Crypto/Web3:**
• **Ripple** acquires prime broker **Hidden Road** for **$1.25 billion**, one of largest crypto acquisitions ever.
• 🇺🇸 US **Justice Department** disbands crypto enforcement team, shifts focus from exchanges to individual fraudsters.
• **Teucrium** launches first-ever **XRP ETF** with 2x leverage on **NYSE Arca** exchange today.
• **Aavegotchi** NFT gaming community votes to migrate from **Polygon** to **Base** (**Coinbase**'s Layer 2 Network).
• 🇨🇦 **Bank of Canada** releases research evaluating flash loans and their potential implications for financial stability.
DIGEST9

# April 8th Digest
read -r -d '' april_8_digest << 'DIGEST8'
### Daily Digest (Apr 8, 2025) – AI, Compute, & Web3

**🌎 Macro:**
• 🇺🇸 **White House** confirms **104%** tariffs on **China** went into effect at noon today, escalating global trade tensions.
• 🇨🇳 **China** vows to "**fight to the end**" against US tariffs, warns against "intimidation and blackmail."
• 🇨🇦 **Canada** implements **25%** tariffs on certain US-made vehicles effective April 9 in response to US auto industry tariffs.

**💻 Technology & Infrastructure:**
• **Apple** airlifted multiple planes of **iPhones** to US to bypass tariffs, showing tech industry scrambling to adapt.
• **TSMC** faces **100%** tariffs if they don't build factories in the US, pressuring semiconductor supply chain.
• **Samsung Electronics** reports better-than-expected Q1 results with only **0.2%** profit decline, partly driven by tariff concerns.

**🤖 AI & Research:**
• **Google** begins rolling out "**Project Astra**" in **Gemini Live**, enabling real-time visual AI conversations through phone cameras.
• **Gemini 2.5 Pro** now powers **Google's** Deep Research feature, significantly boosting performance over previous capabilities.
• **ElevenLabs** introduces **MCP** server integration, allowing AI platforms to access voice capabilities through simple text prompts.

**🪙 Crypto/Web3:**
• **Ripple** acquires prime broker **Hidden Road** for **$1.25 billion**, one of crypto's largest acquisitions to date.
• 🇺🇸 US **Justice Department** disbands crypto enforcement team, ending "regulation by prosecution" approach to digital assets.
• 🇺🇸 US **Senate** schedules vote on **SEC Chairman** nominee **Paul Atkins** tomorrow, with potential confirmation by evening.
DIGEST8

# Escape the texts for JSON
json_april_9=$(printf '%s' "$april_9_digest" | jq -R -s '.')
json_april_8=$(printf '%s' "$april_8_digest" | jq -R -s '.')

# Test April 9th Digest
echo -e "${BLUE}Testing April 9th Digest${NC}"
test_endpoint "/generate" "POST" "{
    \"text\": ${json_april_9},
    \"model\": \"o3mini\",
    \"voices\": [\"donald_trump\", \"walter_cronkite\", \"southpark_eric_cartman\", \"keanu_reeves\", \"fireship\"],
    \"video\": \"minecraft\",
    \"digest_id\": \"2025-04-09\"
}" "Generating video for April 9th Digest"

# Test April 8th Digest
echo -e "${BLUE}Testing April 8th Digest${NC}"
test_endpoint "/generate" "POST" "{
    \"text\": ${json_april_8},
    \"model\": \"o3mini\",
    \"voices\": [\"donald_trump\", \"walter_cronkite\", \"southpark_eric_cartman\", \"keanu_reeves\", \"fireship\"],
    \"video\": \"minecraft\",
    \"digest_id\": \"2025-04-08\"
}" "Generating video for April 8th Digest"

echo -e "\n${GREEN}All tests completed!${NC}"

