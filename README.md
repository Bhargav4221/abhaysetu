# 🛡️ AbhaySetu (अभयसेतु)
### Resilient Emergency & Disaster Response Hub

> **Repository:** [https://github.com/Bhargav4221/abhaysetu](https://github.com/Bhargav4221/abhaysetu)

A production-grade disaster management and emergency coordination platform engineered for **zero-network survival** through decentralized edge nodes, local storage queueing, and intelligent communication fallback hierarchies.

---

## 🏛️ System & Communication Architecture

AbhaySetu Client Frontend
         (React / Vite PWA Progressive Web App)
                        │
    ┌───────────────────┴───────────────────┐
    │ (Online Mode)                         │ (Offline Mode)
    ▼                                       ▼

    ┌───────────────────────┐               ┌───────────────────────┐
│ FastAPI Cloud Backend │               │ Browser Local Storage │
│ (PostgreSQL / Redis)  │               │ (Encrypted Queue)     │
└───────────────────────┘               └───────────┬───────────┘
│ (On Signal Recovery)
▼
┌───────────────────────┐
│   Local Edge Hub      │
│   (SQLite Store &     │
│       Forward)        │
└───────────────────────┘

## ⚡ Communication Fallback Pipeline (`COMMUNICATION_ORDER`)

```text
[SOS Distress Signal Triggered]
         │
         ├──> 1. Internet Available? ──────> [Cloud Backend & Dispatch Database]
         │         (No Connection)
         ▼
         ├──> 2. Local Wi-Fi / LAN? ───────> [Local Edge Hub Node (Port 8080)]
         │         (No Connection)
         ▼
         ├──> 3. Peer-to-Peer Mesh? ───────> [Nearby Device Relay Network]
         │         (No Connection)
         ▼
         ├──> 4. Radio / Satellite? ───────> [Hardware Gateway Adapter]
         │         (No Connection)
         ▼
         └──> 5. Store & Forward ──────────> [Saved locally in device offline queue for auto-sync]

         🚀 Key FeaturesOne-Tap SOS & Distress Beacon: Instant geo-location capture (navigator.geolocation) combined with urgent classification (Medical, Flood/Rescue, Fire, Shelter).Offline-First Resilience: Built as a Progressive Web App (PWA) with local browser caching. During complete network blackouts, alerts queue locally and auto-sync the moment connectivity returns.Interactive Crisis & Safe Zone Map: Real-time map interface tracking active distress calls, relief shelters, medical camps, and safe transit routes avoiding hazard zones.Edge Hub Architecture: Localized SQLite-powered edge nodes (hub service) designed to run on-site during disasters, managing local store-and-forward data packets independently.Resource & Volunteer Matchmaker: Connects citizens in need with nearby volunteers and agencies logging available supplies (food packets, shelter beds, rescue boats).🛠️ Technology StackFrontend: React 18, Vite, TypeScript, Tailwind CSS, Lucide Icons, PWA Service WorkersBackend: Python, FastAPI, Pydantic v2, PostgreSQL 16, Redis 7Edge & Storage: SQLite, Docker & Docker Compose multi-container orchestrationDeployment: Vercel (Frontend) / Cloud Containers (Backend & Edge Hub)🆚 How AbhaySetu Differs from Existing AppsFeature / CapabilityStandard Consumer Apps (e.g., SOS buttons)Existing Government Portals🛡️ AbhaySetuNetwork Dependency❌ Fails completely when internet goes down.❌ Requires constant high-speed cloud connectivity.✅ Offline-First: Queues alerts locally and auto-syncs when signals return.Infrastructure Resilience❌ Dependent on central cloud servers only.❌ Centralized servers prone to regional overloads.✅ Edge Hub Architecture: Localized SQLite nodes run on-site during outages.Communication Fallback❌ Single internet pipeline.❌ Single internet pipeline.✅ Tiered Pipeline: Internet ➔ Local LAN ➔ Peer Relay ➔ Radio ➔ Satellite.Triage & Coordination❌ Raw unformatted text/calls.⚠️ Slow bureaucratic logging.✅ Automated Triage: Auto-categorizes and prioritizes life-safety requests.📋 System RequirementsDocker & Docker Compose (Recommended for multi-container cloud/edge setup)Node.js (v18+) (If running frontend development server independently)Python 3.10+ (If running backend scripts locally)Modern Web Browser with Geolocation permissions enabled.Environment ConfigurationCreate your environment file based on .env.example:Bashcp .env.example .env
Key configuration settings include:POSTGRES_DB=abhaysetuHUB_ID=hub-dev-001COMMUNICATION_ORDER=internet,local_network,peer_relay,radio,satellite,store_and_forward📦 Quickstart & Usage Instructions1. Run with Docker Compose (Recommended)
# Clone the repository
git clone [https://github.com/Bhargav4221/abhaysetu.git](https://github.com/Bhargav4221/abhaysetu.git)
cd abhaysetu

# Build and start all micro-services concurrently
docker-compose up --build
Access the platform modules:

Web Frontend UI: http://localhost:5173

Backend API Docs (Swagger): http://localhost:8000/docs

Local Emergency Hub: http://localhost:8080

2. Testing the Offline-First Feature
Open the Web UI (http://localhost:5173) in your browser.

Open Browser Developer Tools (F12) ➔ Network tab ➔ Set network throttling to Offline.

Trigger an SOS Beacon and submit a test emergency request.

Verify that the application stores the request locally without crashing and displays an "Offline Queued" status badge.

Switch the network throttle back to Online and watch the beacon auto-sync instantly to the backend database.

🐳 Docker Deployment
To launch the complete stack with PostgreSQL, Redis, FastAPI Backend, Local Edge Hub, and Web Frontend:

docker-compose up --build -d

👥 Contributing & Support
Contributions, issues, and feature requests are welcome. Feel free to check issues or submit a pull request.