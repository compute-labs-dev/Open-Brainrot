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
Agent Daily Digest Bot
APP  Today at 2:36 AM
Daily Digest (Mar 4, 2025) – AI, Compute, & Web3
:earth_americas: Macro:
• :us: Trump's 25% tariffs on Canada and Mexico, 20% on China took effect; all three countries announced retaliatory measures.
• :us: Treasury Secretary Bessent confirms administration is "set on bringing interest rates down."
• :us: IRS drafting plans to cut up to half of its 90,000-person workforce through layoffs and buyouts.
:computer: Technology & Infrastructure:
• BlackRock consortium acquires Hutchison Port Holdings for $23 billion, gaining control of 43 ports in 23 countries.
• T-Mobile's parent Deutsche Telekom announced sub-$1K AI phone with Perplexity Assistant launching later this year.
• Reddit co-founder Alexis Ohanian joins bid to acquire TikTok US and "bring it on-chain."
:robot_face: AI & Research:
• OpenAI launching NextGenAI consortium with 15 leading institutions to advance AI research and education.
• Microsoft debuts Dragon Copilot for healthcare, automating clinical documentation with ambient listening and voice dictation.
• Google's Project Astra video capabilities coming to Android this month for Gemini Advanced subscribers.
:coin: Crypto/Web3:
• :us: White House crypto summit scheduled for Friday; Coinbase CEO and MicroStrategy's Michael Saylor among confirmed attendees.
• :flag-mx: Mexican billionaire Ricardo Salinas allocates 70% of his $5.8 billion portfolio to Bitcoin.
• :flag-sv: El Salvador President Bukele affirms country will continue Bitcoin purchases despite IMF's request to stop.
• :us: White House announces support for rescinding the DeFi broker rule, calling it "an 11th hour attack on crypto."
• Bybit hackers successfully launder 100% of stolen $1.4 billion in crypto within 10 days.
See less
Tweet Processing Stats:
• Total Tweets: 342
• Filtered Out: 267
• Quality Tweets: 75
• Quality Rate: 21.9%
• Word Count: 1,795
Additional Source Stats:
• Telegram Messages: 117 (2,250 words)
• RSS Articles: 41 (8,739 words)
Token Usage Stats:
• Prompt Tokens: 50382
• Completion Tokens: 1772
• Reasoning Tokens: 1156
• Total Tokens: 52154
AI Model:
• Provider: Anthropic
• Model: claude-3-7-sonnet-20250219
8 replies

Agent Daily Digest Bot
APP  Today at 2:36 AM
:earth_americas: Macro Analysis (Part 1/2)
• :us: Trump's 25% tariffs on Canada and Mexico, 20% on China took effect; all three countries announced retaliatory measures.
President Trump's tariffs officially went into effect on Tuesday, imposing 25% duties on imports from Canada and Mexico and 20% on Chinese goods. In response, all three countries announced countermeasures. China is imposing tariffs up to 15% on key U.S. farm exports including chicken, pork, soy, and beef, while expanding export restrictions on about two dozen U.S. companies. Canada announced it would implement retaliatory tariffs on over $100 billion of American goods over 21 days, and Mexico indicated it would announce its specific tariffs by Sunday. Moody's Chief Economist Mark Zandi warned these measures could push the U.S. economy into stagflation, with Atlanta Fed's GDPNow model showing the economy potentially contracting 2.8% in Q1. There are indications of possible relief, with Commerce Secretary Howard Lutnick suggesting Trump might announce tariff accommodations for Canada and Mexico as early as tomorrow.
Sources:
• Tweets: @WatcherGuru on tariffs taking effect, @elerianm on retaliation, @unusual_whales on Commerce Secretary comments
• Articles: AP News "What to know about Trump's tariffs and their impact on businesses and shoppers"
• Telegram: PANews reporting on Moody's stagflation warning
• :us: Treasury Secretary Bessent confirms administration is "set on bringing interest rates down."
U.S. Treasury Secretary Scott Bessent has made multiple clear statements that the Trump administration is focused on lowering interest rates. This explicit commitment marks a significant policy position from the Treasury Department. Market expectations have already shifted in response, with forecasts for Federal Reserve rate cuts in 2025 rising from a 15% probability to nearly 25% within just one week. Bessent's statements come amid broader economic concerns, including the potential impact of new tariffs. His remarks also indicated support for Trump's tariff policies, dismissing market concerns and claiming that Chinese manufacturers would ultimately absorb the costs rather than American consumers.
Sources:
• Tweets: @WatcherGuru, @Cointelegraph, and @DegenerateNews all quoted Bessent's "we're set on bringing interest rates down" statement
• Tweets: @Tyler_Did_It showing Fed rate cut probability data
• :us: IRS drafting plans to cut up to half of its 90,000-person workforce through layoffs and buyouts.
See less
2:36
:earth_americas: Macro Analysis (Part 2/2)
The Internal Revenue Service is preparing dramatic staffing reductions that would cut its 90,000-person workforce by as much as half. According to AP sources, the agency is developing plans for a combination of layoffs, attrition, and incentivized buyouts. The IRS has already laid off approximately 7,000 probationary employees with less than one year of service in February. Current staff demographics show people of color represent 56% of IRS workers, with women making up 65%. Additionally, the agency offered "deferred resignation program" buyouts to employees, though tax season workers cannot accept these until mid-May after the filing deadline. Former IRS Commissioner John Koskinen warned such reductions would render the agency "dysfunctional."
Sources:
• Tweets: @AutismCapital, @WatcherGuru, and @unusual_whales all reported on the 50% workforce reduction
• Articles: AP News "The IRS is drafting plans to cut as much as half of its 90,000-person workforce, AP sources say"
See less
2:36
:computer: Technology & Infrastructure Analysis (Part 1/2)
• BlackRock consortium acquires Hutchison Port Holdings for $23 billion, gaining control of 43 ports in 23 countries.
BlackRock and partners have acquired Hong Kong-based CK Hutchison's port operations in a deal valued at nearly $23 billion, including $5 billion in debt. The transaction gives the BlackRock consortium control over 43 ports across 23 countries, including the strategically crucial ports of Balboa and Cristobal positioned at either end of the Panama Canal. This acquisition effectively places these critical shipping infrastructure assets under American control, addressing concerns raised by President Trump, who had alleged Chinese interference with Panama Canal operations. The deal excludes ports in Hong Kong, Shenzhen, and South China. U.S. Senator Ted Cruz had previously raised national security concerns, stating that these ports "give China ready observation posts" that could potentially block passage through the canal.
Sources:
• Articles: AP News "BlackRock strikes deal to bring ports on both sides of Panama Canal under American control"
• T-Mobile's parent Deutsche Telekom announced sub-$1K AI phone with Perplexity Assistant launching later this year.
Deutsche Telekom, T-Mobile's parent company, is developing an AI-focused smartphone priced under $1,000 that will launch later this year. The device will feature Perplexity Assistant as its central interface, designed to eliminate traditional app-based navigation models. This represents a significant shift toward AI-native mobile experiences. Beyond Perplexity integration, the phone will incorporate additional AI tools from Google, ElevenLabs, and PicsArt, creating a comprehensive AI ecosystem in a mobile form factor. This announcement follows the broader industry trend of integrating more sophisticated AI capabilities directly into consumer devices.
Sources:
• Tweets: @rowancheung reporting on Deutsche Telekom's AI phone announcement
• Reddit co-founder Alexis Ohanian joins bid to acquire TikTok US and "bring it on-chain."
Reddit co-founder Alexis Ohanian has officially joined efforts to acquire TikTok's US operations with plans to integrate blockchain technology. Ohanian is partnering with "Project Liberty," a consortium led by former Los Angeles Dodgers owner Frank McCourt. The proposed acquisition would integrate TikTok with Frequency, a decentralized social media protocol designed to give users ownership of their network content. Ohanian stated that "TikTok is a game-changer for creators" and emphasized that "users should own their data" and "creators should own their audiences." He will serve as a strategic advisor focused on social media if the acquisition is successful. Ohanian has previously supported blockchain integration at Reddit, including community points and NFT initiatives.
See less
2:36
:computer: Technology & Infrastructure Analysis (Part 2/2)
Sources:
• Tweets: @DegenerateNews announcing Ohanian's TikTok acquisition bid
• Telegram: theblockbeats reporting details about the Frequency blockchain integration and Project Liberty
2:36
:robot_face: AI & Research Analysis
• OpenAI launching NextGenAI consortium with 15 leading institutions to advance AI research and education.
OpenAI has announced the formation of NextGenAI, a first-of-its-kind consortium that brings together 15 leading institutions focused on using artificial intelligence to advance research and education. While details about the specific participating organizations weren't provided in the sources, OpenAI has committed $50 million to support AI research and education through this initiative. This represents a significant coordinated effort to expand AI's positive impact across academic and research domains while potentially addressing challenges around AI access, capabilities, and responsible development.
Sources:
• Tweets: @OpenAI retweeting the NextGenAI consortium announcement
• Telegram: PANews reporting on OpenAI's $50 million funding commitment
• Microsoft debuts Dragon Copilot for healthcare, automating clinical documentation with ambient listening and voice dictation.
Microsoft has introduced Dragon Copilot, a specialized AI assistant designed for healthcare professionals that combines voice dictation with ambient listening capabilities to automate clinical documentation workflows. The system is designed to significantly reduce administrative burden for healthcare providers by automating documentation tasks during patient encounters. According to Microsoft, Dragon Copilot can save approximately 5 minutes per patient encounter, addressing clinician burnout and fatigue by reducing paperwork demands. This builds on Microsoft's broader efforts to deploy specialized AI solutions in healthcare settings where documentation requirements are particularly time-consuming.
Sources:
• Tweets: @rowancheung detailing Microsoft's Dragon Copilot features and time-saving benefits
• Google's Project Astra video capabilities coming to Android this month for Gemini Advanced subscribers.
Google is rolling out Project Astra's live video and screen-sharing capabilities to Android devices this month, marking a significant expansion of Gemini's multimodal capabilities. These features, which allow Gemini to process and respond to visual inputs in real-time, will be exclusively available to Gemini Advanced subscribers with Google One AI Premium plans. This restricted access indicates Google's strategy of deploying advanced AI features first to premium subscribers before potentially wider release. Project Astra represents Google's effort to close the gap with competitors in real-time visual AI processing on mobile devices.
Sources:
• Tweets: @rowancheung reporting on Google's Project Astra Android rollout and subscription requirements
See less
2:36
:coin: Crypto/Web3 Analysis (Part 1/3)
• :us: White House crypto summit scheduled for Friday; Coinbase CEO and MicroStrategy's Michael Saylor among confirmed attendees.
The White House will host its first cryptocurrency summit on Friday (March 8, 2:30 AM Beijing time), with President Trump personally chairing the event. The high-profile gathering has attracted numerous industry executives, with confirmed attendees including Coinbase CEO Brian Armstrong, MicroStrategy Chairman Michael Saylor, Chainlink Labs co-founder Sergey Nazarov, Exodus CEO J.P. Richardson, and Robinhood CEO Vlad Tenev. Additional participants include Bitcoin Magazine CEO David Bailey, Paradigm co-founder Matt Huang, Multicoin Capital co-founder Kyle Samani, World Liberty Financial co-founder Zach Witkoff, and Kraken CEO Arjun Sethi. From the White House side, Trump's cryptocurrency advisor David Sacks and the President's digital asset working group executive director Bo Hines will also participate, underscoring the administration's focus on engaging directly with crypto industry leaders.
Sources:
• Tweets: @WatcherGuru, @Cointelegraph on Michael Saylor and Coinbase CEO attending
• Telegram: PANews on summit timing, wublock listing comprehensive attendee information
• Telegram: theblockbeats confirming Trump's personal involvement and additional participants
• :flag-mx: Mexican billionaire Ricardo Salinas allocates 70% of his $5.8 billion portfolio to Bitcoin.
Mexican billionaire Ricardo Salinas, with a net worth of $5.8 billion, has allocated a remarkable 70% of his investment portfolio to Bitcoin. This represents one of the largest Bitcoin allocations by percentage among known billionaire investors globally. Salinas's substantial commitment to Bitcoin—described in his own words as being "pretty much all in" on crypto—positions him among the most prominent high-net-worth Bitcoin advocates in Latin America. The size of this allocation (approximately $4 billion at 70% of his portfolio) makes this a significant vote of confidence in Bitcoin's long-term prospects from a major international business figure.
Sources:
• Tweets: @WatcherGuru and @Cointelegraph both reporting on Salinas's 70% Bitcoin allocation
• Tweets: Both sources confirmed his $5.8 billion net worth
• :flag-sv: El Salvador President Bukele affirms country will continue Bitcoin purchases despite IMF's request to stop.
See less
2:36
:coin: Crypto/Web3 Analysis (Part 2/3)
President Nayib Bukele has explicitly stated that El Salvador will continue purchasing Bitcoin for its strategic reserve, directly contradicting the International Monetary Fund's (IMF) requirements for a new $1.4 billion deal. The IMF specifically demanded that "the public sector not voluntarily accumulate Bitcoin" as part of the agreement. Current treasury data shows El Salvador holds 6,101.18 BTC valued at over $520 million, with recent purchases including 1 BTC yesterday and 5 BTC the day before. The country has added 13 BTC in the past week and 45 BTC over the last 30 days, demonstrating their ongoing commitment despite external pressure. El Salvador's continued Bitcoin accumulation represents a significant challenge to traditional IMF conditions for sovereign lending.
Sources:
• Tweets: @WatcherGuru on Bukele's statement
• Telegram: theblockbeats providing specific holdings data and recent purchase history
• Articles: Cointelegraph "El Salvador's Bukele says Bitcoin buys will continue amid IMF pressure"
• Articles: Cointelegraph "IMF asks El Salvador to stop public sector Bitcoin buys for $1.4B deal"
• :us: White House announces support for rescinding the DeFi broker rule, calling it "an 11th hour attack on crypto."
The White House has announced its support for using the Congressional Review Act (CRA) to rescind the IRS's "DeFi broker rule," describing it as "an 11th hour attack on the crypto community by the Biden administration." The resolution has already passed the Senate with significant bipartisan support (70-27) and now awaits House approval before reaching President Trump's desk. If signed, the rule would be permanently abolished, and the IRS would be prohibited from implementing similar regulations in the future. The rule would have required certain DeFi participants to report total proceeds from digital asset transactions and related taxpayer information. Trump is reportedly prepared to quickly sign the resolution if passed by both chambers, marking a significant policy reversal on crypto regulation.
Sources:
• Tweets: @DegenerateNews on White House support for rescinding the rule
• Telegram: theblockbeats detailing Senate vote results and next steps
• Tweets: @coindesk on Trump's readiness to sign the resolution
• Bybit hackers successfully launder 100% of stolen $1.4 billion in crypto within 10 days.
See less
2:36
:coin: Crypto/Web3 Analysis (Part 3/3)
Hackers who breached Bybit have successfully laundered all 499,000 ETH (worth approximately $1.4 billion) within just 10 days of the theft. The attackers primarily utilized THORChain for moving funds, generating $5.5 million in fees for the protocol and sparking controversy over its role in facilitating illicit transfers. According to Bybit CEO Ben Zhou, while 77% of the stolen funds remain traceable, 20% have effectively "gone dark" and 3% have been frozen by authorities. The attackers have converted approximately 83% of the stolen ETH (about $1 billion worth) into Bitcoin. The unprecedented speed of this laundering operation highlights growing challenges in recovering stolen crypto assets, even as tracing capabilities improve.
Sources:
• Telegram: @Tyler_Did_It in Morning Minute reporting on Bybit hackers laundering funds via Thorchain
• Tweets: @Cointelegraph on the 10-day timeframe and THORChain fees
• Tweets: @Cointelegraph providing Ben Zhou's breakdown of traceable vs. dark funds
• Articles: Cointelegraph "Bybit hacker launders 100% of stolen $1.4B crypto in 10 days"
See less
EOF

# Escape the text for JSON
json_text=$(printf '%s' "$text" | jq -R -s '.')

# Test the generate_multiple endpoint with multiple voices at once
# echo -e "${BLUE}Testing generate_multiple endpoint${NC}"
# test_endpoint "/generate" "POST" "{
#     \"text\": ${json_text},
#     \"voices\": [\"donald_trump\", \"keanu_reeves\", \"kermit_the_frog\", \"portals_glados\", \"southpark_eric_cartman\", \"walter_cronkite\"],
#     \"model\": \"o3mini\",
#     \"video\": \"minecraft\"
# }" "Generating multiple videos with different voices simultaneously"

# Test the generate endpoint with a specific digest_id
echo -e "${BLUE}Testing generate endpoint with digest_id${NC}"
test_endpoint "/generate" "POST" "{
    \"text\": \"This is a test with a specific digest_id\",
    \"voices\": [\"donald_trump\"],
    \"model\": \"o3mini\",
    \"video\": \"minecraft\",
    \"digest_id\": \"a1319024-2229-4761-98b9-5c1131bab029\"
}" "Generating a video with a specific digest_id"

echo -e "\n${GREEN}All tests completed!${NC}"

