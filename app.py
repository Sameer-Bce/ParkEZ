from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from models import db, User, ParkingLot, ParkingSpot, Booking
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'secret-key'  
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = User(username=request.form['username'], password=request.form['password'])
        db.session.add(user)
        db.session.commit()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin':
            session['user'] = 'admin'
            return redirect('/admin')
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(f'/dashboard/{user.id}')
        else:
            error = 'Invalid username or password. Please try again.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/admin')
def admin():
    if session.get('user') != 'admin':
        return redirect('/')
    lots = ParkingLot.query.all()
    total_lots = ParkingLot.query.count()
    total_spots = ParkingSpot.query.count()
    occupied_spots = ParkingSpot.query.filter_by(status='O').count()
    unoccupied_spots = ParkingSpot.query.filter_by(status='A').count()
    bookings = Booking.query.all()
    return render_template(
        'admin_dashboard.html',
        lots=lots,
        total_lots=total_lots,
        total_spots=total_spots,
        occupied_spots=occupied_spots,
        unoccupied_spots=unoccupied_spots,
        bookings=bookings
    )

@app.route('/create_lot', methods=['GET', 'POST'])
def create_lot():
    if session.get('user') != 'admin':
        return redirect('/')
    if request.method == 'POST':
        lot = ParkingLot(
            name=request.form['name'],
            price=float(request.form['price']),
            address=request.form['address'],
            pincode=request.form['pincode'],
            total_spots=int(request.form['total_spots'])
        )
        db.session.add(lot)
        db.session.commit()
        for _ in range(lot.total_spots):
            spot = ParkingSpot(lot_id=lot.id, status='A')
            db.session.add(spot)
        db.session.commit()
        return redirect('/admin')
    return render_template('create_lot.html')

@app.route('/delete_lot/<int:lot_id>', methods=['POST'])
def delete_lot(lot_id):
    if session.get('user') != 'admin':
        return redirect('/')
    lot = ParkingLot.query.get(lot_id)
    if lot:
        ParkingSpot.query.filter_by(lot_id=lot.id).delete()
        db.session.delete(lot)
        db.session.commit()
    return redirect('/admin')

@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    if session.get('user_id') != user_id:
        return redirect('/')
    user = User.query.get(user_id)
    lots = ParkingLot.query.all()
    user_bookings = Booking.query.filter_by(user_id=user_id).all()
    return render_template('user_dashboard.html', user=user, lots=lots, user_bookings=user_bookings)

@app.route('/book_lot/<int:lot_id>', methods=['POST'])
def book_lot(lot_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    num_spots = int(request.form.get('num_spots', 1))
    available_spots = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').limit(num_spots).all()
    if len(available_spots) < num_spots:
        return redirect(f'/dashboard/{user_id}')
    for spot in available_spots:
        spot.status = 'O'
        booking = Booking(
            user_id=user_id,
            spot_id=spot.id,
            parking_time=datetime.now()
        )
        db.session.add(booking)
    db.session.commit()
    return redirect(f'/dashboard/{user_id}')

@app.route('/release/<int:user_id>/<int:booking_id>', methods=['POST'])
def release(user_id, booking_id):
    if session.get('user_id') != user_id:
        return redirect('/')
    booking = Booking.query.get(booking_id)
    if booking and booking.user_id == user_id:
        spot = ParkingSpot.query.get(booking.spot_id)
        spot.status = 'A'
        db.session.delete(booking)
        db.session.commit()
    return redirect(f'/dashboard/{user_id}')

@app.route('/stats')
def stats():
    total_lots = ParkingLot.query.count()
    total_spots = ParkingSpot.query.count()
    occupied_spots = ParkingSpot.query.filter_by(status='O').count()
    unoccupied_spots = ParkingSpot.query.filter_by(status='A').count()
    bookings = Booking.query.all()
    return render_template(
        'stats.html',
        total_lots=total_lots,
        total_spots=total_spots,
        occupied_spots=occupied_spots,
        unoccupied_spots=unoccupied_spots,
        bookings=bookings
    )

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
