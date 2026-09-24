// CineBook - dynamic seat selection
// NOTE: All totals shown here are for DISPLAY ONLY. The Django backend
// always re-validates seat availability and recalculates the final price
// from the database before a booking is created.

document.addEventListener('DOMContentLoaded', function () {
    var seatMap = document.getElementById('seatMap');
    if (!seatMap) return;

    var MAX_SEATS = parseInt(seatMap.dataset.maxSeats || '10', 10);

    var selected = new Set();
    var seatIdsInput = document.getElementById('seatIdsInput');
    var continueBtn = document.getElementById('continueBtn');
    var countLabel = document.getElementById('selectedCount');
    var namesLabel = document.getElementById('selectedNames');
    var totalLabel = document.getElementById('selectedTotal');

    function refreshSummary() {
        var count = selected.size;
        var total = 0;
        var names = [];

        selected.forEach(function (id) {
            var el = seatMap.querySelector('.seat[data-id="' + id + '"]');
            if (el) {
                total += parseFloat(el.dataset.price || '0');
                names.push(el.dataset.number);
            }
        });

        countLabel.textContent = count;
        totalLabel.textContent = '\u20B9' + total.toFixed(2);
        namesLabel.textContent = names.length ? names.join(', ') : 'None selected';

        seatIdsInput.value = Array.from(selected).join(',');
        continueBtn.disabled = count === 0;
    }

    seatMap.addEventListener('click', function (e) {
        var seat = e.target.closest('.seat');
        if (!seat || seat.classList.contains('booked')) return;

        var id = seat.dataset.id;

        if (selected.has(id)) {
            selected.delete(id);
            seat.classList.remove('selected');
        } else {
            if (selected.size >= MAX_SEATS) {
                alert('You can select a maximum of ' + MAX_SEATS + ' seats per booking.');
                return;
            }
            selected.add(id);
            seat.classList.add('selected');
        }

        refreshSummary();
    });

    refreshSummary();
});
