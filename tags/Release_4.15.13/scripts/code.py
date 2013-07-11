import web
from web import form
from subprocess import call
import sys, os, tempfile
import re, base64, json, hashlib, datetime,urllib,urllib2,oauth2,urlparse

web.config.debug = False
web.config.session_parameters.cookie_path='/'
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import usermodel, reviewmodel, modelconn, oauthmod as twitmod
import ttp


#CHANGE THIS TO REFLECT PUBLISH ENVIRONMENT(STAGE, WWW)

host=modelconn.envloc
base_url="http://%s.actuallyheard.com" % host


urls = (
    '/moretweets',         'AjaxMoreTweets',
    '/oacb',                'OAuthCallback',
    '/parentrollup',    'AjaxParentRollup',
    '/oaredir',             'OAuthRedirect',
    '/twoacb',                'OAuthTwitterCallback',
    '/twoaredir',             'OAuthTwitterRedirect',
    '/newfbuser',             'NewFacebookUser',
    '/newtwuser',             'NewTwitterUser',
    '/home',                'Home',
    '/account',             'AccountSettings',
    '/',                    'Home',
    '/profile',             'ViewProfile',
    '/resetpw',         'ResetPassword',
    '/recentreviews',       'RecentReviewFeedBackEnd',
    '/myrecentreviews','MyRecentReviewFeedBackEnd',
    '/ajaxprofile','AjaxProfile',
    '/listing',     'Browse',
    '/timeline',    'Timeline',
    '/mytimeline',    'MyTimeline',
    '/editprofile',        'EditProfile',
    '/editpassword','EditPassword',
    '/editsocial','EditSocial',
    '/dynlogin',    'LoginAjax',
    '/dynlogout',    'LogoutAjax',
    '/signup',        'Signup',
    '/ajaxaddinteraction',    'AddInteractionAjax',
    '/ajaxdeletereview',    'DeleteReview',
    '/ajaxeditreview',    'EditReview',
    '/ajaxaddcomment',    'AddComment',
    '/ajaxsearch',    'SearchBackEnd',
    '/ajaxtimeline','TimelineBackEnd',
    '/myajaxtimeline','MyTimelineBackEnd',
    '/confirm',     'ConfirmAccount',
    '/upload', 'ImageUpload',
     '/listing',    'Listing',
     '/about', 'About',
     '/faq', 'FAQ',
     '/team', 'Team',
     '/graphexport','ExportSVGtoPNG',
     '/mytweets','MyTweets',
     '/ajaxtweets','AjaxTweets'

)

#Establish WSGI web app.
app = web.application(urls, globals(), autoreload=False)
application = app.wsgifunc()


#Establish sessions in the DB, login-status and user id.

curdir = os.path.dirname(__file__)
session = web.session.Session(app, web.session.DBStore(usermodel.db, 'sessions'),
                                    initializer={   'fname':        'none',
                                                    'location':     'none',
                                                    'lname':        'none',
                                                    'zip':        'none',
                                                    'displayname':  'none',
                                                    'login_status': 0,
                                                    'email':        'none',
                                                    'badge':        'none',
                                                    'userid':       'none',
                                                    'profilepic':   '/static/profile_photo.jpg',
                                                    'twitoauth':{},
                                                    'fboauth':{},
                                                    'tweetclient':twitmod.Tweeter(usermodel.tw_c_key(),usermodel.tw_c_secret())})

ratingToText = {'-2':'Terrible.',
                '-1':'Dislike.',
                '0':'Meh.',
                '1':'Solid.',
                '2':'Take my money.'}
globals = { 'session' : session, 'ratingLookup' : ratingToText }

render = web.template.render(os.path.join(os.path.dirname(__file__), 'templates/'), base='newbase',globals=globals)

newrender = web.template.render(os.path.join(os.path.dirname(__file__), 'templates/'), base='scansheader',globals=globals)
#Email Validator
emailregex = re.compile('^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}$')
def notfound():
    return web.notfound(autorender().notfound())

app.notfound = notfound

def parse_signed_request(req):
    """takes a base64 encoded string from facebook, validate and return dictionary object."""
    #add validation and catch exceptions.
    (checksum, encoded_string) = req.split('.')
    encoded_string += "=" * ((4 - len(encoded_string) % 4) % 4)
    d = json.loads(base64.b64decode(encoded_string))
    return d


def logged():
    if session.login_status==1:    return True
    else:                return False

def loginbyid(userid):
    session.userid=userid
    session.login_status = 1
    loadprofile(userid)
    userinfo = usermodel.getUserById(userid)
    session.email = userinfo['email']
    session.twitoauth={}
    session.fboauth={}

    if userinfo.tw_handle:
        session.twitoauth = json.loads(userinfo.get('twitter_token'))
        try:
            session.tweetclient.setTweeter(session.twitoauth)
        except AttributeError:
            session.tweetclient = twitmod.Tweeter(usermodel.tw_c_key(),usermodel.tw_c_secret())
            session.tweetclient.setTweeter(session.twitoauth)
    if userinfo.fb_id:  session.fboauth = json.loads(userinfo.get('facebook_token'))


def loadprofile(userid):
    info = usermodel.getProfileInfo(userid)
    session.fname = info.get('fname','')
    session.location = info.get('location','')
    session.lname = info.get('lname','')
    session.displayname = info.get('displayname','')
    session.profilepic = info.get('profilepic','')
    session.zip = info.get('zip','')


def userlogout():
    session.fname='none'
    session.location='none'
    session.lnamelname='none'
    session.zip='none'
    session.displayname='none'
    session.login_status=0
    session.email='none'
    session.badge='none'
    session.profilepic='/static/profile_photo.jpg'
    session.userid='none'
    session.twitoauth = {}
    session.fboauth = {}
    session.kill

def printses(ses):
    for x, v in ses.iteritems():
        print x,v


def autorender():
    printses(session)
    if logged():    return newrender
    else:            return newrender


class MergeAccounts:
    def POST(self):
        data = web.input()
        uid = data.get('uid','')
        fbid = data.get('fb_id','')
        twid = data.get('tw_handle','')
        if uid!='':
            return usermodel.mergeUser(uid,fbid,twid)


class DeleteReview:
    def POST(self):
        returnval = False
        data = web.input()
        try:
            rid = data.get('rid',-1)
        except ValueError:
            return returnval

        uid = session.userid
        rev = reviewmodel.getReview(rid)
        print uid, rev
        if rev.get('uid',False) == uid:
            returnval = reviewmodel.deleteReview(uid,rid)
        if returnval:   returnval=rid
        return returnval

class OAuthCallback:
    def GET(self):
        data = web.input()
        try:
            req_token = data['code']
        except KeyError:
            error_msg = data['error']
            return "error: %s" % error_msg
        args = dict(client_id=usermodel.fb_cli_id(),code=req_token,
                    client_secret=usermodel.fb_cli_secret(),
                    redirect_uri='%s/oacb' % base_url)
        resp = urllib.urlopen('https://graph.facebook.com/oauth/access_token?' + urllib.urlencode(args)).read().split('&')
        access_token=''
        for s in resp:
            key, val = s.split('=')
            if key=='access_token':
                access_token = val
        if access_token!='':
            #ok - we're back from Faceook, we have an access_token.
            #lets check to see what we info we have from the user
            #if they are logged in, lets update their access token
            fb_profile = {}
            profile = json.load(urllib.urlopen(
                                "https://graph.facebook.com/me?" +
                                urllib.urlencode(dict(access_token=access_token))))
            print profile
            fb_profile['access_token'] = access_token
            fb_profile['id'] = profile.get('id','no_id')
            fb_profile['first_name'] = profile.get('first_name','no_first_name')
            fb_profile['last_name'] = profile.get('last_name','no_last_name')
            fb_profile['email'] = profile.get('email','no_email')
            fb_profile['location'] = profile.get('location',{})
            fb_profile['name'] = profile.get('name','no_name')
            fb_profile['profile_url'] = profile.get('link','no_link')
            existingemail = usermodel.getUserByEmail(fb_profile['email'])
            existingtoken = usermodel.getFbUser(fb_profile['id'])

            if session.userid!='none':
                #someone is already logged in and just got us an access token
                #to facebook - update their AH account with their FB token
                usermodel.addFbToken(session.userid,fb_profile)
                session.fboauth=fb_profile
                goto_url = '%s/account' % base_url

            elif existingemail:
                #if we aren't logged in, but the fb token's email matches an
                #account - we can connect the two and log this user in.
                usermodel.addFbToken(existingemail.id,fb_profile)
                loginbyid(existingemail.id)
                goto_url = '%s/' % base_url

            elif existingtoken:
                #if the token matches a user, log them in.
                loginbyid(existing.get('id'))
                goto_url = '%s/' % base_url

            else:
                #new social user
                newuid = usermodel.addFbUser(fb_profile['id'],fb_profile)
                if newuid:    loginbyid(newuid)
                goto_url = '%s/' % base_url

            return autorender().popupcb(goto_url)






class AccountSettings:
    def GET(self):
        if logged(): return autorender().accountsettings()
        else:        raise web.seeother('%s/' % base_url)

    def POST(self):
        if not logged(): raise web.seeother('%s/' % base_url)
        data = web.input()
        network = data.get('network',False)
        print data, network
        if network=='facebook':
            if usermodel.delFbToken(session.userid):
                session.fboauth={}
                return True
        elif network=='twitter':
            if usermodel.delTwToken(session.userid):
                session.twitoauth={}
                return True
        return False

class OAuthTwitterCallback:
    def GET(self):

        data = web.input()
        auth_token = data.get('oauth_token',False)
        if not auth_token:
            if session.userid!='none':
                goto_url = '%s/account' % base_url
            else:
                goto_url = '%s' % base_url
            return autorender().popupcb(goto_url)
        auth_verifier = data['oauth_verifier']
        if session.twitoauth['auth_token'] == auth_token:
            #we have the correct auth token back from twitter.
            #lets exchange this for an access token and then we can save it.
            response = session.tweetclient.get_access_token(twitmod.twitter_at_url,
                                                    auth_token,
                                                    session.twitoauth['auth_token_secret'],
                                                    auth_verifier)

            for pairs in response:
                key, val = pairs.split('=')
                if key=='oauth_token':
                    session.twitoauth['access_token']=val
                elif key=='oauth_token_secret':
                    session.twitoauth['access_token_secret']=val
                else:
                    session.twitoauth[key]=val


            #establish authenticated token for our twitter API client
            session.tweetclient.setTweeter(session.twitoauth) #_access_token(session.twitoauth['access_token'],session.twitoauth['access_token_secret'])

            #save this to user info
            if session.userid!='none':
                update = usermodel.addTwToken(session.userid,session.twitoauth)

                goto_url = '%s/account' % base_url
                return autorender().popupcb(goto_url)

            else:
                existing = usermodel.getTwUser(session.twitoauth['screen_name'])
                #a user who has already verified his twitter info to us.
                #Log them in via session.twitoauth info in twitlogin().
                if existing:
                    loginbyid(existing.get('id'))
                    goto_url = '%s/' % base_url
                    return autorender().popupcb(goto_url)

                else:
                    #we've never seen this twitter handle and they aren't
                    #logged in.  we should treat them as a new user.
                    #newuser = usermodel.addTwUser(screen_name)

                    newuid = usermodel.addTwUser(session.twitoauth['screen_name'],session.twitoauth)
                    if newuid:    loginbyid(newuid)
                    goto_url = '%s/' % base_url
                    return autorender().popupcb(goto_url)

class AjaxTweets:
    def GET(self):
        pass

    def POST(self):
        data = web.input()
        web.header('Content-Type', 'application/json')
        print "received this."
        print data

        action = data.get('action',False)
        twid=str(data.get('tweet_id',False))
        returnval = dict(status=False,tweet_id=str(twid))

        if action=='hide':
            returnval['status'] = reviewmodel.hideTweet(twid, session.userid)
        elif action=='unhide':
            returnval['status'] = reviewmodel.unhideTweet(twid, session.userid)

        print "returning this:"
        print returnval
        return json.dumps(returnval)

class OAuthTwitterRedirect:
    def GET(self):
        data=web.input()
        action = data.get('action','authorize')
        #if action is authenticate we can bypass getting an access token
        #if they've already allowed us, the flow will be seamless
        #if not - twitter will give us back an exchangeable auth token
        if action=='authenticate':
            if session.userid!='none':    raise web.seeother('%s/' % base_url)
            auth_url = twitmod.twitter_authenticate_url
        #otherwise we are looking for an access_token
        else:
            auth_url = twitmod.twitter_auth_url

        callback_url = twitmod.twitter_cb_url
        request_url = twitmod.twitter_rt_url
        redirect_url = session.tweetclient.get_authorization_url(request_url,auth_url,callback_url)
        session.twitoauth['auth_token'] = session.tweetclient.requestToken
        session.twitoauth['auth_token_secret'] = session.tweetclient.requestTokenSecret
        raise web.seeother(redirect_url)


class OAuthRedirect:
    def GET(self):
        args = dict(client_id=usermodel.fb_cli_id(),redirect_uri='%s/oacb' % base_url,scope='email')
        oareq_url = 'https://graph.facebook.com/oauth/authorize?' + urllib.urlencode(args)
        raise web.seeother(oareq_url)

class ExportSVGtoPNG:
    def POST(self):
        #take svg string
        #concat the xml CSS call and the svg string into new svg.
        #convert that SVG to PNG
        #make a watermark with ActuallyHeard and a link back to timeline
        #compose final image overlaying watermark onto graph SVG.
        #return contents of new image back with appropriate content type/dispo.
        #svgstring must be a XMLSerialized group of DOM Elements.
        #filename is the suggested filename based on product name and date.
        data = web.input()
        svgstring = data.get('svgstring','')
        suggfile = data.get('filename','mygraph.png')

        # static dir - dir containing CSS file.
        #linkback - referer should be the source URL.  if not default to homepage
        staticdir = '%s/static' % (os.path.abspath(os.path.dirname(__file__)))
        cssfile = '%s/ahcharts.css' % (staticdir)
        cssfile2 = '%s/entity.css' % (staticdir)
        linkback=web.ctx.environ.get('HTTP_REFERER',base_url)
        copyrighttext = 'ActuallyHeard (%s)' % linkback

        #setup temp files to manipulate
        # infile - temp file to contain SVG string sent from server + CSS declaration
        # outfile - temp file to contain SVG converted to PNG
        # watermarkfile - dynamic watermark containing source link
        # finalfile - composite image of watermarkfile and outfile


        infile = tempfile.mkstemp(suffix='.svg')
        outfile = tempfile.mkstemp(suffix='.png')
        finalfile = tempfile.mkstemp(suffix='.png')
        watermarkfile = tempfile.mkstemp(suffix='.miff')

        try:
            # Open up the temp SVG file
            # Declare CSS attachment and print the SVG DOM elements from POST data.
            fih = infile[1]
            foh = outfile[1]
            wmh = watermarkfile[1]
            ffh = finalfile[1]
            fioutput = open(fih,'w')
            fioutput.write('<?xml-stylesheet href="%s" type="text/css"?>' % cssfile)
            fioutput.write('<?xml-stylesheet href="%s" type="text/css"?>' % cssfile2)
            fioutput.write(svgstring)
            fioutput.close()
            os.close(infile[0])

            #convert the new CSS + SVG into an PNG using ImageMagick's convert
            call(["convert",fih,foh])

            #genereate watermark using ImageMagick's convert
            call(['convert',
                '-undercolor','#00000080',
                '-fill','white',
                'label:%s' % copyrighttext,
                wmh])

            #overlay watermark onto graph using ImageMagick's composite
            #composite -gravity SouthEast wm.watermarkfile foh finalfile
            call(['composite',
                '-gravity','SouthEast',
                wmh,
                foh,
                ffh])

            web.header('Content-Type','image/png')
            web.header('Content-Disposition','attachment; filename=%s' % suggfile)
            sendback = open(ffh,'r').read()
            return sendback


        except:
            return False



class EditReview:
    def POST(self):
        returnval = False
        data = web.input()
        try:
            rid = data.get('reviewid',-1)
            updates = json.loads(data.get('updates',{}))
            if updates.get('comment','')!='':
                updates['comment'] = updates['comment'].replace('\n','<br>')
        except ValueError:
            return returnval

        print data,rid,updates
        rev = reviewmodel.getReview(rid)
        if session.userid == rev.uid:
            returnval = reviewmodel.editReview(rid, **updates)

        return returnval


class ImageUpload:
    def GET(self):
        raise web.seeother('%s/account' % base_url)
    def POST(self):
        x = web.input(myfile={})
        filedir = os.path.join(os.path.dirname(__file__), 'static/ppt') # change this to the directory you want to store the file in.
        if 'myfile' in x: # to check if the file-object is created
            filepath=x.myfile.filename.replace('\\','/') # replaces the windows-style slashes with linux ones.
            filename = "%s_p.jpg" % session.userid # ('/')[-1] # splits the and chooses the last part (the filename with extension)
            relativename = "/static/ppt/%s" % filename
            fout = open(filedir +'/'+ filename,'w') # creates the file where the uploaded file should be stored
            fout.write(x.myfile.file.read()) # writes the uploaded file to the newly created file.
            fout.close() # closes the file, upload complete.
            update = {'profilepic':relativename}

            res=usermodel.updateProfileInfo(session.userid,update)
            if res: session.profilepic=relativename
        raise web.seeother('%s/account' % base_url)


class ViewProfile:
    def GET(self):
        data = web.input()
        userid = data.get('id','none')
        if userid!='none':
            user=usermodel.getProfileInfo(userid)
            return autorender().viewprofile(user)
        else:
            raise web.notfound()
class AjaxMoreTweets:
    def GET(self):
        web.header('Content-Type', 'application/json')
        data = web.input()
        limit = 20
        offset = int(data.get('offset',0))


        usertweets = usermodel.getUserTweets(session.userid,limit,offset)
        tweets = map(lambda x: {'handle':x['data']['user']['screen_name'].replace('\n',''),
                                'name':x['data']['user']['name'].replace('\n',''),
                            'text_html':ttp.Parser().parse(x['data']['text'].replace('\n','<br>').replace('"','\\"')).html,
                            'text':x['data']['text'].replace('\n','\\n'),
                            'created_at':x['data']['created_at'],
                            'profile_pic':x['data']['user']['profile_image_url'],
                            'tweet_id':str(x['data']['id']),
                            'review_id':x.get('rid',0), 'hidden':x.get('hidden',0)}, usertweets)
        return json.dumps(tweets)

class MyTweets:
    def GET(self):
        if not logged():
            #use the generic one
            data = web.input()
            handle = data.get('handle',False)
            if handle:	return autorender().newtweets(handle)
            else:		raise web.seeother('%s/' % base_url)
        elif session.userid==67:
            recenttweets = reviewmodel.getMBTATweets()
            recenttweets.reverse()
            #map to dict, filter out retweets for deegs.
            mbtatweets = map(lambda x:{'handle':x['td']['user']['screen_name'].replace('\n',' '),
                                    'name':x['td']['user']['name'].replace('\n',' '),
                                'text_html':ttp.Parser().parse('@%s:%s' % (x['td']['user']['screen_name'],x['td']['text'].replace('\n','<br>').replace('"','\\"'))).html,
                                'text':'@%s:%s' % (x['td']['user']['screen_name'],x['td']['text'].replace('\n','\\n')),
                                'created_at':x['td']['created_at'],
                                'profile_pic':x['td']['user']['profile_image_url'],
                                'tweet_id':x['td']['id'],
                                'review_id':x.get('rid',''),
                                'hidden':x['hidden']},
                                filter(lambda tweet:
                                    not (tweet['td'].get('retweeted_status',dict(retweeted=False)).get('retweeted',False) or tweet['td'].get('text','RT').startswith('RT')),
                                recenttweets))

        elif session.twitoauth!={}:
            newtweets = session.tweetclient.syncTweets()
            if len(newtweets)>0:
                #save these new tweets to the DB
                 inserts = usermodel.storeUserTweets(session.userid,session.twitoauth,newtweets)
            usertweets = usermodel.getUserTweets(session.userid)
            mbtatweets = map(lambda x: {'handle':x['data']['user']['screen_name'].replace('\n',''),
                                    'name':x['data']['user']['name'].replace('\n',''),
                                'text_html':ttp.Parser().parse(x['data']['text'].replace('\n','<br>').replace('"','\\"')).html,
                                'text':x['data']['text'].replace('\n','\\n'),
                                'created_at':x['data']['created_at'],
                                'profile_pic':x['data']['user']['profile_image_url'],
                                'tweet_id':x['data']['id'],
                                'review_id':x.get('rid',0), 'hidden':x.get('hidden',0)}, usertweets)

        else:   mbtatweets=[]

        return autorender().mytweets(mbtatweets)

class LoginPopup:
    def GET(self):
        return autorender().loginpopup()
    def POST(self):
        pass

class ResetPassword:

    def POST(self):
        data=web.input()
        email=data.get('email', '').lower()
        newpassword = data.get('newpw','')
        oldpassword = data.get('oldpw','')
        print 'Password change attempt...'
        if email:
            if  not emailregex.match(email):
                return "Invalid email."
            print 'non logged in user'
            newpassword=usermodel.resetPassword(email)
            if newpassword:
                body = '<p>Your account recently asked for a password reset.  <p>'
                body+= 'Here is the new password:  %s</p>' % (newpassword)
                body+= '<p>Please click here and login: <a href="http://www.actuallyheard.com/">Log In</a></p></html>'
                web.sendmail('Actually Heard',email,'Password Reset', body, headers=({'Content-Type':'text/html; charset="utf-8";'}))
                return True
            else:
                return "No email registered."
        elif session.userid!='none' and newpassword!='':
            oldpw = hashlib.sha256(oldpassword).hexdigest()
            if usermodel.authUser(session.email, oldpw):
                stat=usermodel.changePassword(session.userid,newpassword)
                if stat:
                    body = '<p>Your account recently changed the password to login.  <p>'
                    body+= '<p>If this was unauthorized, please click <a href="http://www.actuallyheard.com/contactus">here</a> and notify us.</p></html>'
                    web.sendmail('Actually Heard',session.email,'Password Change', body, headers=({'Content-Type':'text/html; charset="utf-8";'}))
                    return True
        return 'Invalid Email';

class SearchT:
    def GET(self):
        form = search_form()
        return autorender().searchtest(form, "Your text goes here.")


    def POST(self):
        form = search_form()
        return autorender().searchtest(form, "Your text goes here.")


class Friends:
    def GET(self):
        friendslist = []
        friendslist = usermodel.getFriends(session.userid)
        if friendslist == '[]':    friendslist = ''
        return autorender().friends(friendslist)


class AddFriends:
    def GET(self):
        friendslist = []
        friendslist = usermodel.getFriends(session.userid)
        return autorender().friends(friendslist)

    def POST(self):
        data=web.input()
        newfriendemail=data.get('friendemail','')

        newfriendid=usermodel.getUserId(newfriendemail)
        if newfriendid:    usermodel.addFriends(session.userid,newfriendid)
        friendslist = []
        friendslist = usermodel.getFriends(session.userid)
        return autorender().friends(friendslist)

class Preview:
    def GET(self):
        return autorender().svgwebtesting()

class Browse:
    def GET(self):
            data=web.input()
            entityID = data.get('id',-1)
            results = reviewmodel.queryEntityInfo(entityID)
            entitytree = reviewmodel.getEntityTree(entityID)
            childtree = []

            if entitytree!=0:
                for c in entitytree.get('children','').split(','):
                    info = reviewmodel.queryEntityInfo(c)
                    childtree.append(info)

                for c in childtree:
                    c['children']=[]
                    entitytree = reviewmodel.getEntityTree(c['id'])
                    if entitytree!=0:
                        for gc in entitytree.get('children','').split(','):

                            info = reviewmodel.queryEntityInfo(gc)
                            c['children'].append(info)
            #print childtree
            if len(childtree)>0:    return autorender().listing(results,childtree)
            else:                       raise web.seeother('%s/timeline?id=%s' % (base_url, entityID))

class DeleteFriends:
    def GET(self,friendid):

        usermodel.removeFriend(session.userid, friendid)
        friendslist = []
        friendslist = usermodel.getFriends(session.userid)
        raise web.found('/friends')
    def POST(self):
        friendslist = []
        usermodel.removeFriend(session.userid, friendid)
        friendslist = usermodel.getFriends(session.userid)
        return autorender().friends(friendslist)

class PreReg:
    def GET(self):
        return autorender().comingsoon()

    def POST(self):
        data=web.input()
        email=data.get('email','')
        if email!='':
            usermodel.preReg(email)
            return autorender().comingsoonthanks(email)
        return autorender().comingsoon()

class ConfirmAccount:
    def GET(self):
        data=web.input()
        confirmID=data.get('clinkid','')
        if confirmID!="":    status=usermodel.confirmUser(confirmID)
        if status:
            loginbyid(status.id)
            raise web.seeother('%s' % base_url)
        else: raise web.seeother('%s/' % base_url)

class FreeBaseLookup:
    def GET(self):
        return autorender().freebase()
    """ Class doc """

    def __init__ (self):
        """ Class initialiser """
        pass


class SearchBackEnd:
    def GET(self):
        web.header('Content-Type', 'application/json')
        data=web.input()
        qstring=data.get('term','')
        bufstr='no_results'
        if qstring!='':
            records = reviewmodel.queryBRPDB(qstring)
            jsondict = json.dumps((map (lambda x:  { 'label': x.name,
                                                    'brand': x.brand,
                                                    'id_info':x.id,
                                                    'bid':x.bid,
                                                    'thumbnail':x.thumbnail,
                                                    'term':x.term,
                                                    'match':x.match,
                                                    'reviewable':x.reviewable
                                                    }, records)))

            if len(records)>0:        bufstr=jsondict
        return    bufstr


    def POST(self):
        web.header('Content-Type', 'application/json')
        data=web.input()
        qstring=data.get('term','')
        bufstr='no_results'
        if qstring!='':
            records = reviewmodel.queryBRPDB(qstring)
            jsondict = json.dumps((map (lambda x:  { 'label': x.name,
                                                    'brand': x.brand,
                                                    'id_info':x.id,
                                                    'bid':x.bid,
                                                    'thumbnail':x.thumbnail,
                                                    'term':x.term,
                                                    'match':x.match,
                                                    'reviewable':x.reviewable
                                                    }, records)))
            if len(records)>0:        bufstr=jsondict
        return    bufstr


class TimelineBackEnd:
    def GET(self):
        pass

    def POST(self):
        data=web.input()
        try:
            qid=int(data.get('id',''))
        except ValueError:
            return False
        qtype=data.get('type','')
        qfilter=data.get('filter','public');
        web.header('Content-Type', 'application/json')
        bufstr=[]
        if qid!='' and qtype!='':
            if qtype=='user':
                records = reviewmodel.queryUserReviews(qid)
            if qtype=='product':
                if logged() and qfilter=='mine':
                    records = reviewmodel.queryEntityReviews(qid, session.userid)
                else:
                    records = reviewmodel.queryEntityReviews(qid)

            if records:
                sortdict = [(dict_['dt'], dict_) for dict_ in records]
                sortdict.sort()
                results = [dict_ for (key, dict_) in sortdict]
            else:
                results = []

            jsondict = json.dumps((map (lambda x:  { 'year': x['dt'].strftime("%Y"),
                                                    'month': x['dt'].strftime("%m"),
                                                    'day': x['dt'].strftime("%d"),
                                                    'comment': x['comment'],
                                                    'userid': x['uid'],
                                                    'productid': x['pid'],
                                                    'rating': x['rating'],
                                                    'reviewid': x['rid'],
                                                    'prodname': x['name'],
                                                    'username':x['displayname'],
                                                    'location':x['location'],
                                                    'profilepic':x['profilepic'],
                                                    'prodthumb':x['thumbnail']
                                                    }, results)))
            bufstr=jsondict
        return    bufstr


class RecentReviewFeedBackEnd:
    def POST(self):
        web.header('Content-Type', 'application/json')
        returnval=[]
        data=web.input()
        try:
            limit=int(data.get('limit',8))
            offset=int(data.get('offset',0))
        except ValueError:
            return returnval

        results=reviewmodel.recentReviews(limit,offset);

        returnval = json.dumps((map (lambda x:  { 'year': x['dt'].strftime("%Y"),
                                                    'month': x['dt'].strftime("%m"),
                                                    'day': x['dt'].strftime("%d"),
                                                    'comment': x['comment'],
                                                    'userid': x['uid'],
                                                    'productid': x['pid'],
                                                    'rating': x['rating'],
                                                    'reviewid': x['rid'],
                                                    'prodname': x['name'],
                                                    'username':x['displayname'],
                                                    'location':x['location'],
                                                    'profilepic':x['profilepic'],
                                                    'prodthumb':x['thumbnail']
                                                    }, results)))
        return    returnval

class MyRecentReviewFeedBackEnd:
    def POST(self):
        data=web.input()
        returnval=[]
        web.header('Content-Type', 'application/json')
        if data.get('rollup',False):
            try:
                results = reviewmodel.queryMyRecentReviews(session.userid)
                returnval = json.dumps((map (lambda x: {'prodthumb':x[5],
                                                        'prodname':x[2],
                                                        'productid':x[0],
                                                        'count':x[9],
                                                        'rating':("%0.2f" % x[10])},results)))
            except:
                return False
        else:
            try:
                limit=int(data.get('limit',5))
                offset=int(data.get('offset',0))
                userid=int(data.get('userid',session.userid))
                results=reviewmodel.queryUserReviews(userid,limit,offset)
                returnval = json.dumps((map (lambda x:  { 'year': x['dt'].strftime("%Y"),
                                                    'month': x['dt'].strftime("%m"),
                                                    'day': x['dt'].strftime("%d"),
                                                    'comment': x['comment'],
                                                    'userid': x['uid'],
                                                    'productid': x['pid'],
                                                    'rating': x['rating'],
                                                    'reviewid': x['rid'],
                                                    'prodname': x['name'],
                                                    'prodthumb':x['thumbnail']
                                                    }, results)))
            except ValueError:
                return False
            #all variables were ints so we can process this.

        print returnval
        return    returnval
    def GET(self):
        pass
class AjaxProfile:
    def POST(self):
        if logged()==False: return False

        data = web.input()
        try:
            userid = int(data.get('uid',-1))
        except ValueError:
            return False

        values = data.get('values',{})
        data.location = data.location.lstrip(' ').rstrip(' ')
        worked=usermodel.updateProfileInfo(userid,data)

        if worked:
            info = usermodel.getProfileInfo(userid)
            session.fname = info.get('fname','')
            session.lname = info.get('lname','')
            session.displayname = info.get('displayname','')
            session.location = info.get('location','')
            session.profilepic = info.get('profilepic','')
            session.zip = info.get('zip','')
            return True

        return False

    def GET(self):
        data = web.input()
        try:
            userid = int(data.get('uid',session.userid))
        except ValueError:
            userid='none'
        if userid!='none':
            info = usermodel.getProfileInfo(userid)
            web.header('Content-Type', 'application/json')
            return json.dumps(  {'displayname':info.get('displayname','none'),
                                'userid':userid,
                                'location':info.get('location','none'),
                                'profilepic':info.get('profilepic','/static/profile_photo.jpg')});
        return False


class AddInteractionAjax:
        def POST(self):
            web.header('Content-Type', 'application/json')
            data = web.input()
            thedate = datetime.datetime.fromtimestamp(float(data.timestamp))
            tweet_id = data.get('tweet_id',False)
            therid = reviewmodel.storeReview(data.userid,data.rating, pid=data.id, date=thedate, comment=data.comment)
            if tweet_id:    reviewmodel.connectTweet(tweet_id, therid, session.userid)

            storedreview = json.dumps({ 'year': thedate.strftime("%Y"),
                                                    'month': thedate.strftime("%m"),
                                                    'day': thedate.strftime("%d"),
                                                    'comment': data.comment.replace('\n','<br>'),
                                                    'userid': data.userid,
                                                    'productid': data.id,
                                                    'rating': data.rating,
                                                    'reviewid': therid,
                                                    'tweet_id':tweet_id,
                                                    'profilepic':session.profilepic
                                                    })

            return storedreview

class AddComment:
        def POST(self):
            web.header('Content-Type', 'application/json')
            data = web.input()

            therid = reviewmodel.storeComment(data.userid, data.reviewid, data.comment)

            storedcomment = json.dumps({    'comment': data.comment,
                                            'userid': data.userid,
                                            'reviewid': data.reviewid
                                            })
            return storedcomment



class dummyRev:
    def GET(self):
        form=review_form()
        return autorender().revinput(form)

    def POST(self):
        form=review_form()
        data=web.input()
        reviewmodel.storeReview(session.userid,data.rating,pid=data.get('product-id',''), bid=data.get('brand-id',''))

        return autorender().revinput(form)



class FBRecvOK:
    def POST(self):
        data=web.input()
        if 'signed_request' in data:
            request_dict=parse_signed_request(data['signed_request'])
            if 'registration' in request_dict:
                    reg_info=request_dict['registration']
                    email=reg_info["email"]
                    password=reg_info["password"]
                    #Check to see if this email is already registered
                    #if so - skip to extra_info
                    if not is_user(email):    add_user(email, password)
                    loginbyid(usermodel.getUserId(email))

                    raise web.seeother('%s/home' % base_url)
        return "error"


class FBLogin:
    def GET(self):
        return autorender().fbreg()


class FBLoginTest:
    def GET(self):
        return autorender().fbtestl()


class Signup:
    def GET(self):
        if logged():    raise web.seeother('%s/home' % base_url)
        else:    return autorender().signup()

    def POST(self):
        data = web.input()
        email = data.email.lower()
        fname = data.fname
        if usermodel.isUser(email): return "Already Registered"
        passwd = hashlib.sha256(data.password).hexdigest()
        clinkhash = hashlib.md5(email).hexdigest()
        confirm_link = 'http://%s.actuallyheard.com/confirm?clinkid=%s' % (host, clinkhash)
        newuid = usermodel.addUser(email, passwd, fname, clinkhash)
        if newuid:
            #New User added.  Send confirmation email.
            confirmbody = '<html>Hi %s,<br>' % (fname)
            confirmbody+= 'Thanks for signing up at RateTheT from ActuallyHeard - the best place to rate and review the MBTA. <br>'
            confirmbody+= 'Please <a href="%s">click this link </a>to confirm your account and start reviewing today!<br>' % (confirm_link)
            confirmbody+= '<br>'
            confirmbody+= 'See you on ActuallyHeard!<br>'
            confirmbody+= 'The ActuallyHeard Team. </html>'
            web.sendmail('Actually Heard',email,'Actually Heard account confirmation for %s' % fname, confirmbody, headers=({'Content-Type':'text/html; charset=utf-8'}))
            return True
        else:   return False


class LoginAjax:
    def POST(self):
        buffer = 'Unable to process'
        (email, passwd) = web.input().login.lower(), hashlib.sha256(web.input().passwd).hexdigest()
        status = usermodel.userStatus(email)
        if status==2:
            if usermodel.authUser(email, passwd):
                loginbyid(usermodel.getUserId(email))
                buffer = 'Success'
            else: buffer = 'Invalid Password'
        elif status==1:
                buffer = 'Unconfirmed account - check email for confirmation link.'
        else:    buffer = 'Invalid Email'
        return buffer

class LogoutAjax:
    def POST(self):
        userlogout()
        return 1


class Login:
    def GET(self):
        if logged():    raise web.seeother('%s' % base_url)
        else:           return autorender().login('Please enter your email and password to log in.')
    def POST(self):
        (email, passwd) = web.input().login.lower(), hashlib.sha256(web.input().passwd).hexdigest()
        if usermodel.authUser(email, passwd):
            status = usermodel.userStatus(email)
            if status == 2:
                loginbyid(usermodel.getUserId(email))
                raise web.seeother('%s' % base_url)
            elif status == 1:
                return autorender().login('Account not confirmed.  Please check your email for the confirmation link')
        else:    return autorender().login('Invalid Email/Password')

class AjaxParentRollup():
    def POST(self):
        data = web.input()
        web.header('Content-Type', 'application/json')
        today = datetime.date.today() + datetime.timedelta(days=1)
        lastweek = datetime.date.today()-datetime.timedelta(days=7)
        sd = data.get('ed',lastweek)
        ed = data.get('sd',today)
        pid = data.get('pid',False)
        if pid:
            mbtaweeklyrevs = reviewmodel.queryParent(pid, sd, ed)
            returnval = json.dumps((map (lambda x:  { 'year': x['dt'].strftime("%Y"),
                                                    'month': x['dt'].strftime("%m"),
                                                    'day': x['dt'].strftime("%d"),
                                                    'comment': x['comment'],
                                                    'userid': x['uid'],
                                                    'productid': x['pid'],
                                                    'rating': x['rating'],
                                                    'reviewid': x['rid'],
                                                    'prodname': x['name'],
                                                    'username':x['displayname'],
                                                    'location':x['location'],
                                                    'profilepic':x['profilepic'],
                                                    'prodthumb':x['thumbnail']
                                                    }, mbtaweeklyrevs)))
            return returnval
        else:   return False

class Home:
    def GET(self):

        return autorender().home()


class Testing:
    def GET(self):
        #printses(session)
        #data=web.input()
        entityID = '5' #data.get('entity',False)
        if entityID:    results = reviewmodel.queryEntityInfo(entityID)
        else:        results=""
        return autorender().testing()
    def POST(self):
        if logged():
            #pull user reviews
            #pass to userhomepage
            data=web.input()
            entityID = data.get(entity,-1)
            results = reviewmodel.queryEntityInfo(entityID)
            #print results
            return autorender().testing(results)
        else:    return autorender().login()
class Timeline:

    def GET(self):
            data=web.input()
            entityID = data.get('id',-1)
            action = data.get('act','view')
            results = reviewmodel.queryEntityInfo(entityID)
            entitytree = reviewmodel.getEntityTree(entityID)
            childtree = []
            parenttree = []
            if entitytree!=0:
                for c in entitytree.get('children','').split(','):
                    info = reviewmodel.queryEntityInfo(c)
                    childtree.append(info)
            parents = reviewmodel.getEntityParent(entityID)

            if parents!='':

                for p in parents.split(','):
                    info = reviewmodel.queryEntityInfo(p)
                    parenttree.append(info)

                parenttree.reverse()
            revfeed = reviewmodel.recentReviews();
            if results: return autorender().entity(results,parenttree,childtree,revfeed,action)
            else:        raise web.notfound()

class MyTimeline:

    def GET(self):
            data=web.input()
            entityID = data.get('id',-1)
            action = data.get('act','view')
            results = reviewmodel.queryEntityInfo(entityID)
            entitytree = reviewmodel.getEntityTree(entityID)
            childtree = []
            parenttree = []
            if entitytree!=0:
                for c in entitytree.get('children','').split(','):
                    info = reviewmodel.queryEntityInfo(c)
                    childtree.append(info)
            parents = reviewmodel.getEntityParent(entityID)

            if parents!='':

                for p in parents.split(','):
                    info = reviewmodel.queryEntityInfo(p)
                    parenttree.append(info)

                parenttree.reverse()
            revfeed = reviewmodel.recentReviews();
            if logged():
                filter='mine'
            else:
                filter='public'
            if results:
                return autorender().entity(results,parenttree,childtree,revfeed,action,filter)
            else:
                raise web.notfound()



class EditProfile:
    def GET(self):
        if logged():    return autorender().settings()
        else:           raise web.seeother('%s' % base_url)


class EditPassword:
    def GET(self):
        if logged():    return autorender().password()
        else:            raise web.seeother('%s' % base_url)


class EditSocial:
    def GET(self):
        if logged(): return autorender().social()
        else:        raise web.seeother('%s/' % base_url)

    def POST(self):
        if not logged(): raise web.seeother('%s/' % base_url)
        data = web.input()
        network = data.get('network',False)
        print data, network
        if network=='facebook':
            if usermodel.delFbToken(session.userid):
                session.fboauth={}
                return True
        elif network=='twitter':
            if usermodel.delTwToken(session.userid):
                session.twitoauth={}
                return True
        return False

class Listing:
    def GET(self):
        if logged():    return autorender().listing()
        else:            return autorender().listing()


class Logout:
    def GET(self):
        if logged():    userlogout()
        return autorender().login()


class receiveRev():
        def GET(self):
            resource=str(web.input().obj)
            return "<html><body><img src=\"%s\"></body></img>" % resource


        def POST(self):
            resource=str(web.input().obj)
            return "<html><body><img src=\"%s\"></body></img>" % resource

class ProductPage:
        def GET(self):
            #product info is a dictionary with all the data for that product.
            productid = str(web.input().pid)
            record = reviewmodel.queryEntityInfo(productid)
            if len(record)==1:    prod=record[0]
            else:                    prod={ 'name' : 'Not Found.', 'brand' : 'Not Found' }
            return autorender().productInfo(prod)

class About:
    def GET(self):
        if logged():    return autorender().about()
        else:            return autorender().about()


class FAQ:
    def GET(self):
        if logged():    return autorender().faq()
        else:            return autorender().faq()

class Team:
    def GET(self):
        if logged():    return autorender().team()
        else:            return autorender().team()


if __name__ == "__main__":
    app.run()
