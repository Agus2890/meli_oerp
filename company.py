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
import datetime
import time
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

REDIRECT_URI = 'https://importadoraver.sistemasmexico.club/get_auth_code'

class res_company(osv.osv):
    _name = "res.company"
    _inherit = "res.company"

    def meli_get_object( self, cr, uid, ids, field_name, attributes, context=None ):
        return True

    def get_meli_state( self, cr, uid, ids, field_name, attributes, context=None ):
        res = {}        
        for company in self.browse(cr,uid,ids):
            res[company.id] = True
        return res
        # recoger el estado y devolver True o False (meli)
        #False if logged ok
        #True if need login
        print 'company get_meli_state() '
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        warningobj = self.pool.get('warning')

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        ML_state = False

        try:
            response = meli.get("/items/MLM", {'access_token':meli.access_token} )
            print "response.content:", response.content
            rjson = response.json()
            _logger.info("error: %s " % (rjson))
            #response = meli.get("/users/")
            if "error" in rjson:
                if "message" in rjson and rjson["message"]=="expired_token":
                    ML_state = True
                                  
            if ACCESS_TOKEN==False:
                ML_state = True
        except requests.exceptions.ConnectionError as e:
            #raise osv.except_osv( _('MELI WARNING'), _('NO INTERNET CONNECTION TO API.MERCADOLIBRE.COM: complete the Cliend Id, and Secret Key and try again'))
            ML_state = True
            error_msg = 'MELI WARNING: NO INTERNET CONNECTION TO API.MERCADOLIBRE.COM: complete the Cliend Id, and Secret Key and try again '
            _logger.error(error_msg)
            
#        except requests.exceptions.HTTPError as e:
#            print "And you get an HTTPError:", e.message

        if ML_state:
            ACCESS_TOKEN = False
            REFRESH_TOKEN =False

            #company.write({'mercadolibre_access_token': ACCESS_TOKEN, 'mercadolibre_refresh_token': REFRESH_TOKEN, 'mercadolibre_code': '' } )

        res = {}		
        for company in self.browse(cr,uid,ids):
            res[company.id] = ML_state
        return res

    def action_gene_orders( self, cr, uid, ids, field_name, args, context=None):
        records=self.browse(cr,uid,ids)
        ordenes_obj  = self.pool.get('mercadolibre.orders')
        orders_ids = ordenes_obj.search(cr, 1 , [('sale_order','=',False)], context=context)
        res={}
        for lin in records:
            res[lin.id]=len(orders_ids)
        return res

    def action_gene_posting( self, cr, uid, ids, field_name, args, context=None):
        records=self.browse(cr,uid,ids)
        posting_obj  = self.pool.get('mercadolibre.posting')
        posting_ids = posting_obj.search(cr, 1 , [('product_id','=',False)], context=context)
        res={}
        for lin in records:
            res[lin.id]=len(posting_ids)
        return res

    def action_gene_orders_erp( self, cr, uid, ids, context=None):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        saleorder_obj = self.pool.get('sale.order')
        partner_obj = self.pool.get('res.partner')
        saleline_obj = self.pool.get('sale.order.line')
        product_temp_obj = self.pool.get('product.template')
        product_obj = self.pool.get('product.product')
        buyer_obj=self.pool.get('mercadolibre.buyers')
        ordenes_obj  = self.pool.get('mercadolibre.orders')
        multipos_obj = self.pool.get('multi.posting')
        delivery_obj = self.pool.get('delivery.carrier')
        orders_ids = ordenes_obj.search(cr, 1 , [('sale_order','=',False),('status','=','paid')], context=context, limit=100)
        cantidad=len(orders_ids)
        count=0
        for reco in orders_ids:
            count+=1
            mlm_order =ordenes_obj.browse(cr, uid, reco, context=context)
            buyer=mlm_order.buyer.id
            buyer_id =buyer_obj.browse(cr, uid, buyer, context=context)
            partner=partner_obj.search(cr, 1 , [('ref','=',buyer_id.buyer_id)], context=context)
            cant=True
            for reco_item in mlm_order.order_items:
                product_id=multipos_obj.search(cr, 1 , [('meli_id','=',reco_item.order_item_id),('product_id','!=',False)], context=context)
                if product_id: 
                    _logger.info("Productos if: %s " % (reco_item.order_item_id))
                else:
                    cant=False
                    _logger.info("False: %s " % (count))
                    break
            ####Validando Productos con SKU
            if cant==True:
                _logger.info("cantidad: %s " % (count))
                if not partner:
                    values={
                        'name':buyer_id.first_name+' '+buyer_id.last_name or False,
                        'ref':buyer_id.buyer_id,
                        'phone':buyer_id.phone,
                        'email':buyer_id.email,
                    }
                    partner_id=partner_obj.create(cr, uid,values) 
                if partner:
                    partner_id=partner[0]
                delivery_id=False    
                if mlm_order.shipment_name: 
                    delivery_ids = delivery_obj.search(cr, 1 , [('name','=',mlm_order.shipment_name)], context=context)
                    if delivery_ids:
                        delivery_id=delivery_ids[0] 

                values_order={
                    'partner_id':partner_id,
                    'warehouse_id':company.stock_id.id,
                    'client_order_ref':mlm_order.order_id,
                    'tienda_idmlm':'Tiendas Oficiales',
                    'orden_id_mlm':mlm_order.id,
                    'name':'TOML'+'-'+mlm_order.order_id,
                    'address_mlm':mlm_order.note,
                    'carrier_id':delivery_id,
                }
                order_id=saleorder_obj.create(cr, uid,values_order)
                ordenes_obj.write(cr,uid,mlm_order.id,{'sale_order':order_id}, context=context)
                _logger.info("Generando Ordenes Cantidad: %s " % (cantidad))
                _logger.info("Generando en proceso: %s " % (count))
                for reco_item in mlm_order.order_items:
                    product_id=multipos_obj.search(cr, 1 , [('meli_id','=',reco_item.order_item_id)], context=context)
                    idposting= self.pool.get('multi.posting').browse(cr, uid,product_id[0], context=context)
                    template_id=idposting.product_id.id
                    idproduct=product_obj.search(cr, 1 , [('product_tmpl_id','=',template_id)], context=context)
                    id_product=idproduct[0]
                    
                    val_order_line={
                        'order_id':order_id,
                        'product_id':id_product,
                        'product_uom_qty':reco_item.quantity,
                        'price_unit':float(reco_item.unit_price)/1.16,
                    }
                    lines_order=saleline_obj.create(cr, uid,val_order_line)
                saleorder_obj.action_button_confirm(cr, uid, [order_id], context=context)
        return True

    def _get_pro_toml(self, cr, user_id, context=None):
        cr.execute('select distinct proveedor from multi_posting where proveedor is not null')
        t = () # declaramos una tupla vacía
        for record in cr.fetchall():
            t = t + ((record[0], record[0]),) # anidamos todos los camps de la tupla como a tuplas hijas
        return t

    _columns = {
        'mercadolibre_client_id': fields.char(string='Client ID to enter MercadoLibre',size=128), 
        'mercadolibre_secret_key': fields.char(string='Secret Key to enter MercadoLibre',size=128),
        'mercadolibre_access_token': fields.char( string='Access Token',size=256),
        'mercadolibre_refresh_token': fields.char( string='Refresh Token', size=256),
        'mercadolibre_code': fields.char( string='Code', size=256),
        'mercadolibre_seller_id': fields.char( string='Seller Id', size=256),
        'mercadolibre_state': fields.function( get_meli_state, method=True, type='boolean', string="Login is required with MLA", store=False ),
        'postin_activas':fields.boolean('Publicaciones Activas'),
        'postin_paused':fields.boolean('Publicaciones Pausadas'),
        'postin_closed':fields.boolean('Publicaciones Finalizadas'),
        'num_order':fields.function(action_gene_orders,type='float',string='Ordenes por generar ERP',
            help='Cantidad de ordenes que faltan para generarlos en el ERP si el numero es mayo a 1 porfavor presione el boton Generar Ordenes  en ERP'),
        'num_posting':fields.function(action_gene_posting,type='float',string='Publicaciones por generar ERP',
            help='Numero de  publicaciones de MLM que no se han generado  como productos en el ERP si este campo contien un numero mayor a uno  porfavor presione el boton  Generar Productos o Generating products'),
        'stock_id':fields.many2one('stock.warehouse','Almacen',required=True),
        'categ_product':fields.many2one('product.category','Categoria Productos',required=True),
        'tienda_oficial':fields.boolean('Tienda Oficial'),
        'official_store_id': fields.char('Identificacion oficial tienda', size=25),
        'date_questions_toml':fields.datetime('Ultima descarga de preguntas'),
        'prov_toml': fields.selection(_get_pro_toml,'Proveedores TOML'),
        'qty_pause':fields.integer('Cant min para pausar'),
        'date_orders_toml':fields.datetime('Ultima descarga de Ordenes'),

        #'mercadolibre_login': fields.selection( [ ("unknown", "Desconocida"), ("logged","Abierta"), ("not logged","Cerrada")],string='Estado de la sesiÃ³n'), ) 
    }
    
    def	meli_logout(self, cr, uid, ids, context=None ):

        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = ''
        REFRESH_TOKEN = ''

        company.write({'mercadolibre_access_token': ACCESS_TOKEN, 'mercadolibre_refresh_token': REFRESH_TOKEN, 'mercadolibre_code': '' } )
        url_logout_meli = '/web?debug=#view_type=kanban&model=product.template&action=150'
        print url_logout_meli
        return {
            "type": "ir.actions.act_url",
            "url": url_logout_meli,
            "target": "new",
        }

    def meli_login(self, cr, uid, ids, context=None ):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET)
        url_login_meli = meli.auth_url(redirect_URI=REDIRECT_URI)
        #url_login_oerp = "/meli_login"
        print "OK company.meli_login() called: url is ", url_login_meli
        return {
            "type": "ir.actions.act_url",
            "url": url_login_meli,
            "target": "self",
        }

    def meli_query_orders(self, cr, uid, ids, context=None ):

        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        orders_obj = self.pool.get('mercadolibre.orders')
        company.write({'date_orders_toml': time.strftime('%Y-%m-%d %H:%M:%S')})            
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        #
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN )
        orders_query = str("/orders/search/recent?seller=")+str(company.mercadolibre_seller_id)+str("&sort=date_desc")

        orders_query = orders_query
        response = meli.get( orders_query, {'access_token':meli.access_token})
        orders_json = response.json()
        #raise orm.except_orm("Valor",str(orders_json))

        if "error" in orders_json:
            _logger.error(orders_json["error"] )            
            if (orders_json["message"]):
                raise orm.except_orm("Error",str(orders_json["message"]))
                _logger.error( orders_json["message"])
            return {}

        if "paging" in orders_json:
            if "total" in orders_json["paging"]:
                if (orders_json["paging"]["total"]):
                    total=orders_json["paging"]["total"]
                    limit=orders_json["paging"]["limit"]
                    melioffset=orders_json["paging"]["offset"]

        ordenes=0
        count=total
        while ordenes<=count:
            _logger.info("Total: %s " % (count))
            _logger.info("Ciclos ordenes: %s " % (ordenes))
            result = orders_obj.orders_query_recent(cr,uid,ordenes)
        #"type": "ir.actions.act_window",
        #"id": "action_meli_orders_tree",
            ordenes+=limit
        return {}

    def meli_query_posting(self, cr, uid,ids,context=None ):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        orders_obj = self.pool.get('mercadolibre.orders')
        posting_obj = self.pool.get('mercadolibre.posting')               

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        postin_activas=company.postin_activas
        postin_paused=company.postin_paused
        postin_closed=company.postin_closed

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN )
        posting_query = str("/users/"+str(company.mercadolibre_seller_id)+"/items/search?access_token=")+str(meli.access_token)

        queryexted=str("&status=active")
        if postin_activas==True:
            queryexted =str("&status=active")
        elif postin_paused==True:
            queryexted =str("&status=paused")
        elif postin_closed==True:
            queryexted =str("&status=closed")       

        responsenum = meli.get(posting_query+str("&limit=50")+str("&offset=0")+str(queryexted))
        posting_json = responsenum.json()
        _logger.info("CONECTANDO : %s " % (queryexted))        

        if "error" in posting_json:
                _logger.error(posting_json )
                _logger.error( posting_json["error"] )            
                if (posting_json["message"]=="invalid_token"):
                    raise orm.except_orm("Posiblemente access_token caducado",str(posting_json["message"]))
                    _logger.error( posting_json["message"])
                return {}
        
        if "paging" in posting_json:
            if "total" in posting_json["paging"]:
                if (posting_json["paging"]["total"]):
                    total=posting_json["paging"]["total"]
                    limit=posting_json["paging"]["limit"]
                    melioffset=posting_json["paging"]["offset"]

        limite=limit
        i=0
        #count=total
        count=total
        querycomplement=queryexted
        
        while i<=count: 
            orders_query = str("/users/"+str(company.mercadolibre_seller_id)+"/items/search?access_token=")+str(meli.access_token)
            #+str("&offset=600")+str("&status=active")
            response = meli.get(orders_query+str("&limit=100")+str("&offset=")+str(i)+str(querycomplement))
            orders_json = response.json()
            _logger.info("posting: %s " % (orders_json))

            if "error" in orders_json:
                _logger.error( orders_query )
                _logger.error( orders_json["error"] )            
                if (orders_json["message"]=="invalid_token"):
                    raise orm.except_orm("Posiblemente access_token caducado",str(orders_json["message"]))
                    _logger.error( orders_json["message"])
                return {}

            if "results" in orders_json:
                for order_json in orders_json["results"]:                   
                    items_id=order_json
                    id_items =posting_obj.search(cr, uid, [('meli_id','=',items_id)], context=context)
                    itemss=id_items
                    if not itemss:
                        responseinfo = meli.get("/items/"+items_id, {'access_token':meli.access_token})
                        #responseinfo = meli.get("/items/MLM00000", {'access_token':meli.access_token})
                        newinfo=responseinfo.json()
                        #raise orm.except_orm("sku",str(newinfo))
                        if "error" in newinfo:            
                            if (newinfo["error"]=="not_found"):
                                raise orm.except_orm("Posiblemente",str(newinfo["message"]))
                                _logger.error( newinfo["error"])
                            return {}
                        meli_status=newinfo["status"]
                        meli_permalink=newinfo["permalink"] or False
                        meli_price=newinfo["price"] or False
                        name=False
                        if newinfo['title'] !='null':
                            name=newinfo['title']
                        result={
                            'meli_id':order_json,
                            'name':name,
                            'meli_permalink':meli_permalink,
                            'meli_price':meli_price,
                            'meli_status':meli_status,
                            'sku':newinfo["seller_custom_field"] or False,
                        }
                        new_posting = posting_obj.create(cr, uid,result)
            i+=limit
            _logger.info("Ciclos: %s " % (i))
        return True

    def action_generating_products(self, cr, uid,ids, context=None):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        orders_obj = self.pool.get('mercadolibre.orders')            
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        postin_activas=company.postin_activas
        postin_paused=company.postin_paused
        postin_closed=company.postin_closed

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN )
        mercadolibre_obj = self.pool.get('mercadolibre.posting')
        product_obj = self.pool.get('product.product')
        category_obj = self.pool.get('mercadolibre.category')
        multipos_obj = self.pool.get('multi.posting')
        mlm_ids = mercadolibre_obj.search(cr, 1 , [('sku','!=',False),('product_id','=',False)], context=context)
        #meli_idss = [x.id for x in mercadolibre_obj.browse(cr, uid, mlm_ids, context=context)
        #if x.id and x.id not in ids]
        cantidad=len(mlm_ids)
        count=0
        #
        for self_obj in mlm_ids:
            count+=1
            id_next=mercadolibre_obj.browse(cr, uid, [self_obj], context=context)
            name=id_next.name
            meli_id=id_next.meli_id
            sku=id_next.sku
            _logger.info("Cantidad: %s " % (cantidad))
            _logger.info("ejecutandose: %s " % (count))
            _logger.info("meli_id: %s " % (meli_id))
            itemp = multipos_obj.search(cr, uid, [('meli_id', '=' ,meli_id)], context=context)
            #raise orm.except_orm("Cantidad",str(itemp))
            if not itemp:
                try:
                    response = meli.get("/items/"+meli_id, {'access_token':meli.access_token})
                    items_response=response.json()
                    _logger.info("Valores: %s " % (items_response))
                    
                    if "error" in items_response:
                        _logger.info("Error: %s " % (items_response))          
                        if (items_response["message"]=="invalid_token"):
                            raise orm.except_orm("Posiblemente access_token caducado",str(items_response["message"]))
                            _logger.error( items_response["message"])
                        return {}

                    response_descri=meli.get("/items/"+meli_id+"/description", {'access_token':meli.access_token})
                    descrip=response_descri.json()
                except Exception, e:
                    raise orm.except_orm("Conexion",str(e))
                id_sku = product_obj.search(cr, uid, [('default_code', '=' ,sku)], context=context)
                if not id_sku: 
                    values_product={
                        'name':name,
                        'default_code':sku,
                        'categ_id':company.categ_product.id,
                        'brand':id_next.brand,
                    }
                    id_product=product_obj.create(cr, uid,values_product)
                else:
                    id_product=id_sku[0]
                id_pro = self.pool.get('product.product').browse(cr, uid,id_product, context=context)
                #product_template=id_pro.product_tmpl_id
                #raise orm.except_orm("Valor",str(product_template)) 

                imagen_m=False
                #raise orm.except_orm("Valor",str(len(items_response["pictures"])))
                image1=False
                image2=False
                image3=False
                image4=False
                image5=False
                image6=False
                if len(items_response["pictures"]):
                    count=len(items_response["pictures"])
                    if count>0:
                        image1=items_response["pictures"][0]["url"]
                    if count>1:
                        image2=items_response["pictures"][1]["url"]
                    if count>2:
                        image3=items_response["pictures"][2]["url"]
                    if count>3:
                        image4=items_response["pictures"][3]["url"]
                    if count>4:
                        image5=items_response["pictures"][4]["url"]
                    if count>5:
                        image6=items_response["pictures"][5]["url"]
                _logger.info("Precio: %s " % (items_response["price"]))  
                valuess={
                    'product_id':id_pro.product_tmpl_id.id,
                    'meli_post_required':True,
                    'meli_permalink':items_response["permalink"],
                    'meli_id':meli_id,
                    'meli_title':name,
                    'meli_currency':items_response["currency_id"],
                    'category_id_mlm':items_response["category_id"],
                    'meli_condition':items_response["condition"],
                    'meli_listing_type':items_response["listing_type_id"],
                    'meli_available_quantity':items_response["available_quantity"],
                    'meli_buying_mode':items_response["buying_mode"],
                    'meli_warranty':items_response["warranty"],
                    'meli_price':items_response["price"],
                    #'meli_imagen_id':id_img,
                    'tienda':'Tiendas Oficiales',
                    'meli_description':descrip["text"],
                    'sku':sku,
                    'meli_imagen_logo':image1 or False,
                    'meli_imagen_link':image2 or False,
                    'meli_multi_imagen_id':image3 or False,
                    'imagen_cuatro':image4 or False,
                    'imagen_cinco':image5 or False,
                    'imagen_seis':image6 or False,
                }
                _logger.info("Registros: %s " % (valuess))
                new_poroduct=multipos_obj.create(cr, uid,valuess)
                mercadolibre_obj.write(cr,uid,self_obj,{'product_variant':new_poroduct,'product_id':id_product}, context=context)
                #if not id_pro.image_medium:
                    #_logger.info("imagem: %s " % (id_pro.id))
                    #product_obj.write(cr,uid,id_pro.id,{'image_medium':imagen_m}, context=context)
            else:
                id_multi = self.pool.get('multi.posting').browse(cr, uid,itemp[0], context=context)
                idproduct=product_obj.search(cr, 1 , [('product_tmpl_id','=',id_multi.product_id.id)], context=context)
                #raise orm.except_orm("Valor",str(id_multi.meli_id))
                if idproduct: 
                    mercadolibre_obj.write(cr,uid,[self_obj],{'product_id':idproduct[0]}, context=context)
                    _logger.info("write: %s " % (itemp[0]))
        return {}

    def action_updates_products(self, cr, uid,ids, context=None):
        mercadolibre_obj = self.pool.get('mercadolibre.posting')
        product_obj = self.pool.get('product.template')
        category_obj = self.pool.get('mercadolibre.category')
        multipos_obj = self.pool.get('multi.posting')

        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        mlm_ids = mercadolibre_obj.search(cr, 1 , [], context=context)
        cantidad=len(mlm_ids)
        count=0
        for rec in mlm_ids:
            count+=1
            _logger.info("Cantidad: %s " % (cantidad))
            _logger.info("next: %s" % (count))
            id_posting = self.pool.get('mercadolibre.posting').browse(cr, uid,rec, context=context)
            meli_id=id_posting.meli_id
            productvariant_id=id_posting.product_variant.id
            if meli_id: 
                meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
                response = meli.get("/items/"+meli_id, {'access_token':meli.access_token})
                items_response=response.json()
                #raise orm.except_orm("Valor",str(items_response))
                if not  "error" in items_response:
                    mercadolibre_obj.write(cr,uid,rec,{
                        'meli_status':items_response["status"],
                        'meli_price':items_response["price"],
                        'name':items_response["title"],
                        'meli_permalink':items_response["permalink"]}, 
                        context=context)
                    if productvariant_id:
                        multipos_obj.write(cr,uid,productvariant_id,{
                            'meli_status':items_response["status"],
                            'meli_available_quantity':items_response["available_quantity"]
                            },context=context)
                else:
                    _logger.info("Revisar access token: %s" % (meli_id))
                    if "title" in items_response:
                        nametitle=items_response["title"]
                    else:
                        nametitle=False
                    mercadolibre_obj.write(cr,uid,rec,{'meli_status':'closed','name':nametitle}, context=context)
                    if productvariant_id:
                        multipos_obj.write(cr,uid,productvariant_id,{
                            'meli_status':'closed'
                            },context=context)
        return {}

    def update_warraty_toml( self, cr, uid, ids, context=None ):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        product_obj = self.pool.get('multi.posting')
        mlm_ids = product_obj.search(cr, 1 , [('meli_id','!=',False)], context=context)
        for recod in mlm_ids:
            idsmlm= product_obj.browse(cr, uid, recod, context=context)
            meli_id=idsmlm.meli_id
            warranty=idsmlm.meli_warranty.encode('utf-8')
            #raise orm.except_orm("Valor",str(warranty))
            meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
            response = meli.put("/items/"+meli_id, { 'warranty':warranty},{'access_token':meli.access_token})
            result_response=response.json()
            if "error" in result_response:
                _logger.info("Error al actualizar en: %s " % (meli_id))
            else:           
                _logger.info("meli Actualizado: %s " % (meli_id))
        return True
    
    def update_price_toml( self, cr, uid, ids, context=None ):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        product_obj = self.pool.get('multi.posting')
        mlm_ids = product_obj.search(cr, 1 , [('meli_id','!=',False),('id_site','=','18')], context=context)
        cantn=len(mlm_ids)
        count=0
        for recod in mlm_ids:
            count+=1
            _logger.info("Cantidad: %s " % (cantn))
            _logger.info("next: %s" % (count))
            idsmlm= product_obj.browse(cr, uid, recod, context=context)
            meli_id=idsmlm.meli_id
            #raise orm.except_orm("Valor",str(idsmlm.meli_price)+'-'+str(meli_id))
            meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
            response = meli.put("/items/"+meli_id, { 'price':idsmlm.meli_price},{'access_token':meli.access_token})
            result_response=response.json()
            if "error" in result_response:
                _logger.info("Error al actualizar en: %s " % (result_response))
                _logger.info("Error al actualizar en: %s " % (meli_id))
            else:           
                _logger.info("meli Actualizado: %s " % (meli_id))
        return True
    
    def update_toml_qty( self, cr, uid, ids, context=None ):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        product_obj = self.pool.get('multi.posting')
        #raise orm.except_orm("Mayor de 0",str(company.qty_pause))
        mlm_ids = product_obj.search(cr, 1 , [('meli_id','!=',False),('proveedor','=',company.prov_toml)], context=context)
        #raise orm.except_orm("Mayor de 0",str(len(mlm_ids)))
        for recod in mlm_ids:
            idsmlm= product_obj.browse(cr, uid, recod, context=context)
            meli_id=idsmlm.meli_id
            cantidad=idsmlm.meli_available_quantity         
            meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
            if cantidad>company.qty_pause: 
                #raise orm.except_orm("Mayor de 0",str(cantidad)+' '+str(meli_id))
                response_status = meli.get("/items/"+meli_id, {'access_token':meli.access_token} )
                rjson = response_status.json()
                statuss=rjson["status"]

                if statuss=='active':
                    #raise orm.except_orm("Mayor de 0 activo",str(cantidad)+' '+str(meli_id)+' '+str(statuss))
                    response = meli.put("/items/"+meli_id, { 'available_quantity':cantidad},{'access_token':meli.access_token})
                    result_response=response.json()
                elif statuss=='paused':
                    #raise orm.except_orm("Mayor de 0 pausado",str(cantidad)+' '+str(meli_id)+' '+str(statuss))
                    response = meli.put("/items/"+meli_id, {'status': 'active','available_quantity':cantidad},{'access_token':meli.access_token})
                    result_response=response.json()
                    product_obj.write(cr,uid,recod,{'meli_status':'active'}, context=context)
                    if "error" in result_response:
                        #_logger.info("Error Tiendas oficiales: %s " % (result_response))
                        _logger.info("Error al actualizar en Tiendas oficiales: %s " % (meli_id))
                    else:           
                        _logger.info("meli Actualizado Tiendas oficiales: %s " % (meli_id))
                    #raise orm.except_orm("Valor 1",str(result_response))
            else:
                #raise orm.except_orm("Menor de 0",str(cantidad)+' '+str(meli_id))
                response = meli.put("/items/"+meli_id, {'status': 'paused'},{'access_token':meli.access_token})
                result_response=response.json()
                product_obj.write(cr,uid,recod,{'meli_status':'paused'}, context=context)
                #raise orm.except_orm("Valor 1",str(result_response))
                if "error" in result_response:
                    _logger.info("Error Tiendas oficiales: %s " % (result_response))
                    _logger.info("Error al actualizar en Tiendas oficiales: %s " % (meli_id))
                else:           
                    _logger.info("meli Actualizado Tiendas oficiales: %s " % (meli_id))
        return True

    def action_asig_categ_toml( self, cr, uid, ids, context=None):
        product_obj  = self.pool.get('product.template')
        tallas_akizi_obj  = self.pool.get('product.line.tallas')
        color_akizi_obj  = self.pool.get('product.lines.color')
        product_toml_obj  = self.pool.get('multi.posting')
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        search_prod_false= product_toml_obj.search(cr, 1 , [('product_id','=',False),('sku','!=',False)], context=context)
        if search_prod_false:
            for rec_up in search_prod_false:
                obj_sku = product_toml_obj.browse(cr, uid,rec_up, context=context)
                ids_product= product_obj.search(cr, 1 , [('default_code','=',obj_sku.sku)], context=context)
                if ids_product: 
                    product_toml_obj.write(cr,uid,rec_up,{'product_id':ids_product[0]}, context=context)
                else:
                    #raise orm.except_orm("Valor",str(company.categ_id_akizi))
                    values_pro={
                        'name':obj_sku.meli_title,
                        'type':'product',
                        'categ_id':company.categ_product.id,
                        'default_code':obj_sku.sku,
                    }
                    new_product_id = product_obj.create(cr, uid,values_pro)
                    product_toml_obj.write(cr,uid,rec_up,{'product_id':new_product_id}, context=context) 
                    
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        categ_false = product_toml_obj.search(cr, 1 , [('category_id_mlm','=',False)], context=context)
        for lin in categ_false:
            #try:
            id_posting = product_toml_obj.browse(cr, uid,lin, context=context)
            response = meli.get("sites/MLM/category_predictor/predict?title="+id_posting.meli_title)
            category_response=response.json()
            #raise orm.except_orm("Valor",str(category_response))
            if not "error" in category_response:
                if category_response["id"]:
                    product_toml_obj.write(cr,uid,lin,{'category_id_mlm':category_response["id"],'name_category_id_mlm':category_response["name"]}, context=context)
            if "variations" in category_response:
                _logger.info("1: %s " % (category_response["variations"]))
                for record in category_response["variations"]:
                    if "type" in record:
                        product_toml_obj.write(cr,uid,lin,{'color_size':True}, context=context)
                        typec=record["type"]
                        if typec=='color' and record["name"]=='Color Primario':
                            for recor in  record["values"]:
                                exist_color= color_akizi_obj.search(cr, 1 , [('id_color','=',recor["id"]),('id_miltipos_toml','=',lin)], context=context)
                                if not exist_color:
                                    if id_posting.colores_proveedor:
                                        colores_erp=id_posting.colores_proveedor.split(',') 
                                        for rec_colo in colores_erp:
                                            #raise orm.except_orm("Valor",str(rec_colo.split('+')[0]))
                                            if recor["name"]==rec_colo.split('+')[0]:
                                                #raise orm.except_orm("valor",str(rec_colo.split(',')))
                                                val_int={
                                                    'id_miltipos_toml':lin,
                                                    'id_color':recor["id"],
                                                    'name':rec_colo,
                                                    'metadata':recor["metadata"]["rgb"],
                                                    'id_type':record["id"],
                                                    'title':record["name"],
                                                    'state':'active',
                                                }
                                                new_color = color_akizi_obj.create(cr, uid,val_int)  
                        if typec=='size':
                            for recsize in record["values"]:
                                exis_size=tallas_akizi_obj.search(cr,uid,[('id_talla','=',recsize["id"]),('id_miltipos_toml','=',lin)],context=context) 
                                if not exis_size:
                                    if id_posting.tallas_proveedor:
                                        tallas_erp=id_posting.tallas_proveedor.split(',')
                                        for rec_tall in tallas_erp:
                                            if recsize["name"]==rec_tall:
                                                values_size={
                                                    'id_miltipos_toml':lin,
                                                    'name':recsize["name"],
                                                    'id_talla':recsize["id"],
                                                    'title':record["name"],
                                                    'id_type':record["id"],
                                                    'state':'active',
                                                }
                                                new_size=tallas_akizi_obj.create(cr, uid,values_size) 
            #except Exception, e:
                #raise orm.except_orm("Error",str(e))
        return True

    def action_update_erp_variation_toml( self, cr, uid, ids, context=None):
        product_toml_obj  = self.pool.get('multi.posting')
        tallas_akizi_obj  = self.pool.get('product.line.tallas')
        colores_akizi_obj  = self.pool.get('product.lines.color')
        num_variation = product_toml_obj.search(cr, 1 , [('color_size','=',True)], context=context)
        #wizard = self.browse(cr, uid, ids[0], context=context)
        #self.write(cr, uid, wizard.id,{'date_size':time.strftime('%Y-%m-%d')},context=context)
        for rec in num_variation:
            id_posting = product_toml_obj.browse(cr, uid,rec, context=context)
            if id_posting.colores_proveedor:
                lines_prove=id_posting.colores_proveedor.split(',')
                #for li_pro in lines_prove: 
                for rec_name in id_posting.lines_color:
                    if rec_name.name in lines_prove:
                        colores_akizi_obj.write(cr,uid,rec_name.id,{'state':'active'}, context=context)
                    if rec_name.name not in lines_prove:
                        colores_akizi_obj.write(cr,uid,rec_name.id,{'state':'inactive'}, context=context)
            if not id_posting.colores_proveedor:
                for rec_name in id_posting.lines_color:
                    colores_akizi_obj.write(cr,uid,rec_name.id,{'state':'inactive'}, context=context)
            if id_posting.tallas_proveedor:
                tallas_prove=id_posting.tallas_proveedor.split(',')
                for tall_name in id_posting.lines_tallas:
                    if tall_name.name in tallas_prove:
                        tallas_akizi_obj.write(cr,uid,tall_name.id,{'state':'active'}, context=context)
                    if tall_name.name not in tallas_prove:
                        tallas_akizi_obj.write(cr,uid,tall_name.id,{'state':'inactive'}, context=context)
            if not id_posting.tallas_proveedor:
                for tall_name in id_posting.lines_tallas:
                    tallas_akizi_obj.write(cr,uid,tall_name.id,{'state':'inactive'}, context=context)   
        return True
    
    def posting_query_questions_toml( self, cr, uid, id, context=None ):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        posting_obj = self.pool.get('mercadolibre.posting')
        #posting = posting_obj.browse(cr, uid, id)     
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        company.write({'date_questions_toml': time.strftime('%Y-%m-%d %H:%M:%S')})

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN )
        #posting_query = str("/users/"+str(company.mercadolibre_seller_id_mrcdzo)+"/items/search?access_token=")+str(meli.access_token)
        #response = meli.get("/my/received_questions/access_token="+str(meli.access_token))
        response = meli.get("/my/received_questions/search?access_token="+str(meli.access_token)+str("&sort_fields=date_created&sort_types=DESC"))
        questions_json = response.json()
        #raise orm.except_orm("Valor",str(questions_json))
        _logger.info("todas::::::::::::::::::::::::::::::: %s " % (questions_json))
        questions_obj = self.pool.get('mercadolibre.questions')
        if 'questions' in questions_json:
            for rec_c in questions_json['questions']:
                for ques in rec_c:
                    _logger.info("Pregunta::::::::::::::::::::::::::::::: %s " % (rec_c)) 
                    posting_id= posting_obj.search(cr, 1 , [('meli_id','=',rec_c['item_id'])], context=context)
                    if posting_id:
                        meli_idss=posting_id[0] 
                    else:
                        response_item = meli.get("/items/"+rec_c['item_id'], {'access_token':meli.access_token} )
                        rjson = response_item.json()
                        values={
                            'meli_id':rec_c['item_id'],
                            'name':rjson["title"],
                            'meli_status':rjson["status"],
                            'meli_price':rjson["price"],
                            'meli_permalink':rjson["permalink"]
                        }
                        meli_idss=posting_obj.create(cr,uid,values,context=context)
                    question_answer = rec_c['answer']
                    #raise orm.except_orm("Valor",str(rec_c['answer']))
                    question_fields = {
                        'posting_id': meli_idss,
                        'question_id': rec_c['id'],
                        'date_created': rec_c['date_created'],
                        'item_id': rec_c['item_id'],
                        'seller_id': rec_c['seller_id'],
                        'text': rec_c['text'],
                        'status': rec_c['status'],
                    }
                    if question_answer:
                        question_fields['answer_text'] = question_answer['text']
                        question_fields['answer_status'] = question_answer['status']
                        question_fields['answer_date_created'] = question_answer['date_created']
                    question_fetch_ids = questions_obj.search(cr,uid,[('question_id','=',question_fields['question_id'])])
                    if not question_fetch_ids:
                        question_fetch_ids = questions_obj.create(cr,uid,( question_fields ))
                    else:
                        questions_obj.write(cr,uid, question_fetch_ids[0], ( question_fields ) )    
        return True
    
    def update_sku_toml( self, cr, uid, ids, context=None ):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        product_obj = self.pool.get('mercadolibre.posting')
        mlm_ids = product_obj.search(cr, 1 , [('meli_id','!=',False),('sku','!=',False)], context=context)
        cantn=len(mlm_ids)
        count=0
        for recod in mlm_ids:
            count+=1
            _logger.info("Cantidad: %s " % (cantn))
            _logger.info("next: %s" % (count))
            idsmlm= product_obj.browse(cr, uid, recod, context=context)
            meli_id=idsmlm.meli_id
            #raise orm.except_orm("Valor",str(idsmlm.meli_price)+'-'+str(meli_id))
            meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
            response = meli.put("/items/"+meli_id, { 'seller_custom_field':idsmlm.sku},{'access_token':meli.access_token})
            result_response=response.json()
            if "error" in result_response:
                _logger.info("Error al actualizar en: %s " % (result_response))
                _logger.info("Error al actualizar en: %s " % (meli_id))
            else:           
                _logger.info("meli Actualizado: %s " % (meli_id))
                _logger.info("meli Actualizado: %s " % (idsmlm.sku))
        return True    


res_company()