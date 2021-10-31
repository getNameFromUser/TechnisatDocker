import platform
import subprocess
import time
import json
import os
import atexit
from json import JSONEncoder

from api.technisat import Technisat, TechnisatFile


class CustomEncoder(JSONEncoder):
    def default(self, o):
        if hasattr(o, "__dict__"):
            return o.__dict__
        else:
            return o


class Application:

    def __init__(self, config, downloads):
        self.technisat = Technisat()
        self.config_file = open(config, "r")
        if os.path.exists(downloads):
            self.downloads_file = open(downloads, "r+")
            self.downloads = json.load(self.downloads_file)
        else:
            file = open(downloads, "w")
            file.write("{}")
            file.close()
            self.downloads_file = open(downloads, "r+")
            self.downloads = {}
        atexit.register(self.__close)

        self.config = json.load(self.config_file)
        self.__check_config()

    def wait_online(self):
        while not self.__ping():
            time.sleep(self.config.get("wait"))  # Wait 2.5 Minutes
            print(".")
        print(time.time(), ": Receiver online!")
        self.__main()
        self.__close()

    def __main(self):
        self.technisat.connect(self.config.get("ip"), self.config.get("port"))
        for name, file in self.technisat.ls().items():
            if isinstance(file, TechnisatFile):
                print("Action: File")
                #self.technisat.download(file, folder)
                self.downloads[name] = file
                self.__update_downloads()
                time.sleep(1)
            else:
                print("Action: Folder")
                destination = os.path.join(self.config.get("output"), name)
                if name not in self.downloads:
                    self.downloads[name] = {}
                if not os.path.exists(destination):
                    self.downloads[name] = {}
                    os.mkdir(destination)
                self.__update_downloads()
                self.__download_rec(self.downloads, name, destination, name)

    def __download_rec(self, downloads, key, folder, path):
        print(path)
        directory = self.technisat.ls(path)
        for name, file in directory.items():
            if isinstance(file, TechnisatFile):
                if name not in downloads[key]:
                    self.technisat.download(file, folder)
                    downloads[key][name] = file.recording_id
                    self.__update_downloads()
            else:
                if name not in downloads[key]:
                    downloads[key][name] = {}
                if not os.path.exists(os.path.join(folder, name)):
                    downloads[key][name] = {}
                    os.mkdir(os.path.join(folder, name))
                self.__update_downloads()
                self.__download_rec(downloads[key], name, os.path.join(folder, name), path + name + "/")

    def __update_downloads(self):
        self.downloads_file.seek(0)
        json.dump(self.downloads, self.downloads_file, sort_keys=True, indent=4)
        self.downloads_file.truncate()
        self.downloads_file.flush()

    def __check_config(self):
        if "ip" not in self.config:
            raise AssertionError("ip in config.json missing: This is the IP-Address of the receiver")
        if "output" not in self.config:
            raise AssertionError("output in config.json missing: This is the output folder of the downloaded files")
        if not os.path.exists(self.config.get("output")):
            raise FileNotFoundError("output in config.json invalid: The output folder does not exist")
        if "port" not in self.config:
            self.config["port"] = 2376
        if "wait" not in self.config:
            self.config["wait"] = 150
        if "format" not in self.config:
            self.config["format"] = "mp4"

    # Thanks to https://stackoverflow.com/a/32684938
    def __ping(self):
        return subprocess.call(['ping', '-n' if platform.system() == 'Windows' else '-c', '1', self.config.get("ip")],
                               stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) == 0

    def __close(self):
        self.technisat.disconnect()
        self.config_file.close()
        self.downloads_file.close()


pwd = os.getcwd()
app = Application(os.path.join(pwd, "config.json"), os.path.join(pwd, "downloads.json"))
while True:
    app.wait_online()
