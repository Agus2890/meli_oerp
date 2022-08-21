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

from openerp.osv import fields, osv, orm
import logging
import meli_oerp_config

import melisdk
from melisdk.meli import Meli

#https://api.mercadolibre.com/questions/search?item_id=MLA508223205

class mercadolibre_questions(orm.Model):
    _name = "mercadolibre.questions"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Preguntas MercadoLibre"
    _track = {
        'status': {
            'meli_oerp.mt_oerp_done': lambda self, cr, uid, obj, ctx=None: obj['status'] in ['ANSWERED']
        },
    }

    def action_Answer(self, cr, uid,ids, context=None ):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        company = user_obj.company_id

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN )
        #/questions/search?item={Item_id}&access_token=$ACCESS_TOKEN
        #Responder /answers
        #response = meli.post("/items", body, {'access_token':meli.access_token})
        wizard= self.browse(cr,uid,ids[0],context=context)
        question_id=wizard.question_id
        answer=wizard.answer_text
        if answer:
            answer=wizard.answer_text
        else:
            raise orm.except_orm("Debe introducir la respuesta para poder Responder",str("campo Texto de Respuesta"))
        answer={
            'question_id':question_id,
            "text":answer,
            }
        response = meli.post("/answers",answer,{'access_token':meli.access_token})
        rjson = response.json()
        if "error" in rjson:
             if (rjson["error"]=="not_unanswered_question"):
                    raise orm.except_orm("la pregunta ya fue respondida",str(question_id))
        else:
            status=rjson["status"]
            answer_user=rjson["answer"]
            for answeruser in answer_user:
                status_answer=rjson["answer"]["status"]
                text_answer= rjson["answer"]['text']
                date_create= rjson["answer"]['date_created']                
                self.write(cr, uid, ids, {
                        'status':status,
                        'answer_status':status_answer,
                        'answer_text':text_answer,
                        'answer_date_created':date_create
                        }, context=context)
                self.write(cr, uid, ids, {'answered_user' :uid}, context=None)
            return True

    _columns = {
        'posting_id': fields.many2one("mercadolibre.posting","Posting"),
        'question_id': fields.char('Question Id'),
        'date_created': fields.date('Creation date'),
        'item_id': fields.char(string="Item Id",size=255),
        'seller_id': fields.char(string="Seller Id",size=255),
        'text': fields.text("Question Text"),
        'status': fields.selection( [("UNANSWERED","Question is not answered yet."),("BANNED","BANNED"),("ANSWERED","Question was answered."),("CLOSED_UNANSWERED","The item is closed and the question was never answered."),("UNDER_REVIEW","The item is under review and the question too.")], string='Question Status'),
        'answer_date_created': fields.date('Answer creation date'),
        'answer_status': fields.selection( [("ACTIVE","Active"),("DISABLED","Disabled"),("BANNED","BANNED")], string='Answer Status'),
        'answer_text': fields.text("Answer Text"),
        'answered_user':fields.many2one("res.users","Respondio"),
    }
    _order = "date_created desc"