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
import requests
import melisdk
import base64
import mimetypes
from meli_oerp_config import *
from melisdk.meli import Meli

from PIL import Image
from urllib import urlopen
from StringIO import StringIO

class product_template(osv.osv):
    _inherit = "product.template"

    _columns = {
    'lines_multiposting':fields.one2many('multi.posting','product_id','Multi Publicacion'),
    'size':fields.char('Size', size=64),
    'price_toml':fields.related('lines_multiposting','meli_price',type='char',relation='multi.posting',string='Precio TOML')
    }
    _defaults = {

    }
product_template()

class multi_posting(osv.osv):
    _name = 'multi.posting'
    _description = 'Multiples Productos'

    def product_meli_get_product( self, cr, uid, ids, context=None ):
        category_obj = self.pool.get('mercadolibre.category')
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        product_obj = self.pool.get('multi.posting')
        product = product_obj.browse(cr, uid, ids[0])

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        response = meli.get("/items/"+product.meli_id, {'access_token':meli.access_token})
        info=response.json()
        # raise osv.except_osv("Val",str(info))
        response_descri=meli.get("/items/"+product.meli_id+"/description", {'access_token':meli.access_token})
        descrip=response_descri.json()      

        if "error" in info:            
            if (info["error"]):
                raise orm.except_orm("Error",str(info["message"]))
                _logger.error( info["error"])
            return {}
        if not product.meli_description:
            self.write(cr, uid, ids, {'meli_description':descrip["text"]}, context=None)
        meli_title=info["title"]
        meli_listing_type=info["listing_type_id"]
        meli_buying_mode=info["buying_mode"]
        meli_price=info["price"]
        meli_currency=info["currency_id"]
        meli_condition=info["condition"]
        meli_available_quantity=info["available_quantity"]
        meli_warranty=info["warranty"]
        meli_images=info["pictures"] 
        count=0
        for recod in meli_images:
            count+=1
        image1=False
        image2=False
        image3=False
        image4=False
        image5=False
        image6=False
        if meli_images:
            if count>0:
                image1=meli_images[0]["url"]
                url=meli_images[0]["url"]
            if count>1:
                image2=meli_images[1]["url"]
            if count>2:
                image3=meli_images[2]["url"]
            if count>3:
                image4=meli_images[3]["url"]
            if count>4:
                image5=meli_images[4]["url"]
            if count>5:
                image6=meli_images[5]["url"]
        self.write(cr, uid, ids, { 
            'meli_title' :meli_title or False,
            'category_id_mlm':info["category_id"],
            'meli_listing_type':meli_listing_type or False, 
            'meli_buying_mode':meli_buying_mode or False,
            'meli_price':meli_price or False,
            'meli_currency':meli_currency or False,
            'meli_condition':meli_condition or False,
            'meli_available_quantity':meli_available_quantity or False,
            'meli_warranty':meli_warranty or False,
            'meli_imagen_logo':image1 or False,
            'meli_imagen_link':image2 or False,
            'meli_multi_imagen_id':image3 or False,
            'imagen_cuatro':image4 or False,
            'imagen_cinco':image5 or False,
            'imagen_seis':image6 or False,
            'meli_status':info["status"],
            "sku":info["seller_custom_field"],
            #"official_store_id":info["official_store_id"],
            }, context=None)
        #print "product_meli_get_product: " + response.content
        return {}

    def product_get_meli_loginstate( self, cr, uid, ids, field_name, attributes, context=None ):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        #company = user_obj.company_id

        #CLIENT_ID = company.mercadolibre_client_id
        #CLIENT_SECRET = company.mercadolibre_secret_key
        #ACCESS_TOKEN = company.mercadolibre_access_token
        #REFRESH_TOKEN = company.mercadolibre_refresh_token

        #meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        ML_state = False
        #if ACCESS_TOKEN=='':
            #ML_state = True
        #else:
            #response = meli.get("/users/me/", {'access_token':meli.access_token} )
            #rjson = response.json()
            #if 'error' in rjson:
                #if rjson['message']=='invalid_token' or rjson['message']=='expired_token':
                    #ACCESS_TOKEN = ''
                    #REFRESH_TOKEN = ''
                    #company.write({'mercadolibre_access_token': ACCESS_TOKEN, 'mercadolibre_refresh_token': REFRESH_TOKEN, 'mercadolibre_code': '' } )
                    #ML_state = True
        res = {}        
        for product in self.browse(cr,uid,ids):
            res[product.id] = ML_state
        return res

    def product_get_permalink( self, cr, uid, ids, field_name, attributes, context=None ):
        ML_permalink = ''

        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id

        product_obj = self.pool.get('multi.posting')
        product = product_obj.browse(cr, uid, ids[0])        

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token


        ML_permalink = ""
        if ACCESS_TOKEN=='':
            ML_permalink = ""
        else:
            meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
            if product.meli_id:
                response = meli.get("/items/"+product.meli_id, {'access_token':meli.access_token} )
                rjson = response.json()
                if "permalink" in rjson:
                    ML_permalink = rjson["permalink"]
                if "error" in rjson:
                    ML_permalink = ""                    
                #if "sub_status" in rjson:
                    #if len(rjson["sub_status"]) and rjson["sub_status"][0]=='deleted':
                    #    product.write({ 'meli_id': '' })

        res = {}        
        for product in self.browse(cr,uid,ids):
            res[product.id] = ML_permalink
        return res

    def product_get_meli_status_multi( self, cr, uid, ids,field_name, arg, context=None):        
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        warningobj = self.pool.get('warning')
        product_obj = self.pool.get('multi.posting')
        product = product_obj.browse(cr, uid, ids[0])
        wizard= self.browse(cr,uid,ids[0],context=context)
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        ML_status = "unknown"
        if ACCESS_TOKEN==False:
            ML_status = "unknown"
        else:
            meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
            if wizard.meli_id:
                response = meli.get("/items/"+wizard.meli_id, {'access_token':meli.access_token} )
                rjson = response.json()
                ML_status = rjson["status"]
                if "error" in rjson:
                    ML_status = rjson["error"]
                if "sub_status" in rjson:
                    if len(rjson["sub_status"]) and rjson["sub_status"][0]=='deleted':
                        wizard.write({ 'meli_status': 'deleted' })

        res = {}  
        for wizard in self.browse(cr,uid,ids):
            res[wizard.id] = ML_status
        return res

    def get_meli_status(self, cr, uid, ids, field_name, arg, context=None):
        records=self.browse(cr,uid,ids,)
        resu={}
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        warningobj = self.pool.get('warning')

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        for r in records:
            ML_status = "unknown"
            if ACCESS_TOKEN==False:
                ML_status = "unknown"
            else:
                meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
                if r.meli_id:
                    response = meli.get("/items/"+r.meli_id, {'access_token':meli.access_token} )
                    rjson = response.json()
                    ML_status = rjson["status"]
                    if "error" in rjson:
                        ML_status = rjson["error"]
                    if "sub_status" in rjson:
                        if len(rjson["sub_status"]) and rjson["sub_status"][0]=='deleted':
                            r.write({'sub_status': 'Eliminado de MLM'})
            resu[r.id]=ML_status
        return resu
        
    def product_meli_upload_image(self, cr, uid, ids, context=None):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        product_obj = self.pool.get('multi.posting')
        product = product_obj.browse(cr, uid, ids[0])
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        if product.image==None:
            return { 'status': 'error', 'message': 'no image to upload' }
        # print "product_meli_upload_image"
        #print "product_meli_upload_image: " + response.content
        imagebin = base64.b64decode(product.image)
        imageb64 = product.image
#       print "data:image/png;base64,"+imageb64
#       files = [ ('images', ('image_medium', imagebin, "image/png")) ]
        files = { 'file': ('image.png', imagebin, "image/png"), }
        #print  files
        response = meli.upload("/pictures", files, { 'access_token': meli.access_token } )
       # print response.content
        rjson = response.json()
        if ("error" in rjson):
            raise osv.except_osv( _('MELI WARNING'), _('Could not load the image into MELI! Error: %s, Menssage: %s, Status: %s') % ( rjson["error"], rjson["message"],rjson["status"],))
            return { 'status': 'error', 'message': 'not uploaded'}
        _logger.info( rjson )
        if ("id" in rjson):
            #guardar id
            product.write( { "meli_imagen_id": rjson["id"], "meli_imagen_link": rjson["variations"][0]["url"] } )
            #asociar imagen a producto
            if product.meli_id:
                response = meli.post("/items/"+product.meli_id+"/pictures", { 'id': rjson["id"] }, { 'access_token': meli.access_token } )
            else:
                return { 'status': 'warning', 'message': 'uploaded but not assigned'}        
        return { 'status': 'success', 'message': 'uploaded and assigned' }

    def product_meli_status_pause( self, cr, uid, ids, context=None ):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        product_obj = self.pool.get('multi.posting')
        product = product_obj.browse(cr, uid, ids[0])

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        response = meli.put("/items/"+product.meli_id, { 'status': 'paused' }, {'access_token':meli.access_token})
        #print "product_meli_status_pause: " + response.content
        product.write({ 'meli_status': 'paused' })
        return {}

    def product_meli_status_active( self, cr, uid, ids, context=None ):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        product_obj = self.pool.get('multi.posting')
        product = product_obj.browse(cr, uid, ids[0])
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        response = meli.put("/items/"+product.meli_id, { 'status': 'active' }, {'access_token':meli.access_token})
        #print "product_meli_status_active: " + response.content
        product.write({ 'meli_status': 'active' })
        return {}

    def product_meli_delete( self, cr, uid, ids, context=None):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        product_obj = self.pool.get('multi.posting')
        product = product_obj.browse(cr, uid, ids[0])
        if product.meli_status!='closed':
            self.product_meli_status_close( cr, uid, ids, context )
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        response = meli.put("/items/"+product.meli_id, { 'deleted': 'true' }, {'access_token':meli.access_token})
        #print "product_meli_delete: " + response.content
        rjson = response.json()
        ML_status = rjson["status"]
        if "error" in rjson:
            ML_status = rjson["error"]
        if "sub_status" in rjson:
            if len(rjson["sub_status"]) and rjson["sub_status"][0]=='deleted':
                product.write({ 'sub_status': 'Eliminado de MLM', 'meli_status': 'close' })
        return {}

    def product_meli_status_close( self, cr, uid, ids, context=None ):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        product_obj = self.pool.get('multi.posting')
        product = product_obj.browse(cr, uid, ids[0])

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        response = meli.put("/items/"+product.meli_id, { 'status': 'closed' }, {'access_token':meli.access_token})
        #print "product_meli_status_close: " + response.content
        product.write({ 'meli_status': 'closed' })
        return {}

    _columns = {
        'product_id':fields.many2one('product.template','Producto'),
        'name':fields.related('meli_title',type='char',relation='multi.posting',string='Producto'),
        ##
        'meli_post_required': fields.boolean(string='This product is publishable in MercadoLibre'),
        'meli_id': fields.char( string='Id the item assigned by Meli', size=256),
        'meli_permalink': fields.function(product_get_permalink, method=True, type='char',  size=256, string='PermaLink in MercadoLibre' ),
        'meli_title': fields.char(string='Product name in MercadoLibre',size=256), 
        'meli_description': fields.html(string='Description'),
        'meli_description_banner_id': fields.many2one("mercadolibre.banner","Banner"),
        'meli_listing_type': fields.selection([("free","Libre"),("bronze","Bronze"),("silver","Silver"),("gold","Gold"),("gold_premium","Gold Premium"),("gold_special","Gold Special"),("gold_pro","Gold Premium MSI")], string='Type of list'),
        'meli_buying_mode': fields.selection( [("buy_it_now","Buy Now"),("classified","Classified")], string='Purchase method'),
        'meli_price': fields.char(string='Sale price', size=128),
        'meli_currency': fields.selection([("MXN","Peso Mexicanos (MXN)"),("USD","Dolares (USD)")],string='Currency'),
        'meli_condition': fields.selection([ ("new", "New"), ("used", "Used"), ("not_specified","Not specified")],'Product Condition'),
        'meli_available_quantity': fields.integer(string='Quantity available'),
        'meli_warranty': fields.char(string='Warranty', size=256),
        'meli_imagen_logo': fields.char(string='Image Logo', size=256),
        'meli_imagen_id': fields.char(string='Image Id', size=256),
        'meli_imagen_link': fields.char(string='Image Link', size=256),
        'meli_multi_imagen_id': fields.char(string='Multi Image Ids', size=512),
        'meli_video': fields.char( string='Video (id de youtube)', size=256),
        'meli_state': fields.function(product_get_meli_loginstate, method=True, type='boolean', string="Login required", store=False ),
        #'meli_status': fields.function(get_meli_status, method=True, type='char', size=128, string="State Product in MLM"),
        'meli_status': fields.char('Estado MLM',size=80),
        #'meli_category': fields.many2one("mercadolibre.category","Categories of MercadoLibre"),
        #'meli_category_dos': fields.many2one("sub.category","Categories of MercadoLibre"),
        #'meli_category_tres': fields.many2one("subsub.category","Categories of MercadoLibre"),
        #'meli_category_cuatro': fields.many2one("subsubsub.category","Categories of MercadoLibre"),
        #'meli_category_quinto': fields.many2one("subsubsubsub.category","Categories of MercadoLibre"),
        #'meli_category_seis': fields.many2one("subquinta.category","Categories of MercadoLibre"),
        'category_id_mlm':fields.char('Categoria MLM',size=64),
        'name_category_id_mlm':fields.char('Nombre Categoria MLM',size=64),
        'permite_publicar':fields.char('Permite Publicar',size=64),
        'tienda':fields.char("Tienda",size=30),
        'image': fields.binary("imagen"),
        'sub_status':fields.text("SubEstado de MLM",size=200),
        #'id_color':fields.many2one('mercadolibre.color','Color'),
        #'id_talla':fields.many2one('mercadolibre.tallas','Talla'),
        'id_model':fields.integer('id'),
        #'model_name':fields.char('Modelo',size=30),
        'campo_name':fields.char('Campo',size=30),
        #'lines_tallas':fields.one2many('product.tallas','id_miltipos','Talla'),
        'attributes':fields.char('Requiere Talla y color',size=30),
        'color_size': fields.boolean('Agregar Talla y color'),
        #'sku_product':fields.related('product_id','default_code',type='char',relation='product.template',string='Sku'),
        'id_site':fields.char('Id site',size=30),
        'colores_proveedor':fields.char('Colores proveedor',size=200),
        'tallas_proveedor':fields.char('Tallas proveedor',size=200),
        'lines_tallas':fields.one2many('product.line.tallas','id_miltipos_toml','Talla'),
        'lines_color':fields.one2many('product.lines.color','id_miltipos_toml','Color'),
        'proveedor':fields.char("proveedor",size=64),
        'sku':fields.char("SKU",size=64),
        'imagen_cuatro': fields.char(string='Image 4', size=200),
        'imagen_cinco': fields.char(string='Image 5', size=200),
        'imagen_seis': fields.char(string='Image 6', size=200),
        'official_store_id':fields.many2one("official.store", 'Tienda Oficial'),

    }

class product_tallas(osv.osv):
    _name = 'product.tallas'
    _description = 'Description'

    _columns = {
        'name':fields.char('Talla', size=64),
        'id_miltipos':fields.many2one('multi.posting','id posting'),
        'id_talla':fields.many2one('mercadolibre.tallas','Talla'),
    }

class product_tallas_toml(osv.osv):
    _name = 'product.line.tallas'
    _description = 'Description'

    _columns = {
        'id_miltipos_toml':fields.many2one('multi.posting','id posting'),
        'id_talla':fields.char('Id Talla',size=30),
        'name':fields.char('Talla', size=30),
        'id_type':fields.char('ID Typo',size=30),
        'title':fields.char("Titulo",size=30),
        'state': fields.selection([('active', 'Activo'),('inactive','Inactivo')], 'Status',readonly=True),
    }

class product_lines_color_toml(osv.osv):
    _name = 'product.lines.color'
    _description = 'Description'

    _columns = {
        'id_miltipos_toml':fields.many2one('multi.posting','id posting'),
        'id_color':fields.char('Id Color',size=30),
        'name':fields.char('Color', size=30),
        'metadata':fields.char("Metadata",size=30),
        'id_type':fields.char('ID Typo',size=30),
        'title':fields.char("Titulo",size=30),
        'state': fields.selection([('active', 'Activo'),('inactive','Inactivo')], 'Status',readonly=True),
    }




