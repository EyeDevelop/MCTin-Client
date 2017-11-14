import json

import requests
import os
import shutil
import hashlib
import sys


def get_checksum(file):
    h_sha256 = hashlib.sha256()
    with open(file, 'rb') as fp:
        h_sha256.update(fp.read())

    return h_sha256.hexdigest()


def download_file(url, name, save_loc):
    file = requests.get(url, stream=True)
    if file.headers.get("Content-Type") == "application/json":
        error = file.json()
        print("[{}]: {}".format(error["error"], error["message"]))
        return False
    else:
        chunk_count = 0
        with open(save_loc, 'wb') as fp:
            for chunk in file.iter_content(8192):
                if chunk:
                    fp.write(chunk)
                    chunk_count += 1

                print("\rDownloading {}: {}%".format(name, min([100, round(chunk_count * 8192 / int(file.headers.get("Content-Length")) * 100)])), end="")
            print()

    return True


def download_pack(tin_address, modpack_name):
    if os.path.exists(os.path.join(os.getcwd(), "modpacks/{}".format(modpack_name))):
        shutil.rmtree(os.path.join(os.getcwd(), "modpacks/{}".format(modpack_name)))

    os.mkdir(os.path.join(os.getcwd(), "modpacks/{}".format(modpack_name)))
    os.mkdir(os.path.join(os.getcwd(), "modpacks/{}/mods".format(modpack_name)))

    modpack = requests.get(tin_address + "/api?modpack={}".format(modpack_name)).json()

    for mod in modpack["mods"]:
        if not download_file(tin_address + "/api?modpack={}&mod={}&download".format(modpack_name, mod), modpack["mods"][mod]["name"], os.path.join(os.getcwd(), "modpacks/{}/mods/{}.jar".format(modpack_name, mod))):
            return False
        for extension in modpack["mods"][mod]["extensions"]:
            if not download_file(tin_address + "/api?modpack={}&mod={}&downloadext={}".format(modpack_name, mod, extension), modpack["mods"][mod]["extensions"][extension]["name"], os.path.join(os.getcwd(), "modpacks/{}/mods/{}-ext-{}.jar".format(modpack_name, mod, extension))):
                return False

    with open(os.path.join(os.getcwd(), "modpacks/{}/version.txt".format(modpack_name)), 'wt') as v_fp:
        v_fp.write(modpack["version"] + "\n")

    return True


def update_pack(tin_address, modpack_name):
    if not os.path.exists(os.path.join(os.getcwd(), "modpacks/{}".format(modpack_name))):
        return False

    modpack = requests.get(tin_address + "/api?modpack={}".format(modpack_name)).json()

    for mod in modpack["mods"]:
        if not os.path.exists(os.path.join(os.getcwd(), "modpacks/{}/mods/{}.jar".format(modpack_name, mod))):
            download_file(tin_address + "/api?modpack={}&mod={}&download".format(modpack_name, mod), modpack["mods"][mod]["name"], os.path.join(os.getcwd(), "modpacks/{}/mods/{}.jar".format(modpack_name, mod)))

        if "remote:" not in modpack["mods"][mod]["link"]:
            if get_checksum(os.path.join(os.getcwd(), "modpacks/{}/mods/{}.jar".format(modpack_name, mod))) != requests.get(tin_address + "/api?modpack={}&mod={}&getchecksum".format(modpack_name, mod)).json()["checksum"]:
                download_file(tin_address + "/api?modpack={}&mod={}&download".format(modpack_name, mod), modpack["mods"][mod]["name"], os.path.join(os.getcwd(), "modpacks/{}/mods/{}.jar".format(modpack_name, mod)))

            for extension in modpack["mods"][mod]["extensions"]:
                if not os.path.exists(os.path.join(os.getcwd(), "modpacks/{}/mods/{}-ext-{}.jar".format(modpack_name, mod, extension))):
                    download_file(tin_address + "/api?modpack={}&mod={}&downloadext={}".format(modpack_name, mod, extension), modpack["mods"][mod]["extensions"][extension]["name"], os.path.join(os.getcwd(), "modpacks/{}/mods/{}-ext-{}.jar".format(modpack_name, mod, extension)))

                if "remote:" not in modpack["mods"][mod]["extensions"][extension]["link"]:
                    if get_checksum(os.path.join(os.getcwd(), "modpacks/{}/mods/{}-ext-{}.jar".format(modpack_name, mod, extension))) != requests.get(tin_address + "/api?modpack={}&mod={}&getextchecksum={}".format(modpack_name, mod, extension)).json()["checksum"]:
                        download_file(tin_address + "/api?modpack={}&mod={}&downloadext={}".format(modpack_name, mod, extension), modpack["mods"][mod]["extensions"][extension]["name"], os.path.join(os.getcwd(), "modpacks/{}/mods/{}-ext-{}.jar".format(modpack_name, mod, extension)))

    installed_mods_and_exts = [x[:-4] for x in os.listdir(os.path.join(os.getcwd(), "modpacks/{}/mods/".format(modpack_name)))]
    installed_mods = [x for x in installed_mods_and_exts if "-ext-" not in x]
    installed_exts = [x for x in installed_mods_and_exts if "-ext-" in x]
    for mod in installed_mods:
        if mod not in modpack["mods"]:
            try:
                os.remove(os.path.join(os.getcwd(), "modpacks/{}/mods/{}.jar".format(modpack_name, mod)))
            except FileNotFoundError:
                pass
            for dep in installed_exts:
                try:
                    os.remove(os.path.join(os.getcwd(), "modpacks/{}/mods/{}.jar".format(modpack_name, dep)))
                except FileNotFoundError:
                    pass

    with open(os.path.join(os.getcwd(), "modpacks/{}/version.txt".format(modpack_name)), 'wt') as v_fp:
        v_fp.write(modpack["version"] + "\n")

    return True


def install_pack(modpack_name, install_loc):
    if not os.path.exists(os.path.join(os.getcwd(), "modpacks/{}".format(modpack_name))):
        return False

    if not os.path.exists(os.path.join(install_loc, "mods")):
        os.mkdir(os.path.join(install_loc, "mods"))
    else:
        shutil.rmtree(os.path.join(install_loc, "mods"))
        os.mkdir(os.path.join(install_loc, "mods"))

    for mod in os.listdir(os.path.join(os.getcwd(), "modpacks/{}/mods/")):
        shutil.copy2(mod, os.path.join(install_loc, "mods"))

    return True


def main():
    if not os.path.exists(os.path.join(os.getcwd(), "modpacks")):
        os.mkdir(os.path.join(os.getcwd(), "modpacks"))

    url = input("Please enter the Tin Server Address: ")
    modpacks = requests.get(url + "/api?getmodpacks").json()

    if len(modpacks.keys()) == 0:
        print("This server has no modpacks available.")
        exit(0)

    print("\nPlease pick one of the installable modpacks: ")
    for i, j in enumerate(modpacks.keys()):
        print("[{}] {} [{}]: {}".format(i + 1, modpacks[j]["name"], modpacks[j]["version"], modpacks[j]["description"]), end="")
        if os.path.exists(os.path.join(os.getcwd(), "modpacks/{}/version.txt".format(j))):
            with open(os.path.join(os.getcwd(), "modpacks/{}/version.txt".format(j)), 'rt') as v_fp:
                installed_version = v_fp.read().replace('\n', '')
            print("\t\t\tInstalled: [{}]".format(installed_version))
        else:
            print()

    option = input("> ")

    modpack_name = list(modpacks.keys())[int(option) - 1]
    modpack = requests.get(url + "/api?modpack={}".format(modpack_name)).json()

    forge_extension = "exe" if sys.platform == "win32" else "jar"

    iu = input("Would you like to [i]nstall, [u]pdate or [r]emove {}: ".format(modpack["name"]))
    if iu.lower() == "i":
        if not (os.path.exists(os.path.join(os.getcwd(), "forge.{}".format(forge_extension))) and get_checksum(os.path.join(os.getcwd(), "forge.{}".format(forge_extension))) == requests.get(url + "/api?modpack={}&getinstallerchecksum={}".format(modpack_name, forge_extension)).json()["checksum"]):
            if not download_file(url + "/api?modpack={}&getinstaller={}".format(modpack_name, forge_extension), "Forge Installer", os.path.join(os.getcwd(), "forge.{}".format(forge_extension))):
                print("Could not download forge installer!")
                exit(1)
        print("\nPlease install Minecraft Forge and then continue here.")
        print("To install, please run vanilla Minecraft {} at least once.".format(modpack["mc_version"]))
        print("Then run the forge.{} located in this folder.".format(forge_extension))
        print("Press enter when you're done.")

        input()
        try:
            os.remove(os.path.join(os.getcwd(), "forge.{}".format(forge_extension)))
        except FileNotFoundError:
            pass

        download_pack(url, modpack_name)
        print("Pack successfully downloaded!")

        dir = "C:\\Users\\YourName\\Appdata\\Roaming\\.minecraft\\" if sys.platform == "win32" else "/Users/yourname/Library/Application Support/minecraft/" if sys.platform == "darwin" else "/home/yourname/.minecraft/"
        print("\nPlease enter your minecraft installation directory. [{}]".format(dir))
        print("Or leave it empty for a manual install.")
        mcdir = input(": ")

        if not mcdir:
            print("\nThe mods to be installed are in {}.".format(os.path.abspath(os.path.join(os.getcwd(), "modpacks/{}/mods".format(modpack_name)))))
            exit(0)

        install_pack(modpack_name, mcdir)
    elif iu.lower() == "u":
        if not update_pack(url, modpack_name):
            download_pack(url, modpack_name)
            print("Could not update pack, so reinstalled.")
        else:
            print("Pack successfully updated!")
    elif iu.lower() == "r":
        if os.path.exists(os.path.join(os.getcwd(), "modpacks/{}".format(modpack_name))):
            shutil.rmtree(os.path.join(os.getcwd(), "modpacks/{}".format(modpack_name)))
        print("Successfully removed {}".format(modpack_name))
    else:
        print("Not a valid option!")
        exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit(0)
    except json.decoder.JSONDecodeError:
        print("Cannot parse server response!")
        exit(1)
