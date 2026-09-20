from enum import Enum


class Role(str, Enum):
    CITIZEN = "CITIZEN"
    VOLUNTEER = "VOLUNTEER"
    RESPONDER = "RESPONDER"
    DISPATCHER = "DISPATCHER"
    ORGANIZATION = "ORGANIZATION"
    ADMIN = "ADMIN"


class EmergencyCategory(str, Enum):
    MEDICAL = "MEDICAL"
    ACCIDENT = "ACCIDENT"
    FIRE = "FIRE"
    FLOOD = "FLOOD"
    CYCLONE = "CYCLONE"
    EARTHQUAKE = "EARTHQUAKE"
    LANDSLIDE = "LANDSLIDE"
    RESCUE_REQUIRED = "RESCUE_REQUIRED"
    TRAPPED_PERSON = "TRAPPED_PERSON"
    MISSING_PERSON = "MISSING_PERSON"
    SHELTER_REQUIRED = "SHELTER_REQUIRED"
    FOOD_REQUIRED = "FOOD_REQUIRED"
    WATER_REQUIRED = "WATER_REQUIRED"
    MEDICINE_REQUIRED = "MEDICINE_REQUIRED"
    OTHER = "OTHER"


class Priority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SosLifecycle(str, Enum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    TRANSMITTING = "TRANSMITTING"
    RELAYED = "RELAYED"
    DELIVERED_TO_HUB = "DELIVERED_TO_HUB"
    DISPATCHER_ACKNOWLEDGED = "DISPATCHER_ACKNOWLEDGED"
    RESPONDER_ASSIGNED = "RESPONDER_ASSIGNED"
    RESPONDER_EN_ROUTE = "RESPONDER_EN_ROUTE"
    RESPONDING = "RESPONDING"
    RESOLVED = "RESOLVED"
    WAITING_FOR_NETWORK = "WAITING_FOR_NETWORK"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class CommunicationMode(str, Enum):
    ONLINE = "ONLINE"
    LOCAL_EMERGENCY_NETWORK = "LOCAL_EMERGENCY_NETWORK"
    PEER_RELAY = "PEER_RELAY"
    RADIO = "RADIO"
    SATELLITE = "SATELLITE"
    COMPLETELY_OFFLINE = "COMPLETELY_OFFLINE"


class ChannelId(str, Enum):
    INTERNET = "internet"
    LOCAL_NETWORK = "local_network"
    PEER_RELAY = "peer_relay"
    RADIO = "radio"
    SATELLITE = "satellite"
    STORE_AND_FORWARD = "store_and_forward"


class DeliveryState(str, Enum):
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    QUEUED_LOCALLY = "QUEUED_LOCALLY"
    TRANSMITTING = "TRANSMITTING"
    RELAYED = "RELAYED"
    AWAITING_ACK = "AWAITING_ACK"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class AcknowledgementStatus(str, Enum):
    NONE = "NONE"
    TRANSPORT_ACK = "TRANSPORT_ACK"
    HUB_ACK = "HUB_ACK"
    SERVER_ACK = "SERVER_ACK"
    DISPATCHER_ACK = "DISPATCHER_ACK"


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ASSIGNED = "ASSIGNED"
    RESPONDING = "RESPONDING"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class ResourceType(str, Enum):
    AMBULANCE = "AMBULANCE"
    RESCUE_VEHICLE = "RESCUE_VEHICLE"
    RESCUE_BOAT = "RESCUE_BOAT"
    MEDICAL_TEAM = "MEDICAL_TEAM"
    DOCTOR = "DOCTOR"
    NURSE = "NURSE"
    FOOD = "FOOD"
    WATER = "WATER"
    MEDICINES = "MEDICINES"
    SHELTER = "SHELTER"
    GENERATOR = "GENERATOR"
    RESCUE_EQUIPMENT = "RESCUE_EQUIPMENT"
    TRANSPORT = "TRANSPORT"
    VOLUNTEERS = "VOLUNTEERS"


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED = "VERIFIED"
    SUSPENDED = "SUSPENDED"


class VolunteerStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED = "VERIFIED"
    SUSPENDED = "SUSPENDED"


class RelayOutcome(str, Enum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    EXPIRED = "EXPIRED"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    TTL_EXHAUSTED = "TTL_EXHAUSTED"
    FORWARDED = "FORWARDED"
    REJECTED = "REJECTED"


class AiMode(str, Enum):
    LOCAL_RULES = "LOCAL_RULES"
    CLOUD = "CLOUD"
    UNAVAILABLE = "UNAVAILABLE"


CRITICAL_CATEGORIES = {
    EmergencyCategory.MEDICAL,
    EmergencyCategory.FIRE,
    EmergencyCategory.FLOOD,
    EmergencyCategory.CYCLONE,
    EmergencyCategory.EARTHQUAKE,
    EmergencyCategory.LANDSLIDE,
    EmergencyCategory.RESCUE_REQUIRED,
    EmergencyCategory.TRAPPED_PERSON,
}

USER_STATUS_COPY = {
    CommunicationMode.ONLINE: "ONLINE",
    CommunicationMode.LOCAL_EMERGENCY_NETWORK: "LOCAL EMERGENCY NETWORK",
    CommunicationMode.PEER_RELAY: "PEER RELAY",
    CommunicationMode.RADIO: "RADIO",
    CommunicationMode.SATELLITE: "SATELLITE",
    CommunicationMode.COMPLETELY_OFFLINE: "COMPLETELY OFFLINE",
}

HONEST_DELIVERY_MESSAGES = {
    "server_ack": "SOS transmitted to AbhaySetu emergency server.",
    "hub_ack": "SOS delivered to local emergency hub.",
    "peer_relay": "SOS relayed through a nearby AbhaySetu device.",
    "radio_ack": "SOS delivered through emergency radio gateway.",
    "satellite_ack": "SOS submitted through satellite communication service.",
    "queued": (
        "SOS saved locally. No communication path is currently available. "
        "AbhaySetu will retry automatically when a communication path becomes available."
    ),
    "offline_mode": "Offline mode active.",
    "queued_short": "SOS saved locally.",
    "waiting": "Delivery status: WAITING FOR COMMUNICATION.",
    "restored": "Communication restored. Sending queued SOS.",
    "delivered": "SOS delivered.",
}
