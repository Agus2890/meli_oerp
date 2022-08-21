# -*- encoding: utf-8 -*-
###########################################################################
#    Module Writen to OpenERP, Open Source Management Solution
#
#    Copyright (c) 2015 MKI - http://www.mikrointeracciones.com.mx
#    All Rights Reserved.
#    info@mikrointeracciones.com.mx
############################################################################
############################################################################
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

from openerp.osv import fields, osv, orm
import time
class sale_order(osv.Model):
    _name = 'sale.order'
    _inherit = 'sale.order'
    _description = 'Order MercadoLibre'

    _columns = {
    	#'linio_order_id': fields.char('Linio Id'),
        'tienda_idmlm':fields.selection([('mlm','MercadoLibre'),('Akizi','Akizi'),('Mercadazo','Mercadazo'),('Tiendas Oficiales','Tienda Oficial')],'Tienda'),
        #'linio_id': fields.char('Linio Id'),
        'orden_id_mlm':fields.many2one('mercadolibre.orders','Orden MercadoLibre'),
        'address_mlm':fields.char('Direccion',size=200),
        #########
        'formaentrega':fields.char('Forma de Entrega',size=200),
        'trasportista':fields.char('Transportista'),
        'nseguimiento':fields.char('No. Seguimiento'),
        'fachacamino':fields.char('Fecha en camino'),
        'fachaentrega':fields.char('Fecha entregado'),
        'urlseguimiento':fields.char('URL Seguimiento',size=200),

    }
sale_order()

class res_partner(osv.Model):
    _inherit = 'res.partner'

    _columns = {
        'ref_code':fields.char('Codigo/ref', size=64),
    }
