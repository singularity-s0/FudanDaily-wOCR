import json
import random
import time
from threading import Thread

import easyocr
import requests
from bs4 import BeautifulSoup

USERS = [('username', 'password', 36000)]

CUDA = None
headers = {
    "Origin": "https://zlapp.fudan.edu.cn",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_1_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.1 Mobile/15E148 Safari/604.1",
    "Referer": "https://zlapp.fudan.edu.cn/site/ncov/fudanDaily?from=history",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-us",
    "Connection": "keep-alive"
}
login_url = "https://uis.fudan.edu.cn/authserver/login?service=https%3A%2F%2Fzlapp.fudan.edu.cn%2Fa_fudanzlapp%2Fapi%2Fsso%2Findex%3Fredirect%3Dhttps%253A%252F%252Fzlapp.fudan.edu.cn%252Fsite%252Fncov%252FfudanDaily%253Ffrom%253Dhistory%26from%3Dwap"
get_info_url = "https://zlapp.fudan.edu.cn/ncov/wap/fudan/get-info"
save_url = "https://zlapp.fudan.edu.cn/ncov/wap/fudan/save"
code_url = "https://zlapp.fudan.edu.cn/backend/default/code"
error_string = "您将登录的是："
max_retry = 3


def tick(user, pwd, max_time):
    print("Ticking for user ", user)
    # Randomize time
    wait_time = random.randint(0, max_time)
    print("Randomize time: waiting for ", wait_time)
    time.sleep(wait_time)

    data = {
        "username": user,
        "password": pwd
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

        ocr_detector = easyocr.Reader(['en'], gpu=False, recognizer=False)
        code = s.get(code_url).content
        boundary_a, boundary_b = ocr_detector.detect(code, reformat=True)
        del ocr_detector
        ocr_recognizer = easyocr.Reader(['en'], gpu=False, detector=False)
        code_result = ocr_recognizer.recognize(code, boundary_a[0], boundary_b[0], reformat=True)
        code_result_trimmed = code_result[0][1].replace(' ', '')
        del ocr_recognizer
        print("Verification code result: ", code_result_trimmed, "confidence: ", code_result[0][2])

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
            "code": code_result_trimmed
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
        if json.loads(response.text)['m'] == '今天已经填报了':
            break
        sleep_t = random.randint(2, 10)
        print("Tick failed, retrying in ", sleep_t)
        time.sleep(sleep_t)
        retry += 1

    if retry == max_retry:
        raise Exception("Tick failed")


if __name__ == '__main__':
    for user in USERS:
        Thread(target=tick, args=(user[0], user[1], user[2])).start()
