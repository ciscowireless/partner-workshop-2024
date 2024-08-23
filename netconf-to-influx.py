"""
    NETCONF RPC demonstration script
    - Collects wireless client live stats from Cisco 9800
    - Parses xml data and converts to Influx Line protocol
    - Posts data to Influx DB
"""
import re, sys, time
import xml.etree.ElementTree as ET
import requests
from ncclient import manager

WLC_HOST = "x.x.x.x"
WLC_USER = "username"
WLC_PASS= "password"

INFLUX_IP = "y.y.y.y"
INFLUX_PORT = "8086"
INFLUX_API_KEY = ""
INFLUX_ORG = "org"
INFLUX_BUCKET = "bucket"

FILTER = '''
        <client-global-oper-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-wireless-client-global-oper">
            <client-live-stats/>
        </client-global-oper-data>
    '''


def netconf_get():

    with manager.connect(host=WLC_HOST,
                            port=830,
                            username=WLC_USER,
                            password=WLC_PASS,
                            device_params={"name":"iosxe"},
                            hostkey_verify=False) as ncc:

        netconf_xml = ncc.get(filter=("subtree", FILTER)).data_xml
        netconf_data = re.sub('xmlns="[^"]+"', "", netconf_xml)

    print(f"From WLC:\n{netconf_data}")
    return netconf_data


def parse_data(client_data_xml):

    client_live_stats = ET.fromstring(client_data_xml).find(".//client-live-stats")

    auth_state = client_live_stats.find("auth-state-clients").text
    mobility_state = client_live_stats.find("mobility-state-clients").text
    iplearn_state = client_live_stats.find("iplearn-state-clients").text
    webauth_state = client_live_stats.find("webauth-state-clients").text
    run_state = client_live_stats.find("run-state-clients").text
    delete_state = client_live_stats.find("delete-state-clients").text
    random_mac = client_live_stats.find("random-mac-clients").text

    influx_data = (
                f"clientLiveStats,wlcName=MyWLC "\
                f"auth={auth_state},"\
                f"mobility={mobility_state},"\
                f"ipLearn={iplearn_state},"\
                f"webauth={webauth_state},"\
                f"run={run_state},"\
                f"delete={delete_state},"\
                f"randomMAC={random_mac} "
                )

    print(f"To Influx:\n{influx_data}")
    return influx_data


def influx_post(client_data_influx, precision="s"):

    influx_api = f'http://{INFLUX_IP}:{INFLUX_PORT}/api/v2/write'
    headers = {
            "Content-Type" : "text/plain; charset=utf-8",
            "Accept" : "application/json",
            "Authorization": f"Token {INFLUX_API_KEY}"
            }
    params = {
            "org" : INFLUX_ORG,
            "bucket" : INFLUX_BUCKET,
            "precision" : precision
            }
    post = requests.post(influx_api, headers=headers, params=params, data=client_data_influx, timeout=3)
    print(f"Influx Result:\n{post.status_code}\n")


if __name__ == "__main__":

    try:
        print("Running : CTRL-C to stop")
        while True:

            client_stats = netconf_get()
            parsed_client_stats = parse_data(client_stats)
            influx_post(parsed_client_stats)

            time.sleep(30)

    except KeyboardInterrupt:
        sys.exit()

