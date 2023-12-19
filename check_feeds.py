#!/usr/bin/env python3
import configparser
import requests
import json
import feedparser
import re
from os.path import exists
from bs4 import BeautifulSoup

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

def check_auth():
    JWT = get_jwt()
    headers = {"Content-Type": "application/json","Authorization":f"Bearer {JWT}"}
    r = requests.get(f"https://{API_BASE}/{API_VERSION}/user/validate_auth", headers=headers)
    return r

def create_post(community_name, name, body, url=None):
    community_id = get_community_id(community_name)
    JWT = get_jwt()
    headers = {"Content-Type": "application/json","Authorization":f"Bearer {JWT}"}
    payload = {
        "community_id":community_id,
        "name":name,
        "body":body,
        "url":url
    }
    r = requests.post(f"https://{API_BASE}/{API_VERSION}/post", headers=headers, data=json.dumps(payload))
    return r

def update_last_guid(k, v):
    with open("last_guids.txt", "r") as f:
        last_guids = f.read()
    last_guids = re.sub(fr"{k}:.*", f"{k}:{v}", last_guids)
    with open("last_guids.txt", "w") as f:
        f.write(last_guids)

def get_new_episodes(feed_id):
    feed = feedparser.parse(FEEDS[feed_id]["url"])
    for item in feed.entries:
        if item.guid == FEEDS[feed_id]["last_guid"]:
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
            url = re.sub(r"[^\w]+", "-", name).strip("-").lower()
            url = f"https://maximumfun.org/episodes/greatest-generation/{url}/"
        except:
            url = ""
        yield name, body, url, item.guid

def get_latest_guid(feed_id):
    feed = feedparser.parse(FEEDS[feed_id]["url"])
    return feed.entries[0].guid

def setup():
    global FEEDS
    global USER
    global PASSWORD
    global API_BASE
    global API_VERSION
    
    API_BASE = "discuss.tchncs.de"
    #API_BASE = "startrek.website"
    API_VERSION = "api/v3"

    config = configparser.ConfigParser()
    config.read("config.ini")
    try:
        USER = config[API_BASE]["USER"]
        PASSWORD = config[API_BASE]["PASSWORD"]
        if check_auth().status_code == 200:
            print(f"Credentials found for user {USER} on {API_BASE}")
        else:
            exit("Set USER in config.ini")
    except:
        exit("Set USER in config.ini")

    FEEDS = {"GG":{}, "GT":{}}
    FEEDS["GG"]["url"] = "http://feeds.feedburner.com/TheGreatestGeneration"
    FEEDS["GT"]["url"] = "http://feeds.feedburner.com/GreatestDiscovery"
    if not exists("last_guids.txt"):
        with open("last_guids.txt", "a") as f:
            for k in FEEDS:
                f.write(f"{k}:{get_latest_guid(k)}\n")
                FEEDS[k]["last_guid"] = get_latest_guid(k)
    else:
        with open("last_guids.txt", "r") as f:
            for l in f.readlines():
                k, v = l.strip().split(":")
                FEEDS[k]["last_guid"] = v


if __name__ == "__main__":
    # Setup last_guids.txt and global variables
    setup()
    
    # Post new episodes of the Greatest Generation, if any
    for name, body, url, guid in get_new_episodes("GG"):
        print(f"Posting {name} to {API_BASE}")
        post = create_post("test", name, body, url)
        if post:
            update_last_guid("GG", guid)
        else:
            print("Error posting")
    
    # Post new episodes of Greatest Trek, if any
    for name, body, url, guid in get_new_episodes("GT"):
        print(f"Posting {name} to {API_BASE}")
        post = create_post("test", name, body, url)
        if post:
            update_last_guid("GT", guid)
        else:
            print("Error posting")

