import enum


class UserRole(str, enum.Enum):
    doctor = "doctor"


class SessionStatus(str, enum.Enum):
    active = "active"
    completed = "completed"

