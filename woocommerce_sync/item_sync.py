import json
import frappe
import requests
from frappe import _
from erpnext.stock.utils import get_bin
from .exceptions import woocommerceError
from frappe.utils import get_datetime, cint
from .utils import make_woocommerce_log, disable_woocommerce_sync_for_item
from .woo_requests import get_woocommerce_settings, get_request, post_request, put_request

per_page = 100  # Default maximum number of items per page

def get_woocommerce_items_from_doctype():
    woocommerce_items = frappe.get_all('WooCommerce Item',['name','woocommerce_item_id'])

    return woocommerce_items

def add_woocommerce_items_to_erp():
    woocommerce_items = get_woocommerce_items_from_doctype()

    # Delete all existing woocommerce items before reinitializing 
    if woocommerce_items:
        for woocommerce_item in woocommerce_items:
            frappe.delete_doc('WooCommerce Item', woocommerce_item['name'])

    item_codes_and_ids = get_item_codes_and_ids_from_woocommerce()
    # make_woocommerce_log(title="Items Codes and IDs Before", status="Success", method="add_woocommerce_items_to_erp", message=str(item_codes_and_ids))

    item_list = [item_code for item in frappe.get_all('Item') for item_code in item.values()]
    # These items exit on WooCommerce but not on ERP
    items_to_not_be_added = [woocommerce_item['name'] for woocommerce_item in woocommerce_items if woocommerce_item['name'] not in item_list]

    for item in items_to_not_be_added:
        if item in list(item_codes_and_ids.keys()): 
            # make_woocommerce_log(title="Item", status="Success", method="add_woocommerce_items_to_erp", message=item)
            del item_codes_and_ids[item]

    # make_woocommerce_log(title="Items Codes and IDs After", status="Success", method="add_woocommerce_items_to_erp", message=str(item_codes_and_ids))
    # # make_woocommerce_log(title="Items", status="Success", method="add_woocommerce_items_to_erp", message=str(items_to_not_be_added))

    for item_code, woocommerce_item_id in item_codes_and_ids.items():
        woocommerce_item = frappe.get_doc({
            'doctype': 'WooCommerce Item',
            'item_code': item_code,
            'woocommerce_item_id': woocommerce_item_id
        })

        woocommerce_item.insert()

def get_item_codes_and_ids_from_woocommerce():
    page = 1
    products = []
    item_codes_and_ids = {}

    while True:
        r = get_request('wp-json/wc/v3/products?per_page={0}&page={1}'.format(per_page, page))

        if not r:
            break

        products.extend(r)
        page += 1

    for product in products:
        if not product['sku']:
            continue
            
        item_codes_and_ids[product['sku']] = product['id'] 

    return item_codes_and_ids    

# TODO: Finish this
def sync_item_by_woocommerce_id(woocommerce_id):
    # update_item_stock_qty()

    # make_woocommerce_log(title="Sync With WooCommerce", status="Success", method="sync_by_woocommerce_id", message="Sync by woocommerce id")
    
    pass

def sync_item_by_item_code():
    # make_woocommerce_log(title="Sync With WooCommerce", status="Success", method="sync_by_item_code", message="Sync by item code")
    
    woocommerce_settings = get_woocommerce_settings()
    item_code = woocommerce_settings['item_code']
    
    # make_woocommerce_log(title="Item Code", status="Success", method="sync_item_by_item_code", message=woocommerce_settings)

    update_item_stock_qty(item_code)

def get_product_update_dict(actual_qty):
    item_data = {}
    item_data["stock_quantity"] = "{0}".format(actual_qty)
    item_data["manage_stock"] = "1"

    # make_woocommerce_log(title="Item Data", status="Success", method="get_product_update_dict", message="Item Data: {0}".format(item_data))

    return item_data

def get_woocommerce_item_id(item_code):
    path = 'wp-json/wc/v3/products?sku={0}'.format(item_code)
    r = get_request(path)
    woocommerce_item_id = r[0]['id']

    # make_woocommerce_log(title="WooCommerce Item ID", status="Success", method="get_woocommerce_item_id", message="WooCommerce Item ID: {0}".format(woocommerce_item_id))

    return woocommerce_item_id

def update_item_stock_qty(item_code):
    woocommerce_settings = frappe.get_doc("WooCommerce Sync", "WooCommerce Sync")

    try:
        update_item_stock(item_code, woocommerce_settings)

    except woocommerceError as e:
        make_woocommerce_log(title="{0}".format(e), status="Error", method="sync_woocommerce_items", message=frappe.get_traceback(),
            request_data=item_code, exception=True)

    except Exception as e:
        if e.args[0] and e.args[0].startswith("402"):
            raise e
            
        else:
            make_woocommerce_log(title="{0}".format(e), status="Error", method="sync_woocommerce_items", message=frappe.get_traceback(),
                request_data=item_code, exception=True)

def bulk_sync():
    woocommerce_settings = frappe.get_doc("WooCommerce Sync", "WooCommerce Sync")
    woocommerce_items = get_woocommerce_items_from_doctype()

    for woocommerce_item in woocommerce_items:
        item_code = woocommerce_item['name']
        woocommerce_item_id = woocommerce_item['woocommerce_item_id']

        update_item_stock(item_code, woocommerce_settings, woocommerce_item_id)

def update_item_stock(item_code, woocommerce_settings, woocommerce_item_id=None):
    item = frappe.get_doc("Item", item_code)

    bin = get_bin(item_code, woocommerce_settings.warehouse)

    actual_qty = bin.actual_qty
    reserved_qty = bin.reserved_qty
    qty = cint(actual_qty - reserved_qty)

    # make_woocommerce_log(title="Bin Data", status="Success", method="update_item_stock", message="Item Quantity: {0}".format(qty))

    if not woocommerce_item_id:
        woocommerce_item_id = get_woocommerce_item_id(item_code)

    resource = "wp-json/wc/v3/products/{0}".format(woocommerce_item_id)

    item_data = get_product_update_dict(qty)
    
    # make_woocommerce_log(title="Item Data", status="Success", method="get_product_update", message="Item Data: {0}".format(item_data))
    # make_woocommerce_log(title="Resource", status="Success", method="get_product_update", message="Resource: {0}".format(resource))
    
    try:
        post_request(resource, item_data)
        
    except requests.exceptions.HTTPError as e:
        if e.args[0] and e.args[0].startswith("404"):
            make_woocommerce_log(title=e.message, status="Error", method="update_item_stock", message=frappe.get_traceback(),
                request_data=item_data, exception=True)
            disable_woocommerce_sync_for_item(item)

        else:
            raise e

# def update_item_stock(item_code, woocommerce_settings):
#     item = frappe.get_doc("Item", item_code)

#     bin = get_bin(item_code, woocommerce_settings.warehouse)

#     actual_qty = bin.actual_qty
#     reserved_qty = bin.reserved_qty
#     qty = cint(actual_qty - reserved_qty)

#     # make_woocommerce_log(title="Bin Data", status="Success", method="update_item_stock", message="Item Quantity: {0}".format(qty))

#     woocommerce_item_id = get_woocommerce_item_id(item_code)

#     resource = "wp-json/wc/v3/products/{0}".format(woocommerce_item_id)

#     item_data = get_product_update_dict(qty)
    
#     # make_woocommerce_log(title="Item Data", status="Success", method="get_product_update", message="Item Data: {0}".format(item_data))
#     # make_woocommerce_log(title="Resource", status="Success", method="get_product_update", message="Resource: {0}".format(resource))
    
#     try:
#         post_request(resource, item_data)
        
#     except requests.exceptions.HTTPError as e:
#         if e.args[0] and e.args[0].startswith("404"):
#             make_woocommerce_log(title=e.message, status="Error", method="update_item_stock", message=frappe.get_traceback(),
#                 request_data=item_data, exception=True)
#             disable_woocommerce_sync_for_item(item)

#         else:
#             raise e