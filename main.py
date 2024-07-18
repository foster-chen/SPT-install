import sys
import requests
from bs4 import BeautifulSoup
import argparse
import json
import os
from tqdm import tqdm
from datetime import datetime
import gdown


COLOR_DICT = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'reset': '\033[0m'
        }

def parse_args(args):
    parser = argparse.ArgumentParser(prog="python3 main.py",
                                     description="install mods from hub_mods.txt")
    parser.add_argument('spt_path', help="installation path of SPT")
    parser.add_argument('--include_outdated', action="store_true", help="sync mods even if it is outdated")
    parser.add_argument('--use_cache', action="store_true", help="use webpage information from cache file")
    args = parser.parse_args(args)

    return args

def fetch(url, timeout=10):
    while True:
        try:
            response = requests.get(url, timeout=timeout)
            return response
        except requests.exceptions.ConnectionError:
            ans = input(f"ConnectionError with {url}. Retry? ([Y]/N)")
            if ans == "N":
                raise requests.exceptions.ConnectionError


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
    if args.use_cache and os.path.exists("webcache.json"):
        with open("webcache.json", "r") as rf:
            data = json.load(rf)
            tabs = data["tabs"]
            message =  f"using cache file created on {data['date']}"
            print(f"{colorize(message, 'yellow')}")
        for key in tabs:
            tabs[key] = BeautifulSoup(tabs[key], "html.parser")
    else:
        tabs = {}
        for i in tqdm(range(pages), desc="Fetching from SPT hub: "):
            currURL = URL.format(i)
            response = fetch(currURL, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            items = soup.find('ol', class_='filebaseFileList')
            currTabs = items.find_all('div', class_="filebaseFileDataContainer")
            for tab in tqdm(currTabs, leave=False):
                modName = tab.find("h3", class_="filebaseFileSubject").text.strip()
                tabs[modName] = tab.parent.parent
                
        with open("webcache.json", "w") as wf:
            result = {"date": datetime.now().strftime("%Y-%m-%d"),
                      "tabs": {n: tabs[modName].prettify() for n in tabs}}
            json.dump(result, wf)
    return tabs

def is_up_to_date(version, targetVersion):
    def numeric_version_compare(version: list, targetVersion: list):
        return all(x >= y for x, y in zip(version, targetVersion)) 
    assert targetVersion.startswith("SPT "), "targetSptVersion must start with \"SPT\""
    targetVersion = [int(i) for i in targetVersion.replace(".x", ".0").split()[-1].split(".")]
    while len(targetVersion) < 3:
        targetVersion.append(0)
    version = version.split("-")[-1].replace(".X", ".0")
    version = [int(i) for i in version.split()[-1].split(".")]
    return numeric_version_compare(version, targetVersion)

def is_installed_up_to_date(installation, targetVersion, args):
    if not installation:
        return False
    for mod in installation["BepInEx"]:
        if not os.path.exists(os.path.join(args.spt_path, "BepInEx/plugins/", mod)):
            return False

    for mod in installation["user"]:
        if os.path.exists(os.path.join(args.spt_path, "user/mods/", mod)):
            packageJson = os.path.join(args.spt_path, "user/mods/", mod, "package.json")
            with open(packageJson, 'r') as rf:
                f = json.load(rf)
                if not is_up_to_date(f["sptVersion"], targetVersion):
                    return False
        else:
            return False
    return True

def main(args):
    args = parse_args(args)
    with open('manifest.json', 'r') as rf:
        config = json.load(rf)
    with open("hub_mods.txt", "r") as rf:
        hubMods = [l.strip() for l in rf.readlines()]
    modTabs = fetch_mod_tabs(config["url"], args=args)
    targetSptVersion = config["targetSptVersion"]

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
            print(f"\"{colorize(modName, 'yellow')}\" has been changed to \"{colorize(hubName, 'yellow')}\"")
            hubMods[i] = hubName
            hasDiff = True
        # create config entry for new mod or update with new info
        if not config["hubMods"].get(hubName) or not args.use_cache:
            modUrl = modTabs[hubName].find("a").get("href")
            modPage = BeautifulSoup(fetch(modUrl, timeout=10).content, "html.parser")
            downloadLink = modPage.find("nav", class_="contentHeaderNavigation").find("a").get("href")
            config["hubMods"][hubName] = {"version": modTabs[hubName].find("ul", class_="labelList").text.strip(),
                                          "download": BeautifulSoup(fetch(downloadLink, timeout=20).content, "html.parser").find("a").get("href")}
            hasDiff = True
    if hasDiff:
        with open("hub_mods.txt", "w") as wf:
            for line in hubMods:
                wf.write(f"{line}\n")
        with open("manifest.json", "w") as wf:
            json.dump(config, wf)
    
    # check installation/download mods
    download_list = []
    skipped_list = []
    for modName, modInfo in config["hubMods"].items():
        # skipping mods with outdated dependencies
        if modInfo.get("dependencies"):
            for dependedMod in modInfo["dependencies"]:
                if not is_up_to_date(config["hubMods"][dependedMod]["version"], targetSptVersion) and not args.include_outdated:
                    print(f"{colorize('WARNING:', 'red')} skipping \"{modName}\" because it depends on an outdated mod \"{dependedMod}\" ({colorize(config["hubMods"][dependedMod]["version"], 'red')})")
                    skipped_list.append(modName)
                    break
        # skipping outdated mods
        elif not is_up_to_date(modInfo["version"], targetSptVersion) and not args.include_outdated:
            print(f"{colorize('WARNING:', 'red')} skipping \"{modName}\" because it is outdated ({colorize(modInfo['version'], 'red')})")
            skipped_list.append(modName)
        else:
            if is_installed_up_to_date(modInfo.get("installation"), targetSptVersion, args):
                print(f"{colorize('-> ', 'blue')}\"{modName}\" is installed and {colorize('up-to-date', 'green')}")
                continue
            color = "green" if is_up_to_date(modInfo["version"], targetSptVersion) else "red"
            print(f"{colorize('-> ', 'blue')}{modName} ({colorize(modInfo['version'], color)}): {colorize(modInfo['download'], 'yellow')}")
            download_list.append(modName)
            input("Press Enter to continue...")
    
    download_list_message = '\n'.join([colorize(f"\t{modName} ({config["hubMods"][modName]["version"]})", 'green') for modName in download_list])
    skipped_list_message = '\n'.join([colorize(f"\t{modName} ({config["hubMods"][modName]["version"]})", 'red') for modName in skipped_list])
    print(f"\n{colorize('-> ', 'blue')}Downloadable mods:\n{download_list_message}")
    print(f"\n{colorize('-> ', 'blue')}Skipped mods:\n{skipped_list_message}")

if __name__ == "__main__":
    main(sys.argv[1:])
