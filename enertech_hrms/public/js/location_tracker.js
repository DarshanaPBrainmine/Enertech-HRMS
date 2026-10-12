(function () {
  const INTERVAL = 5 * 60 * 1000; // 5 minutes
  let timer = null;

  function send() {
    const attendance = localStorage.getItem("se_tracking_attendance");
    if (!attendance) return window.se_stop_tracking();

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        frappe.call({
          method: "enertech_hrms.enertech_hrms.utils.location_tracking.log_location",
          args: {
            attendance,
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
          },
        });
      },
      (err) => console.warn("Location error", err.message),
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 }
    );
  }

  window.se_start_tracking = function () {
    window.se_stop_tracking();
    send();
    timer = setInterval(send, INTERVAL);
  };

  window.se_stop_tracking = function () {
    if (timer) clearInterval(timer);
    timer = null;
  };

  $(document).on("startup", () => {
    if (localStorage.getItem("se_tracking_attendance")) window.se_start_tracking();
  });
})();