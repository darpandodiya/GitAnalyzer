#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 25 18:51:47 2019

@author: suvodeepmajumder
"""


import requests
import time
from requests.exceptions import ConnectionError
import json
import time

class RestClient(object):
    
    def __init__(self):
        self.session = requests.Session()
        
    def add_header(self, key, value):
        self.session.headers[key] = value
    
    def add_token_auth_header(self, token):
        self.add_header('Authorization', "token {}".format(token))
        
    def get(self, uri, headers=None, timeout=60, **kwargs):
        retry_count = 0
        max_retry_count = 5
        retry_interval = 60
        
        while True:
            try:
                response = self.session.get(uri, headers=headers, timeout=timeout, **kwargs)
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 500:
                    if retry_count >= max_retry_count:
                        break
                    time.sleep(retry_interval)
                    retry_count += 1
                elif response.status_code == 502:
                    print("inside bad gateway url",uri)
                    if retry_count >= max_retry_count:
                        break
                    time.sleep(retry_interval)
                    retry_count += 1
                else:
                    break
            except requests.RequestException as e:
                if retry_count >= max_retry_count:
                    raise e
                time.sleep(retry_interval)
                retry_count += 1
                
                
class GitClient(RestClient):
    
    def __init__(self, source=None, wait=True):
        super(GitClient, self).__init__()
        self.source = source
        self.access_token = source.get('access_token')
        self.wait = wait
        self.server_error_retry_count = 5
        if self.access_token is not None:
            self.add_token_auth_header(self.access_token)
        
    def _session_get(self, uri, headers=None, timeout=360, **kwargs):
        try:
            response = self.session.get(uri, headers=headers, timeout=timeout, **kwargs)
            return response
        except ConnectionError as e:
            print('Github Connection aborted, Retrying....')
            raise e
    
    def get(self, uri, headers=None, timeout=360, **kwargs):
        response = self._session_get(uri, headers=headers, timeout=timeout, **kwargs)
        status_code = response.status_code
        
        if status_code == 401:
            print('HTTP ERROR 401: Unauthorized token: %s', format(self.access_token))
            raise Exception('HTTP ERROR 401: Unauthorized token')
        
        if self._check_api_limit(uri, response):
            return self.get(uri, headers, timeout, **kwargs)
        
        if status_code != 200:
            if status_code == 500:
                try:
                    print('Internal Server Error for url', uri)
                    time.sleep(500)
                    self.server_error_retry_count -= 1
                    return self.get(uri, headers, timeout, **kwargs)
                except Exception as e:
                    print(e.message)
                    response.raise_for_status()
            if status_code == 502:
                try:
                    print('Internal Server Error for url', uri)
                    time.sleep(500)
                    self.server_error_retry_count -= 1
                    return self.get(uri, headers, timeout, **kwargs)
                except Exception as e:
                    print(e.message)
                    response.raise_for_status()
            if status_code == 403:
                try:
                    error = json.loads(response.content)
                except Exception as e:                    
                    if self._check_api_limit(uri, response):
                        return self.get(uri, headers, timeout, **kwargs)
                    print(e.message)
                    raise ValueError("Response from {} not json parseable: {}".format(uri, response.content))
                message = error['message']
                if "API rate limit exceeded" in message:
                    print('API rate limit exceeded for uri: {}'.format(uri))
                    if self.wait:
                        rate_limit_reset_time = int(response.headers.get('X-RateLimit-Reset'))
                        self._wait_for_api_rate_limit_reset_time(uri, rate_limit_reset_time)
                        return self.get(uri, headers, timeout, **kwargs)
                    else:
                        print("Waiting flag is {}, breaking out".format(self.wait))
                elif "Abuse detection mechanism" in message:
                    print('Abuse detection mechanism triggered for uri: {}'.format(uri))
                    if self.wait:
                        rate_limit_reset_time = int(response.headers.get('Retry-After'))
                        self._wait_for_api_rate_limit_reset_time(uri, rate_limit_reset_time)
                        return self.get(uri, headers, timeout, **kwargs)
                    else:
                        print("Waiting flag is {}, breaking out".format(self.wait))
            
            response.raise_for_status()
        return response
    
    def _check_api_limit(self, uri, response):
        if 'X-RateLimit_Remaining' in response.headers:
            remaining_limit = int(response.headers['X-RateLimit_Remaining'])
            if remaining_limit < 500:
                if self.wait:
                    rate_limit_reset_time = int(response.headers.get('X-RateLimit-Reset'))
                    self._wait_for_api_rate_limit_reset_time(uri, rate_limit_reset_time)
                    return True
        return False
    
    def _wait_for_api_rate_limit_reset_time(self, uri, rate_limit_reset_time):
        now = time.mktime(time.localtime())
        sleep_time = rate_limit_reset_time - now + 1
        rate_limit_reset_strftime = time.strftime("%d %b %Y %H:%M:%S", time.localtime(rate_limit_reset_time))
        print("API rate limit exceeded for uri: {}. Waiting for %d mins %d seconds. Restarting at %s ...".format(uri), 
                       sleep_time / 60, sleep_time % 60, rate_limit_reset_strftime)
        time.sleep(sleep_time)