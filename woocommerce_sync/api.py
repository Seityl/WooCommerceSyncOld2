import json
import frappe
import requests
from frappe import _
from erpnext.stock.utils import get_bin
from .exceptions import woocommerceError
from frappe.utils import get_datetime, cint
from .utils import make_woocommerce_log, disable_woocommerce_sync_for_item
from .woo_requests import get_woocommerce_settings, get_request, post_request, put_request
from .item_sync import bulk_sync, sync_item_by_item_code, get_item_codes_and_ids_from_woocommerce, add_woocommerce_items_to_erp, get_woocommerce_items_from_doctype

@frappe.whitelist()
def bulk_sync_items_to_woocommerce():
    # add_woocommerce_items_to_erp()
    bulk_sync()
    # make_woocommerce_log(title="Item Codes", status="Success", method="bulk_sync_items_to_woocommerce", message=str(item_codes))

# TODO: Finish this
@frappe.whitelist()
def sync_single_item_to_woocommerce():
    woocommerce_settings = get_woocommerce_settings()
    sync_based_on = woocommerce_settings["sync_based_on"] 

    # make_woocommerce_log(title="Sync Based On", status="Success", method="sync_single_item_to_woocommerce", message=sync_based_on)
    
    # if (sync_based_on == "WooCommerce Item ID"):
        # sync_item_by_woocommerce_id()

    if (sync_based_on == "Item Code"):
        sync_item_by_item_code()