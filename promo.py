#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import logging


# local files
from nearwoo_sessions import promo_session_config
import promo_handlers
import partner_promo_shared


def handle_404(request, response, exception):
    logging.exception(str(exception))
    response.write('Could not find this page :(')
    response.set_status(404)


def handle_500(request, response, exception):
    logging.exception(str(exception))
    response.write('A server error occurred :(')
    response.set_status(500)


app = webapp2.WSGIApplication([
    webapp2.Route('/promo/applypromotional/<promo_id>/' +
                  '<n_block_groups>/<campaign_value>',
                  handler=promo_handlers.ApplyPromotional),
    # admin
    webapp2.Route('/promo/repdash',
                  handler=promo_handlers.RepDash),
    webapp2.Route('/promo/updatecampaign/<promo_id>/<partner_promo_category>/' +
                  '<n_block_groups>/<camp_key>',
                  handler=promo_handlers.UpdateCampaignPromotional),
    webapp2.Route('/promo/loggedin',
                  handler=promo_handlers.PromotionalLoggedIn),
    webapp2.Route('/promo/editinfo',
                  handler=promo_handlers.EditPromotional),
    webapp2.Route('/promo/verify/<promo_id>/<token>',
                  handler=promo_handlers.VerifyPromotional,
                  name='verifypromotional'),
    webapp2.Route('/promo/login',
                  handler=promo_handlers.PromotionalLogin),
    webapp2.Route('/promo/logout',
                  handler=promo_handlers.PromotionalLogout),
    webapp2.Route('/promo/forgotpassword',
                  handler=promo_handlers.ForgotPromoPassword),
    webapp2.Route('/promo/media/library',
                  handler=promo_handlers.MediaLibrary),
    webapp2.Route('/promo/listadvertisercampaigns/<advertiser_key>',
                  handler=promo_handlers.ListAdvertiserCampaigns),
    webapp2.Route('/promo/listcampaigns',
                  handler=promo_handlers.ListCampaigns),
    webapp2.Route('/promo/forgotpromoid',
                  handler=promo_handlers.ForgotPromoID),
    webapp2.Route('/promo/info',
                  handler=promo_handlers.PromotionalInfo),
    webapp2.Route('/promo/info/<promo_id>',
                  handler=promo_handlers.PromotionalInfo),
    # representative and partner dash dash
    webapp2.Route('/promo/dash/promoeffectiveness/' +
                  '<agent_type>/<agent_id>/<tdelta>/<n_history>',
                  handler=partner_promo_shared.DashPromoEffectiveness),
    webapp2.Route('/promo/dash/promouriviews/' +
                  '<agent_type>/<agent_id>/<tdelta>/<n_history>',
                  handler=partner_promo_shared.DashNPromoUriViews),
    webapp2.Route('/promo/dash/newcampaigns/' +
                  '<agent_type>/<agent_id>/<tdelta>/<n_history>',
                  handler=partner_promo_shared.DashNCampaigns),
    webapp2.Route('/promo/dash/nblockgroups/' +
                  '<agent_type>/<agent_id>/<tdelta>/<n_history>',
                  handler=partner_promo_shared.DashNBlockGroups),
    webapp2.Route('/promo/dash/revenue/' +
                  '<agent_type>/<agent_id>/<tdelta>/<n_history>',
                  handler=partner_promo_shared.DashRevenue),
    webapp2.Route('/promo/dash/campaigncategories/' +
                  '<agent_type>/<agent_id>/<tdelta>',
                  handler=partner_promo_shared.DashCampaignCategories),
    webapp2.Route('/promo/dash/totalrevenue/' +
                  '<agent_type>/<agent_id>',
                  handler=partner_promo_shared.DashTotalRevenue),
    webapp2.Route('/promo/dash/totalnblockgroups/' +
                  '<agent_type>/<agent_id>/<tdelta>/<n_history>',
                  handler=partner_promo_shared.DashTotalNBlockGroups),
    webapp2.Route('/promo/dash/totalnblockgroups/' +
                  '<agent_type>/<agent_id>',
                  handler=partner_promo_shared.DashTotalNBlockGroups),
    webapp2.Route('/promo/dash/totalncampaigns/' +
                  '<agent_type>/<agent_id>',
                  handler=partner_promo_shared.DashTotalNCampaigns),
], config=promo_session_config, debug=True)
app.error_handlers[404] = handle_404
app.error_handlers[500] = handle_500
