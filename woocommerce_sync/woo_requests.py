import frappe
import requests
from frappe import _
from frappe.utils import cint
from .utils import make_woocommerce_log
from .exceptions import woocommerceError
from requests_oauthlib import OAuth1Session

per_page = 100

def get_woocommerce_settings():
    d = frappe.get_doc("WooCommerce Sync", "WooCommerce Sync")
    
    if d.woocommerce_url:
        d.api_secret = d.get_password(fieldname='api_secret')
        return d.as_dict()
    
    else:
        frappe.throw(_("woocommerce store URL is not configured on WooCommerce Sync"), woocommerceError)

def get_request(path, data=None):
    woocommerce_settings = get_woocommerce_settings()

    woocommerce_url = woocommerce_settings["woocommerce_url"]
    api_key = woocommerce_settings["api_key"]
    api_secret = woocommerce_settings["api_secret"]

    woocommerce = OAuth1Session(client_key=api_key, client_secret=api_secret) 

    # Construct the API endpoint
    api_endpoint = f'{woocommerce_url}{path}'
    
    # make_woocommerce_log(title="API Endpoint", status="Success", method="get_request", message=api_endpoint, request_data=data, exception=True)

    r = woocommerce.get(api_endpoint)
    
    if r.status_code != requests.codes.ok:
        make_woocommerce_log(title="WooCommerce get error {0}".format(r.status_code), 
            status="Error", 
            method="get_request", 
            message="{0}: {1}".format(r.url, r.json()),
            request_data=data, 
            exception=True)
            
    # make_woocommerce_log(title="SUCCESS: GET", status="Success", method="get_request", message=str(r.json()), request_data=data, exception=True)

    return r.json()

def post_request(path, data):
    woocommerce_settings = get_woocommerce_settings()

    woocommerce_url = woocommerce_settings["woocommerce_url"]
    api_key = woocommerce_settings["api_key"]
    api_secret = woocommerce_settings["api_secret"]

    woocommerce = OAuth1Session(client_key=api_key, client_secret=api_secret) 

    # Construct the API endpoint
    api_endpoint = f'{woocommerce_url}{path}'

    # make_woocommerce_log(title="API Endpoint", status="Success", method="get_request", message=api_endpoint, request_data=data, exception=True)
    
    r = woocommerce.post(api_endpoint, data)
    
    # make_woocommerce_log(title="Json", status="Success", method="post_request", message=str(r.json()), request_data=data, exception=True)

    if r.status_code != requests.codes.ok:
        make_woocommerce_log(title="WooCommerce post error {0}".format(r.status_code), 
            status="Error", 
            method="post_request", 
            message="{0}: {1}".format(r.url, r.json()),
            request_data=data, 
            exception=True)
            
    # make_woocommerce_log(title="SUCCESS: POST", status="Success", method="post_request", message=str(r.json()), request_data=data, exception=True)

    return r.json()

def put_request(path, data):
    woocommerce_settings = get_woocommerce_settings()

    woocommerce_url = woocommerce_settings["woocommerce_url"]
    api_key = woocommerce_settings["api_key"]
    api_secret = woocommerce_settings["api_secret"]

    woocommerce = OAuth1Session(client_key=api_key, client_secret=api_secret) 

    # Construct the API endpoint
    api_endpoint = f'{woocommerce_url}{path}'
    
    r = woocommerce.put(api_endpoint, data)
    
    if r.status_code != requests.codes.ok:
        make_woocommerce_log(title="WooCommerce put error {0}".format(r.status_code), 
            status="Error", 
            method="put_request", 
            message="{0}: {1}".format(r.url, r.json()),
            request_data=data, 
            exception=True)
            
    # make_woocommerce_log(title="SUCCESS: PUT", status="Success", method="put_request", message=str(r.json()), request_data=data, exception=True)

    return r.json()

# TODO: Fix This
def get_filtering_condition():
    woocommerce_settings = get_woocommerce_settings()

    # if woocommerce_settings.last_sync_datetime:
    #     last_sync_datetime = get_datetime(woocommerce_settings.last_sync_datetime)
        
    #     return "modified_after={0}".format(last_sync_datetime.isoformat() )
    return ''

def get_woocommerce_items(ignore_filter_conditions=False):
    woocommerce_settings = get_woocommerce_settings()
    woocommerce_products = []
    filter_condition = ''
    page = 1

    if not ignore_filter_conditions:
        filter_condition = get_filtering_condition()

        if woocommerce_settings['sync_only_published'] == 1:
            filter_condition += "status=publish"

    while True:
        r = get_request('wp-json/wc/v3/products?per_page={0}&page={1}&{2}'.format(per_page, page, filter_condition))

        if not r:
            break

        woocommerce_products.extend(r)
        page += 1

    return woocommerce_products

def get_woocommerce_item_variants(woocommerce_product_id):
    woocommerce_product_variants = []
    filter_condition = ''

    while True:
        r = get_request('wp-json/wc/v3/products/{0}/variations?per_page={1}&page={2}&{3}'.format(woocommerce_product_id, per_page, page, filter_condition))

        if not r:
            break

        woocommerce_product_variants.extend(r)
        page += 1

    return woocommerce_product_variants

# def get_woocommerce_item_image(woocommerce_product_id):
#     return get_request("products/{0}".format(woocommerce_product_id))["images"]


# def get_woocommerce_tax(woocommerce_tax_id):
#     return get_request("taxes/{0}".format(woocommerce_tax_id))