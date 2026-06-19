# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from elasticsearch import Elasticsearch

import json


def attain_uuid(entities, uuid_dict):
    for k, v in uuid_dict.items():
        fg = True
        for entity in entities:
            if entity not in k:
                fg = False
                break
        if fg:
            print(entities, k)
            return v
    return None


if __name__ == "__main__":
    es = Elasticsearch('http://localhost:50004')

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    with open(os.path.join(BASE_DIR, "data/chatglm_llm_fintech_raw_dataset/uuid.json"), "r", encoding="utf-8") as f:
        uuid_dict = json.load(f)

    with open(os.path.join(BASE_DIR, "data/chatglm_llm_fintech_raw_dataset/allcrawl.json"), "r", encoding="utf-8") as f:
        crawl_dict = json.load(f)

    for i, company in enumerate(crawl_dict):
        for year in crawl_dict[company]:
            if year not in ["2019年报", "2020年报", "2021年报"]:
                continue
            try:
                uuid = attain_uuid(
                    [crawl_dict[company][year]['SECURITY_CODE'], year[:-1]], uuid_dict)
                for idx, key in enumerate(crawl_dict[company][year]):
                    doc = {
                        "text": key,
                    }
                    resp = es.index(index=str(uuid), id=idx, document=doc)
            except:
                print(f"error {company} {year}")
        if i % 99 == 0 and i > 0:
            print(f"insert {3*(i+1)} file")
    print(f"insert {3*len(crawl_dict)} file")
