// frappe.ui.form.on("Service Engineer Attendence", {
// 	onload: function(frm) {
// 		if (frm.is_new()) {
// 			capture_gps(frm);
// 		}
// 	},
// 	checkin_type: function(frm) {
// 		capture_gps(frm);
// 	},
// 	location_on_map: function(frm) {
// 		if (frm.doc.location_on_map) {
// 			try {
// 				let geo = JSON.parse(frm.doc.location_on_map);
// 				if (geo && geo.features && geo.features.length) {
// 					let coords = geo.features[0].geometry.coordinates;
// 					frm.set_value('longitude', coords[0]);
// 					frm.set_value('latitude', coords[1]);
// 					reverse_geocode(frm, coords[1], coords[0]);
// 				}
// 			} catch (e) {
// 				console.log("Invalid geolocation data");
// 			}
// 		}
// 	}
// });

// function capture_gps(frm) {
// 	if (navigator.geolocation) {
// 		navigator.geolocation.getCurrentPosition(
// 			function(position) {
// 				let lat = position.coords.latitude;
// 				let lng = position.coords.longitude;

// 				frm.set_value('latitude', lat);
// 				frm.set_value('longitude', lng);
// 				frm.set_value('gps_accuracy', position.coords.accuracy);

// 				let geojson = {
// 					"type": "FeatureCollection",
// 					"features": [{
// 						"type": "Feature",
// 						"properties": {},
// 						"geometry": {
// 							"type": "Point",
// 							"coordinates": [lng, lat]
// 						}
// 					}]
// 				};
// 				frm.set_value('location_on_map', JSON.stringify(geojson));

// 				frm.refresh_field('latitude');
// 				frm.refresh_field('longitude');
// 				frm.refresh_field('gps_accuracy');
// 				frm.refresh_field('location_on_map');

// 				reverse_geocode(frm, lat, lng);
// 			},
// 			function(error) {
// 				frappe.msgprint('Location access is required. Please allow location permission.');
// 			},
// 			{ enableHighAccuracy: true, timeout: 10000 }
// 		);
// 	} else {
// 		frappe.msgprint('Geolocation is not supported in this browser.');
// 	}
// }

// function reverse_geocode(frm, lat, lng) {
// 	fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`)
// 		.then(response => response.json())
// 		.then(data => {
// 			if (data && data.display_name) {
// 				frm.set_value('location_address', data.display_name);
// 				frm.refresh_field('location_address');
// 			}
// 		})
// 		.catch(error => {
// 			console.log("Reverse geocoding failed:", error);
// 		});
// }

frappe.ui.form.on("Service Engineer Attendence", {
	onload: function(frm) {
		if (frm.is_new()) {
			capture_gps(frm);
		}
	},

	checkin_type: function(frm) {
		capture_gps(frm);
	},

	location_on_map: function(frm) {
		if (frm.doc.location_on_map) {
			try {
				let geo = JSON.parse(frm.doc.location_on_map);
				if (geo && geo.features && geo.features.length) {
					let coords = geo.features[0].geometry.coordinates;
					frm.set_value('longitude', coords[0]);
					frm.set_value('latitude', coords[1]);
					reverse_geocode(frm, coords[1], coords[0]);
				}
			} catch (e) {
				console.log("Invalid geolocation data");
			}
		}
	},

	// Start tracking on Check In, stop on Check Out
	after_save: function(frm) {
		if (frm.doc.checkin_type === "Check In") {
			localStorage.setItem("se_tracking_attendance", frm.doc.name);
			window.se_start_tracking && window.se_start_tracking();
			frappe.show_alert({ message: __("Live tracking started"), indicator: "green" });
		} else {
			localStorage.removeItem("se_tracking_attendance");
			window.se_stop_tracking && window.se_stop_tracking();
			frappe.show_alert({ message: __("Live tracking stopped"), indicator: "orange" });
		}
	}
});

function capture_gps(frm) {
	if (navigator.geolocation) {
		navigator.geolocation.getCurrentPosition(
			function(position) {
				let lat = position.coords.latitude;
				let lng = position.coords.longitude;

				frm.set_value('latitude', lat);
				frm.set_value('longitude', lng);
				frm.set_value('gps_accuracy', position.coords.accuracy);

				let geojson = {
					"type": "FeatureCollection",
					"features": [{
						"type": "Feature",
						"properties": {},
						"geometry": {
							"type": "Point",
							"coordinates": [lng, lat]
						}
					}]
				};
				frm.set_value('location_on_map', JSON.stringify(geojson));

				frm.refresh_field('latitude');
				frm.refresh_field('longitude');
				frm.refresh_field('gps_accuracy');
				frm.refresh_field('location_on_map');

				reverse_geocode(frm, lat, lng);
			},
			function(error) {
				frappe.msgprint('Location access is required. Please allow location permission.');
			},
			{ enableHighAccuracy: true, timeout: 10000 }
		);
	} else {
		frappe.msgprint('Geolocation is not supported in this browser.');
	}
}

function reverse_geocode(frm, lat, lng) {
	fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`)
		.then(response => response.json())
		.then(data => {
			if (data && data.display_name) {
				frm.set_value('location_address', data.display_name);
				frm.refresh_field('location_address');
			}
		})
		.catch(error => {
			console.log("Reverse geocoding failed:", error);
		});
}