from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from functools import wraps

# If your folder is named "Templates" (capital T), this makes Flask find it.
app = Flask(__name__, template_folder="Templates")
app.secret_key = "final-project"

# Path to reservations.db (must be in the same folder as this file)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reservations.db")


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
    conn = get_db_connection()
    cur = conn.execute(
        "SELECT 1 FROM reservations WHERE seatRow = ? AND seatColumn = ?",
        (row, col),
    )
    result = cur.fetchone()
    conn.close()
    return result is not None


def create_reservation(first_name, last_name, seat_row, seat_col):
    if is_seat_taken(seat_row, seat_col):
        return None

    full_name = f"{first_name} {last_name}".strip()
    eticket = generate_eticket(first_name)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO reservations (passengerName, seatRow, seatColumn, eTicketNumber)
        VALUES (?, ?, ?, ?)
        """,
        (full_name, seat_row, seat_col, eticket),
    )
    conn.commit()
    reservation_id = cur.lastrowid
    conn.close()

    return {
        "id": reservation_id,
        "first_name": first_name,
        "last_name": last_name,
        "seat_row": seat_row,
        "seat_col": seat_col,
        "reservation_code": eticket,
    }


def get_seating_chart():
    """
    Returns a 12x4 chart of 'X' (reserved) and 'O' (open).
    """
    conn = get_db_connection()
    rows = conn.execute("SELECT seatRow, seatColumn FROM reservations").fetchall()
    conn.close()

    reserved_seats = {(r["seatRow"], r["seatColumn"]) for r in rows}

    chart = []
    for row in range(1, 13):
        row_data = []
        for col in range(1, 5):
            if (row, col) in reserved_seats:
                row_data.append("X")
            else:
                row_data.append("O")
        chart.append(row_data)

    return chart


def get_cost_matrix():
    """
    Function to generate cost matrix for flights
    Output: Returns a 12 x 4 matrix of prices
    """
    cost_matrix = [[100, 75, 50, 100] for _ in range(12)]
    return cost_matrix


def calculate_total_sales():
    conn = get_db_connection()
    rows = conn.execute("SELECT seatRow, seatColumn FROM reservations").fetchall()
    conn.close()

    cost_matrix = get_cost_matrix()
    total = 0
    for r in rows:
        row = r["seatRow"]
        col = r["seatColumn"]
        # seatRow/seatColumn are 1-based, matrix is 0-based
        total += cost_matrix[row - 1][col - 1]
    return total


def get_all_reservations():
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT id, passengerName, seatRow, seatColumn, eTicketNumber
        FROM reservations
        ORDER BY seatRow, seatColumn
        """
    ).fetchall()
    conn.close()
    return rows


def admin_login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in as an administrator.")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)

    return wrapper


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        choice = request.form.get("menu")

        if choice == "reserve":
            return redirect(url_for("reserve"))
        elif choice == "admin":
            return redirect(url_for("admin_login"))
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
            return render_template(
                "reserve.html",
                seating_chart=seating_chart,
                success_message=success_message,
                ticket_message=ticket_message,
            )

        try:
            seat_row = int(seat_row)
            seat_col = int(seat_col)
        except ValueError:
            flash("Seat row and seat column must be numbers.")
            return render_template(
                "reserve.html",
                seating_chart=seating_chart,
                success_message=success_message,
                ticket_message=ticket_message,
            )

        if seat_row < 1 or seat_row > 12 or seat_col < 1 or seat_col > 4:
            flash("Seat row must be 1–12 and seat column must be 1–4.")
            return render_template(
                "reserve.html",
                seating_chart=seating_chart,
                success_message=success_message,
                ticket_message=ticket_message,
            )

        reservation = create_reservation(first_name, last_name, seat_row, seat_col)

        if reservation is None:
            flash("That seat is already reserved. Please choose another.")
            seating_chart = get_seating_chart()
            return render_template(
                "reserve.html",
                seating_chart=seating_chart,
                success_message=success_message,
                ticket_message=ticket_message,
            )

        success_message = (
            f"Congratulations {first_name}! "
            f"Row: {seat_row}, Seat: {seat_col} is now reserved for you. Enjoy your trip!"
        )
        ticket_message = "Your eticket number is: " + reservation["reservation_code"]

        seating_chart = get_seating_chart()

    return render_template(
        "reserve.html",
        seating_chart=seating_chart,
        success_message=success_message,
        ticket_message=ticket_message,
    )


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password are required.")
            return render_template("admin_login.html")

        conn = get_db_connection()
        admin = conn.execute(
            "SELECT * FROM admins WHERE username = ? AND password = ?",
            (username, password),
        ).fetchone()
        conn.close()

        if admin:
            session["admin_logged_in"] = True
            session["admin_username"] = username
            flash("Successfully logged in.")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid username or password.")
            return render_template("admin_login.html")

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
@admin_login_required
def admin_dashboard():
    seating_chart = get_seating_chart()
    total_sales = calculate_total_sales()
    reservations = get_all_reservations()
    return render_template(
        "admin_dashboard.html",
        seating_chart=seating_chart,
        total_sales=total_sales,
        reservations=reservations,
    )


@app.route("/admin/delete/<int:reservation_id>", methods=["POST"])
@admin_login_required
def delete_reservation(reservation_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))
    conn.commit()
    conn.close()
    flash("Reservation deleted.")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
