var NotificationSystem = {
  modal: null,
  content: null,
  icon: null,
  title: null,
  message: null,
  closeBtn: null,
  progress: null,
  autoHideTimeout: null,
  hideTimeout: null,

  types: {
    success: {
      icon: "✓",
      iconBg: "bg-emerald-500/20 text-emerald-400",
      border: "border-emerald-500/50",
      progressClass: "bg-emerald-500",
    },
    error: {
      icon: "✕",
      iconBg: "bg-red-500/20 text-red-400",
      border: "border-red-500/50",
      progressClass: "bg-red-500",
    },
    info: {
      icon: "ℹ",
      iconBg: "bg-blue-500/20 text-blue-400",
      border: "border-blue-500/50",
      progressClass: "bg-blue-500",
    },
    warning: {
      icon: "⚠",
      iconBg: "bg-yellow-500/20 text-yellow-400",
      border: "border-yellow-500/50",
      progressClass: "bg-yellow-500",
    },
  },

  init: function () {
    this.modal = document.getElementById("notificationModal");
    this.content = document.getElementById("notificationContent");
    this.icon = document.getElementById("notificationIcon");
    this.title = document.getElementById("notificationTitle");
    this.message = document.getElementById("notificationMessage");
    this.closeBtn = document.getElementById("notificationClose");
    this.progress = document.getElementById("notificationProgress");

    if (
      !this.modal ||
      !this.content ||
      !this.icon ||
      !this.title ||
      !this.message ||
      !this.closeBtn ||
      !this.progress
    ) {
      return;
    }

    this.closeBtn.addEventListener("click", this.hide.bind(this));

    document.addEventListener("keydown", function (e) {
      if (
        e.key === "Escape" &&
        !NotificationSystem.modal.classList.contains("hidden")
      ) {
        NotificationSystem.hide();
      }
    });
  },

  show: function (message, type, title) {
    var config = this.types[type] || this.types.info;

    if (!type) {
      type = "info";
    }

    window.clearTimeout(this.autoHideTimeout);
    window.clearTimeout(this.hideTimeout);

    this.content.className =
      "pointer-events-auto mx-auto w-full max-w-md translate-y-[-8px] rounded-2xl border bg-dark-card shadow-2xl overflow-hidden transform transition-all duration-200 opacity-0 " +
      config.border;
    this.icon.className =
      "w-12 h-12 rounded-full flex items-center justify-center text-xl " +
      config.iconBg;
    this.icon.textContent = config.icon;
    this.title.textContent = title || this.getTitleFromType(type);
    this.message.textContent = message;

    this.progress.className =
      "h-full w-full origin-left scale-x-100 " + config.progressClass;
    this.progress.style.transition = "transform 3s linear";
    this.progress.style.transform = "scaleX(1)";

    this.modal.classList.remove("hidden");

    window.setTimeout(function () {
      NotificationSystem.content.classList.remove(
        "translate-y-[-8px]",
        "opacity-0",
      );
      NotificationSystem.content.classList.add("translate-y-0", "opacity-100");
      NotificationSystem.progress.style.transform = "scaleX(0)";
    }, 16);

    this.autoHideTimeout = window.setTimeout(function () {
      NotificationSystem.hide();
    }, 3000);
  },

  hide: function () {
    window.clearTimeout(this.autoHideTimeout);
    window.clearTimeout(this.hideTimeout);

    if (!this.modal || !this.content) {
      return;
    }

    this.content.classList.remove("translate-y-0", "opacity-100");
    this.content.classList.add("translate-y-[-8px]", "opacity-0");

    this.hideTimeout = window.setTimeout(function () {
      NotificationSystem.modal.classList.add("hidden");
    }, 200);
  },

  getTitleFromType: function (type) {
    var titles = {
      success: "Berhasil",
      error: "Gagal",
      info: "Informasi",
      warning: "Peringatan",
    };

    return titles[type] || "Pemberitahuan";
  },
};

function showQueuedMessages() {
  var messagesContainer = document.querySelector("[data-django-messages]");

  if (!messagesContainer) {
    return;
  }

  var messages = messagesContainer.querySelectorAll("[data-message]");
  var index;
  for (index = 0; index < messages.length; index++) {
    (function (msg, delayIndex) {
      var type = msg.getAttribute("data-message") || "info";
      var text = msg.getAttribute("data-text") || "";

      window.setTimeout(
        function () {
          NotificationSystem.show(text, type);
        },
        150 + delayIndex * 200,
      );
    })(messages[index], index);
  }
}

function initializeNotifications() {
  NotificationSystem.init();
  showQueuedMessages();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeNotifications);
} else {
  initializeNotifications();
}
