from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "final-project"

# Fake database for now. someone else will need to add the one given

DB_PATH = os.path.join(os.getcwd(), "reservations.db")
next_id = 1

def get_db_connection(): 
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def generate_eticket(first_name):
    base = "infotc4320"
    first_name = first_name.lower()

    ticket = ""
    length = max(len(first_name), len(base))

    for i in range(length):
        if i < len(first_name):
            ticket += first_name[i].upper()
        if i < len(base):
            ticket += base[i].lower()

    return ticket

def is_seat_taken(row, col):
    connection = get_db_connection()
    result = connection.execute(
        "SELECT 1 FROM reservations WHERE seat_row = ? AND seat_col = ?",
        (row, col),
    ).fetchone()
    connection.close()
    
    return result is not None


def create_reservation(first_name, last_name, seat_row, seat_col):

    if is_seat_taken(seat_row, seat_col):
        return None
    
    reservation_code = generate_eticket(first_name)
    connection = get_db_connection()
    connection.execute(
        """
        INSERT INTO reservations (first_name, last_name, seat_row, seat_col, reservation_code)
        VALUES (?, ?, ?, ?,)
        """,
        (first_name, last_name, seat_row, seat_col, reservation_code),
    )
    connection.commit()

    new_res_code = connection.execute(
        """
        SELECT id, first_name, last_name, seat_row, seat_col, reservation_code
        FROM reservations
        ORDER by id DESC
        LIMIT 1
        """
    ).fetchone()
    
    connection.close()
    return new_res_code


def get_seating_chart():
    chart = []

    for row in range(1, 13):
        row_data = []
        for col in range(1, 5):
            if is_seat_taken(row, col):
                row_data.append("X")
            else:
                row_data.append("O")
        chart.append(row_data)

    return chart

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        choice = request.form.get("menu")

        if choice == "reserve":
            return redirect(url_for("reserve"))
        elif choice == "admin":
            flash("Someone needs to add the admin features")
            return redirect(url_for("index"))
        else:
            flash("Please select an option.")
            return redirect(url_for("index"))

    return render_template("index.html")

@app.route("/reserve", methods=["GET", "POST"])
def reserve():
    seating_chart = get_seating_chart()

    success_message = ""
    ticket_message = ""

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        seat_row = request.form.get("seat_row", "").strip()
        seat_col = request.form.get("seat_col", "").strip()

        if first_name == "" or last_name == "" or seat_row == "" or seat_col == "":
            flash("All fields are required.")
            return render_template("reserve.html",
                                   seating_chart=seating_chart,
                                   success_message=success_message,
                                   ticket_message=ticket_message)

        try:
            seat_row = int(seat_row)
            seat_col = int(seat_col)
        except ValueError:
            flash("Seat row and seat column must be numbers.")
            return render_template("reserve.html",
                                   seating_chart=seating_chart,
                                   success_message=success_message,
                                   ticket_message=ticket_message)

        if seat_row < 1 or seat_row > 12 or seat_col < 1 or seat_col > 4:
            flash("Seat row must be 1–12 and seat column must be 1–4.")
            return render_template("reserve.html",
                                   seating_chart=seating_chart,
                                   success_message=success_message,
                                   ticket_message=ticket_message)

        reservation = create_reservation(first_name, last_name, seat_row, seat_col)

        if reservation is None:
            flash("That seat is already reserved. Please choose another.")
            seating_chart = get_seating_chart()
            return render_template("reserve.html",
                                   seating_chart=seating_chart,
                                   success_message=success_message,
                                   ticket_message=ticket_message)

        success_message = f"Congratulations {first_name}! Row: {seat_row}, Seat: {seat_col} is now reserved for you. Enjoy your trip!"
        ticket_message = "Your eticket number is: " + reservation["reservation_code"]

        seating_chart = get_seating_chart()

    return render_template("reserve.html",
                           seating_chart=seating_chart,
                           success_message=success_message,
                           ticket_message=ticket_message)


if __name__ == "__main__":
    app.run(debug=True)