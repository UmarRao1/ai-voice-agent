def get_business_information() -> dict:
    """Return the configured medical reception clinic information."""
    return {
        "name": "Medical Reception Clinic",
        "services": [
            "General Consultation (30 minutes)",
            "Follow-up Consultation (15 minutes)",
            "Preventive Health Visit (30 minutes)",
        ],
        "hours": {
            "Monday-Friday": "8:30 AM-6:00 PM",
            "Saturday": "Closed",
            "Sunday": "Closed",
        },
        "schedule_restrictions": {
            "Monday-Wednesday": (
                "No appointments from 9:00 AM to 3:00 PM, because they are already booked."
            ),
        },
        "message": (
            "Provide the clinic information accurately. "
            "Confirm actual appointment availability and bookings "
            "through the appointment database before making claims."
        ),
    }


def create_greeting(name: str = "there") -> str:
    """Create a short greeting for a caller."""
    clean_name = name.strip()[:80] or "there"
    return f"Hello, {clean_name}! How can I help you today?"
