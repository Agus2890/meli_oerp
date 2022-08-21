# -*- encoding: utf-8 -*- 

from openerp.osv import fields, osv,orm
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)
import urllib2

from meli_oerp_config import *
from warning import warning

import requests
import melisdk
from melisdk.meli import Meli

import base64

from PIL import Image
from urllib import urlopen
from StringIO import StringIO


class generare_acces(osv.osv_memory):
    _name = 'generare.acces' 

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(generare_acces, self).default_get(cr, uid, fields, context=context)
        prod_obj = self.pool.get('res.company')
        prod = prod_obj.browse(cr, uid, context.get('active_id'), context=context)
        if 'name' in fields:
            res.update({'name': prod.name,'company_id':prod.id,'client_id':prod.mercadolibre_client_id,'mercadolibre_secret_key':prod.mercadolibre_secret_key})
        return res

    def action_generating_code(self, cr, uid,ids, context=None):
        wizard= self.browse(cr,uid,ids[0],context=context)
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        orders_obj = self.pool.get('mercadolibre.orders')
        posting_obj = self.pool.get('mercadolibre.posting')            
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        redirect_Url=wizard.redirect_url

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET)
        redirectUrl = meli.auth_url(redirect_URI=redirect_Url)

        return {
            "type": "ir.actions.act_url",
            "url": redirectUrl,
            "target": "new",
        }
    def action_generating_token(self, cr, uid,ids,response_info, context=None):
        wizard= self.browse(cr,uid,ids[0],context=context)
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        orders_obj = self.pool.get('mercadolibre.orders')
        posting_obj = self.pool.get('mercadolibre.posting')
        company_obj = self.pool.get('res.company')            
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        redirect_Url=wizard.redirect_url
        code=wizard.mercadolibre_code
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET)
        access_token=meli.authorize_mki(code=code, redirect_URI=redirect_Url)
        company_ids=wizard.company_id.id

        if "active_id" in access_token:
            for order_json in access_token:
                active_id=access_token["active_id"]
                raise orm.except_orm("Error Al parecer ya existe un acces token Activo",str(active_id))

        if "error" in access_token:          
            if (access_token["message"]):
                raise orm.except_orm("Error",str(access_token["message"]))
            return {}


        if "refresh_token" in access_token:
            user_id=access_token["user_id"]
            refresh_mki=access_token["refresh_token"]
            access_token=access_token["access_token"]

            company_obj.write(cr,uid,[company_ids],{
                'mercadolibre_access_token':access_token,
                'mercadolibre_refresh_token':refresh_mki,
                'mercadolibre_seller_id':user_id
                }, context=context)
        return  True
        

    _columns = {
    'company_id':fields.many2one('res.company','Compañia',required=True),
    'name':fields.char("Nombre",size=90),
    'client_id':fields.char("ID Client para ingresar a MercadoLibre",size=100), 
    'mercadolibre_secret_key': fields.char(string='Secret Key to enter MercadoLibre',size=250,required=True),
    'mercadolibre_code': fields.char( string='Code', size=256),
    'redirect_url':fields.char("Redirect URI",size=300,required=True),
    }
generare_acces()