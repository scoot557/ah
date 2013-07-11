import urllib #for url-encode
import urllib2 #for getting and receiving data from server
import time #Unix timestamp
import hmac #for signing
import hashlib #for signing
import random #For nonce generation
import base64 #For conversion of hmac hash from bytes to human-readable string
import json
import modelconn
import datetime

from oauth2 import *




host=modelconn.envloc
base_url="http://%s.actuallyheard.com" % host

twitter_rt_url = 'https://api.twitter.com/oauth/request_token'
twitter_auth_url = 'https://api.twitter.com/oauth/authorize'
twitter_authenticate_url = 'https://api.twitter.com/oauth/authenticate'
twitter_at_url = 'https://api.twitter.com/oauth/access_token'
twitter_connect_cb = '%s/twconnectcb'
twitter_signup_cb = '%s/twsignupcb'
twitter_cb_url = '%s/twoacb' % base_url
twitter_login_cb_url = '%s/twoalogincb' % base_url


class Tweeter:
    def __init__(self, consumerKey = '', consumerSecret = '', accessToken = '', accessTokenSecret = ''):
        self.setConsumerCreds(consumerKey, consumerSecret)
        self.set_access_token(accessToken, accessTokenSecret)
        self.requestToken = ''
        self.requestTokenSecret = ''
        self.screen_name=''
        self.user_id=''
        self.since_id=''
        self.last_sync=''

    def syncTweets(self):
        #if its the first time we grab the 200 tweets
        #if not, we'll be a little less greedy
        if self.since_id=='':
            count=200
        else:
            count=40

        newres = self.read_tweets(count)
        res = newres
        #as long as we get the same # of results as we ask for
        #we have to keep pulling.
        #40 at a time no matter what now.
        while len(newres)==count:
            count=40
            #max_id is a stopper point so twitter knows to keep it to
            #tweets that are further down the timeline
            max_id = str(long(res[len(res)-1]['id'])-1)
            newres = self.read_tweets(count,max_id)

            #append our new results to a overall list
            res += newres

        #when we are done, update this value. have model save state
        if len(res)>0:
            self.since_id=str(res[0]['id_str'])
        self.last_sync = datetime.datetime.now().isoformat()
        return res

    def read_tweets(self, count='40', max_id=''):
        try:
            
            twit_params = dict(screen_name=self.screen_name,count=str(count))
            if max_id!='':
                twit_params['max_id'] = str(max_id)
            if self.since_id!='':
                twit_params['since_id'] = str(self.since_id)

            results = json.loads(self.get_api_response('https://api.twitter.com/1.1/statuses/user_timeline.json',
                                    parameters=twit_params,
                                    method='GET'))

        except ValueError, e:
            print 'exception %s' % e
            return ''
        return results

    def returnHTML(self, tweet=[]):

        return HTMLTEXT

    def setTweeter(self, twitinfo={}):
        val=twitinfo.get('screen_name',False)
        if val:    self.screen_name = val
        val=twitinfo.get('user_id',False)
        if val:    self.user_id = val
        val=twitinfo.get('access_token',False)
        if val:    self.accessToken = val
        val=twitinfo.get('access_token_secret',False)
        if val:    self.accessTokenSecret = val
        val=twitinfo.get('since_id',-1)
        if val!=-1:    self.since_id = val
        val=twitinfo.get('last_sync',-1)
        if val!=-1:    self.last_sync = val

    def setConsumerCreds(self, ckey, csecret):
        self.consumerKey = ckey
        self.consumerSecret = csecret

    def set_access_token(self, key, secret):
        self.accessToken = key
        self.accessTokenSecret = secret

    def get_authorization_url(self, resourceUrl, endpointUrl, callbackUrl):
        oauthParameters = {}
        _add_oauth_parameters(oauthParameters, dict(consumerKey=self.consumerKey),False)
        oauthParameters["oauth_callback"] = callbackUrl
        baseString = _get_base_string(resourceUrl, oauthParameters)
        signingKey = self.consumerSecret + "&"
        oauthParameters["oauth_signature"] = _get_signature(signingKey, baseString)
        headers = _build_oauth_headers(oauthParameters)
        httpRequest = urllib2.Request(resourceUrl)
        httpRequest.add_header("Authorization", headers)
        try:
            httpResponse = urllib2.urlopen(httpRequest,data={})
        except urllib2.HTTPError, e:
            return "Response: %s" % e.read()
        responseData = httpResponse.read()
        responseParameters = responseData.split('&') #gives is a list with each parameter / value pair
        for s in responseParameters: #these are strings, so we're iterating over a list of strings.
            key, value = s.split('=')
            if (key=='oauth_token_secret'):
                self.requestTokenSecret = value
            elif (key=='oauth_token'):
                self.requestToken = value
        return endpointUrl + "?oauth_token=" + self.requestToken

    def get_access_token(self, resourceUrl, requestTok, requestTokSecret, oauth_verifier):

        self.requestToken = requestTok
        self.requestTokenSecret = requestTokSecret
        oauthParameters = {"oauth_verifier" : oauth_verifier, "oauth_token" : self.requestToken}

        _add_oauth_parameters(oauthParameters, dict(consumerKey=self.consumerKey),False)
        baseString = _get_base_string(resourceUrl, oauthParameters)
        signingKey = self.consumerSecret + "&" + self.requestTokenSecret
        oauthParameters["oauth_signature"] = _get_signature(signingKey, baseString)
        header = _build_oauth_headers(oauthParameters)
        httpRequest = urllib2.Request(resourceUrl)
        httpRequest.add_header("Authorization", header)
        httpResponse = urllib2.urlopen(httpRequest,data={})
        responseParameters = httpResponse.read().split('&')
        return responseParameters

    def get_api_response(self, resourceUrl, method = "POST", parameters = {}):
        _add_oauth_parameters(parameters, dict(consumerKey=self.consumerKey, accessToken=self.accessToken))
        baseString = _get_base_string(resourceUrl, parameters, method)
        signingKey = self.consumerSecret + "&" + self.accessTokenSecret
        parameters["oauth_signature"] = _get_signature(signingKey, baseString)
        parameters2 = {}
        for s in sorted(parameters.keys()):
            if s.find("oauth_") == -1:
                parameters2[s] = parameters[s]
                del parameters[s]
        header = _build_oauth_headers(parameters)

        if method.lower()=='post':
            httpRequest = urllib2.Request(resourceUrl)
            httpRequest.add_header("Authorization" , header)
            httpResponse = urllib2.urlopen(httpRequest, data=urllib.urlencode(parameters2))
        else:
            print parameters2
            print resourceUrl
            print header
            if len(parameters2)>0:
                url = resourceUrl + '?' + urllib.urlencode(parameters2)
            else:
                url = resourceUrl
            httpRequest = urllib2.Request(url)
            httpRequest.add_header("Authorization" , header)
            httpResponse = urllib2.urlopen(httpRequest)

        respStr = httpResponse.read()
        return respStr


def _get_base_string(resourceUrl, values, method="POST"):
    # In the format METHOD&encoded(resource)&parameter=value&parameter=value&...
    baseString = method + "&" + _url_encode(resourceUrl) + "&"
    #The parameters and values should be sorted by name, and then by value.
    sortedKeys = sorted(values.keys())
    #We use sorted() as opposed to values.keys().sort() so we don't modify the original collection.
    for i in range(len(sortedKeys)):
        baseString = baseString + _url_encode(sortedKeys[i] + "=") + _url_encode(_url_encode(values[sortedKeys[i]]))
        #Don't put an encoded & at the end of the string; trailing ampersands are not allowed here.
        if i < len(sortedKeys) - 1:
            baseString = baseString + _url_encode("&")
    return baseString

def _add_oauth_parameters(parameters, creds, addAccessToken = True):
    parameters["oauth_consumer_key"] = creds['consumerKey']
    if (addAccessToken):
        parameters["oauth_token"] = creds['accessToken']
    parameters["oauth_version"] = "1.0"
    #Nonce in our case is a numeric value, but we need
    #to cast it to a string so it can be url-encoded.
    parameters["oauth_nonce"] = str(_get_nonce())
    parameters["oauth_timestamp"] = str(_get_timestamp())
    parameters["oauth_signature_method"] = "HMAC-SHA1"

def _get_nonce():
    # Simply choose a number between 1 and 999,999,999
    r = random.randint(1, 999999999)
    return r

def _get_timestamp():
    return int(time.time())

def _get_signature(signingKey, stringToHash):
    hmacAlg = hmac.HMAC(signingKey, stringToHash, hashlib.sha1)
    return base64.b64encode(hmacAlg.digest())

def _url_encode(data):
    return urllib.quote(data, "")


def _build_oauth_headers(parameters):
    header = "OAuth "
    sortedKeys = sorted(parameters.keys()) #although not necessary
    for i in range(len(sortedKeys)):
        header = header + _url_encode(sortedKeys[i]) + "=\"" + _url_encode(parameters[sortedKeys[i]]) + "\""
        if i < len(sortedKeys) - 1:
            header = header + ","
    return header
