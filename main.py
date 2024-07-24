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
    parser.add_argument('--skip_links', action="store_true", help="skip the mod download links and logs")
    parser.add_argument('--pages', type=int, default=40, help="number of mod pages to crawl on SPT hub")
    args = parser.parse_args(args)

    return args

def fetch(url, timeout=10):
    while True:
        try:
            response = requests.get(url, timeout=timeout)
            return response
        except requests.exceptions.ConnectionError or requests.exceptions.ReadTimeout:
            ans = input(f"ConnectionError with {url}. Retry? ([Y]/N)")
            if ans == "N":
                raise requests.exceptions.ConnectionError

def dice_coefficient(s1, s2):
    '''
    Return the similarity of two strings with dice coefficient
    '''
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

def fetch_mod_tabs(pages):
    '''
    get webcache from request or local cache depending on --use_cache
    '''
    if args.use_cache and os.path.exists("webcache.json"):
        with open("webcache.json", "r") as rf:
            webcache = json.load(rf)
            message =  f"using cache file created on {webcache['date']}"
            print(f"{colorize(message, 'yellow')}")
    else:
        tabs = {}
        for i in tqdm(range(pages), desc="Fetching from SPT hub: "):
            currURL = manifest["url"].format(i)
            response = fetch(currURL, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            items = soup.find('ol', class_='filebaseFileList')
            currTabs = items.find_all('div', class_="filebaseFileDataContainer")
            for tab in tqdm(currTabs, leave=False):
                modName = tab.find("h3", class_="filebaseFileSubject").text.strip()
                tabs[modName] = {"content": tab.parent.parent}
                
        with open("webcache.json", "w") as wf:
            webcache = {"date": datetime.now().strftime("%Y-%m-%d"),
                      "tabs": {n: {"content": tabs[n]["content"].prettify()} for n in tabs}}
            json.dump(webcache, wf)

    for key in webcache["tabs"]:
        webcache["tabs"][key]["content"] = BeautifulSoup(webcache["tabs"][key]["content"], "html.parser")

    return webcache

def verify_hub_mod_names(webcache):
    '''
    Checks the mod name in hub_mods.txt, and add/update manifest.json
    '''
    hasDiff = False
    for i, modName in tqdm(enumerate(hubMods), desc="Verifying hub mod list: ", total=len(hubMods)):
        highestScore = 0
        hubName = None
        # find the closest name from webcache
        for modHubName in webcache["tabs"]:
            score = dice_coefficient(modName, modHubName)
            if score >= highestScore:
                highestScore = score
                hubName = modHubName
        # if hub_mod.txt mod name is different from the webcache, make corrections
        if hubName != modName:
            print(f"\"{colorize(modName, 'yellow')}\" has been changed to \"{colorize(hubName, 'yellow')}\"")
            hubMods[i] = hubName
            hubModsFile[hubModsFile.index(modName)] = hubName
            hasDiff = True
        # create manifest entry for new mod or update with new info
        if not manifest["hubMods"].get(hubName) or not args.use_cache:
            modUrl = webcache["tabs"][hubName]["content"].find("a").get("href")
            modPage = BeautifulSoup(fetch(modUrl, timeout=10).content, "html.parser")
            downloadLink = modPage.find("nav", class_="contentHeaderNavigation").find("a").get("href")
            if not manifest["hubMods"].get(hubName):
                manifest["hubMods"][hubName] = {"version": "",
                                              "download": "",
                                              "installation": {"BepInEx": [],
                                                               "user": []},
                                              "dependencies": []}
            manifest["hubMods"][hubName]["version"] = webcache["tabs"][hubName]["content"].find("ul", class_="labelList").text.strip()
            if webcache["tabs"][hubName].get("download"):
                manifest["hubMods"][hubName]["download"] = webcache["tabs"][hubName]["download"]
            else:
                downloadUrl = BeautifulSoup(fetch(downloadLink, timeout=20).content, "html.parser").find("a").get("href")
                manifest["hubMods"][hubName]["download"] = downloadUrl
                webcache["tabs"][hubName]["download"] = downloadUrl
            hasDiff = True
    # save new entries
    if hasDiff:
        with open("hub_mods.txt", "w") as wf:
            for line in hubModsFile:
                wf.write(f"{line}\n")
        with open("manifest.json", "w") as wf:
            json.dump(manifest, wf)
        with open("webcache.json", "w") as wf:
            for modName in webcache["tabs"]:
                webcache["tabs"][modName]["content"] = webcache["tabs"][modName]["content"].prettify()
            json.dump(webcache, wf)

def is_up_to_date(version):
    '''
    Check wether the mod version from webcache is newer than targetSptVersion
    '''
    def numeric_version_compare(version: list, targetVersion: list):
        return all(x >= y for x, y in zip(version, targetVersion))
    assert targetSptVersion.startswith("SPT "), "targetSptVersion must start with \"SPT\""
    serializedTargetSptVersion = [int(i) for i in targetSptVersion.replace(".x", ".0").split()[-1].split(".")]
    while len(serializedTargetSptVersion) < 3:
        serializedTargetSptVersion.append(0)
    version = version.split("-")[-1].replace(".X", ".0")
    version = [int(i) for i in version.split()[-1].split(".")]
    return numeric_version_compare(version, serializedTargetSptVersion)

def is_installed_up_to_date(installation):
    '''
    return true if the mod is properly installed and up-tp-date
    '''
    if not installation["BepInEx"] and not installation["user"]:
        return False
    for mod in installation["BepInEx"]:
        if not os.path.exists(os.path.join(args.spt_path, "BepInEx/plugins/", mod)):
            return False

    for mod in installation["user"]:
        if os.path.exists(os.path.join(args.spt_path, "user/mods/", mod)):
            packageJson = os.path.join(args.spt_path, "user/mods/", mod, "package.json")
            with open(packageJson, 'r') as rf:
                f = json.load(rf)
                if not is_up_to_date(f["sptVersion"]):
                    return False
        else:
            return False
    return True

def verify_installation(type):
    '''
    check the installation of mods based on the given installation manifest
    '''
    assert type in ["hubMods", "customMods"]
    # check installation/download mods
    download_list = []
    skipped_list = []
    for modName, modInfo in manifest[type].items():
        # skipping mods with outdated dependencies
        if modInfo.get("dependencies"):
            outdated = False
            for dependedMod in modInfo["dependencies"]:
                if not is_up_to_date(manifest[type][dependedMod]["version"]) and not args.include_outdated:
                    if not args.skip_links:
                        print(f"{colorize('WARNING:', 'red')} skipping {colorize(modName, 'yellow')} because it depends on an outdated mod {colorize(dependedMod, 'yellow')} ({colorize(manifest[type][dependedMod]["version"], 'red')})")
                    skipped_list.append(modName)
                    outdated = True
                    break
            if outdated:
                continue
        # skipping outdated mods
        if not is_up_to_date(modInfo["version"]) and not args.include_outdated:
            if not args.skip_links:
                print(f"{colorize('WARNING:', 'red')} skipping {colorize(modName, 'yellow')} because it is outdated {colorize('(' + modInfo['version'] + ')', 'red')}")
            skipped_list.append(modName)
        else:
            if is_installed_up_to_date(modInfo.get("installation")):
                if not args.skip_links:
                    print(f"{colorize('-> ', 'blue')}\"{modName}\" is installed and {colorize('up-to-date', 'green')}")
                continue
            color = "green" if is_up_to_date(modInfo["version"]) else "red"
            if not args.skip_links:
                print(f"{colorize('-> ', 'blue')}{modName} {colorize('(' + modInfo['version'] + ')', color)}: {colorize(modInfo['download'], 'blue')}")
                input("Press Enter to continue...")
            download_list.append(modName)
    
    download_list_message = '\n'.join([colorize(f"\t{modName} ({manifest[type][modName]["version"]})", 'green') for modName in download_list])
    skipped_list_message = '\n'.join([colorize(f"\t{modName} ({manifest[type][modName]["version"]})", 'red') for modName in skipped_list])
    print(f"\n{colorize('-> ', 'blue')}Downloadable {type}:\n{download_list_message}")
    print(f"\n{colorize('-> ', 'blue')}Skipped {type}:\n{skipped_list_message}\n")

def main():
    webcache = fetch_mod_tabs(args.pages)

    verify_hub_mod_names(webcache)
    verify_installation("hubMods")
    verify_installation("customMods")


if __name__ == "__main__":

    # GLOBAL variables
    args = parse_args(sys.argv[1:])
    with open('manifest.json', 'r') as rf:
        manifest = json.load(rf)
    with open("hub_mods.txt", "r") as rf:
        hubModsFile = [l.strip() for l in rf.readlines()]
        hubMods = [mod for mod in hubModsFile if mod and "#" not in mod]
    targetSptVersion = manifest["targetSptVersion"]

    main()
