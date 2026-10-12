
# import json
# from datetime import datetime

# import frappe
# import requests
# from frappe.utils import convert_utc_to_system_timezone, now_datetime, nowdate


# @frappe.whitelist()
# def log_location(attendance, latitude, longitude, accuracy=None):
#     """Browser based logging (kept for manual / fallback use)."""
#     employee = frappe.db.get_value("Service Engineer Attendence", attendance, "employee")
#     if not employee:
#         frappe.throw("Invalid attendance record")

#     doc = frappe.get_doc({
#         "doctype": "Service Engineer Location Log",
#         "employee": employee,
#         "attendance": attendance,
#         "timestamp": now_datetime(),
#         "latitude": latitude,
#         "longitude": longitude,
#         "accuracy": accuracy,
#     }).insert(ignore_permissions=True)

#     frappe.enqueue(
#         "enertech_hrms.enertech_hrms.utils.location_tracking.fill_address",
#         log=doc.name, lat=latitude, lng=longitude,
#     )
#     return doc.name


# @frappe.whitelist(allow_guest=True)
# def push_location():
#     """Endpoint for Traccar Client (background tracking, works with screen locked).

#     Needs `se_tracker_secret` in site_config.json.
#     Traccar Client sends: id, lat, lon, timestamp, accuracy, speed, bearing, altitude, batt
#     The device id in the app must be the Employee ID (e.g. EUPL152).
#     """
#     data = dict(frappe.form_dict)
#     if frappe.request.data:
#         try:
#             data.update(json.loads(frappe.request.data))
#         except Exception:
#             pass

#     secret = frappe.conf.get("se_tracker_secret")
#     if not secret or data.get("key") != secret:
#         frappe.throw("Unauthorized", frappe.PermissionError)

#     employee = data.get("id") or data.get("device_id")
#     lat, lon = data.get("lat"), data.get("lon")
#     if not (employee and lat and lon) or not frappe.db.exists("Employee", employee):
#         frappe.throw("Invalid data")

#     # track only if today's latest attendance record is Check In
#     last = frappe.get_all(
#         "Service Engineer Attendence",
#         filters={"employee": employee, "creation": [">=", nowdate()]},
#         fields=["name", "checkin_type"],
#         order_by="creation desc",
#         limit=1,
#     )
#     if not last or last[0].checkin_type != "Check In":
#         return "ignored"

#     # use the time recorded by the phone (Traccar may send offline points later)
#     ts = now_datetime()
#     if data.get("timestamp"):
#         try:
#             ts = convert_utc_to_system_timezone(
#                 datetime.utcfromtimestamp(int(float(data["timestamp"])))
#             ).replace(tzinfo=None)
#         except Exception:
#             pass

#     doc = frappe.get_doc({
#         "doctype": "Service Engineer Location Log",
#         "employee": employee,
#         "attendance": last[0].name,
#         "timestamp": ts,
#         "latitude": lat,
#         "longitude": lon,
#         "accuracy": data.get("accuracy"),
#     }).insert(ignore_permissions=True)
#     frappe.db.commit()

#     frappe.enqueue(
#         "enertech_hrms.enertech_hrms.utils.location_tracking.fill_address",
#         log=doc.name, lat=lat, lng=lon,
#     )
#     return doc.name


# def fill_address(log, lat, lng):
#     try:
#         r = requests.get(
#             "https://nominatim.openstreetmap.org/reverse",
#             params={"lat": lat, "lon": lng, "format": "json"},
#             headers={"User-Agent": "enertech-hrms"},
#             timeout=10,
#         )
#         if r.ok:
#             frappe.db.set_value(
#                 "Service Engineer Location Log", log, "address",
#                 r.json().get("display_name"),
#             )
#             frappe.db.commit()
#     except Exception:
#         frappe.log_error(frappe.get_traceback(), "Location address lookup failed")



import json
from datetime import datetime

import frappe
import requests
from frappe.utils import convert_utc_to_system_timezone, now_datetime, nowdate


@frappe.whitelist()
def log_location(attendance, latitude, longitude, accuracy=None):
    """Browser based logging (kept for manual / fallback use)."""
    employee = frappe.db.get_value("Service Engineer Attendence", attendance, "employee")
    if not employee:
        frappe.throw("Invalid attendance record")

    doc = frappe.get_doc({
        "doctype": "Service Engineer Location Log",
        "employee": employee,
        "attendance": attendance,
        "timestamp": now_datetime(),
        "latitude": latitude,
        "longitude": longitude,
        "accuracy": accuracy,
    }).insert(ignore_permissions=True)

    frappe.enqueue(
        "enertech_hrms.enertech_hrms.utils.location_tracking.fill_address",
        log=doc.name, lat=latitude, lng=longitude,
    )
    return doc.name


@frappe.whitelist(allow_guest=True)
def push_location():
    """Endpoint for Traccar Client (background tracking, works with screen locked).

    Needs `se_tracker_secret` in site_config.json.
    Traccar Client sends: id, lat, lon, timestamp, accuracy, speed, bearing, altitude, batt
    The device id in the app must be the Employee ID (e.g. EUPL152).
    """
    data = dict(frappe.form_dict)
    if frappe.request.data:
        try:
            data.update(json.loads(frappe.request.data))
        except Exception:
            pass

    secret = frappe.conf.get("se_tracker_secret")
    if not secret or data.get("key") != secret:
        frappe.throw("Unauthorized", frappe.PermissionError)

    employee = data.get("id") or data.get("device_id")
    lat, lon = data.get("lat"), data.get("lon")
    if not (employee and lat and lon) or not frappe.db.exists("Employee", employee):
        frappe.throw("Invalid data")

    # track only if today's latest attendance record is Check In
    last = frappe.get_all(
        "Service Engineer Attendence",
        filters={"employee": employee, "creation": [">=", nowdate()]},
        fields=["name", "checkin_type"],
        order_by="creation desc",
        limit=1,
    )
    if not last or last[0].checkin_type != "Check In":
        return "ignored"

    # use the time recorded by the phone (Traccar may send offline points later)
    ts = now_datetime()
    if data.get("timestamp"):
        try:
            ts = convert_utc_to_system_timezone(
                datetime.utcfromtimestamp(int(float(data["timestamp"])))
            ).replace(tzinfo=None)
        except Exception:
            pass

    doc = frappe.get_doc({
        "doctype": "Service Engineer Location Log",
        "employee": employee,
        "attendance": last[0].name,
        "timestamp": ts,
        "latitude": lat,
        "longitude": lon,
        "accuracy": data.get("accuracy"),
    }).insert(ignore_permissions=True)
    frappe.db.commit()

    frappe.enqueue(
        "enertech_hrms.enertech_hrms.utils.location_tracking.fill_address",
        log=doc.name, lat=lat, lng=lon,
    )
    return doc.name


def fill_address(log, lat, lng):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lng, "format": "json"},
            headers={"User-Agent": "enertech-hrms"},
            timeout=10,
        )
        if r.ok:
            frappe.db.set_value(
                "Service Engineer Location Log", log, "address",
                r.json().get("display_name"),
            )
            frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Location address lookup failed")


@frappe.whitelist()
def get_day_logs(employee, date):
    """Return all location logs of an employee for one date (for Attendance form)."""
    if not frappe.has_permission("Attendance", "read") and not frappe.has_permission(
        "Service Engineer Attendence", "read"
    ):
        frappe.throw("Not permitted", frappe.PermissionError)

    from frappe.utils import getdate

    day = getdate(date)
    return frappe.get_all(
        "Service Engineer Location Log",
        filters={
            "employee": employee,
            "timestamp": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]],
        },
        fields=["name", "timestamp", "address", "latitude", "longitude", "accuracy"],
        order_by="timestamp asc",
        limit_page_length=500,
    )