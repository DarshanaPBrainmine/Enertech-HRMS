// Copyright (c) 2026, shrey and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Engineer Location Log", {
  refresh(frm) {
    if (frm.doc.latitude && frm.doc.longitude) {
      frm.add_custom_button(__("Open in Google Maps"), () => {
        window.open(
          `https://www.google.com/maps?q=${frm.doc.latitude},${frm.doc.longitude}`,
          "_blank"
        );
      });
    }
  },
});