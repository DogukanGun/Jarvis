import sys
from requests import get
from requests.exceptions import RequestException
from core.config import shodan_api


def honeypot(inp):
    honey = 'https://api.shodan.io/labs/honeyscore/%s?key=%s' % (inp, shodan_api)
    try:
        result = get(honey, timeout=10).text
    except RequestException as e:
        result = None
        sys.stdout.write('\n[-] No information available: %s\n' % str(e))
    if "error" in result or "404" in result:
        print("IP Not found")
        return
    elif result:
            probability = str(float(result) * 10)
            print('\n[+] Honeypot Probabilty: %s%%' % (probability) + '\n')
    else:
        print("Something went Wrong")
