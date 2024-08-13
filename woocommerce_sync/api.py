import json
import frappe
import requests
from frappe import _
from erpnext.stock.utils import get_bin
from .exceptions import woocommerceError
from frappe.utils import get_datetime, cint
from .utils import make_woocommerce_log, disable_woocommerce_sync_for_item, disable_woocommerce_sync_on_exception
from .woo_requests import get_woocommerce_items, get_woocommerce_settings, get_request, post_request, put_request
from .item_sync import get_item_code_from_woocommerce_item_id, sync_products, sync_individual_item, get_item_codes_and_ids_from_woocommerce, add_woocommerce_items_to_erp, get_woocommerce_items_from_doctype, update_item_stock_qty

@frappe.whitelist()
def sync_single_item_to_woocommerce():
    woocommerce_settings = get_woocommerce_settings()
    sync_based_on = woocommerce_settings["sync_based_on"] 

    if (sync_based_on == "WooCommerce Item ID"):
        sync_individual_item(woocommerce_item_id=woocommerce_settings['woocommerce_item_id'])

    if (sync_based_on == "Item Code"):
        sync_individual_item(item_code=woocommerce_settings['item_code'])

# TODO: Finish this
@frappe.whitelist()
def sync_woocommerce_items():
    woocommerce_settings = frappe.get_doc("WooCommerce Sync")

    make_woocommerce_log(title="Item Sync Job Queued", status="Queued", method=frappe.local.form_dict.cmd, message="Item Sync Job Queued")
    
    if woocommerce_settings.enable_sync:
        make_woocommerce_log(title="Item Sync Job Started", status="Started", method=frappe.local.form_dict.cmd, message="Item Sync Job Started")
        try :
            validate_woocommerce_settings(woocommerce_settings)
            sync_start_time = frappe.utils.now()
            sync_products(woocommerce_settings.price_list, woocommerce_settings.warehouse, True if woocommerce_settings.enable_sync == 1 else False)
            # sync_customers()
            # sync_orders()
            update_item_stock_qty()
            frappe.db.set_value("WooCommerce Sync", None, "last_sync_datetime", sync_start_time)
            make_woocommerce_log(title="Item Sync Completed", status="Success", method=frappe.local.form_dict.cmd, message= "Synced Item List")

        except Exception as e:
            if e.args[0] and hasattr(e.args[0], "startswith") and e.args[0].startswith("402"):
                make_woocommerce_log(title="woocommerce has suspended your account", status="Error",
                    method="sync_woocommerce_resources", message=_("""woocommerce has suspended your account till
                    you complete the payment. We have disabled ERPNext woocommerce Sync. Please enable it once
                    your complete the payment at woocommerce."""), exception=True)

                disable_woocommerce_sync_on_exception()
            
            else:
                make_woocommerce_log(title="sync has terminated", status="Error", method="sync_woocommerce_resources",
                    message=frappe.get_traceback(), exception=True)
                    
    else:
        frappe.msgprint("WooCommerce Sync is not enabled. Click on 'Enable Sync' to connect ERPNext and your WooCommerce store.")
        make_woocommerce_log(
            title="WooCommerce Sync is disabled",
            status="Error",
            method="sync_woocommerce_resources",
            message=_("""woocommerce connector is not enabled. Click on 'Connect to woocommerce' to connect ERPNext and your woocommerce store."""),
            exception=True)

def validate_woocommerce_settings(woocommerce_settings):
    """
        This will validate mandatory fields and access token or app credentials 
        by calling validate() of WooCommerce Config.
    """
    try:
        woocommerce_settings.save()
    except woocommerceError:
        disable_woocommerce_sync_on_exception()