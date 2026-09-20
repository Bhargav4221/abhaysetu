# 🛡️ AbhaySetu (अभयसेतु)
> **Resilient Emergency & Disaster Response Hub**  
> **Repository:** [https://github.com/Bhargav4221/abhaysetu](https://github.com/Bhargav4221/abhaysetu)

A production-grade disaster management and emergency coordination platform engineered for **zero-network survival** through decentralized edge nodes, local storage queueing, and intelligent communication fallback hierarchies.

---

## 🏛️ System Architecture

```mermaid
graph TD
    Client[Client Frontend <br> React / Vite PWA] -->|Online Mode| Cloud[FastAPI Cloud Backend <br> PostgreSQL / Redis]
    Client -->|Offline Mode| Storage[Browser Local Storage <br> Encrypted Queue]
    Storage -->|On Signal Recovery| Edge[Local Edge Hub <br> SQLite Store & Forward]
    ⚡ Communication Fallback Pipeline
    sequenceDiagram
    participant App as SOS Triggered
    participant Net as 1. Internet
    participant LAN as 2. Local Wi-Fi / LAN
    participant Mesh as 3. Peer-to-Peer Mesh
    participant Sat as 4. Radio / Satellite
    participant Queue as 5. Store & Forward

    App ->> Net: Available?
    alt Yes
        Net -->> App: Send to Cloud Database
    else No
        App ->> LAN: Available?
        alt Yes
            LAN -->> App: Send to Edge Hub (Port 8080)
        else No
            App ->> Mesh: Available?
            alt Yes
                Mesh -->> App: Relay via Nearby Devices
            else No
                App ->> Sat: Available?
                alt Yes
                    Sat -->> App: Hardware Gateway
                else No
                    App ->> Queue: Save locally in device queue for auto-sync
                end
            end
        end
    end

    🚀 Key Features

    Feature,Description
🚨 One-Tap SOS Beacon,"Instant geo-location capture (navigator.geolocation) paired with urgent classification (Medical, Flood, Fire, Shelter)."
🔄 Offline-First Resilience,Progressive Web App (PWA) with local caching. Alerts queue securely during blackouts and auto-sync when signals return.
🗺️ Crisis & Safe Zone Map,"Real-time map interface tracking active distress calls, relief shelters, medical camps, and safe transit routes."
🏢 Edge Hub Architecture,Localized SQLite-powered edge nodes (hub service) running on-site to handle local data packets independently.
🤝 Resource Matchmaker,Connects citizens in need with nearby volunteers and agencies logging available supplies and rescue gear.
🆚 Competitive Differentiation
Capability,Standard Consumer Apps,Existing Government Portals,🛡️ AbhaySetu
Network Dependency,Fails completely offline.,Requires constant high-speed cloud connection.,Offline-First: Queues locally and auto-syncs.
Infrastructure Resilience,Dependent on central cloud.,Centralized servers prone to overloads.,Edge Hub Architecture: Localized nodes on-site.
Communication Fallback,Single internet pipeline.,Single internet pipeline.,Tiered Pipeline: Internet ➔ LAN ➔ Mesh ➔ Sat.
Triage & Coordination,Raw unformatted calls.,Slow bureaucratic logging.,Automated Triage: Priority-based safety sorting.
📋 System Requirements & Setup
Prerequisites
Docker & Docker Compose (Recommended for container orchestration)

Node.js (v18+) (For local frontend development)

Python 3.10+ (For local backend execution)

Quickstart with Docker
# Clone the repository
git clone [https://github.com/Bhargav4221/abhaysetu.git](https://github.com/Bhargav4221/abhaysetu.git)
cd abhaysetu

# Spin up all containers
docker-compose up --build
Access Points
Web Frontend: http://localhost:5173

Backend API Docs: http://localhost:8000/docs

Local Edge Hub: http://localhost:8080

🧪 Testing the Offline-First Feature
Open http://localhost:5173 in your browser.

Open Developer Tools (F12) ➔ Network tab ➔ Set throttling to Offline.

Trigger an SOS Beacon and submit a test request.

Verify the app stores it locally and displays an "Offline Queued" badge.

Reconnect to the network and watch it sync automatically to the backend.
