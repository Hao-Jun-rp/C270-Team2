/*
=========================================================

Dashboard JavaScript

Handles:

- Interactive Calendar
- Cleaning Tip Carousel
- Future dashboard interactions

=========================================================
*/

// ------------------------------------------------------
// Booking Calendar Data
//
// Reads booking events passed from Flask.
// ------------------------------------------------------

const bookingEvents = JSON.parse(
    document
        .getElementById("dashboard-calendar-data")
        .textContent
);

document.addEventListener("DOMContentLoaded", function () {

    //------------------------------------------------------
    // Status Colours
    //------------------------------------------------------

    bookingEvents.forEach(event => {

        switch (event.extendedProps.status) {

            case "Pending":
                event.backgroundColor = "#F59E0B";
                event.borderColor = "#F59E0B";
                break;

            case "Confirmed":
                event.backgroundColor = "#2563EB";
                event.borderColor = "#2563EB";
                break;

            case "Completed":
                event.backgroundColor = "#22C55E";
                event.borderColor = "#22C55E";
                break;

        }

    });


    //------------------------------------------------------
    // Calendar
    //------------------------------------------------------

    const calendarEl = document.getElementById("bookingCalendar");

    const today = new Date();

    const minDate = new Date(
        today.getFullYear() - 1,
        today.getMonth(),
        1
    );

    const maxDate = new Date(
        today.getFullYear() + 1,
        today.getMonth(),
        31
    );
    const calendar = new FullCalendar.Calendar(calendarEl, {

        initialView: "dayGridMonth",

        initialDate: today,

        height: "auto",

        events: bookingEvents,

        validRange: {

            start: minDate,

            end: maxDate

        },

        headerToolbar: {

            left: "prev,next today",

            center: "title",

            right: ""

        },

        dayMaxEvents: true,

        eventClick: function(info){

            showBooking(info.event);

        }

    });

    calendar.render();


    //------------------------------------------------------
    // Booking Detail Card
    //------------------------------------------------------

    function showBooking(event) {

    const card = document.getElementById(
        "selectedBookingCard"
    );

    const p = event.extendedProps;

    card.innerHTML = `

    <h2>Selected Booking</h2>

    <hr>

    <h3>${event.title}</h3>

    <p>
    <strong>Date:</strong>
    ${event.start.toDateString()}
    </p>

    <p>
    <strong>Time:</strong>
    ${p.time}
    </p>

    <p>
    <strong>Status:</strong>
    <span style="
    padding:4px 10px;
    border-radius:8px;
    background:${event.backgroundColor};
    color:white;
    font-weight:600;
    ">
    ${p.status}
    </span>
    </p>

    <p>
    <strong>Duration:</strong>
    ${p.duration}
    </p>

    <p>
    <strong>Price:</strong>
    $${p.price}
    </p>

    <p>
    <strong>Address:</strong>
    ${p.address}
    </p>

    <p>
    <strong>Notes:</strong><br>
    ${p.notes || "No additional notes."}
    </p>

    `;


}
});