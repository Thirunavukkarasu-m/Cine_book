// CineBook - shared front-end interactions

document.addEventListener('DOMContentLoaded', function () {
    var toggle = document.getElementById('navToggle');
    var links = document.getElementById('navLinks');

    if (toggle && links) {
        toggle.addEventListener('click', function () {
            links.classList.toggle('open');
        });
    }

    // Auto-dismiss success/info messages after a few seconds.
    document.querySelectorAll('.message-success, .message-info').forEach(function (el) {
        setTimeout(function () {
            el.style.transition = 'opacity .4s';
            el.style.opacity = '0';
            setTimeout(function () { el.remove(); }, 400);
        }, 5000);
    });

    // Confirm before cancelling a booking.
    document.querySelectorAll('[data-confirm]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!window.confirm(form.getAttribute('data-confirm'))) {
                e.preventDefault();
            }
        });
    });

    // Print ticket button.
    document.querySelectorAll('[data-print]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            window.print();
        });
    });
});
