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
import logging
import meli_oerp_config
import melisdk
from melisdk.meli import Meli
import json
import logging
_logger = logging.getLogger(__name__)

import posting
#https://api.mercadolibre.com/questions/search?item_id=MLA508223205

class mercadolibre_orders(osv.osv):
    _name = "mercadolibre.orders"
    _description = "Orders in MercadoLibre"

    def billing_info( self, cr, uid, billing_json, context=None ):
        billinginfo = ''

        if 'doc_type' in billing_json:
            if billing_json['doc_type']:
                billinginfo+= billing_json['doc_type']

        if 'doc_number' in billing_json:
            if billing_json['doc_number']:
                billinginfo+= billing_json['doc_number']

        return billinginfo

    def full_phone( self, cr, uid, phone_json, context=None ):
        full_phone = ''

        if 'area_code' in phone_json:
            if phone_json['area_code']:
                full_phone+= phone_json['area_code']

        if 'number' in phone_json:
            if phone_json['number']:
                full_phone+= phone_json['number']

        if 'extension' in phone_json:
            if phone_json['extension']:
                full_phone+= phone_json['extension']

        return full_phone

    def pretty_json( self, cr, uid, ids, data, indent=0, context=None ):
        return json.dumps( data, sort_keys=False, indent=4 )

    def orders_update_order_json( self, cr, uid, data, context=None ):
        oid = data["id"]
        order_json = data["order_json"]
        #_logger.info("orders_update_order_json > data[id]: " + oid + " order_json:" + order_json )
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        order_obj = self.pool.get('mercadolibre.orders')
        buyers_obj = self.pool.get('mercadolibre.buyers')
        posting_obj = self.pool.get('mercadolibre.posting')
        order_items_obj = self.pool.get('mercadolibre.order_items')
        payments_obj = self.pool.get('mercadolibre.payments')
        order = None
        # if id is defined, we are updating existing one
        if (oid):
            order = order_obj.browse(cr, uid, oid )
        else:
        #we search for existing order with same order_id => "id"
            order_s = order_obj.search(cr,uid, [ ('order_id','=',order_json['id']) ] )
            if (order_s):
                order = order_obj.browse(cr, uid, order_s[0])        
        #process base order fields
        order_fields = {
            'order_id': '%i' % (order_json["id"]),
            'status': order_json["status"],
            'status_detail': order_json["status_detail"] or '' ,
            'total_amount': order_json["total_amount"],
            'currency_id': order_json["currency_id"],
            'date_created': order_json["date_created"] or '',
            'date_closed': order_json["date_closed"] or '',
            
        }
        #_logger.info("direccion de envio=================xxxxxxxxxxxxxxxxxxxxxxxxxx: %s" % (order_json))
        if (order_json["shipping"]):
            order_fields['shipping'] = self.pretty_json( cr, uid, id, order_json["shipping"])

            order_fields['status_shipping'] =order_json["shipping"]["status"] if "status" in order_json["shipping"] else False
            order_fields['shipment_type'] =order_json["shipping"]["shipment_type"] if "shipment_type" in order_json["shipping"] else False
            if 'shipping_option' in order_json["shipping"]:
                _logger.info("buscando eerror: %s" % (order))
                if order:
                    if order.shipment_type!='custom_shipping':  
                    #raise orm.except_orm("Valor",str(order.shipment_name))
                        order_fields['shipment_name'] ='Agregar costo de envio' if order_json["shipping"]["shipping_option"]["name"]=='add_shipping_cost' else order_json["shipping"]["shipping_option"]["name"]
                else:
                    order_fields['shipment_name'] ='Agregar costo de envio' if order_json["shipping"]["shipping_option"]["name"]=='add_shipping_cost' else order_json["shipping"]["shipping_option"]["name"]    
                order_fields['cost_shipping'] =order_json["shipping"]["shipping_option"]["cost"]
            if 'receiver_address' in order_json["shipping"]:
                street_name=''
                com=''
                cy=''
                country=''
                zipp=''
                state=''
                street_number=''
                if order_json["shipping"]["receiver_address"]["street_name"]:
                    street_name=order_json["shipping"]["receiver_address"]["street_name"]
                if order_json["shipping"]["receiver_address"]["comment"]:
                    com=order_json["shipping"]["receiver_address"]["comment"]
                if order_json["shipping"]["receiver_address"]["city"]["name"]:
                    cy=order_json["shipping"]["receiver_address"]["city"]["name"]
                if order_json["shipping"]["receiver_address"]["country"]["name"]:
                    country=order_json["shipping"]["receiver_address"]["country"]["name"]
                if order_json["shipping"]["receiver_address"]["zip_code"]:
                    zipp=order_json["shipping"]["receiver_address"]["zip_code"]
                if order_json["shipping"]["receiver_address"]["state"]["name"]:
                    state=order_json["shipping"]["receiver_address"]["state"]["name"]
                if order_json["shipping"]["receiver_address"]["street_number"]:
                    street_number=order_json["shipping"]["receiver_address"]["street_number"]  
                order_fields['note'] =street_name+', '+'N exterior '+street_number+' '+com+' '+cy+' '+country+'('+zipp+')'+' '+state
        #create or update order
        if (order and order.id):
            _logger.info("Updating order: %s" % (order.id))
            order.write( order_fields )
        else:
            _logger.info("Adding new order: " )
            _logger.info(order_fields)
            return_id = order_obj.create(cr,uid,(order_fields))
            order = order_obj.browse(cr,uid,return_id)
        #check error
        if not order:
            _logger.error("Error adding order.")
            return {}        
        #update internal fields (items, payments, buyers)        
        if 'order_items' in order_json:
            items = order_json['order_items']
            #raise orm.except_orm("Valor",str(items)+str(order_json["id"]))            
            _logger.info( items )
            cn = 0
            for Item in items:
                cn = cn + 1
                _logger.info(cn)
                _logger.info(Item )
                post_related = posting_obj.search( cr, uid, [('meli_id','=',Item['item']['id'])])
                post_related_obj = ''
                if (post_related):
                    if (post_related[0]):
                        post_related_obj = post_related[0]
                else:
                    vall={
                        'meli_id':Item['item']['id'],
                        'name':Item['item']['title'],
                        #'sku':Item['item']['seller_custom_field'],
                    }
                    post_related_obj=posting_obj.create(cr, uid,vall)
                order_item_fields = {
                    'order_id': order.id,
                    'posting_id': post_related_obj,
                    'order_item_id': Item['item']['id'],
                    'order_item_title': Item['item']['title'],
                    'order_item_category_id': Item['item']['category_id'],
                    'unit_price': Item['unit_price'],
                    'quantity': Item['quantity'],
                    'currency_id': Item['currency_id'],
                    'payment_type': Item["payment_type"] or '',
                }
                order_item_ids = order_items_obj.search(cr,uid,[('order_item_id','=',order_item_fields['order_item_id']),('order_id','=',order.id)] )

                if not order_item_ids:
	                order_item_ids = order_items_obj.create(cr,uid,( order_item_fields ))
                else:
                    order_items_obj.write(cr,uid, order_item_ids[0], ( order_item_fields ) )


        if 'payments' in order_json:
            payments = order_json['payments']
            #raise orm.except_orm("Valor",str(payments))            
            #_logger.info( payments )
            _logger.info("Pagos: %s" % (payments))
            cn = 0
            for Payment in payments:
                cn = cn + 1
                _logger.info(cn)
                _logger.info(Payment )
                if Payment['payment_type'] not in  ['prepaid_card','debit_card','atm','ticket','account_money','credit_card','digital_currency']:
                    raise orm.except_orm("Valor payment_type no in ",str(Payment['payment_type']))      

                payment_fields = {
                    'order_id': order.id,
                    'payment_id': Payment['id'],
                    'transaction_amount': Payment['transaction_amount'] or '',
                    'currency_id': Payment['currency_id'] or '',
                    'status': Payment['status'] or '',
                    'date_created': Payment['date_created'] or '',
                    'date_last_modified': Payment['date_last_modified'] or '',
                    'payment_type':Payment['payment_type'] if Payment['payment_type'] in ['prepaid_card','debit_card','atm','ticket','account_money','credit_card','digital_currency']  else False  or '',
                }
                #raise orm.except_orm("",str(payment_fields))
                
                payment_ids = payments_obj.search(cr,uid,[  ('payment_id','=',payment_fields['payment_id']),
                                                            ('order_id','=',order.id ) ] )

                if not payment_ids:
                    #raise orm.except_orm( "",str( payment_fields))
                    try:
                        payment_ids = payments_obj.create(cr,uid,( payment_fields ))
                    except Exception as e:
                        raise orm.except_orm("",str(payment_fields )+"-"+str(e))
                    
                else:
                    payments_obj.write(cr,uid, payment_ids[0], ( payment_fields ) )
        

        if 'buyer' in order_json:
            Buyer = order_json['buyer']
            _logger.info("Compradores==================: %s" % (Buyer))
            buyer_fields = {
                'buyer_id': Buyer['id'],
                'nickname': Buyer['nickname'],
                'first_name': Buyer['nickname'],
                #'email': Buyer['email'],
                #'phone': self.full_phone( cr, uid, Buyer['phone']),
                #'alternative_phone': self.full_phone( cr, uid, Buyer['alternative_phone']),
                #'first_name': Buyer['first_name'],
                #'last_name': Buyer['last_name'],
                #'billing_info': self.billing_info( cr, uid, Buyer['billing_info']),
            }
        
            buyer_ids = buyers_obj.search(cr,uid,[  ('buyer_id','=',buyer_fields['buyer_id'] ) ] )

            if not buyer_ids:
                buyer_ids = buyers_obj.create(cr,uid,( buyer_fields ))
		if order:
			return_id = self.pool.get('mercadolibre.orders').write(cr,uid,order.id,{'buyer':buyer_ids})
            else:
                buyers_obj.write(cr,uid, buyer_ids[0], ( buyer_fields ) )
    		return_id = self.pool.get('mercadolibre.orders').write(cr,uid,order.id,{'buyer':buyer_ids[0]})
        if order:
            return_id = self.pool.get('mercadolibre.orders').update
        return {}

    def orders_update_order( self, cr, uid, id, context=None ):

        #get with an item id
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id

        order_obj = self.pool.get('mercadolibre.orders')
        order_items_obj = self.pool.get('mercadolibre.order_items')
        order = order_obj.browse(cr, uid, id )

        log_msg = 'orders_update_order: %s' % (order.order_id)
        _logger.info(log_msg)

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        #
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN )

        response = meli.get("/orders/"+order.order_id, {'access_token':meli.access_token})
        order_json = response.json()
        #_logger.info( product_json )

        if "error" in order_json:
            _logger.error( order_json["error"] )
            _logger.error( order_json["message"] )
        else:
            self.orders_update_order_json( cr, uid, {"id": id, "order_json": order_json } )
        return {}


    def orders_query_iterate( self, cr, uid, offset=0, context=None ):
        offset_next = 0
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id
        orders_obj = self.pool.get('mercadolibre.orders')               

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        #
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN )
        orders_query = str("/orders/search/recent?seller=")+str(company.mercadolibre_seller_id)+str("&sort=date_desc")
        if (offset):
            orders_query = orders_query + "&offset="+str(offset).strip()
        response = meli.get( orders_query, {'access_token':meli.access_token})
        orders_json = response.json()

        if "error" in orders_json:
            _logger.error( orders_query )
            _logger.error( orders_json["error"] )            
            if (orders_json["message"]=="invalid_token"):
                _logger.error( orders_json["message"] )
            return {}    

        _logger.info( orders_json )

        #testing with json:
        if (True==False):
            with open('/home/fabricio/envOdoo8/sources/meli_oerp/orders.json') as json_data:
                _logger.info( json_data )
                orders_json = json.load(json_data)
                _logger.info( orders_json )


        if "paging" in orders_json:
            if "total" in orders_json["paging"]:
                if (orders_json["paging"]["total"]==0):
                    return {}
                else:
                    if (orders_json["paging"]["total"]==orders_json["paging"]["limit"]):
                        offset_next = offset + orders_json["paging"]["limit"]

        if "results" in orders_json:
            for order_json in orders_json["results"]:
                if order_json:
                    self.orders_update_order_json( cr, uid, {"id": False, "order_json": order_json} )


        if (offset_next>0):
            self.orders_query_iterate(cr,uid,offset_next)
            
        return {}

    def orders_query_recent( self, cr, uid,ordenes, context=None ):
        self.orders_query_iterate( cr, uid,ordenes)
        return {}

    def _total_paid(self,cr,uid,ids,field_name, arg, context=None):
            records=self.browse(cr,uid,ids,)
            resu={}
            total_amount=0.0
            cost_shipping=0.0
            for r in records:
                if r.total_amount:
                    total_amount=float(r.total_amount)
                if r.cost_shipping:
                    cost_shipping=float(r.cost_shipping)
                resu[r.id]=total_amount+cost_shipping
            return resu 

    def _get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        if not company_id:
            raise orm.except_orm(('Error!'), ('There is no default company for the current user!'))
        return company_id

    _columns = {
        'order_id': fields.char('Order Id'),
        'name':fields.related('order_id',type='char',relation='mercadolibre.orders',string='Name'),
        'status': fields.selection( [ 
        #Initial state of an order, and it has no payment yet.
                                        ("confirmed","Confirmed"),
        #The order needs a payment to become confirmed and show users information.
                                      ("payment_required","Payment Required"),
        #There is a payment related with the order, but it has not accredited yet
                                    ("partially_paid","Parcialmente pagada"),
                                    ("payment_in_process","Payment in progress"),
        #The order has a related payment and it has been accredited.
                                    ("paid","Paid"),
        #The order has not completed by some reason.
                                    ("cancelled","Cancel")], string='Order Status'),

        'status_detail': fields.text(string='Status detail, in case the order was cancelled.'),
        'date_created': fields.date('Creation date'),
        'date_closed': fields.date('Closing date'),

        'order_items': fields.one2many('mercadolibre.order_items','order_id','Order Items' ),
        'payments': fields.one2many('mercadolibre.payments','order_id','Payments' ),
        'shipping': fields.text(string="Shipping"),

        'total_amount': fields.char(string='Total amount'),
        'currency_id': fields.char(string='Currency'),
        'buyer': fields.many2one( "mercadolibre.buyers","Buyer"),
        'seller': fields.text( string='Seller' ),
        'sale_order':fields.many2one('sale.order','Orden de Venta ERP'),
        'status_shipping':fields.selection([("to_be_agreed","Lo retira"),("not_delivered","No entregado"),
            ("pending","Pendiente"),("ready_to_ship","Listo para enviar"),("shipped","Enviado"),("delivered","Entregado")], string='Estado de envio'),
        'shipment_type':fields.selection([("shipping","Mercado Envios"),("custom_shipping","Envio Personalizado")],'Tipo de envío'),
        #'shipment_name':fields.selection([("DHL Estándar","DHL Estándar"),("DHL Express","DHL Express"),("add_shipping_cost","agregar el costo de envio")],'Forma de envio'),
        'shipment_name':fields.char('Forma de envio',size=30),
        'cost_shipping':fields.char('Costo de envio',size=15),
        'cost_amount':fields.related('total_amount',type='char',relation='mercadolibre.orders',string='Cantidad Total'),
        'total_paid':fields.function(_total_paid,type='float',string='Comprador Pago'),
        'note':fields.text('Informacion de envio',size=300),
        'state_order_odoo':fields.related('sale_order','state',type='selection',relation='sale.order',selection=[
            ('draft', 'Cotizacion'),
            ('sent', 'Cotizacion Enviado'),
            ('cancel', 'Cancelado'),
            ('waiting_date', 'Esperando Fecha Planificada'),
            ('progress', 'Pedido de Venta'),
            ('manual', 'Pedido a facturar'),
            ('shipping_except', 'Excepcion de envio'),
            ('invoice_except', 'Excepcion de Factura'),
            ('done', 'Completado')],string='Estado Orden ERP'),
        'company_id': fields.many2one('res.company', 'Company'),
    }
    _order = "date_created desc"
    _defaults = {
        'company_id': _get_default_company,
    }

mercadolibre_orders()


class mercadolibre_order_items(osv.osv):
	_name = "mercadolibre.order_items"
	_description = "Product order in MercadoLibre"
    
	_columns = {
        'posting_id': fields.many2one("mercadolibre.posting","Posting"),
        'order_id': fields.many2one("mercadolibre.orders","Order"),
        'order_item_id': fields.char('Item Id'),
        'order_item_title': fields.char('Item Title'),
        'order_item_category_id': fields.char('Item Category Id'),
        'unit_price': fields.char(string='Unit price'),
        'quantity': fields.integer(string='Quantity'),
#        'total_price': fields.char(string='Total price'),
        'currency_id': fields.char(string='Currency'),
        
	}
mercadolibre_order_items()


class mercadolibre_payments(osv.osv):
	_name = "mercadolibre.payments"
	_description = "Payments MercadoLibre"
    
	_columns = {
        'order_id': fields.many2one("mercadolibre.orders","Order"),
        'payment_id': fields.char('Payment Id'),
        'transaction_amount': fields.char('Transaction Amount'),
        "currency_id": fields.char(string='Currency'),
        "status": fields.char(string='Payment Status'),
        "date_created": fields.char('Creation date'),
        "date_last_modified": fields.char('Modification date'),#'prepaid_card','debit_card','atm','ticket','account_money','credit_card','digital_currency'
        # 'payment_type':fields.selection([("prepaid_card","Tarjeta de prepago"),("debit_card","Tarjeta de debito"),("atm","Cajero automatico"),("ticket","Efectivo"),
        #     ("account_money","cuenta de dinero"),("credit_card","Tarjeta de crédito"),('digital_currency','=','digital_currency')],'Tipo de Pago'),
        'payment_type':fields.char('Forma de Pago'),
    }
mercadolibre_payments()

class mercadolibre_buyers(osv.osv):
    _name = "mercadolibre.buyers"
    _description = "Buyers in MercadoLibre"

    def _name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (list, tuple)) and not len(ids):
            return []
        if isinstance(ids, (long, int)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['first_name','buyer_id'], context=context)
        res = []
        for record in reads:
            name2 = record['first_name']       
            if name2==False:
                name1 = record['buyer_id']
            elif record['buyer_id']==False:
                name1 =name2
            else:
                name1='['+record['buyer_id']+ '] '+name2
            res.append((record['id'], name1))
        return res

    def _get_name(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self._name_get(cr, uid, ids, context=context)
        return dict(res)
    
    _columns = {
        'buyer_id': fields.char(string='Buyer ID'),
        'nickname': fields.char(string='Nickname'),
        'email': fields.char(string='Email'),
        'phone': fields.char( string='Phone'),
        'alternative_phone': fields.char( string='Alternative Phone'),
        'first_name': fields.char( string='First Name'),
        'last_name': fields.char( string='Last Name'),
        'billing_info': fields.char( string='Billing Info'),
        'name':fields.function(_get_name, type="char", string='Nombre'),
	}
mercadolibre_buyers()


class mercadolibre_orders_update(osv.osv_memory):
    _name = "mercadolibre.orders.update"
    _description = "Update Order"
    
    def order_update(self, cr, uid, ids, context=None):

        orders_ids = context['active_ids']
        orders_obj = self.pool.get('mercadolibre.orders')

        for order_id in orders_ids:

            _logger.info("order_update: %s " % (order_id) )

            order = orders_obj.browse(cr,uid, order_id)
            orders_obj.orders_update_order( cr, uid, order_id )

        return {}

mercadolibre_orders_update()