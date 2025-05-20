import json
import os
from typing import List, Dict

BOOKING_FILE = 'data/bookings.json'


def load_bookings() -> List[Dict]:
    try:
        if not os.path.exists(BOOKING_FILE):
            return []

        with open(BOOKING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def save_bookings(bookings: List[Dict]) -> bool:
    try:
        os.makedirs(os.path.dirname(BOOKING_FILE), exist_ok=True)
        with open(BOOKING_FILE, 'w', encoding='utf-8') as f:
            json.dump(bookings, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False


def get_user_bookings(user_id: str) -> List[Dict]:
    bookings = load_bookings()
    user_bookings = []

    for booking in bookings:
        if (booking.get('user_id') == user_id or
                booking.get('user') == user_id or
                (isinstance(booking.get('user'), dict) and booking['user'].get('id') == user_id)):

            if 'id' not in booking:
                booking = booking.copy()
                booking['id'] = f"{booking['movie'][:3]}{booking.get('session', '').replace(' ', '')}{booking['seat']}"

            user_bookings.append(booking)

    return user_bookings


def cancel_booking(booking_id: str) -> bool:
    bookings = load_bookings()
    new_bookings = [b for b in bookings if b.get('id') != booking_id]

    if len(new_bookings) == len(bookings):
        return False

    return save_bookings(new_bookings)