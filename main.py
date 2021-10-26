import json
import random
import time
import os
from threading import Thread

import easyocr
import requests
from bs4 import BeautifulSoup

# Constants
usernames = os.getenv("USERNAMES")
passwords = os.getenv("PASSWORDS")
CUDA = None
reader = easyocr.Reader(['en'], gpu=False)
headers = {
    "Origin": "https://zlapp.fudan.edu.cn",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                  "Version/14.0 Mobile/15E148 Safari/604.1",
    "Referer": "https://zlapp.fudan.edu.cn/site/ncov/fudanDaily?from=history",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-us",
    "Connection": "keep-alive"
}
login_url = "https://uis.fudan.edu.cn/authserver/login?service=https%3A%2F%2Fzlapp.fudan.edu.cn%2Fa_fudanzlapp%2Fapi" \
            "%2Fsso%2Findex%3Fredirect%3Dhttps%253A%252F%252Fzlapp.fudan.edu.cn%252Fsite%252Fncov%252FfudanDaily" \
            "%253Ffrom%253Dhistory%26from%3Dwap "
get_info_url = "https://zlapp.fudan.edu.cn/ncov/wap/fudan/get-info"
save_url = "https://zlapp.fudan.edu.cn/ncov/wap/fudan/save"
code_url = "https://zlapp.fudan.edu.cn/backend/default/code"
error_string = "您将登录的是："
max_retry = 3


def tick_for_id(id: int):
    # Randomize time
    time.sleep(random.randint(0, 36000))

    data = {
        "username": usernames[id],
        "password": passwords[id]
    }

    s = requests.Session()
    s.headers.update(headers)
    response = s.get(login_url)
    content = response.text
    soup = BeautifulSoup(content, "lxml")
    inputs = soup.find_all("input")
    for i in inputs[2::]:
        data[i.get("name")] = i.get("value")
    response = s.post(login_url, data=data)
    if error_string in response.text:
        raise Exception("Error logging in")

    retry = 0
    while retry < max_retry:
        response = s.get(get_info_url)
        old_pafd_data = json.loads(response.text)
        pafd_data = old_pafd_data["d"]["info"]
        code = s.get(code_url).content
        code_result = reader.readtext(code)[0][1].replace(" ", "")
        print("Verification code result: ", code_result, "confidence: ", reader.readtext(code)[0][2])

        pafd_data.update({
            "ismoved": 0,
            "number": old_pafd_data["d"]["uinfo"]["role"]["number"],
            "realname": old_pafd_data["d"]["uinfo"]["realname"],
            "area": old_pafd_data["d"]["oldInfo"]["area"],
            "city": old_pafd_data["d"]["oldInfo"]["city"],
            "province": old_pafd_data["d"]["oldInfo"]["province"],
            "sffsksfl": 0,
            "sfjcgrq": 0,
            "sfjcwhry": 0,
            "sfjchbry": 0,
            "sfcyglq": 0,
            "sfcxzysx": 0,
            "sfyyjc": 0,
            "jcjgqr": 0,
            "sfwztl": 0,
            "sftztl": 0,
            "code": code_result
        })

        if not pafd_data['sfzx']:
            pafd_data['sfzx'] = 1

        for key in old_pafd_data["d"]["oldInfo"]:
            if key.startswith("xs_"):
                pafd_data.update({key: old_pafd_data["d"]["oldInfo"][key]})

        response = s.post(save_url, data=pafd_data)
        print(response.text)

        if json.loads(response.text)['e'] == 0:
            break

        sleep_t = random.randint(2, 10)
        print("Tick failed, retrying in ", sleep_t)
        time.sleep(sleep_t)
        retry += 1

    if retry == max_retry:
        raise Exception("Tick failed")


if __name__ == "__main__":
    for i in range(len(usernames)):
        Thread(target=tick_for_id, args=(i,)).start()
