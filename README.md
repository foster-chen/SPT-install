# SPT-install
My personal Single Player Tarkov installation and mod update helper for friends.

## 1. Install SPT

Update to the latest EFT, then download the SPT installer [here](https://sp-tarkov.com/#download). Place the insatller into a new folder **OUTSIDE** the vanilla EFT folder. Run the installer.

## 2. Setup Python

Install Python if not already done so from [here](https://www.python.org/downloads/windows/). Check your installation by typing `python3 -V` or `python -V` in the cli. A version newer than `3.9` is recommended.

```bash
$ python3 -V

Python 3.12.4
```

## 3. Install Python dependencies

Go to the cloned downloaded repository, run the following command to install dependant Python libraries.

```bash
$ python3 -m pip install -r ./requirements.txt
```

## 4. Run the program to check for mods in the mod list `hubMods.txt`

You can obtain the website cache `webcache.json` from me and place it in the repository, then run `python3 main.py ${my/SPT/path} --use_cache`. Replace `${my/SPT/path}` with the actual installation path of your SPT. You could also run without the `--use_cache` flag, crawl the hub and generate the `webcache.json` yourself and get the latest mod updates and download links, which might take longer.

## Adding more mods to the wishlist

if you wish to add more mods to the list, simply add the name of the mod to the end of hub_mods.txt. Don't worry on getting the name exactly right as the program can search the name and replace it for you!