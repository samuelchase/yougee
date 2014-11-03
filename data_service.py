from google.appengine.ext import ndb
from google.appengine.ext.db import Key
import pprint

import datetime
import wootils
from decorators import polycamp
from wootils import make_status_message
from wootils import set_attributes
from wootils import ordinal
import models
import webapp2
import logging
import json
import stripe
from collections import defaultdict

from jfactory import new_banner_template

from jfactory import page_template

PAGEWOO = 'http://app.pagewoo.com'


class WoosLeft(webapp2.RequestHandler):
    def get(self, key):
        camp = models.NearWooCampaignDS.urlsafe_get(key)
        url = (PAGEWOO +
               '/chernobyl/woosleft?camp_key=' +
               camp.pagewoo_campaign_key)
        respo = wootils.fetch_no_cache(url)
        logging.debug(respo.content)
        self.response.write(respo.content)


class GetClickLocations(webapp2.RequestHandler):
    def get(self, key):
        camp = models.NearWooCampaignDS.urlsafe_get(key)
        url = (PAGEWOO +
               '/chernobyl/clicklocations?camp_key=' +
               camp.pagewoo_campaign_key + '&n=100')
        respo = wootils.fetch_no_cache(url)
        logging.debug(url)
        self.response.write(respo.content)


class GetConversionData(webapp2.RequestHandler):
    def get(self, key):
        logging.warning("INLKSHBLVSFHBSHBDV")
        camp = models.NearWooCampaignDS.urlsafe_get(key)
        respo = wootils.fetch_no_cache(PAGEWOO + '/chernobyl/getconversiondata?camp_key=' + camp.pagewoo_campaign_key)
        logging.debug(PAGEWOO + '/chernobyl/getconversiondata?camp_key=' + camp.pagewoo_campaign_key)
        try:
            content = json.loads(respo.content)
        except Exception:
            logging.exception('could not load response data')
            self.response.status_code = 500
            self.response.write('Server error communicating with pagewoo')
            return
        if 'anytime' in content:
            self.response.write(json.dumps(content))
            logging.info('Pagewoo responded with backwards compatible'
                         ' conversion request')
            return
        if 'data' not in content:
            logging.error('No "data" key in PW response. (Response was: %s)',
                          content)
            self.response.status_code = 500
            self.response.write('No data from pagewoo')
            return
        data = content['data']
        # group all the data together so we don't have to on front end
        out_data = defaultdict(int)
        for block in data:
            for conv_data in block['conversions']:
                out_data[conv_data['name']] += conv_data['value']
        final_data = {'anytime': [{'name': k, 'value': v} for k, v in
                      out_data.items()]}
        self.response.out.write(json.dumps(final_data))


class PagePreview(webapp2.RequestHandler):
    def get(self, key):
        yelp_obj = models.YelpJsonDS.urlsafe_get(key)
        yelp = yelp_obj.to_dict()
        content = yelp['yelp_data']
        camp_key = yelp['campaign_key']
        page_html = page_template.page_preview(camp_key, content)
        self.response.write(page_html)


class MobilePreview(webapp2.RequestHandler):
    def get(self, gae_key):
        val = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>NearWoo Mobile Preview</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <meta name="description" content="Movie times, tickets, reviews and more on your mobile phone. Fandango on the go - mobile.Fandango.com." />
    <meta name="keywords" content="movie times, movie tickets, mobile movie times, fandango mobile, theaters, mobile.fandango" />
    <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
    <meta name="viewport" content="width=device-width, user-scalable=no" />

    <!-- HTML5 shim, for IE6-8 support of HTML5 elements -->
    <!--[if lt IE 9]>
      <script src="http://html5shim.googlecode.com/svn/trunk/html5.js"></script>
    <![endif]-->

    <link rel="stylesheet"  href="http://mobile.fandango.com/res/fandango/fandango/480/_sp.css" type="text/css"/>
    <link rel="stylesheet"  href="http://mobile.fandango.com/res/fandango/fandango/320/style_site.css" type="text/css"/>
    <link rel="stylesheet"  href="http://mobile.fandango.com/res/fandango/fandango/320/style_AndroidGiftCard.css" type="text/css"/>
    <link rel="stylesheet"  href="http://mobile.fandango.com/res/css/image-gallery.css" type="text/css"/>
    <link rel="stylesheet"  href="http://mobile.fandango.com/res/css/carousel.css" type="text/css"/>
    <link rel="stylesheet"  href="http://mobile.fandango.com/res/onlineopinionV5/oo_style.css" type="text/css"/>
    <!-- HTML5 shim, for IE6-8 support of HTML5 elements -->
    <!--[if lt IE 9]>
      <script src="http://html5shim.googlecode.com/svn/trunk/html5.js"></script>
    <![endif]-->

    <script type="text/javascript" src="http://mobile.fandango.com/res/js/jquery.min.js" ></script>
    <script type="text/javascript" src="http://mobile.fandango.com/res/js/jquery.touchwipe.js" ></script>
<script type="text/javascript"  >var myScroll;
var navUserAgent = navigator.userAgent.toLowerCase();
var isAndroid = (navUserAgent.indexOf("android") != -1);
var isIpad = (navUserAgent.toLowerCase().indexOf("ipad") != -1);



/**temp ajax*/
var host = window.location.hostname;
if (host === '127.0.0.1') {
  host = 'http://' + host + ':8082';
} else {
  host = 'http://' + host;
}

var yelp;
var yelp_data;


function get_yelp(){
    var url = host + '/api/v1/yelp/"""+ gae_key + """/'
    $.getJSON(url, function(data){
        console.log('get call_data');
        console.log(data);
        yelp = data.data;
        yelp_data = data.data.yelp_data;
    })
    console.log('url get yelp_data' + url)
}


function on_banner_load(){
  var src = host + '/api/v1/bannerpreview/""" + gae_key + """'
  $('#banner_frame').attr('src', src);
  console.log(src);
}

function load_preview_page(){
    console.log(yelp_data.show_menu)
    var url;
    if(yelp_data.show_menu === 'ActionBanner'){
        if(yelp_data.banner_actions.call.is_checked){
            var url = yelp_data.banner_actions.call.value
            window.open(url, '_blank');
        }else if(yelp_data.banner_actions.map.is_checked){
            var url = 'http://maps.google.com/maps?daddr=' + yelp_data.banner_actions.map.value
            window.open(url,'_blank')
        }else if(yelp_data.banner_actions.web.is_checked){
            var url = yelp_data.banner_actions.web.value
            window.open(url, '_blank')
        }else{

        }
    }else if (yelp_data.show_menu === 'No Action'){
        url = ''
    }else if (yelp_data.show_menu === 'Website Redirect'){
        url = yelp_data.website_redirect.value
    }else if (yelp_data.show_menu === 'Landing Page'){
        url = host + '/api/v1/pagepreview/""" + gae_key + """'
    }
    console.log('banner url ' + url)
    window.location.href = url
}

  addEventListener("load", function() { setTimeout(hideURLbar, 0); }, false);
  function hideURLbar(){ window.scrollTo(0,1); }
  var fbId = '5885186655';
  addEventListener("load", function() { setTimeout(hideURLbar, 800); }, false);
  function hideURLbar() {
    window.scrollTo(0,1);
  }

$("document").ready( function(){
    on_banner_load();
    get_yelp();
  });


</script>


<link rel="apple-touch-icon" href="http://mobile.fandango.com/res/fandango/fandango/480/bookmarkicon-trans.png"/>
<link rel="apple-touch-icon-precomposed" href="http://mobile.fandango.com/res/fandango/fandango/480/"/>
<link rel="icon" type="image/png" href="http://mobile.fandango.com/res/fandango/fandango/480/bookmarkicon-trans.png"/>
<meta name="apple-mobile-web-app-capable" content="yes" />
</head>
<body onload='if(self.load)load();'  style="margin:0px;background-color:#ffffff;" >


<div id="home" style="clear:both;margin:0px;
padding:0px;
" >
<form  style="margin:0.0px;"  id='home_form'  method="post"  action="http://mobile.fandango.com/?&amp;from=home" onsubmit = "if(self.setOnSubmit) return setOnSubmit(this);" enctype="application/x-www-form-urlencoded" >

<div >
<div style="clear:both;margin:0px;
padding:0px;
" ><div class="ad_div"><div id="ADSCRIPTTOP" align="center">

    <div style="width:320px; height:50px; overflow:hidden;">
        <iframe id="banner_frame" style="padding:0px;" width="320px" height="50px"  src="" scrolling="no"></iframe>
    </div>
     <div style="width:100%; height:50px; background:transparent; position:absolute; top:7px; z-index:100px; " onclick="load_preview_page()"></div>
</div></div>
</div><script type="text/javascript"></script><noscript><div class="noscript-message"><p style="padding-left: 10px;" class="clrall normal_error2">Please enable javascript for optimal performance of this site</p></div></noscript><H1 class="hidden">Movie Times, Tickets + More</H1>
<div id="r5" class="clrall" style="background-color:#ffffff;" >
<div id="r5_c1" style="width:100.0%;float:left;" ><img  src="http://mobile.fandango.com/res/fandango/fandango/480/header_fandango.png"  alt="img"  class="width_header"  style="margin:10px 10px 0px;
padding:0px;" />
</div>
</div>
<div id="r7" class="pad10l pad10r pad10b clrall" >
<div id="r7_c1" style="width:100.0%;float:left;" ><span  class="clrall normal_error2 error" ></span>
</div>
</div>
<ul style="margin:0px;padding:0px;" >
<li style="list-style-type:none;padding:0px;font-size:small;">
<div style="clear:both;margin:0px;
padding:0px;
" >
<div id="home_menu_movie_embed_r1" class="pad10 list_grad2 clrall" >
<div id="home_menu_movie_embed_r1_c1" style="width:76.0%;float:left;" ><img  src="http://mobile.fandango.com/res/fandango/fandango/480/menu_tab_movies.png"  alt="img"  class="valignm display"  style="height:32.0px;margin:0px;
padding:0px 10px 0px 0px;" /><span  class="display valignm"  style="color:#333333;background-color:transparent;font-size:16.0px;font-weight:bold;margin:0px;
padding:0px;" >MOVIES</span>
</div>
<div id="home_menu_movie_embed_r1_c2" style="width:24.0%;float:left;text-align:right;" ><img  src="http://mobile.fandango.com/res/fandango/fandango/480/chevron.png"  alt="img"  class="valignm display"  style="height:17.0px;margin:0px;
padding:9px 0px 0px;" />
</div>
</div>
</div></li>
</ul>
<ul style="margin:0px;padding:0px;" >
<li style="list-style-type:none;padding:0px;font-size:small;">
<div style="clear:both;margin:0px;
padding:0px;
" >
<div id="home_menu_theaters_embed_r1" class="pad10 list_grad2 clrall" >
<div id="home_menu_theaters_embed_r1_c1" style="width:76.0%;float:left;" ><img  src="http://mobile.fandango.com/res/fandango/fandango/480/menu_tab_theaters.png"  alt="img"  class="valignm display"  style="height:32.0px;margin:0px;
padding:0px 10px 0px 0px;" /><span  class="display valignm"  style="color:#333333;background-color:transparent;font-size:16.0px;font-weight:bold;margin:0px;
padding:0px;" >THEATERS</span>
</div>
<div id="home_menu_theaters_embed_r1_c2" style="width:24.0%;float:left;text-align:right;" ><img  src="http://mobile.fandango.com/res/fandango/fandango/480/chevron.png"  alt="img"  class="valignm display"  style="height:17.0px;margin:0px;
padding:9px 0px 0px;" />
</div>
</div>
</div></li>
</ul>
<ul style="margin:0px;padding:0px;" >
<li style="list-style-type:none;padding:0px;font-size:small;">
<div style="clear:both;margin:0px;
padding:0px;
" >
<div id="home_menu_videos_r1" class="pad10 list_grad2 clrall" >
<div id="home_menu_videos_r1_c1" style="width:76.0%;float:left;" ><img  src="http://mobile.fandango.com/res/fandango/fandango/480/menu_tab_videos.png"  alt="img"  class="valignm display"  style="height:32.0px;margin:0px;
padding:0px 10px 0px 0px;" /><span  class="display valignm"  style="color:#333333;background-color:transparent;font-size:16.0px;font-weight:bold;margin:0px;
padding:0px;" >VIDEOS</span>
</div>
<div id="home_menu_videos_r1_c2" style="width:24.0%;float:left;text-align:right;" ><img  src="http://mobile.fandango.com/res/fandango/fandango/480/chevron.png"  alt="img"  class="valignm display"  style="height:17.0px;margin:0px;
padding:9px 0px 0px;" />
</div>
</div>
</div></li>
</ul>
<ul style="margin:0px;padding:0px;" >
<li style="list-style-type:none;padding:0px;font-size:small;">
<div style="clear:both;margin:0px;
padding:0px;
" >
<div id="home_menu_blog_r1" class="pad10 list_grad2 clrall" >
<div id="home_menu_blog_r1_c1" style="width:76.0%;float:left;" ><img  src="http://mobile.fandango.com/res/fandango/fandango/480/menu_tab_blog.png"  alt="img"  class="valignm display"  style="height:32.0px;margin:0px;
padding:0px 10px 0px 0px;" /><span  class="display valignm"  style="color:#333333;background-color:transparent;font-size:16.0px;font-weight:bold;margin:0px;
padding:0px;" >MOVIE BLOG</span>
</div>
<div id="home_menu_blog_r1_c2" style="width:24.0%;float:left;text-align:right;" ><img  src="http://mobile.fandango.com/res/fandango/fandango/480/chevron.png"  alt="img"  class="valignm display"  style="height:17.0px;margin:0px;
padding:9px 0px 0px;" />
</div>
</div>
</div></li>
</ul>
<ul style="margin:0px;padding:0px;" >
<li style="list-style-type:none;padding:0px;font-size:small;">
<div style="clear:both;margin:0px;
padding:0px;
" >
<div id="home_menu_account_embed_r1" class="pad10 list_grad2 clrall" >
<div id="home_menu_account_embed_r1_c1" style="width:76.0%;float:left;" ><img  src="http://mobile.fandango.com/res/fandango/fandango/480/menu_tab_my_account.png"  alt="img"  class="valignm display"  style="height:32.0px;margin:0px;
padding:0px 10px 0px 0px;" /><span  class="display valignm"  style="color:#333333;background-color:transparent;font-size:16.0px;font-weight:bold;margin:0px;
padding:0px;" >MY ACCOUNT</span>
</div>
<div id="home_menu_account_embed_r1_c2" style="width:24.0%;float:left;text-align:right;" ><img  src="http://mobile.fandango.com/res/fandango/fandango/480/chevron.png"  alt="img"  class="valignm display"  style="height:17.0px;margin:0px;
padding:9px 0px 0px;" />
</div>
</div>
</div></li>
</ul>
</div>
<div id="r13" class="clrall" style="background-color:#ffffff;" >
<div id="r13_c1" style="width:100.0%;float:left;" ><hr style="text-align:left;margin-left:0px;background-color:#eeeeee;border:0px solid #eeeeee;height:1.0px;"  align="left" />
</div>
</div>
<div >
<div style="clear:both;margin:0px;
padding:0px;
" >
<ul style="margin:0px;padding:0px;" >
<li style="list-style-type:none;padding:0px;font-size:small;">
<div style="clear:both;margin:0px;
padding:0px;
" >
<div id="embed_giftcard_r1" class="clrall" style="background-color:#ffffff;" >
<div id="embed_giftcard_r1_c1" style="width:100.0%;float:left;" ><hr class="GCshadow" />
</div>
</div>
<div id="embed_giftcard_r2" class="pad1t pad12b mar8lr VAm clrall" >
<div id="embed_giftcard_r2_c1" style="width:1.0%;float:left;text-align:center;" ><img  src="http://mobile.fandango.com/res/fandango/fandango/480/fan_giftcard.png"  alt="img"  class="GCimg" />
</div>
<div id="embed_giftcard_r2_c2" style="width:99.0%;float:left;" ><span  class="pad10t GCmar Db GCtitle3 VAm" >Fandango Gift Cards</span><span  class="Db  GCmar GCdesc VAm" >The perfect gift for any occasion.</span>
</div>
</div>
<div id="embed_giftcard_r3" class="mar8lr clrall" >
<div id="embed_giftcard_r3_c1" style="width:100.0%;float:left;" ><hr style="text-align:left;margin-left:0px;background-color:#d8d8d8;border:0px solid #d8d8d8;height:1.0px;"  align="left" />
</div>
</div>
</div></li>
</ul>
<div id="footer_r2" class="padtop10 padbottom10 mar3b mar8lr clrall" >
<div id="footer_r2_c1" style="width:100.0%;float:left;background-color:#ffffff;" ><span ><a  href=""  class="clrall footer_link2 display"  style="text-decoration:none;" >Get Movie Alerts</a></span><span  style="color:#bbbbbb;background-color:transparent;font-size:13.0px;display:inline-block;margin:0px;
padding:0px 5px;" > | </span><span ><a  href=""  class="clrall footer_link2 display"  style="text-decoration:none;" >Feedback</a></span><span  style="color:#bbbbbb;background-color:transparent;font-size:13.0px;display:inline-block;margin:0px;
padding:0px 5px;" > | </span><span ><a  href=""  class="clrall footer_link2 display"  style="text-decoration:none;" >Full Site</a></span><span  style="color:#bbbbbb;background-color:transparent;font-size:13.0px;display:inline-block;margin:0px;
padding:0px 5px;" > | </span><span ><a  href=""  class="clrall footer_links display"  style="text-decoration:none;" >Your Privacy Rights - Privacy Policy</a></span>
</div>
<div id="footer_r3_c1" style="width:100.0%;float:left;background-color:#ffffff;clear:both;" ><span ><a  href=""  class="clrall footer_links display"  style="text-decoration:none;" >Terms</a></span><span  style="color:#bbbbbb;background-color:transparent;font-size:13.0px;display:inline-block;margin:0px;
padding:0px 5px;" > | </span><span ><a  href=""  class="clrall footer_links display"  style="text-decoration:none;" >Help</a></span>
</div>
</div>
<div id="footer_r4" class="pad10 clrall" >
<div id="footer_r4_c1" style="width:100.0%;float:left;" ><span  class="clrall small_light" >Mobile Web by </span><span ><a  href=""  class="clrall small_light"  style="text-decoration:none;" >Trilibis</a></span>
</div>
</div>
</div>
</div>
<div >
<div style="clear:both;margin:0px;
padding:0px;
" ><div></div>
</div>
</div>
<div id="r16" class="clrall" style="background-color:#ffffff;" >
<div id="r16_c1" style="width:100.0%;float:left;" ><input  type="submit"  name="submit-initloc1-LOCATION"  id='LOCATION'  value="hidden"  style="font-size:small;color:#000000;text-align:left;background-color:transparent;font-size:small;margin:0px;
padding:0px;"  class="button_orange MyriadProRegular  hidden" />
</div>
</div>
<div id="r17" class="clrall" style="background-color:#ffffff;" >
<div id="r17_c1" style="width:100.0%;float:left;" ><input  type="submit"  name="submit-initloc2-BUTTON0"  id='BUTTON0'  value="hidden" style="font-size:small;color:#000000;text-align:left;background-color:transparent;font-size:small;margin:0px;
padding:0px;"  class="button_orange MyriadProRegular  hidden" />
</div>
</div>
<div id="r18" class="_sphiddenParam clrall" >
<div id="r18_c1" style="width:100.0%;float:left;" ><input  type="hidden"  name="_spAllCompKey"  value="QUERY"  style="color:#000000;background-color:#000000;height:0.0px;width:0.0px;font-size:small;margin:0px;
padding:0px;" />
</div>
</div></form>
</div>

</html>

  </body>
</html>
 """


        self.response.write(val)


class BannerPreview(webapp2.RequestHandler):
    def get(self, key):
        try:
            yelp_obj = models.YelpJsonDS.urlsafe_get(key)
            yelp = yelp_obj.to_dict()
            content = yelp['yelp_data']
            logging.info(content)
            banner_html = new_banner_template.banner_preview(content)
            self.response.write(banner_html)
        except Exception as e:
            logging.exception(e)
            content = {
                "campaign_category": {"cat_color":'arts'},
                "banner": {
                    "banner_type": "flipdown_v2",
                    "top_line": "Please select a banner type"}}
            banner_html = new_banner_template.banner_preview(content)
            self.response.write(banner_html)


class TestBannerPreview(webapp2.RequestHandler):
    def get(self, key):
        try:
            yelp_obj = models.YelpJsonDS.urlsafe_get(key)
            yelp = yelp_obj.to_dict()
            content = yelp['yelp_data']
            logging.info(content)
            banner_html = new_banner_template.test_banner_preview(content)
            self.response.write(banner_html)
        except Exception as e:
            logging.exception(e)
            content = {
                "campaign_category": {"cat_color":'arts'},
                "banner": {
                    "banner_type": "flipdown_v2",
                    "top_line": "Please select a banner type"}}
            banner_html = new_banner_template.test_banner_preview(content)
            self.response.write(banner_html)




class YelpService(webapp2.RequestHandler):
    ''' Returns all models.YelpJsonDS entities associated with the
    key provided '''

    def get(self, key, blank):
        k = Key(encoded=key)
        if k.kind() == 'YelpJsonDS':
            yelp_obj = models.YelpJsonDS.urlsafe_get(key)
            yelp = yelp_obj.to_dict()
        elif k.kind() == 'NearWooCampaignDS':
            logging.info('is campaign key?????')
            camp = models.NearWooCampaignDS.urlsafe_get(key)
            yelp_obj = models.YelpJsonDS.urlsafe_get(camp.yelp_key)
            yelp = yelp_obj.to_dict()
        elif k.kind() == 'Advertiser':
            logging.info('is models.Advertiser?????')
            yelp = models.YelpJsonDS.gql(
                'where advertiser_key = :1', key).fetch(1000)
        else:
            yelp = None
        if not yelp:
            m = "Yelp Entity cannot be retrieved with given key"
            msg = make_status_message(success=False, message=m,
                                      code=500, data=None)
            self.response.write(msg)
        else:
            result = None
            if type(yelp) == list:
                result = []
                for c in yelp:
                    result.append(c.to_dict())
            else:
                result = yelp

            msg = make_status_message(
                success=True, message='successfully retrieved',
                code=200, data=result)
            self.response.write(msg)

    def post(self, key, save_type):
        data = json.loads(self.request.body)
        if save_type == 'save' or save_type == 'insert':
            yelp = models.YelpJsonDS.urlsafe_get(key)
            if yelp:
                for k, v in data.items():
                    if isinstance(v, (list, dict)):
                        data[k] = json.dumps(v)
                set_attributes(data, yelp)
                msg = make_status_message(
                    success=True, message='successfully created',
                    code=200, data=[])
                self.response.write(msg)
            else:
                msg = make_status_message(
                    success=False, message='Could not find entity',
                    code=400, data=[])
                self.response.write(msg)

        if save_type == 'create' or save_type == 'insert':
            yelp = models.YelpJsonDS()
            set_attributes(data, yelp)
            msg = make_status_message(
                success=True, message='successfully created',
                code=200, data=[])
            self.response.write(msg)


class CampService(webapp2.RequestHandler):
    ''' Returns all models.NearWooCampaignDS entities
    associated with the key provided '''

    def get(self, key):
        k = Key(encoded=key)
        if k.kind() == 'NearWooCampaignDS':
            logging.info('is this camp?????')
            camp_obj = models.NearWooCampaignDS.urlsafe_get(key)
            camp = camp_obj.to_dict()
            # logging.info(camp.to_dict())
        elif k.kind() == 'YelpJsonDS':
            yelp = models.YelpJsonDS.urlsafe_get(key)
            camp = models.NearWooCampaignDS.urlsafe_get(yelp.campaign_key)
        elif k.kind() == 'Advertiser':
            camp = models.NearWooCampaignDS.gql(
                'where advertiser_key = :1', key).fetch(1000)
        else:
            camp = None
        if not camp:
            m = "Camp Entity cannot be retrieved with given key"
            msg = make_status_message(success=False, message=m,
                                      code=500, data=None)
            self.response.write(msg)
        else:
            result = None
            if type(camp) == list:
                result = []
                for c in camp:
                    result.append(c.to_dict())
            else:
                result = camp

            msg = make_status_message(
                success=True, message='successfully retrieved',
                code=200, data=result)
            self.response.write(msg)

    def post(self, save_type, key):
        data = json.loads(self.request.body)
        if save_type == 'save' or save_type == 'insert':
            camp = models.NearWooCampaignDS.urlsafe_get(key)

            if camp:
                logging.info(camp)
                set_attributes(data, camp)
                msg = make_status_message(
                    success=True, message='successfully ' + save_type,
                    code=200, data=[])
                self.response.write(msg)
                return
            else:
                msg = make_status_message(
                    success=False, message='Could not find entity',
                    code=400, data=[])
                self.response.write(msg)
                return

        elif save_type == 'create':
            camp = models.NearWooCampaignDS()
            set_attributes(data, camp)
            msg = make_status_message(
                success=True, message='successfully created',
                code=200, data=[])
            self.response.write(msg)
            return



class NucleusAdvService(webapp2.RequestHandler):
    ''' Returns the models.NucleusAdvertiser entity associated '''
    def get(self, key):
        nadv = models.NucleusAdvertiser.urlsafe_get(key)
        if nadv:
            data = nadv.to_dict()
            success = True
            code = 200
            message = 'successfully retrieved'
        else:
            data = {}
            success = False
            message = (
                "models.NucleusAdvertiser Entity cannot be retrieved with given key")
            code = 500

        status = make_status_message(success=success, message=message, code=code, data=data)
        self.response.write(status)

    def post(self, save_type, key):
        data = json.loads(self.request.body)
        if save_type == 'save' or save_type == 'insert':
            nadv = models.NucleusAdvertiser.urlsafe_get(key)
            if adv:
                set_attributes(data, adv)
                msg = make_status_message(
                    success=True, message='successfully created',
                    code=200, data=[])
                self.response.write(msg)
                return
            elif save_type == 'save':
                msg = make_status_message(
                    success=False, message='Could not find entity',
                    code=400, data=[])
                self.response.write(msg)
                return

        if save_type == 'create' or save_type == 'insert':
            adv = models.Advertiser()
            set_attributes(data, adv)
            msg = make_status_message(
                success=True, message='successfully created',
                code=200, data=[])
            self.response.write(msg)
            return



class AdvService(webapp2.RequestHandler):
    ''' Returns the models.Advertiser entity associated with the key provided '''
    def get(self, save_type, key):
        k = ndb.Key(urlsafe=key)
        logging.info('getting kind  %s', k.kind())
        adv_key = None
        if k.kind() == 'Advertiser':
            adv_key = key
        elif k.kind() == 'YelpJsonDS':
            yelpie = k.get()
            adv_key = yelpie.advertiser_key
        elif k.kind() == 'NearWooCampaignDS':
            camp = k.get()
            adv_key = camp.advertiser_key

        if key:
            adv = models.Advertiser.urlsafe_get(adv_key)
            data = adv.to_dict()
            success = True
            code = 200
            message = 'successfully retrieved'
        else:
            data = {}
            success = False
            message = (
                "models.Advertiser Entity cannot be retrieved with given key")
            code = 500

        status = make_status_message(
            success=success, message=message, code=code, data=data)
        self.response.write(status)

    def post(self, save_type, key):
        data = json.loads(self.request.body)
        if save_type == 'save' or save_type == 'insert':
            adv_key = ndb.Key(urlsafe=key)
            adv = adv_key.get()
            if adv:
                set_attributes(data, adv)
                msg = make_status_message(
                    success=True, message='successfully created',
                    code=200, data=[])
                self.response.write(msg)
                return
            elif save_type == 'save':
                msg = make_status_message(
                    success=False, message='Could not find entity',
                    code=400, data=[])
                self.response.write(msg)
                return

        if save_type == 'create' or save_type == 'insert':
            adv = models.Advertiser()
            set_attributes(data, adv)
            msg = make_status_message(
                success=True, message='successfully created',
                code=200, data=[])
            self.response.write(msg)
            return


class StripeService(webapp2.RequestHandler):
    # TODO: same as billing service??
    def get(self, adv_key):
        adv = models.Advertiser.urlsafe_get(adv_key)
        stripe_customer = stripe.Customer.retrieve(adv.stripe_id)
        stripe_customer = json.loads(str(stripe_customer))
        msg = make_status_message(
            success=True,
            message='billing successfully restrieved',
            code=200,
            data=stripe_customer)
        self.response.write(msg)


class BillingService(webapp2.RequestHandler):
    def get(self, adv_key):
        adv = models.Advertiser.urlsafe_get(adv_key)
        logging.debug('retrieving customer with stripe id %s', adv.stripe_id)
        charges = []
        if not adv.stripe_id:
            msg = make_status_message(
                success=False,
                message='Advertiser\'s stripe ID is None',
                code=404)
        else:
            try:
                stripe_customer = stripe.Customer.retrieve(adv.stripe_id)
                stripe_customer = json.loads(str(stripe_customer))
                invoices = models.Invoices.gql(
                    'where advertiser_key = :1', adv_key).fetch(1000)
                for invoice in invoices:
                    camp = models.NearWooCampaignDS.urlsafe_get(
                        invoice.campaign_key)
                    charge = json.loads(str(invoice.charge))
                    logging.info('charging')
                    logging.info(charge)
                    invoice_type = invoice.invoice_type
                    if invoice_type is None:
                        invoice_type = 'N/A'
                    charge['invoice_type'] = invoice_type
                    charge['date'] = invoice.date_created.strftime('%m/%d/%y')
                    charge['camp_name'] = camp.name
                    charge['stripe_customer'] = stripe_customer
                    charge['stripe_id'] = adv.stripe_id
                    charge['partner_key'] = adv.partner_key
                    charge['rep_key'] = adv.rep_key
                    charge['bill_day'] = camp.charge_day
                    charge['bill_day_spoken'] = (
                        ordinal(camp.charge_day) if camp.charge_day else None),
                    charge['monthly_amt'] = camp.amount_subscribed,
                    charge['neighborhood_ct'] = invoice.neighborhood_ct
                    charges.append(charge)

                msg = make_status_message(
                    success=True,
                    message='billing successfully restrieved',
                    code=200,
                    data=charges)
            except Exception:
                msg = make_status_message(
                    success=False,
                    message='error retrieving billing data',
                    data=charges,
                    code=500)
                logging.exception("Failed to load stripe info for %s" %
                                  adv_key)
        self.response.write(msg)


class MetricsService(webapp2.RequestHandler):
    """
    >>> import pprint
    >>> import wootils
    >>> import json
    >>>
    >>>
    >>> camp_key = 'aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGMiBPgw'
    >>> payload = {
    >>>     'start_date': '2013-12-1',
    >>>     'end_date': '2013-12-5',
    >>>     'batch_size': 20}
    >>> url = 'http://nearwoo.appspot.com/api/v1/camp/metrics/%s' % camp_key
    >>> resp = wootils.fetch_no_cache(url, payload=json.dumps(payload), deadline=60)
    >>> resp = json.loads(resp.content)
    >>> pprint.pprint(resp)
    >>>
    """
    DEFAULT_BATCH_SIZE = 20

    def get(self, camp_key):
        logging.debug('metrics service for camp_key %s', camp_key)
        start_date = self.request.get('start_date', None)
        end_date = self.request.get('end_date', None)
        if end_date:
            logging.warning("End date not supported in metrics service. Got: %s"
                    % end_date)
        if start_date:
            start_date = datetime.datetime.strptime(start_date, wootils.ISO_DATE_FORMAT)
        else:
            start_date = datetime.datetime(2014, 2, 1, 0, 0, 0)
        # if end_date:
        #     end_date = datetime.datetime.strptime(end_date, wootils.ISO_DATE_FORMAT)
        # else:
        #     end_date = datetime.datetime.today()

        # for now we always want to get 8 7-day chunks as weeks
        end_date = start_date + datetime.timedelta(days=56)
        batch_size = int(self.request.get('batch_size', '') or 20)
        old_cursor = ndb.Cursor(urlsafe=self.request.get('cursor', None))
        data, errored = get_metrics(camp_key, start_date, end_date, batch_size,
                                    old_cursor=old_cursor)
        if not data:
            status = make_status_message(success=False,
                                         message='Campaign not found.')
        elif errored:
            status = make_status_message(success=False,
                                         message="Server error.")
        else:
            status = make_status_message(success=True, data=data,
                                         message='Found metrics')
        self.response.write(status)


class OSMetricsService(webapp2.RequestHandler):
    def get(self, camp_key):
        camp = models.NearWooCampaignDS.urlsafe_get(camp_key)
        if not camp:
            logging.error("Could not find camp for %s" % camp_key)
            status = make_status_message(success=False,
                    message='Campaign not found')
            self.response.write(status)
            return
        start_date = self.request.get('start_date', None)
        end_date = self.request.get('end_date', None)
        if start_date:
            start_date = datetime.datetime.strptime(
                start_date, wootils.ISO_DATE_FORMAT)
        else:
            start_date = datetime.datetime(2014, 2, 1, 0, 0, 0)
        end_date = start_date + datetime.timedelta(days=56)
        pw_key = camp.pagewoo_campaign_key
        call_data = {
                'start_date': date_to_pw_json(start_date),
                'end_date': date_to_pw_json(end_date),
                'camp_key': pw_key,
                'data_type': 'get_monthly_views_by_os',}
        data = wootils.get_pagewoo_analytics(call_data)
        if data:
            status = make_status_message(success=True, data=data)
        else:
            status = make_status_message(success=False, message='error')
            logging.error("Failed to communicate with pagewoo for %s" %
                    camp.key.urlsafe())
        self.response.write(status)


class ConvMetricsService(webapp2.RequestHandler):
    def get(self, camp_key):
        camp = models.NearWooCampaignDS.urlsafe_get(camp_key)
        if not camp:
            logging.error("Could not find camp for %s" % camp_key)
            status = make_status_message(success=False,
                    message='Campaign not found')
            self.response.write(status)
            self.response.status_code = 404
            return
        start_date = self.request.get('start_date', None)
        end_date = self.request.get('end_date', None)
        if start_date:
            start_date = datetime.datetime.strptime(
                start_date, wootils.ISO_DATE_FORMAT)
        else:
            start_date = datetime.datetime(2014, 2, 1, 0, 0, 0)
        end_date = start_date + datetime.timedelta(days=56)
        pw_key = camp.pagewoo_campaign_key
        call_data = {
                'start_date': date_to_pw_json(start_date),
                'end_date': date_to_pw_json(end_date),
                'camp_key': pw_key,
                'data_type': 'get_weekly_conversions_by_type',}
        data = wootils.get_pagewoo_analytics(call_data)
        if not data:
            status = make_status_message(success=False, message='error')
            logging.error("Failed to communicate with pagewoo for %s" %
                    camp.key.urlsafe())
            self.response.write(status)
            self.response.status_code = 500
            return

        # group all the data together so we don't have to 
        out_data = defaultdict(int)
        for block in data:
            for conv_data in block['conversions']:
                out_data[conv_data['name']] += conv_data['value']
        final_data = {'anytime': [{'name': k, 'value': v} for k, v in
                      out_data.items()]}
        self.response.write(json.dumps(final_data))


@polycamp
def get_metrics(camp, start_date, end_date, batch_size, old_cursor=None):
    """
    Args: camp, start_date, end_date, batch_size, old_cursor=None
    >>> import models
    >>> import datetime
    >>> import data_service
    >>> import pprint
    >>>
    >>> start_date = datetime.date(2013, 12, 1)
    >>> end_date = datetime.date(2013, 12, 5)
    >>>
    >>> camp = models.NearWooCampaignDS.query().get()
    >>> data_service.get_metrics(camp, start_date, end_date, 20)

    Return format:
    [{'date': %Y-%m-%D,
      'camp_key': URLSAFE_KEY,
      'banner_views': {BLOCKGROUP => VIEWS [int]}
      }]
    """
    camp_key = camp.key.urlsafe()
    pw_key = camp.pagewoo_campaign_key
    logging.debug('fetching camp metrics for %s', camp_key)
    if not camp:
        return False, True
    # edit_query = models.CampaignEdit.within_date_range(
    #  start_date, end_date,camp_key=camp_key)
    # edits, cursor, _ = edit_query.fetch_page(batch_size,
    #                                          start_cursor=old_cursor)
    # last_date = None
    # if the older edit doesn't have a next_edit_date, reverse the cursor
    # and use that as last_date
    # if edits and old_cursor and not edits[0].get_effective_end_date(camp=camp):
    #     last_edit = old_cursor.reversed().get()
    #     last_date = date_to_pw_json(last_edit.created)
    # for edit in edits:
    #     this_data = {}
    #     # we're iterating in descending order by date, so we always know
    #     # that the last date is at least the ending date to the previous
    #     end_date = edit.get_effective_end_date(camp=camp)
    #     if end_date:
    #         this_data['end_date'] = date_to_pw_json(end_date)
    #     else:
    #         this_data['end_date'] = last_date
    #     this_data['start_date'] = date_to_pw_json(edit.created)
    #     this_data['camp_key'] = pw_key
    #     geoids = json.loads(edit.geoids)
    #     this_data['geoids'] = list(g['geoid'] for g in geoids)
    #     this_data['home_geoid'] = edit.home_geoid
    #     this_data['data_type'] = 'get_metrics'
    #     # TODO: perhaps aggregate?
    #     logging.debug('requesting %s', pprint.pformat(this_data))
    #     resp = wootils.get_pagewoo_analytics(this_data)
    #     metrics_data.append(resp)
    metrics_data = []
    cursor = None
    errored = False
    if not metrics_data:
        this_data = {}
        this_data['start_date'] = date_to_pw_json(start_date)
        this_data['end_date'] = date_to_pw_json(end_date)
        this_data['camp_key'] = pw_key
        logging.warning(this_data)
        # TODO: revert this to an empty list to see what data looks
        # like if we cannot bring up results
        # this_data['geoids'] = []
        try:
            geoids = camp.geoids
        except Exception as e:
            logging.exception(e)
            geoids = []

        if camp.home_geoid not in geoids:
            if geoids:
                camp.home_geoid = geoids[0]
            else:
                camp.home_geoid = ''

        this_data['geoids'] = geoids
        this_data['home_geoid'] = camp.home_geoid or ''
        this_data['data_type'] = 'get_metrics'
        # TODO: perhaps aggregate?
        logging.debug('requesting %s', pprint.pformat(this_data))
        resp = wootils.get_pagewoo_analytics(this_data)
        if resp == "error":
            errored = True
        else:
            metrics_data.extend(resp)
    data = {
        'metrics': metrics_data,
        'cursor': cursor.urlsafe() if cursor else None,
        }
    return data, errored


def date_to_pw_json(dtime):
    if dtime:
        return {'year': dtime.year,
                'month': dtime.month,
                'day': dtime.day}
