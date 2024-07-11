import sys
import requests
from bs4 import BeautifulSoup
import argparse


COLOR_DICT = {
        'red': '\033[91m',
        'green': '\033[92m',
        'reset': '\033[0m'
        }


def parse_args(args):
    parser = argparse.ArgumentParser(prog="python3 main.py",
                                     description="install mods from hubMods.txt")
    parser.add_argument('spt_path', help="installation path of SPT")

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

def main(args):
    args = parse_args(args)


if __name__ == "__main__":
    main(sys.argv[1:])

