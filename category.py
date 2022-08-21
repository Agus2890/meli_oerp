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


class mercadolibre_category(osv.osv):
    _name = "mercadolibre.category"
    _description = "Categories of MercadoLibre"

    def action_subcategory(self, cr, uid,ids, context=None):
        subcategory_obj = self.pool.get('sub.category')
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id        
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        wizard = self.browse(cr, uid, ids[0], context=context)
        model_ids=wizard.id
        category_id=wizard.meli_category_id
        lines_cat=len(wizard.lines_subcategory)
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        response = meli.get("/categories/"+category_id, {'access_token':meli.access_token})
        category_response=response.json()

        if "error" in category_response:
            _logger.error(category_response)
            _logger.error( category_response["error"] )            
            if (category_response["message"]):
                raise orm.except_orm("Error",str(category_response["message"]))
                _logger.error( category_response["message"])
            return {}

        if len(category_response["children_categories"]):
            for reco in category_response["children_categories"]:
                response_item = meli.get("/categories/"+reco["id"], {'access_token':meli.access_token})
                category_response_item=response_item.json()
                id_cat=subcategory_obj.search(cr, uid, [('meli_category_id','=',reco["id"])], context=context)
                if not id_cat:
                    if ("id" in reco):
                        values={
                            'id_category':model_ids,
                            'name':reco["name"],
                            'meli_category_id':reco["id"],
                            'listing_allowed':str(category_response_item["settings"]["listing_allowed"]),
                            'attribute_types':category_response["attribute_types"],
                        }
                        new_poroduct=subcategory_obj.create(cr, uid,values)
                else:
                    subcategory_obj.write(cr,uid,id_cat[0],{'listing_allowed':str(category_response_item["settings"]["listing_allowed"])}, context=context) 
                    self.write(cr, uid, ids, { 'listing_allowed':str(category_response["settings"]["listing_allowed"])}, context=None)                   
        return True
    
    _columns = {
	'name': fields.char('Name'),
	'meli_category_id': fields.char('Category Id'),
    'listing_allowed':fields.char('Permitido listado',size=15),
    'attribute_types':fields.char('Tallas y Colores',size=15),
    'lines_subcategory':fields.one2many('sub.category','id_category','Categoria Id'),#Lineas sub.category

    }
mercadolibre_category()

class sub_category(osv.osv):
    _name = "sub.category"
    _description = "Subcategorias Categories of MercadoLibre"

    def action_subcategory(self, cr, uid,ids, context=None):
        subcategory_obj = self.pool.get('subsub.category')
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id        
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        wizard = self.browse(cr, uid, ids[0], context=context)
        model_ids=wizard.id
        category_id=wizard.meli_category_id
        lines_cat=len(wizard.lines_subsubcategory)
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        response = meli.get("/categories/"+category_id, {'access_token':meli.access_token})
        category_response=response.json()

        if "error" in category_response:
            _logger.error(category_response)
            _logger.error( category_response["error"] )            
            if (category_response["message"]):
                raise orm.except_orm("Error",str(category_response["message"]))
                _logger.error( category_response["message"])
            return {}

        if len(category_response["children_categories"]):
            for reco in category_response["children_categories"]:
                response_item = meli.get("/categories/"+reco["id"], {'access_token':meli.access_token})
                category_response_item=response_item.json()
                id_cat=subcategory_obj.search(cr, uid, [('meli_category_id','=',reco["id"]),('id_category','=',model_ids)], context=context)
                if not id_cat:                
                    if ("id" in reco):
                        values={
                            'id_category':model_ids,
                            'name':reco["name"],
                            'meli_category_id':reco["id"],
                            'listing_allowed':str(category_response_item["settings"]["listing_allowed"]),
                            'attribute_types':category_response["attribute_types"],
                        }
                        new_poroduct=subcategory_obj.create(cr, uid,values)
                else:
                    subcategory_obj.write(cr,uid,id_cat[0],{'listing_allowed':str(category_response_item["settings"]["listing_allowed"])}, context=context)

        if category_response["attribute_types"]=="variations":
            color_obj = self.pool.get('mercadolibre.color')
            size_obj = self.pool.get('mercadolibre.tallas')

            response_attrib = meli.get("/categories/"+category_id+"/attributes", {'access_token':meli.access_token})
            category_response_attrib=response_attrib.json()
            for record in category_response_attrib:
                #name=record["name"].encode('utf-8')
                #typecolor=record["type"]
                if "type" in record:
                    typec=record["type"]
                    if typec=='color':
                        for recor in  record["values"]:
                            exis_color=color_obj.search(cr,uid,[('id_color','=',recor["id"])],context=context)
                            if not exis_color: 
                                values_color={
                                'id_category':model_ids,
                                'name':recor["name"],
                                'id_color':recor["id"],
                                'metadata':recor["metadata"]["rgb"],
                                'title':record["name"],
                                'id_type':record["id"],
                                }
                                new_colors=color_obj.create(cr, uid,values_color)
                            else:
                                color_obj.write(cr,uid,exis_color[0],{'id_category':model_ids}, context=context)
                            #else:
                                #color_obj.write(cr,uid,model_ids,{'id_category':model_ids}, context=context)
                    if typec=='size':
                        for recsize in record["values"]:
                            exis_size=size_obj.search(cr,uid,[('id_talla','=',recsize["id"])],context=context)
                            if not exis_size:
                                values_size={
                                    'id_category':model_ids,
                                    'name':recsize["name"],
                                    'id_talla':recsize["id"],
                                    'id_type':record["id"],
                                    'title':record["name"],
                                }
                                new_size=size_obj.create(cr, uid,values_size)
                            else:
                                size_obj.write(cr,uid,exis_size[0],{'id_category':model_ids}, context=context)
                            #else:
                                #size_obj.write(cr,uid,model_ids,{'id_category':model_ids}, context=context)
        return True

    _columns = {
        'id_category':fields.many2one('mercadolibre.category','Categoria Id'),#id lineas
        'name': fields.char('Name'),
        'meli_category_id': fields.char('Category Id'),
        'listing_allowed':fields.char('Permitido listado',size=15),
        'attribute_types':fields.char('Tallas y Colores',size=15),

        'lines_subsubcategory':fields.one2many('subsub.category','id_category','Categoria Id'),#Lineas subsubcategori
        'lines_color':fields.one2many('mercadolibre.color','id_category','Colores de Categoria'),
        'lines_talla':fields.one2many('mercadolibre.tallas','id_category','Tallas de Categoria'),
    }
sub_category()
#######
class subsub_category(osv.osv):
    _name = "subsub.category"
    _description = "Subcategorias Categories of MercadoLibre"

    def action_subcategory(self, cr, uid,ids, context=None):
        subcategory_obj = self.pool.get('subsubsub.category')
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id        
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        wizard = self.browse(cr, uid, ids[0], context=context)
        model_ids=wizard.id
        category_id=wizard.meli_category_id
        lines_cat=len(wizard.lines_subsubsubcategory)
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        response = meli.get("/categories/"+category_id, {'access_token':meli.access_token})
        category_response=response.json()

        if "error" in category_response:
            _logger.error(category_response)
            _logger.error( category_response["error"] )            
            if (category_response["message"]):
                raise orm.except_orm("Error",str(category_response["message"]))
                _logger.error( category_response["message"])
            return {}

        if len(category_response["children_categories"]):
            for reco in category_response["children_categories"]:
                response_item = meli.get("/categories/"+reco["id"], {'access_token':meli.access_token})
                category_response_item=response_item.json()
                id_cat=subcategory_obj.search(cr, uid, [('meli_category_id','=',reco["id"]),('id_category','=',model_ids)], context=context)
                if not id_cat:
                    if ("id" in reco):
                        values={
                            'id_category':model_ids,
                            'name':reco["name"],
                            'meli_category_id':reco["id"],
                            'listing_allowed':str(category_response_item["settings"]["listing_allowed"]),
                            'attribute_types':category_response["attribute_types"],
                        }
                        new_poroduct=subcategory_obj.create(cr, uid,values)
                else:
                    subcategory_obj.write(cr,uid,id_cat[0],{'listing_allowed':str(category_response_item["settings"]["listing_allowed"])}, context=context)

        if category_response["attribute_types"]=="variations":
            color_obj = self.pool.get('mercadolibre.color')
            size_obj = self.pool.get('mercadolibre.tallas')

            response_attrib = meli.get("/categories/"+category_id+"/attributes", {'access_token':meli.access_token})
            category_response_attrib=response_attrib.json()
            for record in category_response_attrib:
                #name=record["name"].encode('utf-8')
                #typecolor=record["type"]
                if "type" in record:
                    typec=record["type"]
                    if typec=='color':
                        for recor in  record["values"]:
                            exis_color=color_obj.search(cr,uid,[('id_color','=',recor["id"])],context=context)
                            if not exis_color: 
                                values_color={
                                'id_subsub':model_ids,
                                'name':recor["name"],
                                'id_color':recor["id"],
                                'metadata':recor["metadata"]["rgb"],
                                'title':record["name"],
                                'id_type':record["id"],
                                }
                                new_colors=color_obj.create(cr, uid,values_color)
                            else:
                                color_obj.write(cr,uid,exis_color[0],{'id_subsub':model_ids}, context=context)
                            #else:
                                #color_obj.write(cr,uid,exis_color[0],{'id_subsub':model_ids}, context=context)
                    if typec=='size':
                        for recsize in record["values"]:
                            exis_size=size_obj.search(cr,uid,[('id_talla','=',recsize["id"])],context=context)
                            if not exis_size:
                                values_size={
                                    'id_subsub':model_ids,
                                    'name':recsize["name"],
                                    'id_talla':recsize["id"],
                                    'id_type':record["id"],
                                    'title':record["name"],
                                }
                                new_size=size_obj.create(cr, uid,values_size)
                            else:
                                size_obj.write(cr,uid,exis_size[0],{'id_subsub':model_ids}, context=context)
                            #else:
                                #size_obj.write(cr,uid,exis_size[0],{'id_subsub':model_ids}, context=context)
        return True

    _columns = {
        'id_category':fields.many2one('sub.category','Categoria Id'),
        'name': fields.char('Name'),
        'meli_category_id': fields.char('Category Id'),
        'attribute_types':fields.char('Tallas y Colores',size=15),
        'listing_allowed':fields.char('Permitido listado',size=15),
        'lines_subsubsubcategory':fields.one2many('subsubsub.category','id_category','Categoria Id'),

        'lines_color':fields.one2many('mercadolibre.color','id_subsub','Colores de Categoria'),
        'lines_talla':fields.one2many('mercadolibre.tallas','id_subsub','Tallas de Categoria'),
    }
subsub_category()

class subsubsub_category(osv.osv):
    _name = "subsubsub.category"
    _description = "Subcategorias Categories of MercadoLibre"

    def action_subcategory(self, cr, uid,ids, context=None):
        subcategory_obj = self.pool.get('subsubsubsub.category')
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id        
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        wizard = self.browse(cr, uid, ids[0], context=context)
        model_ids=wizard.id
        category_id=wizard.meli_category_id
        lines_cat=len(wizard.lines_subsubsubsubcategory)
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        response = meli.get("/categories/"+category_id, {'access_token':meli.access_token})
        category_response=response.json()

        if "error" in category_response:
            _logger.error(category_response)
            _logger.error( category_response["error"] )            
            if (category_response["message"]):
                raise orm.except_orm("Error",str(category_response["message"]))
                _logger.error( category_response["message"])
            return {}

        if len(category_response["children_categories"]) !=lines_cat:
            for reco in category_response["children_categories"]:
                response_item = meli.get("/categories/"+reco["id"], {'access_token':meli.access_token})
                category_response_item=response_item.json()
                id_cat=subcategory_obj.search(cr, uid, [('meli_category_id','=',reco["id"]),('id_category','=',model_ids)], context=context)
                if not id_cat:
                    if ("id" in reco):
                        values={
                            'id_category':model_ids,
                            'name':reco["name"],
                            'meli_category_id':reco["id"],
                            'listing_allowed':str(category_response_item["settings"]["listing_allowed"]),
                            'attribute_types':category_response["attribute_types"],
                        }
                        new_poroduct=subcategory_obj.create(cr, uid,values)
                else:
                    subcategory_obj.write(cr,uid,id_cat[0],{'listing_allowed':str(category_response_item["settings"]["listing_allowed"])}, context=context)

        if category_response["attribute_types"]=="variations":
            color_obj = self.pool.get('mercadolibre.color')
            size_obj = self.pool.get('mercadolibre.tallas')

            response_attrib = meli.get("/categories/"+category_id+"/attributes", {'access_token':meli.access_token})
            category_response_attrib=response_attrib.json()
            for record in category_response_attrib:
                #name=record["name"].encode('utf-8')
                #typecolor=record["type"]
                if "type" in record:
                    typec=record["type"]
                    if typec=='color':
                        for recor in  record["values"]:
                            exis_color=color_obj.search(cr,uid,[('id_color','=',recor["id"])],context=context)
                            if not exis_color: 
                                values_color={
                                'id_subsubtres':model_ids,
                                'name':recor["name"],
                                'id_color':recor["id"],
                                'metadata':recor["metadata"]["rgb"],
                                'title':record["name"],
                                'id_type':record["id"],
                                }
                                new_colors=color_obj.create(cr, uid,values_color)
                            else:
                                color_obj.write(cr,uid,exis_color[0],{'id_subsubtres':model_ids}, context=context)
                            #else:
                                #color_obj.write(cr,uid,exis_color[0],{'id_subsubtres':model_ids}, context=context)
                    if typec=='size':
                        for recsize in record["values"]:
                            exis_size=size_obj.search(cr,uid,[('id_talla','=',recsize["id"])],context=context)
                            if not exis_size:
                                values_size={
                                    'id_subsubtres':model_ids,
                                    'name':recsize["name"],
                                    'id_talla':recsize["id"],
                                    'title':record["name"],
                                    'id_type':record["id"],
                                }
                                new_size=size_obj.create(cr, uid,values_size)
                            else:
                                size_obj.write(cr,uid,exis_size[0],{'id_subsubtres':model_ids}, context=context)
                            #else:
                                #size_obj.write(cr,uid,exis_size[0],{'id_subsubtres':model_ids}, context=context)
        return True

    _columns = {
        'id_category':fields.many2one('subsub.category','Categoria Id'),
        'name': fields.char('Name'),
        'meli_category_id': fields.char('Category Id'),
        'listing_allowed':fields.char('Permitido listado',size=15),
        'attribute_types':fields.char('Tallas y Colores',size=15),

        'lines_subsubsubsubcategory':fields.one2many('subsubsubsub.category','id_category','Categoria Id'),

        'lines_color':fields.one2many('mercadolibre.color','id_subsubtres','Colores de Categoria'),
        'lines_talla':fields.one2many('mercadolibre.tallas','id_subsubtres','Tallas de Categoria'),
    }
subsubsub_category()

class subsubsubsub_category(osv.osv):
    _name = "subsubsubsub.category"
    _description = "Subcategorias Categories of MercadoLibre"

    def action_subcategory(self, cr, uid,ids, context=None):
        subcategory_obj = self.pool.get('subquinta.category')
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id        
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        wizard = self.browse(cr, uid, ids[0], context=context)
        model_ids=wizard.id
        category_id=wizard.meli_category_id
        lines_cat=len(wizard.lines_subquintacategory)
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        response = meli.get("/categories/"+category_id, {'access_token':meli.access_token})
        category_response=response.json()

        if "error" in category_response:
            _logger.error(category_response)
            _logger.error( category_response["error"] )            
            if (category_response["message"]):
                raise orm.except_orm("Error",str(category_response["message"]))
                _logger.error( category_response["message"])
            return {}

        if len(category_response["children_categories"]) !=lines_cat:
            for reco in category_response["children_categories"]:
                response_item = meli.get("/categories/"+reco["id"], {'access_token':meli.access_token})
                category_response_item=response_item.json()
                id_cat=subcategory_obj.search(cr, uid, [('meli_category_id','=',reco["id"]),('id_subsub','=',model_ids)], context=context)
                if not id_cat:
                    if ("id" in reco):
                        values={
                            'id_category':model_ids,
                            'name':reco["name"],
                            'meli_category_id':reco["id"],
                            'listing_allowed':str(category_response_item["settings"]["listing_allowed"]),
                            'attribute_types':category_response["attribute_types"],
                        }
                        new_poroduct=subcategory_obj.create(cr, uid,values)
                else:
                    subcategory_obj.write(cr,uid,id_cat[0],{'listing_allowed':str(category_response_item["settings"]["listing_allowed"])}, context=context) 

        if category_response["attribute_types"]=="variations":
            color_obj = self.pool.get('mercadolibre.color')
            size_obj = self.pool.get('mercadolibre.tallas')

            response_attrib = meli.get("/categories/"+category_id+"/attributes", {'access_token':meli.access_token})
            category_response_attrib=response_attrib.json()
            for record in category_response_attrib:
                #name=record["name"].encode('utf-8')
                #typecolor=record["type"]
                if "type" in record:
                    typec=record["type"]
                    if typec=='color':
                        for recor in  record["values"]:
                            exis_color=color_obj.search(cr,uid,[('id_color','=',recor["id"])],context=context)
                            if not exis_color: 
                                values_color={
                                    'id_subsubquinta':model_ids,
                                    'name':recor["name"],
                                    'id_color':recor["id"],
                                    'metadata':recor["metadata"]["rgb"],
                                    'title':record["name"],
                                    'id_type':record["id"],
                                }
                                new_colors=color_obj.create(cr, uid,values_color)
                            else:
                                color_obj.write(cr,uid,exis_color[0],{'id_subsubquinta':model_ids}, context=context)
                            #else:
                                #color_obj.write(cr,uid,exis_color[0],{'id_subsubquinta':model_ids}, context=context)
                    if typec=='size':
                        for recsize in record["values"]:
                            exis_size=size_obj.search(cr,uid,[('id_talla','=',recsize["id"])],context=context)
                            if not exis_size:
                                values_size={
                                    'id_subsubquinta':model_ids,
                                    'name':recsize["name"],
                                    'id_talla':recsize["id"],
                                    'id_type':record["id"],
                                    'title':record["name"],
                                }
                                new_size=size_obj.create(cr, uid,values_size)
                            else:
                                size_obj.write(cr,uid,exis_size[0],{'id_subsubquinta':model_ids}, context=context)
                            #else:
                                #size_obj.write(cr,uid,exis_size[0],{'id_subsubquinta':model_ids}, context=context)
        return True

    _columns = {
        'id_category':fields.many2one('subsubsub.category','Categoria Id'),
        ##
        'name': fields.char('Name'),
        'meli_category_id': fields.char('Category Id'),
        'listing_allowed':fields.char('Permitido listado',size=15),
        'attribute_types':fields.char('Tallas y Colores',size=15),

        'lines_subquintacategory':fields.one2many('subquinta.category','id_category','Categoria Id'),
        'lines_color':fields.one2many('mercadolibre.color','id_subsubquinta','Colores de Categoria'),
        'lines_talla':fields.one2many('mercadolibre.tallas','id_subsubquinta','Tallas de Categoria'),
    }
subsubsubsub_category()

class subquinta_category(osv.osv):
    _name = "subquinta.category"
    _description = "Subcategorias Categories of MercadoLibre"

    _columns = {
        'id_category':fields.many2one('subsubsubsub.category','Categoria Id'),
        ##
        'name': fields.char('Name'),
        'listing_allowed':fields.char('Permitido listado',size=15),
        'meli_category_id': fields.char('Category Id'),
        'attribute_types':fields.char('Tallas y Colores',size=15),
    }
subquinta_category()

##Tallas
class mercadolibre_tallas(osv.osv):
    _name = 'mercadolibre.tallas'
    _description = 'Tallas MercadoLibre'
    _columns = {
        'id_category':fields.many2one('sub.category','Id Talla'),
        'id_subsub':fields.many2one('subsub.category','Id Talla'),
        'id_subsubtres':fields.many2one('subsubsub.category','Id Talla'),
        'id_subsubquinta':fields.many2one('subsubsubsub.category','Id Talla'),
        'id_talla':fields.char('Id Talla',size=30),
        'name':fields.char('Talla', size=30),
        'id_type':fields.char('ID Typo',size=30),
        'title':fields.char("Titulo",size=30),
    }
###Genero
class mercadolibre_color(osv.osv):
    _name = 'mercadolibre.color'
    _description = 'color MercadoLibre'
    _columns = {
        'id_category':fields.many2one('sub.category','Id Color'),
        'id_subsub':fields.many2one('subsub.category','Id Color'),
        'id_subsubtres':fields.many2one('subsubsub.category','Id Color'),
        'id_subsubquinta':fields.many2one('subsubsubsub.category','Id Color'),
        'id_color':fields.char('Id Color',size=30),
        'name':fields.char('Color', size=30),
        'metadata':fields.char("Metadata",size=30),
        'id_type':fields.char('ID Typo',size=30),
        'title':fields.char("Titulo",size=30),
    }