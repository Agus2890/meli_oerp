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

class product_multi_edit(osv.osv_memory):
    _name = "product.multi.edit"

    def actualizar_multiple(self, cr, uid, ids, context=None):
        wizard= self.browse(cr,uid,ids[0],context=context)   
        product_mlm_obj  = self.pool.get('multi.posting')
        ids_product = product_mlm_obj.search(cr, 1 , [('sku_product','!=',False)], context=context)
        for rec in ids_product: 
            salones_obj  = self.pool.get('gym.gym')
            idsgen= product_mlm_obj.browse(cr, uid, rec, context=context)
            sku=idsgen.product_id.default_code 
            valor=wizard.name.encode('utf-8').replace("'sku'",str(sku) or '')
            #raise orm.except_orm("Error",str(valor))
            product_mlm_obj.write(cr, uid,rec, {'meli_warranty':valor}, context=None)
        return True

    _columns = {
        'name':fields.char('Garantia',size=264,required=True),
    }

class asig_shipping(osv.osv_memory):
    _name = "asig.shipping"

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(asig_shipping, self).default_get(cr, uid, fields, context=context)
        prod_obj = self.pool.get('mercadolibre.orders')
        prod = prod_obj.browse(cr, uid, context.get('active_id'), context=context)
        if 'name' in fields:
            res.update({'name': prod.order_id,'toml_order_id':prod.id})
        return res

    def act_confirm_shipping(self, cr, uid, ids, context=None):
        toml_obj= self.pool.get('mercadolibre.orders')
        for this in self.browse(cr, uid, ids, context=context):
            if this.toml_order_id:
                toml_obj.write(cr,uid,this.toml_order_id.id,{'shipment_name':this.shipping_type.name}, context=context)
        return True

    _columns = {
        'name':fields.char('Forma de envio',size=264,required=True),
        'toml_order_id':fields.many2one('mercadolibre.orders','Orden'),
        'shipping_type':fields.many2one('delivery.carrier','Forma de envio',required=True)
    }

   