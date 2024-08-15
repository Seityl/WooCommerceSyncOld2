import json
import frappe
import requests
from frappe import _
from erpnext.stock.utils import get_bin
from .exceptions import woocommerceError
from frappe.utils import get_datetime, cint
from .utils import make_woocommerce_log, disable_woocommerce_sync_for_item
from .woo_requests import get_woocommerce_items, get_woocommerce_settings, get_request, post_request, put_request, get_woocommerce_item_variants

per_page = 100  # Default maximum number of items per response page

def sync_individual_item(item_code=None, woocommerce_item_id=None, price_list=None):
    if item_code or woocommerce_item_id:
        if item_code:
            try:
                update_item_stock_qty(item_code=item_code)
                update_item_price(item_code, price_list)

            except woocommerceError as e:
                make_woocommerce_log(title="{0}".format(e), status="Error", method="sync_single_item_to_woocommerce", message=frappe.get_traceback(), request_data=item_code, exception=True)

            except Exception as e:
                if e.args[0] and e.args[0] == 402:
                    raise e

                else:
                    make_woocommerce_log(title="{0}".format(e), status="Error", method="sync_single_item_to_woocommerce", message=frappe.get_traceback(), request_data=item_code, exception=True)

        if woocommerce_item_id:
            item_code = get_item_code_from_woocommerce_item_id(woocommerce_item_id)

            try:
                update_item_stock_qty(woocommerce_item_id=woocommerce_item_id)
                update_item_price(item_code, price_list, woocommerce_item_id=woocommerce_item_id)

            except woocommerceError as e:
                make_woocommerce_log(title="{0}".format(e), status="Error", method="sync_single_item_to_woocommerce", message=frappe.get_traceback(), request_data=woocommerce_item_id, exception=True)

            except Exception as e:
                if e.args[0] and e.args[0] == 402:
                    raise e

                else:
                    make_woocommerce_log(title="{0}".format(e), status="Error", method="sync_single_item_to_woocommerce", message=frappe.get_traceback(), request_data=woocommerce_item_id, exception=True)

# TODO: Finish This
def sync_products(price_list, warehouse, enable_sync=False):
    if enable_sync:
        sync_woocommerce_items(warehouse)

    # if woocommerce_settings.if_not_exists_create_item_to_woocommerce == 1:
    #     sync_erpnext_items(price_list, warehouse, woocommerce_item_list)

def sync_woocommerce_items(warehouse):    
    for woocommerce_item in get_woocommerce_items():
        make_woocommerce_log(title="WooCommerce Item", status="Success", method="get_product_update_dict", message=str(woocommerce_item))
        try:
            make_item(warehouse, woocommerce_item)

        except woocommerceError as e:
            make_woocommerce_log(title="{0}".format(e), status="Error", method="sync_woocommerce_items", message=frappe.get_traceback(), request_data=woocommerce_item, exception=True)

        except Exception as e:
            if e.args[0] and e.args[0] == 402:
                raise e

            else:
                make_woocommerce_log(title="{0}".format(e), status="Error", method="sync_woocommerce_items", message=frappe.get_traceback(), request_data=woocommerce_item, exception=True)

def get_item_price(item_code, price_list):
    values = {
        'item_code': item_code,
        'price_list': price_list
        }
    if values:
        try:
            item_price = frappe.db.sql("""
                SELECT
                    `price_list_rate`
                FROM `tabItem Price`
                WHERE `item_code` = %(item_code)s
                    AND `price_list` = %(price_list)s
            """, values=values, as_dict=1)[0]['price_list_rate']
                
            if item_price:
                return item_price
            else:
                return None

        except Exception as e:
            make_woocommerce_log(title="{0}".format(e), status="Error", method="get_item_price", message=frappe.get_traceback(), request_data=item_code, exception=True)
            return None
    else:
        make_woocommerce_log(title="ERROR: get_item_price", status="Error", method="get_item_price", message="No Item data")
    
def get_woocommerce_items_from_doctype():
    woocommerce_items = frappe.get_all('WooCommerce Item',['name','woocommerce_item_id'])

    return woocommerce_items

def get_item_code_from_woocommerce_item(woocommerce_item):
    item_code = str(woocommerce_item.get("sku"))

    return item_code
def get_item_code_from_woocommerce_item_id(woocommerce_item_id):
    item_code = get_request('wp-json/wc/v3/products/{0}'.format(woocommerce_item_id))['sku']

    return str(item_code)

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

#add childtable with categories into items
#TODO: Fix this
def get_categories(woocommerce_item, is_variant=False):
    categories = []
    if not is_variant:
        try:
            for category in woocommerce_item.get("categories"):
                categories.append({'category': category.get("name")})
        except:
            pass
    else:
        try:
            erpnext_categories = frappe.db.sql("""SELECT `category` FROM `tabItem Product Category` WHERE `parent` = '{item_code}'""".format(item_code=woocommerce_item.name), as_list=True)
            for category in erpnext_categories:
                categories.append({'category': category[0]})
        except:
            pass
    return categories

def get_product_update_dict(actual_qty=None, item_price=None):
    item_data = {}

    if actual_qty:
        item_data["stock_quantity"] = "{0}".format(actual_qty)
        item_data["manage_stock"] = "1"

    if item_price:
        item_data["price"] = item_price
        item_data["regular_price"] = item_price

    return item_data

def get_woocommerce_item_id(item_code):
    path = 'wp-json/wc/v3/products?sku={0}'.format(item_code)
    r = get_request(path)
    woocommerce_item_id = r[0]['id']

    # make_woocommerce_log(title="WooCommerce Item ID", status="Success", method="get_woocommerce_item_id", message="WooCommerce Item ID: {0}".format(woocommerce_item_id))

    return woocommerce_item_id

#TODO: Finish this
def get_item_details(woocommerce_item):
    item_details = {}

    item_details = frappe.db.get_value('WooCommerce Item', {'woocommerce_item_id': woocommerce_item.get('id')},
        ['name', 'stock_uom', 'item_name'], as_dict=1)

    if item_details:
        return item_details

    # else:
    # item_details = frappe.db.get_value('WooCommerceItem', {'woocommerce_variant_id': woocommerce_item.get('id')},
    #     ['name', 'stock_uom', 'item_name'], as_dict=1)
    #     return item_details

#TODO: Finish this
def get_item_group(item_code):
    item_group = frappe.db.get_value('Item', {'item_code':item_code}, 'item_group')

    if item_group:
        return item_group
        
    else:
        make_woocommerce_log(title="Item does not exist", status="Error", method="get_item_group", message="Item {0} not found".format(item_code))

#TODO: Finish this
def get_erpnext_uom(woocommerce_item, woocommerce_settings, attributes=[]):
    if len(attributes) > 0:
        for attr in attributes:
            if attr["attribute"] == woocommerce_settings.attribute_for_uom:
                uom_match = frappe.get_all("UOM", filters={'uom_name': "{0}".format(attr["attribute_value"])}, fields=['name'])
                if len(uom_match) > 0:
                    return attr["attribute_value"]
                else:
                    frappe.log_error("{0} {1}".format(attr, woocommerce_item))
                    new_uom = frappe.get_doc({
                        'doctype': 'UOM',
                        'uom_name': attr["attribute_value"]
                    }).insert()
                    return attr["attribute_value"]
    else:
        return 'Nos'

#TODO: Finish this
def get_erpnext_items(price_list):
    erpnext_items = []
    woocommerce_settings = frappe.get_doc("WooCommerce Config", "WooCommerce Config")

    last_sync_condition, item_price_condition = "", ""
    if woocommerce_settings.last_sync_datetime:
        last_sync_condition = "and modified >= '{0}' ".format(woocommerce_settings.last_sync_datetime)
        item_price_condition = "AND `tabItem Price`.`modified` >= '{0}' ".format(woocommerce_settings.last_sync_datetime)

    item_from_master = """select name, item_code, item_name, item_group,
        description, woocommerce_description, has_variants, variant_of, stock_uom, image, woocommerce_product_id,
        woocommerce_variant_id, sync_qty_with_woocommerce, weight_per_unit, weight_uom from tabItem
        where sync_with_woocommerce=1 and (variant_of is null or variant_of = '')
        and (disabled is null or disabled = 0)  %s """ % last_sync_condition

    erpnext_items.extend(frappe.db.sql(item_from_master, as_dict=1))

    template_items = [item.name for item in erpnext_items if item.has_variants]

    if len(template_items) > 0:
    #    item_price_condition += ' and i.variant_of not in (%s)'%(' ,'.join(["'%s'"]*len(template_items)))%tuple(template_items)
        # escape raw item name
        for i in range(len(template_items)):
            template_items[i] = template_items[i].replace("'", r"\'")
        # combine condition
        item_price_condition += ' AND `tabItem`.`variant_of` NOT IN (\'{0}\')'.format(
            ("' ,'".join(template_items)))
    
    item_from_item_price = """SELECT `tabItem`.`name`, 
                                     `tabItem`.`item_code`, 
                                     `tabItem`.`item_name`, 
                                     `tabItem`.`item_group`, 
                                     `tabItem`.`description`,
                                     `tabItem`.`woocommerce_description`, 
                                     `tabItem`.`has_variants`, 
                                     `tabItem`.`variant_of`, 
                                     `tabItem`.`stock_uom`, 
                                     `tabItem`.`image`, 
                                     `tabItem`.`woocommerce_product_id`,
                                     `tabItem`.`woocommerce_variant_id`, 
                                     `tabItem`.`sync_qty_with_woocommerce`, 
                                     `tabItem`.`weight_per_unit`, 
                                     `tabItem`.`weight_uom`
        FROM `tabItem`, `tabItem Price`
        WHERE `tabItem Price`.`price_list` = '%s' 
          AND `tabItem`.`name` = `tabItem Price`.`item_code`
          AND `tabItem`.`sync_with_woocommerce` = 1 
          AND (`tabItem`.`disabled` IS NULL OR `tabItem`.`disabled` = 0) %s""" %(price_list, item_price_condition)
    frappe.log_error("{0}".format(item_from_item_price))

    updated_price_item_list = frappe.db.sql(item_from_item_price, as_dict=1)

    # to avoid item duplication
    return [frappe._dict(tupleized) for tupleized in set(tuple(item.items())
        for item in erpnext_items + updated_price_item_list)]

# TODO: Finish this
def get_item_image(woocommerce_item):
    if woocommerce_item.get("images"):
        for image in woocommerce_item.get("images"):
            if image.get("position") == 0: # the featured image
                return image
            return None

    else:
        return None

#TODO: Finish this
def add_woocommerce_items_to_erp():
    woocommerce_items = get_woocommerce_items_from_doctype()

    # Delete all existing woocommerce items before reinitializing 
    if woocommerce_items:
        for woocommerce_item in woocommerce_items:
            frappe.delete_doc('WooCommerce Item', woocommerce_item['name'])

    item_codes_and_ids = get_item_codes_and_ids_from_woocommerce()
    # make_woocommerce_log(title="Items Codes and IDs Before", status="Success", method="add_woocommerce_items_to_erp", message=str(item_codes_and_ids))

    item_list = [item_code for item in frappe.get_all('Item') for item_code in item.values()]
    # These items exist on WooCommerce but not on ERP
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

# TODO: Finish this
def add_to_price_list(item, name):
    price_list = frappe.db.get_value("WooCommerce Sync", "Woocommerce Sync", "price_list")
    item_price_name = frappe.db.get_value("Item Price",
        {"item_code": name, "price_list": price_list}, "name")
    rate = item.get("sale_price") or item.get("price") or item.get("item_price") or 0
    if float(rate) > 0 and frappe.db.exists("Item", name):
        # only apply price if it is bigger than 0
        if not item_price_name:
            frappe.get_doc({
                "doctype": "Item Price",
                "price_list": price_list,
                "item_code": name,
                "price_list_rate": rate
            }).insert()
        else:
            item_rate = frappe.get_doc("Item Price", item_price_name)
            item_rate.price_list_rate = rate
            item_rate.save()

def update_item_stock_qty(item_code=None, woocommerce_item_id=None):
    woocommerce_settings = frappe.get_doc("WooCommerce Sync", "WooCommerce Sync")

    if item_code:    
        try:
            update_item_stock(item_code, woocommerce_settings)

        except woocommerceError as e:
            make_woocommerce_log(title="{0}".format(e), status="Error", method="update_item_stock_qty", message=frappe.get_traceback(),
                request_data=item_code, exception=True)

        except Exception as e:
            if e.args[0] and e.args[0].startswith("402"):
                raise e
                
            else:
                make_woocommerce_log(title="{0}".format(e), status="Error", method="update_item_stock_qty", message=frappe.get_traceback(),
                    request_data=item_code, exception=True)

    elif woocommerce_item_id:    
        item_code = get_item_code_from_woocommerce_item_id(woocommerce_item_id)
        
        try:
            update_item_stock(item_code, woocommerce_settings, woocommerce_item_id=woocommerce_item_id)

        except woocommerceError as e:
            make_woocommerce_log(title="{0}".format(e), status="Error", method="update_item_stock_qty", message=frappe.get_traceback(),
                request_data=item_code, exception=True)

        except Exception as e:
            if e.args[0] and e.args[0].startswith("402"):
                raise e
                
            else:
                make_woocommerce_log(title="{0}".format(e), status="Error", method="update_item_stock_qty", message=frappe.get_traceback(),
                    request_data=item_code, exception=True)

    else:  
        for item in frappe.get_all("WooCommerce Item", fields=["stock_keeping_unit"], filters={"sync_to_woocommerce": 1}):
            try:
                update_item_stock(item.stock_keeping_unit, woocommerce_settings)
            except woocommerceError as e:
                make_woocommerce_log(title="{0}".format(e), status="Error", method="sync_woocommerce_items", message=frappe.get_traceback(),
                    request_data=item, exception=True)

            except Exception as e:
                if e.args[0] and e.args[0].startswith("402"):
                    raise e
                else:
                    make_woocommerce_log(title="{0}".format(e), status="Error", method="sync_woocommerce_items", message=frappe.get_traceback(),
                        request_data=item, exception=True)

# def bulk_sync():
#     woocommerce_settings = frappe.get_doc("WooCommerce Sync", "WooCommerce Sync")
#     woocommerce_items = get_woocommerce_items_from_doctype()

#     for woocommerce_item in woocommerce_items:
#         item_code = woocommerce_item['name']
#         woocommerce_item_id = woocommerce_item['woocommerce_item_id']

#         try:
#             update_item_stock(item_code, woocommerce_settings, woocommerce_item_id)

#         except woocommerceError as e:
#             make_woocommerce_log(title="{0}".format(e), status="Error", method="bulk_sync", message=frappe.get_traceback(),
#                 request_data=item_code, exception=True)

#         except Exception as e:
#             if e.args[0] and e.args[0].startswith("402"):
#                 raise e
                
#             else:
#                 make_woocommerce_log(title="{0}".format(e), status="Error", method="bulk_sync", message=frappe.get_traceback(),
#                     request_data=item_code, exception=True)

# TODO: Finish this
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

    item_data = get_product_update_dict(actual_qty=qty)
    
    # make_woocommerce_log(title="Item Data", status="Success", method="get_product_update", message="Item Data: {0}".format(item_data))
    # make_woocommerce_log(title="Resource", status="Success", method="get_product_update", message="Resource: {0}".format(resource))
    
    try:
        post_request(resource, item_data)
        make_woocommerce_log(title="Updated Stock of {0}".format(item_code), status="Success", method="update_item_price",
        message="Stock Quantity: {0}\nManage Stock: {1}".format(item_data['stock_quantity'], item_data['manage_stock']))
        
    except requests.exceptions.HTTPError as e:
        if e.args[0] and e.args[0].startswith("404"):
            make_woocommerce_log(title=e.message, status="Error", method="update_item_stock", message=frappe.get_traceback(),
                request_data=item_data, exception=True)
            # disable_woocommerce_sync_for_item(item)

        else:
            raise e

def update_item(item_details, item_dict):

    item = frappe.get_doc("WooCommerce Item", item_details['name'])
        
    item_dict["stock_uom"] = item_details['stock_uom']

    if not item_dict["web_long_description"]:
        del item_dict["web_long_description"]

    if item_dict.get("warehouse"):
        del item_dict["warehouse"]

    del item_dict["description"]
    del item_dict["item_code"]
    del item_dict["variant_of"]
    del item_dict["item_name"]
    if "attributes" in item_dict:
        del item_dict["attributes"]

    item.update(item_dict)
    item.flags.ignore_mandatory = True
    item.save()

#TODO: Finish this
def update_item_price(item_code, price_list, woocommerce_item_id=None):
    item_price = get_item_price(item_code, price_list)

    # make_woocommerce_log(title="Item Code", status="Success", method="update_item_price", message="Item Code: {0}".format(item_code))
    # make_woocommerce_log(title="Price List", status="Success", method="update_item_price", message="Price List: {0}".format(price_list))
    # make_woocommerce_log(title="Item Price", status="Success", method="update_item_price", message="Item Price: {0}".format(item_price))

    if not woocommerce_item_id:
        woocommerce_item_id = get_woocommerce_item_id(item_code)

    resource = "wp-json/wc/v3/products/{0}".format(woocommerce_item_id)

    item_data = get_product_update_dict(item_price=item_price)
    
    # make_woocommerce_log(title="Item Data", status="Success", method="get_product_update", message="Item Data: {0}".format(item_data))
    # make_woocommerce_log(title="Resource", status="Success", method="get_product_update", message="Resource: {0}".format(resource))
    
    try:
        post_request(resource, item_data)
        make_woocommerce_log(title="Updated Price of {0}".format(item_code), status="Success", method="update_item_price",
        message="Price: {0}\nRegular Price: {1}".format(item_data['price'], item_data['regular_price']))
        
    except requests.exceptions.HTTPError as e:
        if e.args[0] and e.args[0].startswith("404"):
            make_woocommerce_log(title=e.message, status="Error", method="update_item_stock", message=frappe.get_traceback(),
                request_data=item_data, exception=True)
            # disable_woocommerce_sync_for_item(item)

        else:
            raise e

def is_item_exists(item_dict, attributes=None, variant_of=None):
    # woocommerce_item_id = str(item_dict['woocommerce_item_id'])
    # erp_item_match = frappe.get_all("WooCommerce Item",filters={'woocommerce_item_id': woocommerce_item_id})[0]

    # if erp_item_match:
    #     # item does exist in ERP --> Update
    #     update_item(item_details=erp_item_match, item_dict=item_dict)

    #     return True

    # else:
    return False

def has_variants(woocommerce_item):
    if len(woocommerce_item.get("variations")) >= 1:
        return True
    return False


# TODO: Finish this
def make_item(warehouse, woocommerce_item):
    # if has_variants(woocommerce_item):
    #     # woocommerce_item['variants'] = get_woocommerce_item_variants(woocommerce_item.get("id"))
        
    #     # attributes = create_attribute(woocommerce_item)
    #     # create_item(woocommerce_item, warehouse, 1, attributes=attributes)
    #     # create_item_variants(woocommerce_item, warehouse, attributes, woocommerce_variants_attr_list, woocommerce_item_list)

    # else:
    """woocommerce_item["variant_id"] = woocommerce_item['variants'][0]["id"]"""
    attributes = create_attribute(woocommerce_item)
    create_item(woocommerce_item, warehouse, attributes=attributes)

def create_item(woocommerce_item, warehouse, has_variant=0, attributes=None, variant_of=None, template_item=None):
    woocommerce_settings = frappe.get_doc("WooCommerce Sync", "WooCommerce Sync")
    valuation_method = woocommerce_settings.get("valuation_method")
    weight_unit =  woocommerce_settings.get("weight_unit")
    item_code = get_item_code_from_woocommerce_item(woocommerce_item)

    woocommerce_item_dict = {
        "doctype": "WooCommerce Item",
        "woocommerce_item_id": woocommerce_item.get("id"),
        "woocommerce_variant_id": woocommerce_item.get("id"),
        "variant_of": variant_of,
        "sync_to_woocommerce": 1,
        "is_stock_item": 1,
        "item_name": woocommerce_item.get("name"),
        "valuation_method": valuation_method,
        "description": woocommerce_item.get("description") or woocommerce_item.get("name"),
        "woocommerce_description": woocommerce_item.get("description") or woocommerce_item.get("name"),
        "woocommerce_short_description": woocommerce_item.get("short_description") or woocommerce_item.get("name"),
        "item_group": get_item_group(item_code) or None,
        "has_variants": has_variant,
        "attributes": attributes or [],
        "stock_uom": get_erpnext_uom(woocommerce_item, woocommerce_settings, attributes),
        "stock_keeping_unit": woocommerce_item.get("sku"), #or get_sku(woocommerce_item),
        "default_warehouse": warehouse,
        "image": get_item_image(woocommerce_item),
        "weight_uom": weight_unit, #woocommerce_item.get("weight_unit"),
        "weight_per_unit": woocommerce_item.get("weight"),
        "web_long_description": woocommerce_item.get("description") or woocommerce_item.get("name")
    }
    
    if not item_code:
        woocommerce_item_dict['item_code'] = str(woocommerce_item.get("id"))
    else:
        woocommerce_item_dict['item_code'] = item_code
        
    if template_item:
        #variants
        woocommerce_item_dict["product_category"] = get_categories(template_item, is_variant=True)
    else:
        #single & templates
        woocommerce_item_dict["product_category"] = get_categories(woocommerce_item, is_variant=False)
            
    if not is_item_exists(woocommerce_item_dict, attributes, variant_of=variant_of):
        item_details = get_item_details(woocommerce_item)

        if not item_details:
            new_item = frappe.get_doc(woocommerce_item_dict)
            new_item.insert()
            name = new_item.name

        else:
            update_item(item_details, woocommerce_item_dict)
            name = item_details.name

        # make_woocommerce_log(title='Item Name', status="Success", method="sync_woocommerce_items", message=name)
        # if not has_variant:
        #     add_to_price_list(woocommerce_item, name)
    
        frappe.db.commit()

# TODO: Finish this
# This function makes sure that all attributes exist in ERPNext as "Item Attribute"
def create_attribute(woocommerce_item):
    attribute = []

    # # WooCommerce item dict
    # for attr in woocommerce_item.get('attributes'):
    #     if not frappe.db.get_value("Item Attribute", attr.get("name"), "name"):
    #         new_item_attribute_entry = frappe.get_doc({
    #             "doctype": "Item Attribute",
    #             "attribute_name": attr.get("name"),
    #             "woocommerce_attribute_id": attr.get("id"),
    #             "item_attribute_values": []
    #         })
            
    #         for attr_value in attr.get("options"):
    #             row = new_item_attribute_entry.append('item_attribute_values', {})
    #             row.attribute_value = attr_value[:140]
    #             row.abbr = attr_value[:140]
            
    #         new_item_attribute_entry.insert()
            
    #         if len(attr.get("options")[0]) > 140:
    #             attribute_value = attr.get("options")[0][:140]
    #         else:
    #             attribute_value = attr.get("options")[0]
    #         attribute.append({"attribute": attr.get("name"), "attribute_value": attribute_value})
    #     else:
    #         # check for attribute values
    #         item_attr = frappe.get_doc("Item Attribute", attr.get("name"))
    #         if not item_attr.numeric_values:
    #         # line below hinders insert of new attribute values for existing attributes
    #         #    if not item_attr.get("woocommerce_attribute_id"):
    #                 item_attr.woocommerce_attribute_id = attr.get("id")
    #                 old_len = len(item_attr.item_attribute_values)
    #                 item_attr = set_new_attribute_values(item_attr, attr.get("options"))
    #                 if len(item_attr.item_attribute_values) > old_len:    # only save item attributes if they have changed
    #                     item_attr.save()
    #         if len(attr.get("options")) > 0:
    #             if len(attr.get("options")[0]) > 140:
    #                 attribute_value = attr.get("options")[0][:140]
    #             else:
    #                 attribute_value = attr.get("options")[0]
    #         else:
    #             attribute_value = None
    #         attribute.append({"attribute": attr.get("name"), "attribute_value": attribute_value})
    #             #frappe.log_error(attribute.append.format(attribute.append), "append attributes")
    #         #else:
    #             #attribute.append({
    #                 #"attribute": attr.get("name"),
    #                 #"from_range": item_attr.get("from_range"),
    #                 #"to_range": item_attr.get("to_range"),
    #                 #"increment": item_attr.get("increment"),
    #                 #"numeric_values": item_attr.get("numeric_values")
    #             #})

    return attribute
