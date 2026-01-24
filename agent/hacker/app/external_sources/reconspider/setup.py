from setuptools import setup, find_packages
import os
import sys
import subprocess

fout = open("core/config.py", "w")

# Shodan.io API (https://developer.shodan.io/api)
fout.write("shodan_api = " + '"' + "e9SxSRCE1xDNS4CzyWzOQTUoE55KB9HX" + '"' + "\n")
fout.close()

fout = open("plugins/api.py", "w")

# NumVerify API (https://numverify.com/documentation)
fout.write("def phoneapis():"+ "\n")
fout.write("    api= "+ '"' + "ecf584dd7bccdf2c152fdf3f5595ba20" + '"' + "\n")

# IP Stack API (https://ipstack.com/documentation)
fout.write("    return str(api)"+ "\n")
fout.write("def ipstack():"+ "\n")
fout.write("    api="+ '"' +"406792616a740641c6a0588a0ee1c509"+ '"' + "\n")
fout.write("    return str(api)"+ "\n")

# Google Maps API (hhttps://developers.google.com/maps/documentation/places/web-service/get-api-key)
fout.write("def gmap():"+ "\n")
fout.write("    api="+ '"' +"AIzaSyBY9Rfnjo3UWHddicUrwHCHY37OoqxI478"+ '"' + "\n")
fout.write("    return str(api)"+ "\n")
fout.close()

setup(
    name="ReconSpider",
    version="1.0.7",
    description="Most Advanced OSINT Framework",
    url="https://github.com/bhavsec/reconspider/",
    author="BhavKaran (bhavsec.com)",
    author_email="bhavsec@gmail.com",
    license="GPL-3.0",
    packages=["core", "plugins", "plugins.webosint", "plugins.webvuln"],
    py_modules=["reconspider"],
    install_requires=[
        "shodan",
        "requests",
        "prompt_toolkit",
        "wget",
        "beautifulsoup4",
        "click",
        "urllib3",
        "paramiko",
        "pythonping",
        "python-whois",
        "gmplot",
        "pillow",
        "lxml",
    ],
    entry_points={
        "console_scripts": [
            "reconspider=reconspider:main",
        ],
    },
)

try:
    import wget
except ImportError as e:
    print(e)
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'wget'])
    import wget

# ip2 Location Database (https://lite.ip2location.com/database/px8-ip-proxytype-country-region-city-isp-domain-usagetype-asn-lastseen?lang=en_US)
url="https://www.ip2location.com/download?token=hg5uYe2Jvri4R7P1j8b71Pk8dnvIU2M6A9jz2tvcVtGx8ZK2UPQgzr6Hk3cV68oH&file=PX8LITEBIN"
print('\nDownloading IP2PROXY-IP-PROXYTYPE-COUNTRY-REGION-CITY-ISP-DOMAIN-USAGETYPE-ASN-LASTSEEN.BIN...')
filepath=os.getcwd()+"/plugins/"
wget.download(url,out=filepath)
print('\nDownload Finished')

import zipfile
print('\nExtracting Files')
with zipfile.ZipFile(filepath+"IP2PROXY-LITE-PX8.BIN.ZIP","r") as zip_ref:
    zip_ref.extract("IP2PROXY-LITE-PX8.BIN",filepath)

print("\nInstallation Successfull")
print("\n\nNote: APIs included in ReconSpider are FREE and having limited & restricted usage per month, Please update the current APIs with New APIs in setup.py file, and re-install once done.")
print("\nWarning: Not updating the APIs can result in not showing the expected output or it may show errors.")