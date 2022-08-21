# -*- coding: utf-8 -*-
##############################################################################
#
#       Pere Ramon Erro Mas <pereerro@tecnoba.com> All Rights Reserved.
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Mercado Libre',
    'version': '0.1',
    'author': 'Moldeo Interactive & Mikrointeracciones de México',
    'website': 'http://business.moldeo.coop',
    "category": "Sales",
    "depends": ['base', 'product','sale','mail'],
    'data': [
    'security/meli_security.xml',
    'security/ir.model.access.csv',
    'wizard/product_muti_edit_view.xml',
    'data/categories_view.xml',
    #'data/question_cron.xml',
    'wizard_acces_token_view.xml',
	'company_view.xml',
	'posting_view.xml',
    'product_post.xml',
    'product_view.xml',	
	'category_view.xml',
	'banner_view.xml',
    'warning_view.xml',
    'questions_view.xml',
    'orders_view.xml',
    'sale_view.xml',
    ],
    'demo_xml': [],
    'active': False,
    'installable': True,
    'application': True,
}
