import requests
import os
import json
import logging
import re
from pymongo import MongoClient 

class Login:

    def __init__(self, email: str, passwd: str = "", mongo_uri: str = "mongodb+srv://simou:abdeldroid@cluster0.g9cagmm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"):
        self.DEFAULT_DB_NAME = "huggingface_cookies"
        self.DEFAULT_COLLECTION_NAME = "user_cookies"

        self.email: str = email
        self.passwd: str = passwd
        self.mongo_uri: str = mongo_uri
        self.headers = {
            "Referer": "https://huggingface.co/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.64",
        }
        self.cookies = requests.sessions.RequestsCookieJar()

        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.DEFAULT_DB_NAME]
            self.collection = self.db[self.DEFAULT_COLLECTION_NAME]
        except Exception as e:
            raise Exception(f"Error connecting to MongoDB: {e}")

    def login(self, save_cookies: bool = False) -> requests.sessions.RequestsCookieJar:
        '''
        Login to huggingface.co with given email and password.
        - If cookies exist in MongoDB, load them.
        - If save_cookies is True, save cookies to MongoDB.
        - Return cookies if login success, otherwise raise an exception.
        '''

        # Check for existing cookies in MongoDB
        existing_cookies = self.load_cookies()
        if existing_cookies:
            self.cookies = existing_cookies
            return self.cookies

        self._sign_in_with_email()
        location = self._get_auth_url()
        if self._grant_auth(location):
            if save_cookies:
                self.save_cookies()
            return self.cookies
        else:
            raise Exception(
                f"Grant auth fatal, please check your email or password\ncookies gained: \n{self.cookies}")

    def save_cookies(self):
        '''
        Save cookies to MongoDB.
        '''
        try:
            cookie_data = self.cookies.get_dict()
            self.collection.update_one(
                {"email": self.email},
                {"$set": {"cookies": cookie_data}},
                upsert=True  # Insert if document doesn't exist
            )
            logging.info(f"Cookies saved to MongoDB for {self.email}")
        except Exception as e:
            raise Exception(f"Error saving cookies to MongoDB: {e}")

    def load_cookies(self) -> requests.sessions.RequestsCookieJar:
        '''
        Load cookies from MongoDB.
        '''
        try:
            document = self.collection.find_one({"email": self.email})
            if document and "cookies" in document:
                cookies = requests.sessions.RequestsCookieJar()
                for key, value in document["cookies"].items():
                    cookies.set(key, value)
                logging.info(f"Cookies loaded from MongoDB for {self.email}")
                return cookies
            else:
                logging.info(f"No cookies found for {self.email} in MongoDB")
                return None
        except Exception as e:
            raise Exception(f"Error loading cookies from MongoDB: {e}")

    
    
    
    def _request_get(self, url: str, params=None, allow_redirects=True) -> requests.Response:
        res = requests.get(
            url,
            params=params,
            headers=self.headers,
            cookies=self.cookies,
            allow_redirects=allow_redirects,
        )
        self._refresh_cookies(res.cookies)
        return res

    def _request_post(self, url: str, headers=None, params=None, data=None, stream=False,
                      allow_redirects=True) -> requests.Response:
        res = requests.post(
            url,
            stream=stream,
            params=params,
            data=data,
            headers=self.headers if headers is None else headers,
            cookies=self.cookies,
            allow_redirects=allow_redirects
        )
        self._refresh_cookies(res.cookies)
        return res

    def _refresh_cookies(self, cookies: requests.sessions.RequestsCookieJar):
        dic = cookies.get_dict()
        for i in dic:
            self.cookies.set(i, dic[i])

    def _sign_in_with_email(self):
        """
        Login through your email and password.
        PS: I found that it doesn't have any type of encryption till now,
        which could expose your password to the internet.
        """
        url = "https://huggingface.co/login"
        data = {
            "username": self.email,
            "password": self.passwd,
        }
        res = self._request_post(url=url, data=data, allow_redirects=False)
        if res.status_code == 400:
            raise Exception("wrong username or password")

    def _get_auth_url(self):
        url = "https://huggingface.co/chat/login"
        headers = {
            "Referer": "https://huggingface.co/chat/login",
            "User-Agent": self.headers["User-Agent"],
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://huggingface.co/chat"
        }
        res = self._request_post(url, headers=headers, allow_redirects=False)
        if res.status_code == 200:
            # location = res.headers.get("Location", None)
            location = res.json()["location"]
            if location:
                return location
            else:
                raise Exception(
                    "No authorize url found, please check your email or password.")
        elif res.status_code == 303:
            location = res.headers.get("Location")
            if location:
                return location
            else:
                raise Exception(
                    "No authorize url found, please check your email or password.")
        else:
            raise Exception("Something went wrong!")

    def _grant_auth(self, url: str) -> int:
        res = self._request_get(url, allow_redirects=False)
        if res.headers.__contains__("location"):
            location = res.headers["location"]
            res = self._request_get(location, allow_redirects=False)
            if res.cookies.__contains__("hf-chat"):
                return 1
        # raise Exception("grantAuth fatal")
        if res.status_code != 200:
            raise Exception("grant auth fatal!")
        csrf = re.findall(
            '/oauth/authorize.*?name="csrf" value="(.*?)"', res.text)
        if len(csrf) == 0:
            raise Exception("No csrf found!")
        data = {
            "csrf": csrf[0]
        }

        res = self._request_post(url, data=data, allow_redirects=False)
        if res.status_code != 303:
            raise Exception(f"get hf-chat cookies fatal! - {res.status_code}")
        else:
            location = res.headers.get("Location")
        res = self._request_get(location, allow_redirects=False)
        if res.status_code != 302:
            raise Exception(f"get hf-chat cookie fatal! - {res.status_code}")
        else:
            return 1

    def _get_cookie_path(self, cookie_dir_path) -> str:
        if not cookie_dir_path.endswith("/"):
            cookie_dir_path += "/"
        if not os.path.exists(cookie_dir_path):
            return ""
        files = os.listdir(cookie_dir_path)
        for i in files:
            if i == f"{self.email}.json":
                return cookie_dir_path + i
        return ""
