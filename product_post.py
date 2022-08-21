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
import json
from datetime import datetime
from meli_oerp_config import *
from warning import warning
import melisdk
from melisdk.meli import Meli
import logging
_logger = logging.getLogger(__name__)
import requests
import base64
import mimetypes
import time

class product_post(osv.osv_memory):
    _name = "mercadolibre.product.post"
    _description = "Wizard of Product Posting in MercadoLibre"

    _columns = {
	    'type': fields.selection([('post','Registered'),('put','Edited'),('delete','Delete')], string='Type of transaction'),
	    'posting_date': fields.date('Date posting'),
        'qty_pause':fields.integer('Cant min para pausar'),
        'type_action': fields.selection([('publicar','Publicar'),('republicar','Republicar'),
            ('category','Asignar Categoria'),('update_price','Actualizar Precio'),('update_qty','Actualizar Stock')], string='seleccion una opcion',required=True),
    }
    _defaults = {
        "qty_pause":5,
    }


    def pretty_json( self, cr, uid, ids, data, indent=0, context=None ):
        return json.dumps( data, sort_keys=False, indent=4 )

    def product_post(self, cr, uid, ids, context=None):
        tallas_toml_obj  = self.pool.get('product.line.tallas')
        colores_toml_obj  = self.pool.get('product.lines.color')

        product_ids = context['active_ids']
        product_product_obj = self.pool.get('product.product')
        product_obj = self.pool.get('multi.posting')
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        warningobj = self.pool.get('warning')
    
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        if ACCESS_TOKEN==False:
            meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET)
            url_login_meli = meli.auth_url(redirect_URI=REDIRECT_URI)
            return {
	            "type": "ir.actions.act_url",
	            "url": url_login_meli,
	            "target": "new",
            }
        for product_id in product_ids:
            product = product_obj.browse(cr,uid,product_id)

            product_product_id=product_product_obj.search(cr, 1 , [('product_tmpl_id','=',product.product_id.id)], context=context)
            if product_product_id: 
                id_product_pro=product_product_id[0]
            if (product.meli_id):
                response = meli.get("/items/%s" % product.meli_id, {'access_token':meli.access_token})
            default_code=product.product_id.default_code
            if default_code==False: 
                raise orm.except_orm("El producto no contiene un SKU",str(product.product_id.name))  
            if product.meli_imagen_logo:
                upluadd=[{'source':product.meli_imagen_logo}]
            lista=False
            id_colorproduct=[]
            lines_color_toml=colores_toml_obj.search(cr, 1 , [('id_miltipos_toml','=',product.id),('state','=','active')], context=context)
            for rc_color in lines_color_toml:
                color_obj = colores_toml_obj.browse(cr, uid,rc_color, context=context)
                id_colorproduct.append({'value_name':color_obj.name,'value_id':color_obj.id_color,
                    'id':color_obj.id_type,'name':color_obj.title})

            tallaproduct={'value':{}}
            lines_tallas_toml=tallas_toml_obj.search(cr, 1 , [('id_miltipos_toml','=',product.id),('state','=','active')], context=context)
            for recorrd in lines_tallas_toml:
                tallas_obj = tallas_toml_obj.browse(cr, uid,recorrd, context=context)
                tallaproduct['value'][recorrd]= {'value_name':tallas_obj.name,'value_id':tallas_obj.id_talla,'id':tallas_obj.id_type,'name':tallas_obj.title}
                lista=tallaproduct['value'].values()
                for k in id_colorproduct:
                    lista.append(k)   
            body = {
                "title":product.meli_title,
                "description":product.meli_description,	
                "category_id":product.category_id_mlm,
                "listing_type_id":product.meli_listing_type,
                "buying_mode":product.meli_buying_mode,
                "price":product.meli_price,
                "currency_id":product.meli_currency,
                "condition":product.meli_condition,
                "available_quantity":product.meli_available_quantity,
                "warranty":product.meli_warranty,
                "pictures":upluadd,
                "video_id": product.meli_video  or '',
                "seller_custom_field":product.sku,
                #"official_store_id":company.official_store_id,
                "official_store_id":product.official_store_id.official_store_id,
                "shipping":{"mode":"me2","local_pick_up":True},
            }
            if product.meli_id:
                body = {
                	"title":product.meli_title,
                    #"buying_mode":product.meli_buying_mode,
                    "price":product.meli_price,
                    "currency_id":product.meli_currency,
                    "condition":product.meli_condition,
                    "available_quantity":product.meli_available_quantity,
                    "warranty":product.meli_warranty,
                    "pictures":upluadd,
                    "video_id": product.meli_video or '',
                    "seller_custom_field":product.sku,
                    #"official_store_id":company.official_store_id,
                    "official_store_id":product.official_store_id.official_store_id,
                    "shipping":{"mode":"me2","local_pick_up":True}
                }
            if product.meli_imagen_link:
                body["pictures"]+= [{'source':product.meli_imagen_link}]

            if product.meli_multi_imagen_id:
                body["pictures"]+= [{'source':product.meli_multi_imagen_id}]
                
                
            if product.imagen_cuatro:
                body["pictures"]+= [{'source':product.imagen_cuatro}]
            if product.imagen_cinco:
                body["pictures"]+= [{'source':product.imagen_cinco}]
            if product.imagen_seis:
                body["pictures"]+= [{'source':product.imagen_seis}]
            if product.color_size==True :
                body["variations"]=[{"price":product.meli_price,"attribute_combinations":lista,"picture_ids":[product.meli_imagen_logo],
                    'available_quantity':product.meli_available_quantity}]

            if product.meli_description==False:
                return warningobj.info(cr, uid, title='MELI WARNING', message="Debe completar el campo 'description' (en html)", message_html="")
          
            if product.meli_id:
                response = meli.put("/items/"+product.meli_id, body, {'access_token':meli.access_token})
            else:
                response = meli.post("/items", body, {'access_token':meli.access_token})
                rjson = response.json()

                if "error" in rjson:
                    product.write({'sub_status': rjson})
                if "id" in rjson:
                    product.write( { 'meli_id': rjson["id"],'meli_permalink':rjson['permalink'],'meli_status':'active','sku':default_code})
                    #product.write( { 'meli_id': rjson["id"],'sub_status':False} )
                    posting_id = self.pool.get('mercadolibre.posting').search(cr,uid,[('meli_id','=',rjson['id'])])
                    if not posting_id:
                        posting_id = self.pool.get('mercadolibre.posting').create(cr,uid,({
                            'meli_id':rjson['id'],
                            'posting_date':rjson['date_created'],
                            'name':rjson['title'],
                            'product_id':id_product_pro,
                            'meli_permalink':rjson['permalink'],
                            'meli_status':rjson['status'],
                            'meli_price':rjson['price'],
                            'sku':rjson['seller_custom_field'],
                            'product_variant':product.id,
                            'posting_date':time.strftime('%Y-%m-%d')}))
        return {}


    def product_republica_post_toml(self, cr, uid, ids, context=None):
        tallas_toml_obj  = self.pool.get('product.line.tallas')
        colores_toml_obj  = self.pool.get('product.lines.color')

        product_ids = context['active_ids']
        product_product_obj = self.pool.get('product.product')
        product_obj = self.pool.get('multi.posting')
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        warningobj = self.pool.get('warning')
    
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        if ACCESS_TOKEN==False:
            meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET)
            url_login_meli = meli.auth_url(redirect_URI=REDIRECT_URI)
            return {
                "type": "ir.actions.act_url",
                "url": url_login_meli,
                "target": "new",
            }
        for product_id in product_ids:
            product = product_obj.browse(cr,uid,product_id)

            product_product_id=product_product_obj.search(cr, 1 , [('product_tmpl_id','=',product.product_id.id)], context=context)
            if product_product_id: 
                id_product_pro=product_product_id[0]
            if (product.meli_id):
                response = meli.get("/items/%s" % product.meli_id, {'access_token':meli.access_token})
            default_code=product.product_id.default_code
            if default_code==False: 
                raise orm.except_orm("El producto no contiene un SKU",str(product.product_id.name)) 
            if product.meli_imagen_logo:
                upluadd=[{'source':product.meli_imagen_logo}]

            lista=False
            id_colorproduct=[]
            lines_color_toml=colores_toml_obj.search(cr, 1 , [('id_miltipos_toml','=',product.id),('state','=','active')], context=context)
            for rc_color in lines_color_toml:
                color_obj = colores_toml_obj.browse(cr, uid,rc_color, context=context)
                id_colorproduct.append({'value_name':color_obj.name,'value_id':color_obj.id_color,
                    'id':color_obj.id_type,'name':color_obj.title})

            tallaproduct={'value':{}}
            lines_tallas_toml=tallas_toml_obj.search(cr, 1 , [('id_miltipos_toml','=',product.id),('state','=','active')], context=context)
            for recorrd in lines_tallas_toml:
                tallas_obj = tallas_toml_obj.browse(cr, uid,recorrd, context=context)
                tallaproduct['value'][recorrd]= {'value_name':tallas_obj.name,'value_id':tallas_obj.id_talla,'id':tallas_obj.id_type,'name':tallas_obj.title}
                lista=tallaproduct['value'].values()
                for k in id_colorproduct:
                    lista.append(k)
            product.write({'sub_status':'','meli_id':''})   
            body = {
                "title":product.meli_title,
                "description":product.meli_description, 
                "category_id":product.category_id_mlm,
                "listing_type_id":product.meli_listing_type,
                "buying_mode":product.meli_buying_mode,
                "price":product.meli_price,
                "currency_id":product.meli_currency,
                "condition":product.meli_condition,
                "available_quantity":product.meli_available_quantity,
                "warranty":product.meli_warranty,
                "pictures":upluadd,
                "video_id": product.meli_video  or '',
                "seller_custom_field":default_code,
                #"official_store_id":company.official_store_id,
                "official_store_id":product.official_store_id.official_store_id,
                "shipping":{"mode":"me2","local_pick_up":True},
            }

            if product.meli_imagen_link:
                body["pictures"]+= [{'source':product.meli_imagen_link}]
            if product.meli_multi_imagen_id:
                body["pictures"]+= [{'source':product.meli_multi_imagen_id}]
            if product.imagen_cuatro:
                body["pictures"]+= [{'source':product.imagen_cuatro}]
            if product.imagen_cinco:
                body["pictures"]+= [{'source':product.imagen_cinco}]
            if product.imagen_seis:
                body["pictures"]+= [{'source':product.imagen_seis}]

            if product.color_size==True :
                body["variations"]=[{"price":product.meli_price,"attribute_combinations":lista,"picture_ids":[product.meli_imagen_logo],
                    'available_quantity':product.meli_available_quantity}]

            if product.meli_description==False:
                return warningobj.info(cr, uid, title='MELI WARNING', message="Debe completar el campo 'description' (en html)", message_html="")
          
            #if product.meli_id:
                #response = meli.put("/items/"+product.meli_id, body, {'access_token':meli.access_token})
            #else:
            if product.meli_status!='active':
                response = meli.post("/items", body, {'access_token':meli.access_token})
                rjson = response.json()

                if "error" in rjson:
                    product.write({'sub_status': rjson})
                if "id" in rjson:
                    product.write( { 'meli_id': rjson["id"],'meli_permalink':rjson['permalink'],'meli_status':'active','sku':default_code})
                    #product.write( { 'meli_id': rjson["id"],'sub_status':False} )
                    posting_id = self.pool.get('mercadolibre.posting').search(cr,uid,[('meli_id','=',rjson['id'])])
                    if not posting_id:
                        posting_id = self.pool.get('mercadolibre.posting').create(cr,uid,({
                            'meli_id':rjson['id'],
                            'posting_date':rjson['date_created'],
                            'name':rjson['title'],
                            'product_id':id_product_pro,
                            'meli_permalink':rjson['permalink'],
                            'meli_status':rjson['status'],
                            'meli_price':rjson['price'],
                            'sku':rjson['seller_custom_field'],
                            'product_variant':product.id,
                            'posting_date':time.strftime('%Y-%m-%d')}))
        return {}

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
        #search_prod_false= product_toml_obj.search(cr, 1 , [('product_id','=',False),('sku','!=',False)], context=context)
        search_prod_false=context.get('active_ids')
        if search_prod_false:
            for rec_up in search_prod_false:
                obj_sku = product_toml_obj.browse(cr, uid,rec_up, context=context)
                if not obj_sku.sku:
                    raise osv.except_osv("Warning","Indica el sku de producto "+obj_sku.meli_title) 
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
            try:
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
            except Exception, e:
                raise orm.except_orm("Error",str(e))
        return True

    def update_toml_qty( self, cr, uid, ids, context=None ):
        wizard = self.browse(cr, uid, ids[0], context=context)
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        product_obj = self.pool.get('multi.posting')
        #raise orm.except_orm("Mayor de 0",str(company.qty_pause))
        #mlm_ids = product_obj.search(cr, 1 , [('meli_id','!=',False),('proveedor','=',company.prov_toml)], context=context)
        mlm_ids=context.get('active_ids')
        #raise orm.except_orm("Mayor de 0",str(len(mlm_ids)))
        for recod in mlm_ids:
            idsmlm= product_obj.browse(cr, uid, recod, context=context)
            meli_id=idsmlm.meli_id
            if not meli_id:
                raise osv.except_osv("Error","Al parecer hay un producto que no se a publicado "+idsmlm.meli_title) 
            cantidad=idsmlm.meli_available_quantity         
            meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
            if cantidad>wizard.qty_pause: 
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

    def update_price_toml( self, cr, uid, ids, context=None ):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        product_obj = self.pool.get('multi.posting')
        #mlm_ids = product_obj.search(cr, 1 , [('meli_id','!=',False),('id_site','=','18')], context=context)
        mlm_ids=context.get('active_ids')
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

