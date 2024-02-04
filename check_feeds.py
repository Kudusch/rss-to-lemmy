#!/usr/bin/env python3
import configparser
import requests
import json
import feedparser
import re
from os.path import exists, dirname, abspath
from bs4 import BeautifulSoup
from datetime import datetime

def get_jwt():
    headers = {"Content-Type": "application/json",}
    payload = {"username_or_email":USER, "password":PASSWORD}
    r = requests.post(f"https://{API_BASE}/{API_VERSION}/user/login", headers=headers, json=payload)
    try:
        return r.json()["jwt"].strip()
    except:
        return None

def get_community_id(community_name):
    r = requests.get(f"https://{API_BASE}/{API_VERSION}/resolve_object", params = {"q":f"https://{API_BASE}/c/{community_name}"})
    try:
        return r.json()["community"]["community"]["id"]
    except:
        return None

def get_auth_type():
    r = requests.get(f"https://{API_BASE}/{API_VERSION}/site")
    version = r.json()["version"].split(".")
    if version[1] == "18":
        return "payload"
    elif version[1] == "19":
        return "header"

def create_post(name, body, url=None):
    community_id = get_community_id(COMMUNITY)
    JWT = get_jwt()
    payload = {
        "community_id":community_id,
        "name":name,
        "body":body,
        "url":url
    }
    headers = {"Content-Type": "application/json"}
    if get_auth_type() == "header":
        headers["Authorization"] = f"Bearer {JWT}"
    else:
        payload["auth"] = JWT
    try:
        r = requests.post(f"https://{API_BASE}/{API_VERSION}/post", headers=headers, data=json.dumps(payload))
        if r.status_code == 200:
            return r.json()
        else:
            return None
    except Exception as e:
        return None

def update_last_guid(k, v):
    with open(f"{BASE_PATH}/last_guids.txt", "r") as f:
        last_guids = f.read()
    last_guids = re.sub(fr"{k}:.*", f"{k}:{v}", last_guids)
    with open(f"{BASE_PATH}/last_guids.txt", "w") as f:
        f.write(last_guids)

def get_new_episodes(feed_id):
    feed = feedparser.parse(FEEDS[feed_id]["url"])
    n = 0
    for n, item in enumerate(feed.entries):
        # Stop the loop when the latest episode is reached
        if item.guid == FEEDS[feed_id]["last_guid"]:
            break
        # Stop the loop after the 5th new episode to prevent spamming
        # in case something changed in the feed structure
        if n > 5:
            break
        if "itunes_episode" in item.keys():
            name = f"Ep {item.itunes_episode}: {item.title}"
        else:
            name = f"{item.title}"

        try:
            soup = BeautifulSoup(item.content[0]['value'], features="html.parser")
            body = f"{soup.find('p').text}"
        except:
            body = ""

        try:
            url = re.sub(r"['’]", "", name)
            url = re.sub(r"[^\w]+", "-", url).strip("-").lower()
            url = f"{FEEDS[feed_id]['maxfun_url']}/{url}/"
        except:
            url = ""
        yield name, body, url, item.guid
    if n == 0:
        print(f"{datetime.now():%Y-%m-%dT%H:%M:%S} - Found no new posts in {feed_id}")

def get_latest_guid(feed_id):
    feed = feedparser.parse(FEEDS[feed_id]["url"])
    return feed.entries[0].guid

def setup(api_base):
    global FEEDS
    global USER
    global PASSWORD
    global COMMUNITY
    global API_BASE
    global API_VERSION
    global BASE_PATH

    API_BASE = api_base
    API_VERSION = "api/v3"

    BASE_PATH = abspath(dirname(__file__))
    config = configparser.ConfigParser()
    config.read(f"{BASE_PATH}/config.ini")
    try:
        USER = config[API_BASE]["USER"]
        PASSWORD = config[API_BASE]["PASSWORD"]
        COMMUNITY =  config[API_BASE]["COMMUNITY"]
    except:
        exit("Set USER, PASSWORD and COMMUNITY in config.ini")

    FEEDS = {"GG":{}, "GT":{}}
    FEEDS["GG"]["url"] = "https://feeds.simplecast.com/_mp2DeJd"
    FEEDS["GG"]["maxfun_url"] = "https://maximumfun.org/episodes/greatest-generation"

    FEEDS["GT"]["url"] = "https://feeds.simplecast.com/d1rbEtgZ"
    FEEDS["GT"]["maxfun_url"] = "https://maximumfun.org/episodes/greatest-trek"
    if not exists(f"{BASE_PATH}/last_guids.txt"):
        with open(f"{BASE_PATH}/last_guids.txt", "a") as f:
            for k in FEEDS:
                f.write(f"{k}:{get_latest_guid(k)}\n")
                FEEDS[k]["last_guid"] = get_latest_guid(k)
    else:
        with open(f"{BASE_PATH}/last_guids.txt", "r") as f:
            for l in f.readlines():
                k, v = l.strip().split(":")
                FEEDS[k]["last_guid"] = v


if __name__ == "__main__":
    # Setup last_guids.txt and global variables
    setup("startrek.website")

    # Post new episodes of the Greatest Generation, if any
    for name, body, url, guid in get_new_episodes("GG"):
        post = create_post(name, body, url)
        if post:
            print(f"{datetime.now():%Y-%m-%dT%H:%M:%S} - Posting {name} to {API_BASE}/c/{COMMUNITY}")
            update_last_guid("GG", guid)
        else:
            print("{datetime.now():%Y-%m-%dT%H:%M:%S} - Error posting")

    # Post new episodes of Greatest Trek, if any
    for name, body, url, guid in get_new_episodes("GT"):
        post = create_post( name, body, url)
        if post:
            print(f"{datetime.now():%Y-%m-%dT%H:%M:%S} - Posting {name} to {API_BASE}/c/{COMMUNITY}")
            update_last_guid("GT", guid)
        else:
            print("{datetime.now():%Y-%m-%dT%H:%M:%S} - Error posting")

