import jconfig

# This is a session secret key used by webapp2 framework.
NUCLEUS_SESSION_KEY = '58c2f5b5dcf64eb7894098db70fa9b3f161fd66fa4322b9391737b00521de6d'
ADVERTISER_SESSION_KEY = '58c2f5b5dcf64eb789409893a5c17e7530bd17fa22754f86910a13ba0db7940c'
PARTNERS_SESSION_KEY = 'f76e874a416012e5b177009db70fa9b3f161fd66fa4322b9391737b00521de6d'
PROMOTIONAL_SESSION_KEY = 'a937a20f549f4fa351ae3d0f20a14d6a896ac8867a85416294da333827d678a7'

# Google APIs
GOOGLE_APP_ID = '876126723064.apps.googleusercontent.com'
GOOGLE_APP_SECRET = 'X1dq8XbbezlbfOOHmsyA27le'
# needed for making requests to places search - chet
GOOGLE_APP_KEY = 'AIzaSyDsIM8o2P-zsYF3j5TcySsra3bF7bP8pfE'

# Factual API
FACTUAL_OAUTH_KEY = 'EcTecwIPOKwPMDzkBrNr5rTBH7LPy6I4ib2Hq8BH'
FACTUAL_OAUTH_SECRET = '4uEwgANjJ1n35iHdSsLOUUZy6DSTWsfylSqkMz7C'

if jconfig.on_dev_server():
    # Facebook for TESTING
    FACEBOOK_APP_ID = '384606674973394'
    FACEBOOK_APP_SECRET = 'bb4f1fed42f2c780490f4c1679daa285'
elif jconfig.on_test_app():
    FACEBOOK_APP_ID = '553819364676762'
    FACEBOOK_APP_SECRET = 'd42795d2860388d40177ae105045a041'
else:
    # Facebook auth apis
    FACEBOOK_APP_ID = '532194020175026'
    FACEBOOK_APP_SECRET = 'cebae90d138ffa58857a4a7bc6c2f124'

# Key/secret for both LinkedIn OAuth 1.0a and OAuth 2.0
# https://www.linkedin.com/secure/developer
LINKEDIN_KEY = 'consumer key'
LINKEDIN_SECRET = 'consumer secret'

# https://manage.dev.live.com/AddApplication.aspx
# https://manage.dev.live.com/Applications/Index
WL_CLIENT_ID = 'client id'
WL_CLIENT_SECRET = 'client secret'

# https://dev.twitter.com/apps
TWITTER_CONSUMER_KEY = 'kenaZqhpYJinBAkKXqNsKQ'
TWITTER_CONSUMER_SECRET = 'BipbUikA2Ogi84gX1DnB8wtHbtDEIvpUs5EzHGx88'

# https://foursquare.com/developers/apps
FOURSQUARE_CLIENT_ID = 'EN5NCI45HQHHXL0HTJREDZRBFDR4YVCL30MGHEZHFPPGXU4S'
FOURSQUARE_CLIENT_SECRET = '3W5F0BQLISYHTKIRE0IMBIEVRKRU2AZMVHU1TBZ22J50ETPL'

# config that summarizes the above
AUTH_CONFIG = {
    # OAuth 2.0 providers
    'google': (GOOGLE_APP_ID, GOOGLE_APP_SECRET,
               'https://www.googleapis.com/auth/userinfo.email ' +
               'https://www.googleapis.com/auth/userinfo.profile'),
    'facebook': (FACEBOOK_APP_ID, FACEBOOK_APP_SECRET,
                 'user_about_me,email,publish_actions'),
    # OAuth 1.0 providers don't have scopes
    'twitter': (TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET),

    # unused OAuth 2.0 providers
    'linkedin2': (LINKEDIN_KEY, LINKEDIN_SECRET,
                  'r_basicprofile'),
    'windows_live': (WL_CLIENT_ID, WL_CLIENT_SECRET,
                     'wl.signin'),
    'foursquare': (FOURSQUARE_CLIENT_ID, FOURSQUARE_CLIENT_SECRET,
                   'authorization_code'),

    # OAuth 1.0 providers don't have scopes
    'linkedin': (LINKEDIN_KEY, LINKEDIN_SECRET),

    # OpenID doesn't need any key/secret
}

# We can't pay for actual sandboxing (needs a level up on Salesforce) so if you
# need to figure out an API use these test keys instead.
if not jconfig.on_real_app():
    SALESFORCE_USERNAME = "jeff@nearwoo.com"
    SALESFORCE_PASSWORD = "nearwoo90401"
    SALESFORCE_SECURITY_TOKEN = "xj1yPQP0dA4AYQSLuOOHIJRfH"
    SALESFORCE_WSDL_FILENAME = 'partner.wsdl.xml'
else:
    # else:
    SALESFORCE_USERNAME = "michael@nearwoo.com"
    # pass + security token
    SALESFORCE_PASSWORD = "burdette177415"
    SALESFORCE_SECURITY_TOKEN = 'uJFgQLcwu8xQDLvqWxWpGGSvb'
    SALESFORCE_WSDL_FILENAME = 'partner.wsdl.xml'

'''----- yelp api login ------'''
yelp_consumer_key = 'lm0BKm9_pOlZDactUsJR2w'
yelp_consumer_secret = 'CTk8vPzoekwTZAZlU29sUpnysqg'
yelp_token = 'H-1_LXtDM5cS2nZ-8hJoT1kKw-1jpZOv'
yelp_token_secret = 'Ua9hlfOHSuaRAQ9RxWK2yT9TRXM'
