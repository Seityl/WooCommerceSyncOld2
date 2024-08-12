// Copyright (c) 2024, Jeriel Francis and contributors
// For license information, please see license.txt

frappe.ui.form.on("WooCommerce Sync", {
	refresh: function(frm) {
        sync_based_on_visibility(frm);
        sync_based_on_options_visibility(frm);
	},

    sync_options: function(frm) {
        sync_based_on_visibility(frm);
    }, 

    sync_based_on: function(frm) {
        sync_based_on_options_visibility(frm);
    }
});

function sync_based_on_visibility(frm) {
    if (frm.doc.sync_options === 'Single Item Sync') {
        frm.toggle_display('sync_based_on', true);
        frm.remove_custom_button('Sync Items to WooCommerce')
        
        frm.add_custom_button(__('Sync Item'), function() {
            if (frm.is_dirty()) {
                frm.save();
                sync_item(frm);
            }
            else {
                sync_item(frm);
            }
        });
    }
    else if (frm.doc.sync_options === 'Bulk Sync') {
        clear_sync_based_on_values(frm);

        frm.remove_custom_button('Sync Item');
        frm.toggle_display('sync_based_on', false);
        frm.set_value('sync_based_on', '');

        frm.add_custom_button(__('Sync WooCommerce Items'), function() {
            frappe.call({
                method:"woocommerce_sync.api.sync_woocommerce_item_list",
                freeze: true,
                freeze_message: __('Syncing WooCommerce Items...')
            })
        });
    }
}

function sync_based_on_options_visibility(frm) {
    if (frm.doc.sync_based_on === '') {
        clear_sync_based_on_values(frm);

        frm.toggle_display('item_code', false);
        frm.toggle_display('woocommerce_item_id', false);
    }
    else if (frm.doc.sync_based_on === 'Item Code') {
        frm.toggle_display('item_code', true);
        frm.toggle_display('woocommerce_item_id', false);
    } 
    else if (frm.doc.sync_based_on === 'WooCommerce Item ID') {
        frm.toggle_display('woocommerce_item_id', true);
        frm.toggle_display('item_code', false);
    }
}

function clear_sync_based_on_values(frm) {
    frm.set_value('item_code', '');
    frm.set_value('woocommerce_item_id', '');
}

function sync_item(frm) {
    if (frm.doc.sync_based_on) {
        if (frm.doc.woocommerce_item_id || frm.doc.item_code) {
            frappe.call({
                method:"woocommerce_sync.api.sync_single_item_to_woocommerce",
                freeze: true,
                freeze_message: __('Syncing Item...')                            
            }).then(() => {
                frappe.msgprint(`Successfully Synced ${frm.doc.item_code}.`);
                clear_sync_based_on_values(frm);
            })
        }
        else {
            frappe.msgprint('Error Syncing Item: Enter Item Code / WooCommerce Item ID');
        }
    }
    else {
        frappe.msgprint('Error Syncing Item: Select Item Code / WooCommerce Item ID from Sync Based On');
    }
}