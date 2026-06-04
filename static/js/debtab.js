// DebTab — Global JS utilities

// Auto-dismiss alerts after 5 seconds
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".alert.alert-dismissible").forEach(function (el) {
    setTimeout(function () {
      var bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });
});
