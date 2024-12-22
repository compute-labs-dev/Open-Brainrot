import requests



### main scripts used for scraping the text
def scrape(reddit_url):
    map = {}
    headers = {'User-agent': 'Mozilla/5.0'}
    r = requests.get(reddit_url + "/.json", headers=headers)
    data = r.json()  # Parse JSON data
    self_text = data[0]['data']['children'][0]['data']['selftext']
    title = data[0]['data']['children'][0]['data']['title']
    map['title'] = title
    map['desc'] = self_text
    print("Scraped! Currently saving ...")
    return map

def save_map_to_txt(map, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(f"Title: {map['title']}\n")
        file.write(f"Description: {map['desc']}\n")
    print("SCRAPING DONE! SUCCESSFULLY SAVED")
    