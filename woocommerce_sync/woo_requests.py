import frappe
import requests
from frappe import _
from frappe.utils import cint
from .utils import make_woocommerce_log
from .exceptions import woocommerceError
from requests_oauthlib import OAuth1Session

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