// frappe.ui.form.on("Gate Pass", {
//     gate_pass_type(frm) {
//         if (frm.doc.gate_pass_type === "Personal") {
//             frm.set_value("official_type", "");
//         }
//     },
//     from_time: calc_duration,
//     to_time: calc_duration,
// });

// function calc_duration(frm) {
//     if (frm.doc.from_time && frm.doc.to_time) {
//         const f = moment(frm.doc.from_time, "HH:mm:ss");
//         const t = moment(frm.doc.to_time, "HH:mm:ss");
//         frm.set_value("duration_mins", t.diff(f, "minutes"));
//     }
// }


frappe.ui.form.on("Gate Pass", {
    refresh(frm) {
        if (frm.is_new() && !frm.doc.employee) {
            frappe.db.get_value("Employee", { user_id: frappe.session.user }, "name")
                .then(r => {
                    if (r.message && r.message.name) {
                        frm.set_value("employee", r.message.name);
                    }
                });
        }
    },

    gate_pass_type(frm) {
        if (frm.doc.gate_pass_type === "Personal") {
            frm.set_value("official_type", "");
        }
    },

    from_time: calc_duration,
    to_time: calc_duration,
});

function calc_duration(frm) {
    if (frm.doc.from_time && frm.doc.to_time) {
        const f = moment(frm.doc.from_time, "HH:mm:ss");
        const t = moment(frm.doc.to_time, "HH:mm:ss");
        frm.set_value("duration_mins", t.diff(f, "minutes"));
    }
}