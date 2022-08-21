# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
import logging
import melisdk
from melisdk.meli import Meli


class mercadolibre_banner(osv.osv):
    _name = "mercadolibre.banner"
    _description = "Banners for MercadoLibre descriptions"
    
    _columns = {
    'name': fields.char('Name'),
    'description': fields.html(string='Description'),
    }

class official_store(osv.osv):
    _name = 'official.store'
    _description = 'Description'

    def store_get_mlm( self, cr, uid, ids, context=None ):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        store_obj = self.pool.get('official.store')
        store_ids = store_obj.search(cr,uid, [], context=context)

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        vendor=company.mercadolibre_seller_id
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        response = meli.get("/users/"+vendor+"/brands")
        rjson = response.json()
        if "brands" in rjson:
            for rec in rjson["brands"]:
                exis=False
                for exist in store_ids:
                    id_sto =store_obj.browse(cr, uid,exist,context=context)
                    if rec["official_store_id"]==id_sto.official_store_id:
                        store_obj.write(cr,uid,exist.id,{'state':rec["status"]},context=context)
                        exis=True
                        continue
                if exis==False:
                    store_obj.create(cr,uid,{'name':rec["name"],'official_store_id':rec["official_store_id"],
                        'state':rec["status"]},context=context)                 
        return True

    _columns={
        'name':fields.char("Tienda",size=30,readonly=True),
        'official_store_id':fields.char("ID Tienda",readonly=True),
        'state':fields.char("status",readonly=True),
    }


