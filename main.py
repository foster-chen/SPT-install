import sys
import requests
from bs4 import BeautifulSoup
import argparse
import json
import os
from tqdm import tqdm
from datetime import datetime

COLOR_DICT = {
        'red': '\033[91m',
        'green': '\033[92m',
        'reset': '\033[0m'
        }


def parse_args(args):
    parser = argparse.ArgumentParser(prog="python3 main.py",
                                     description="install mods from hubMods.txt")
    parser.add_argument('spt_path', help="installation path of SPT")
    parser.add_argument('--include_outdated', action="store_true", help="sync mods even if it is outdated")
    parser.add_argument('--use_cache', action="store_true", help="use webpage information from cache file")
    args = parser.parse_args(args)

    return args

def dice_coefficient(s1, s2):
    # Convert strings to lowercase and remove spaces
    s1 = s1.lower().replace(" ", "")
    s2 = s2.lower().replace(" ", "")
                    
    # Create sets of bigrams for each string
    bigrams1 = set(s1[i:i+2] for i in range(len(s1) - 1))
    bigrams2 = set(s2[i:i+2] for i in range(len(s2) - 1))

    # Calculate the Dice coefficient
    intersection = len(bigrams1 & bigrams2)
    union = len(bigrams1) + len(bigrams2)
    if union == 0:
        return 0.0
    else:
        return 2.0 * intersection / union

def colorize(string, color):
    assert color in COLOR_DICT
    return f"{COLOR_DICT[color]}{string}{COLOR_DICT['reset']}"

def fetch_mod_tabs(URL, args, pages=40):
    if args.use_cache and os.path.exists("webCache.json"):
        with open("webCache.json", "r") as rf:
            data = json.load(rf)
            tabs = data["tabs"]
            print(f'{colorize("WARNING:", "red")} using cache file create on {data["date"]}')
        for key in tabs:
            tabs[key] = BeautifulSoup(tabs[key], "html.parser")
    else:
        tabs = {}
        for i in tqdm(range(pages), desc="Fetching from SPT hub: "):
            currURL = URL.format(i)
            response = requests.get(currURL)
            soup = BeautifulSoup(response.content, 'html.parser')
            items = soup.find('ol', class_='filebaseFileList')
            currTabs = items.find_all('div', class_="filebaseFileDataContainer")
            for tab in tqdm(currTabs, leave=False):
                modName = tab.find("h3", class_="filebaseFileSubject").text.strip()
                tabs[modName] = tab.parent.parent
                
        with open("webCache.json", "w") as wf:
            result = {"date": datetime.now().strftime("%Y-%m-%d"),
                      "tabs": {n: tabs[modName].prettify() for n in tabs}}
            json.dump(result, wf)
    return tabs


def main(args):
    args = parse_args(args)
    with open('config.json', 'r') as rf:
        config = json.load(rf)
    with open("hubMods.txt", "r") as rf:
        hubMods = [l.strip() for l in rf.readlines()]
    modTabs = fetch_mod_tabs(config["url"], args=args)

    # check mod names
    hasDiff = False
    for i, modName in tqdm(enumerate(hubMods), desc="Verifying hub mod list: ", total=len(hubMods)):
        highestScore = 0
        hubName = None
        for modHubName in modTabs:
            score = dice_coefficient(modName, modHubName)
            if score >= highestScore:
                highestScore = score
                hubName = modHubName
        # name is different from the hub, make corrections
        if hubName != modName:
            print(f"\"{colorize(modName, 'red')}\" has been changed to \"{colorize(hubName, 'red')}\"")
            hubMods[i] = hubName
            hasDiff = True
        # create config entry for new mod
        if not config["hubMods"].get(hubName) or not args.use_cache:
            modUrl = modTabs[hubName].find("a").get("href")
            modPage = BeautifulSoup(requests.get(modUrl).content, "html.parser")
            downloadLink = modPage.find("nav", class_="contentHeaderNavigation").find("a").get("href")
            config["hubMods"][hubName] = {"version": modTabs[hubName].find("ul", class_="labelList").text.strip(),
                                          "download": BeautifulSoup(requests.get(downloadLink).content, "html.parser").find("a").get("href")}
            hasDiff = True
    if hasDiff:    
        with open("hubMods.txt", "w") as wf:
            for line in hubMods:
                wf.write(f"{line}\n")
        with open("config.json", "w") as wf:
            json.dump(config, wf)
    

if __name__ == "__main__":
    main(sys.argv[1:])
