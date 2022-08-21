# -*- coding: utf-8 -*-
import base64

import werkzeug
import werkzeug.urls
from openerp.addons.web.controllers.main import _serialize_exception
from openerp import http, SUPERUSER_ID
from openerp.http import request
# import simplejson
from openerp.tools.translate import _
from openerp.tools import html_escape
import werkzeug

import logging
_logger = logging.getLogger(__name__)
#from urllib.parse import urlencode
from openerp.addons.meli_oerp.melisdk.meli import Meli

class melierp(http.Controller):

    @http.route(['/get_auth_code'], type='http', auth='public', website=True)
    def render_meli_get(self, **kwarg):
        if kwarg.get('code'):
            code = kwarg.get('code')
            company_id = http.request.env['res.users'].sudo().search([('id','=',request.uid)], limit=1).company_id
            #url = urlencode({'redirect_uri':'https://importadoraver.sistemasmexico.club'})
            meli = Meli(client_id=company_id.mercadolibre_client_id,client_secret=company_id.mercadolibre_secret_key)
            REDIRECT_URI="https://importadoraver.sistemasmexico.club/get_auth_code"
            result=meli.authorize_mki( code, REDIRECT_URI)
            #raise Warning("",str(result))
            _logger.info("error: %s " % (result))
            ACCESS_TOKEN =result.get('access_token')
            REFRESH_TOKEN = result.get('refresh_token')
            company_id.write({
                'mercadolibre_access_token': ACCESS_TOKEN,
                'mercadolibre_refresh_token': REFRESH_TOKEN,
                'mercadolibre_code': code,
                'mercadolibre_seller_id': result.get('user_id')
                } )
            return "Successfully Connected,Please Close this window"