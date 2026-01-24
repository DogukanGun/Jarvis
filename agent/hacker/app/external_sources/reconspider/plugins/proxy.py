import re
import requests
from plugins.api import *
from plugins.webosint.who.whois import *

try:
    import IP2Proxy
    IP2PROXY_AVAILABLE = True
except ImportError:
    IP2PROXY_AVAILABLE = False


def ip2Proxy(IP):
    if not IP2PROXY_AVAILABLE:
        print("IP2Proxy module not installed. Install with: pip install IP2Proxy")
        print("Also download database from: https://lite.ip2location.com/database/px8-ip-proxytype-country-region-city-isp-domain-usagetype-asn-lastseen")
        return

    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",IP):
        db = IP2Proxy.IP2Proxy()
        db.open("./plugins/IP2PROXY-LITE-PX8.BIN")
        record = db.get_all(IP)
        db.close()
        if record['is_proxy']!=0:
            #print(record)
            print("Proxy: " + "Enabled")
            print("Proxy Type:" + record['proxy_type'])
            print("Country Code:" + record['country_short'])
            print("Country:" + record['country_long'])
            print("Region Name:" + record['region'])
            print("City:" + record['city'])
            print("Isp:" + record['isp'])
            print("Domain:" + record['domain'])
            print("Usage:" + record['usage_type'])
            print("ASN:" + record['asn'])
            print("Name:" + record['as_name'])
            api_key = ipstack()
            if api_key == "":
                print("Add you ipstack api key to plugins/api.py")
                exit()
            r = requests.get("http://api.IPstack.com/" + IP + "?access_key=" + api_key)
            response = r.json()
            print("Latitude :"+" {latitude}".format(**response))
            print("Longitude :"+" {longitude}".format(**response))
            if input("Want More Whois Details (Y/N):") in ["Y","y"]:
                whois_more(IP)
            if response['latitude'] and response['longitude']:
                lats = response['latitude']
                lons = response['longitude']
                url = "https://maps.google.com/maps?q=%s,+%s" % (lats, lons)
                print("Google Map Link :" + url)
        else:
            print("IP does not use any Proxy or VPN")
    else:
        print("\nEnter a Valid IP Address")
    print("")
