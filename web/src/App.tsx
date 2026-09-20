import { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { api, AuthApi } from "./api";
import { modeFromSnapshot, sendSos, snapshot, type ChannelStatus } from "./comms";
import { generateSosId, getOrCreateDeviceKeys, hashPayload, signPayload } from "./crypto";
import { getLang, setLang, t, type Lang } from "./i18n";
import { enqueueSos, listQueue, updateQueued, type QueuedSos } from "./offlineQueue";

type Session = { access: string; role: string; name: string; userId: string } | null;

function loadSession(): Session {
  const access = localStorage.getItem("abhaysetu.access");
  const role = localStorage.getItem("abhaysetu.role");
  const name = localStorage.getItem("abhaysetu.name");
  const userId = localStorage.getItem("abhaysetu.user");
  if (!access || !role || !userId) return null;
  return { access, role, name: name || "", userId };
}

const CATEGORIES = [
  ["MEDICAL", "medical"],
  ["ACCIDENT", "accident"],
  ["FIRE", "fire"],
  ["FLOOD", "flood"],
  ["CYCLONE", "cyclone"],
  ["EARTHQUAKE", "earthquake"],
  ["LANDSLIDE", "landslide"],
  ["RESCUE_REQUIRED", "rescue"],
  ["TRAPPED_PERSON", "trapped"],
  ["MISSING_PERSON", "missing"],
  ["SHELTER_REQUIRED", "shelter"],
  ["FOOD_REQUIRED", "food"],
  ["WATER_REQUIRED", "water"],
  ["MEDICINE_REQUIRED", "medicine"],
  ["OTHER", "other"],
] as const;

export default function App() {
  const [session, setSession] = useState<Session>(loadSession);
  const [lang, setLangState] = useState<Lang>(getLang());
  const [channels, setChannels] = useState<ChannelStatus[]>([]);
  const [mode, setMode] = useState("COMPLETELY_OFFLINE");
  const onboarded = localStorage.getItem("abhaysetu.onboarded") === "1";

  useEffect(() => {
    let mounted = true;
    const tick = async () => {
      const snap = await snapshot();
      if (!mounted) return;
      setChannels(snap);
      const next = modeFromSnapshot(snap);
      setMode((prev) => {
        if (prev === "COMPLETELY_OFFLINE" && next !== "COMPLETELY_OFFLINE") {
          void flushQueue();
        }
        return next;
      });
    };
    tick();
    const id = setInterval(tick, 8000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  const changeLang = (value: Lang) => {
    setLang(value);
    setLangState(value);
  };

  return (
    <div className="min-h-screen bg-ink">
      <Routes>
        <Route path="/" element={<Splash />} />
        <Route path="/onboarding" element={<Onboarding onDone={() => (window.location.href = "/login")} />} />
        <Route path="/login" element={<Auth mode="login" onSession={setSession} />} />
        <Route path="/register" element={<Auth mode="register" onSession={setSession} />} />
        <Route
          path="/app/*"
          element={
            session ? (
              <Shell session={session} mode={mode} channels={channels} lang={lang} onLang={changeLang} onLogout={() => {
                localStorage.removeItem("abhaysetu.access");
                setSession(null);
              }} />
            ) : (
              <Navigate to={onboarded ? "/login" : "/onboarding"} replace />
            )
          }
        />
      </Routes>
    </div>
  );
}

function Splash() {
  const nav = useNavigate();
  useEffect(() => {
    const tmr = setTimeout(() => {
      nav(localStorage.getItem("abhaysetu.onboarded") === "1" ? "/login" : "/onboarding");
    }, 1200);
    return () => clearTimeout(tmr);
  }, [nav]);
  return (
    <main className="grid min-h-screen place-items-center px-6 text-center">
      <div>
        <p className="text-sm tracking-[0.4em] text-amber">SAFETY BRIDGE</p>
        <h1 className="mt-3 text-5xl font-black tracking-tight">ABHAYSETU</h1>
        <p className="mt-4 max-w-md text-slate-300">{t("tagline")}</p>
      </div>
    </main>
  );
}

function Onboarding({ onDone }: { onDone: () => void }) {
  const [step, setStep] = useState(0);
  const slides = [t("onboarding1"), t("onboarding2"), t("onboarding3")];
  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-6">
      <h1 className="text-3xl font-black">ABHAYSETU</h1>
      <p className="mt-8 text-xl leading-relaxed text-slate-200">{slides[step]}</p>
      <div className="mt-10 flex gap-3">
        <button className="rounded-lg bg-amber px-5 py-3 font-semibold text-ink" onClick={() => {
          if (step < 2) setStep(step + 1);
          else {
            localStorage.setItem("abhaysetu.onboarded", "1");
            onDone();
          }
        }}>{t("continue")}</button>
        <button className="rounded-lg border border-slate-600 px-5 py-3" onClick={() => {
          localStorage.setItem("abhaysetu.onboarded", "1");
          onDone();
        }}>{t("skip")}</button>
      </div>
    </main>
  );
}

function Auth({ mode, onSession }: { mode: "login" | "register"; onSession: (s: Session) => void }) {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const keys = await getOrCreateDeviceKeys();
      const extra = { device_id: keys.deviceId, public_key: keys.publicKey, platform: "web" };
      const data: any = mode === "login"
        ? await AuthApi.login(email, password, extra)
        : await AuthApi.register({ email, password, name, role: "CITIZEN", ...extra });
      localStorage.setItem("abhaysetu.access", data.access_token);
      localStorage.setItem("abhaysetu.refresh", data.refresh_token);
      localStorage.setItem("abhaysetu.role", data.role);
      localStorage.setItem("abhaysetu.name", data.name);
      localStorage.setItem("abhaysetu.user", data.user_id);
      onSession({ access: data.access_token, role: data.role, name: data.name, userId: data.user_id });
      nav("/app");
    } catch (err: any) {
      setError(navigator.onLine ? err.message : t("offlineMode"));
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <h1 className="text-3xl font-black">ABHAYSETU</h1>
      <form className="mt-8 space-y-4" onSubmit={submit}>
        {mode === "register" && (
          <label className="block">
            <span className="text-sm text-slate-300">{t("name")}</span>
            <input className="mt-1 w-full rounded-lg bg-panel p-3" value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
        )}
        <label className="block">
          <span className="text-sm text-slate-300">{t("email")}</span>
          <input className="mt-1 w-full rounded-lg bg-panel p-3" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label className="block">
          <span className="text-sm text-slate-300">{t("password")}</span>
          <input className="mt-1 w-full rounded-lg bg-panel p-3" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
        </label>
        {error && <p className="text-amber">{error}</p>}
        <button className="w-full rounded-lg bg-amber py-3 font-bold text-ink">{mode === "login" ? t("login") : t("register")}</button>
      </form>
      <Link className="mt-4 text-slate-300 underline" to={mode === "login" ? "/register" : "/login"}>
        {mode === "login" ? t("register") : t("login")}
      </Link>
    </main>
  );
}

function Shell({ session, mode, channels, lang, onLang, onLogout }: {
  session: NonNullable<Session>; mode: string; channels: ChannelStatus[]; lang: Lang;
  onLang: (l: Lang) => void; onLogout: () => void;
}) {
  const loc = useLocation();
  const staff = ["DISPATCHER", "ADMIN", "RESPONDER", "ORGANIZATION"].includes(session.role);
  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col">
      <header className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <Link to="/app" className="font-black tracking-wide">ABHAYSETU</Link>
        <StatusBadge mode={mode} />
      </header>
      <div className="flex flex-1">
        <nav className="hidden w-52 flex-col gap-1 border-r border-slate-800 p-3 md:flex" aria-label="Main">
          <Nav to="/app" label={t("home")} active={loc.pathname === "/app"} />
          <Nav to="/app/map" label={t("map")} />
          <Nav to="/app/shelters" label={t("shelters")} />
          <Nav to="/app/queue" label={t("queue")} />
          <Nav to="/app/connectivity" label={t("connectivity")} />
          {staff && <Nav to="/app/ops" label={t("dispatcher")} />}
          {session.role === "RESPONDER" && <Nav to="/app/responder" label="Responder" />}
          <Nav to="/app/profile" label={t("profile")} />
          <Nav to="/app/settings" label={t("settings")} />
        </nav>
        <main className="flex-1 p-4">
          <Routes>
            <Route path="" element={<Home session={session} mode={mode} />} />
            <Route path="sos" element={<SosScreen session={session} />} />
            <Route path="track/:id" element={<Tracking />} />
            <Route path="map" element={<CrisisMap />} />
            <Route path="shelters" element={<Shelters />} />
            <Route path="queue" element={<Queue />} />
            <Route path="connectivity" element={<Connectivity channels={channels} mode={mode} />} />
            <Route path="ops" element={<Dispatcher />} />
            <Route path="responder" element={<Responder />} />
            <Route path="profile" element={<Profile session={session} onLogout={onLogout} />} />
            <Route path="settings" element={<Settings lang={lang} onLang={onLang} />} />
            <Route path="notifications" element={<Notifications />} />
          </Routes>
        </main>
      </div>
      <MobileNav staff={staff} responder={session.role === "RESPONDER"} />
    </div>
  );
}

function Nav({ to, label, active }: { to: string; label: string; active?: boolean }) {
  return (
    <Link to={to} className={`rounded-lg px-3 py-2 text-sm ${active ? "bg-panel text-amber" : "text-slate-300 hover:bg-panel"}`}>
      {label}
    </Link>
  );
}

function MobileNav({ staff, responder }: { staff: boolean; responder: boolean }) {
  return (
    <nav className="grid grid-cols-5 border-t border-slate-800 bg-ink p-2 md:hidden" aria-label="Mobile">
      <Link className="py-2 text-center text-xs" to="/app">SOS</Link>
      <Link className="py-2 text-center text-xs" to="/app/map">{t("map")}</Link>
      <Link className="py-2 text-center text-xs" to="/app/queue">{t("queue")}</Link>
      <Link className="py-2 text-center text-xs" to={staff ? "/app/ops" : "/app/shelters"}>{staff ? t("dispatcher") : t("shelters")}</Link>
      <Link className="py-2 text-center text-xs" to={responder ? "/app/responder" : "/app/settings"}>{t("settings")}</Link>
    </nav>
  );
}

function StatusBadge({ mode }: { mode: string }) {
  const color = mode === "ONLINE" ? "bg-ok" : mode === "COMPLETELY_OFFLINE" ? "bg-sos" : "bg-amber";
  const label = mode === "ONLINE" ? t("online") : mode === "LOCAL_EMERGENCY_NETWORK" ? t("local") : t("offline");
  return (
    <div className="flex items-center gap-2 rounded-full border border-slate-700 px-3 py-1 text-xs font-semibold" role="status">
      <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
      {label}
    </div>
  );
}

function Home({ session, mode }: { session: NonNullable<Session>; mode: string }) {
  const nav = useNavigate();
  return (
    <section className="flex flex-col items-center pt-6">
      <p className="text-slate-300">Hi {session.name}</p>
      <p className="mt-2 max-w-md text-center text-slate-400">{t("tagline")}</p>
      <button
        className="sos-pulse mt-10 h-48 w-48 rounded-full bg-sos text-3xl font-black shadow-xl"
        aria-label={t("pressSos")}
        onClick={() => {
          if (navigator.vibrate) navigator.vibrate(80);
          nav("/app/sos");
        }}
      >
        {t("sos")}
      </button>
      <p className="mt-6 text-sm text-slate-400">{t("holdToConfirm")}</p>
      {mode === "COMPLETELY_OFFLINE" && <p className="mt-4 text-amber">{t("offlineMode")}</p>}
      <div className="mt-10 grid w-full max-w-lg grid-cols-2 gap-3">
        <Quick to="/app/map" label={t("map")} />
        <Quick to="/app/shelters" label={t("shelters")} />
        <Quick to="/app/queue" label={t("queue")} />
        <Quick to="/app/connectivity" label={t("connectivity")} />
      </div>
    </section>
  );
}

function Quick({ to, label }: { to: string; label: string }) {
  return <Link to={to} className="rounded-xl bg-panel px-4 py-6 text-center font-semibold">{label}</Link>;
}

function SosScreen({ session }: { session: NonNullable<Session> }) {
  const nav = useNavigate();
  const [type, setType] = useState("MEDICAL");
  const [people, setPeople] = useState("");
  const [injured, setInjured] = useState("");
  const [desc, setDesc] = useState("");
  const [status, setStatus] = useState("Capturing location…");
  const [busy, setBusy] = useState(false);

  const captureLocation = (): Promise<{ latitude?: number; longitude?: number; accuracy_meters?: number; source: string; captured_at: string }> =>
    new Promise((resolve) => {
      if (!navigator.geolocation) {
        resolve({ source: "unavailable", captured_at: new Date().toISOString() });
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy_meters: pos.coords.accuracy,
          source: "gps",
          captured_at: new Date().toISOString(),
        }),
        () => resolve({ source: "unavailable", captured_at: new Date().toISOString() }),
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
      );
    });

  const send = async () => {
    setBusy(true);
    setStatus("Capturing location…");
    const keys = await getOrCreateDeviceKeys();
    const location = await captureLocation();
    const payload = {
      sos_id: generateSosId(),
      user_id: session.userId,
      device_id: keys.deviceId,
      timestamp: new Date().toISOString(),
      location,
      emergency_type: type,
      priority: ["MEDICAL", "FIRE", "TRAPPED_PERSON", "RESCUE_REQUIRED", "EARTHQUAKE", "FLOOD"].includes(type) ? "CRITICAL" : "HIGH",
      description: desc,
      people_count: people ? Number(people) : null,
      injured_count: injured ? Number(injured) : null,
      origin_public_key: keys.publicKey,
      schema_version: 1,
      language: getLang(),
    };
    const digital_signature = await signPayload(payload, keys.secretKey);
    await hashPayload(payload);
    const body = { payload, digital_signature, received_via: "internet", current_channel: "internet" };
    await enqueueSos({
      sos_id: payload.sos_id,
      payload,
      digital_signature,
      created_at: payload.timestamp,
      attempts: 0,
      last_error: "",
      status: "WAITING_FOR_COMMUNICATION",
      honest_status_message: t("savedLocal"),
      priority: payload.priority,
    });
    setStatus("Selecting communication path…");
    const result = await sendSos(body);
    if (result.acknowledgement) {
      await updateQueued(payload.sos_id, { status: "DELIVERED", honest_status_message: result.statusMessage });
    } else {
      await updateQueued(payload.sos_id, { status: "WAITING_FOR_COMMUNICATION", honest_status_message: result.statusMessage });
    }
    localStorage.setItem("abhaysetu.lastSos", payload.sos_id);
    nav(`/app/track/${payload.sos_id}`, { state: { message: result.statusMessage, ack: result.acknowledgement } });
  };

  return (
    <section className="mx-auto max-w-lg space-y-4">
      <h2 className="text-2xl font-bold">{t("pressSos")}</h2>
      <p className="text-sm text-slate-400">Optional details. You can send immediately.</p>
      <div className="grid grid-cols-2 gap-2">
        {CATEGORIES.map(([id, key]) => (
          <button key={id} onClick={() => setType(id)} className={`rounded-lg px-3 py-3 text-sm ${type === id ? "bg-amber text-ink" : "bg-panel"}`}>
            {t(key)}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <input className="rounded-lg bg-panel p-3" placeholder={t("people")} value={people} onChange={(e) => setPeople(e.target.value)} inputMode="numeric" />
        <input className="rounded-lg bg-panel p-3" placeholder={t("injured")} value={injured} onChange={(e) => setInjured(e.target.value)} inputMode="numeric" />
      </div>
      <textarea className="w-full rounded-lg bg-panel p-3" placeholder={t("description")} value={desc} onChange={(e) => setDesc(e.target.value)} />
      <button disabled={busy} className="w-full rounded-xl bg-sos py-4 text-xl font-black" onClick={send}>
        {t("sos")}
      </button>
      <p role="status">{status}</p>
    </section>
  );
}

function Tracking() {
  const { id } = useParams();
  const loc = useLocation() as { state?: { message?: string; ack?: boolean } };
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!id) return;
    api(`/api/v1/sos/${id}`).then(setData).catch(() => setError(t("offlineMode")));
  }, [id]);
  const steps = [
    "CREATED", "GPS_CAPTURED", "TRANSMITTING", "RELAYED", "HUB_RECEIVED",
    "DISPATCHER_ACKNOWLEDGED", "RESPONDER_ASSIGNED", "RESPONDER_EN_ROUTE", "RESPONDING", "RESOLVED",
  ];
  const done = new Set((data?.events || []).map((e: any) => e.event_type));
  if (data?.lifecycle) done.add(data.lifecycle);
  if (loc.state?.ack) done.add("HUB_RECEIVED");
  return (
    <section className="mx-auto max-w-lg">
      <h2 className="text-2xl font-bold">{t("tracking")}</h2>
      <p className="mt-2 font-mono text-amber">{id}</p>
      <p className="mt-3 text-slate-200">{loc.state?.message || data?.honest_status_message}</p>
      {error && <p className="mt-2 text-amber">{error}</p>}
      <ol className="mt-6 space-y-3">
        {steps.map((step) => (
          <li key={step} className="flex items-center gap-3">
            <span className={`grid h-6 w-6 place-items-center rounded-full text-xs ${done.has(step) ? "bg-ok" : "bg-slate-700"}`}>
              {done.has(step) ? "✓" : ""}
            </span>
            {step.replaceAll("_", " ")}
          </li>
        ))}
      </ol>
    </section>
  );
}

function CrisisMap() {
  const [payload, setPayload] = useState<any>(null);
  useEffect(() => {
    api("/api/v1/map").then(setPayload).catch(() => setPayload({ markers: [], map_data_last_updated: "device cache / unknown" }));
  }, []);
  const markers = payload?.markers || [];
  const center = markers[0] ? [markers[0].latitude, markers[0].longitude] : [17.385, 78.486];
  return (
    <section className="h-[70vh]">
      <p className="mb-2 text-sm text-slate-300">{t("mapUpdated")}: {payload?.map_data_last_updated || "unknown"}</p>
      <p className="mb-3 text-xs text-slate-400">{payload?.route_disclaimer || t("reportedRoute")}</p>
      <MapContainer center={center as [number, number]} zoom={11} className="h-full rounded-xl" scrollWheelZoom>
        <TileLayer attribution={payload?.attribution || "© OpenStreetMap"} url={payload?.tile_url || "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"} />
        {markers.map((m: any) => (
          <Marker key={m.id} position={[m.latitude, m.longitude]} icon={dot(m.kind)}>
            <Popup>
              <strong>{m.kind}</strong>
              <div>{m.name || m.id}</div>
              {m.last_verified_at && <div>Last verified: {m.last_verified_at}</div>}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </section>
  );
}

function dot(kind: string) {
  const color = kind === "SOS" || kind === "HIGH_PRIORITY" ? "#d7263d" : kind === "SHELTER" ? "#3b82f6" : "#111";
  return L.divIcon({ className: "", html: `<div style="width:14px;height:14px;border-radius:50%;background:${color};border:2px solid white"></div>` });
}

function Shelters() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => {
    api<{ items: any[] }>("/api/v1/shelters").then((d) => setItems(d.items)).catch(() => setItems([]));
  }, []);
  return (
    <section className="space-y-3">
      <h2 className="text-2xl font-bold">{t("shelters")}</h2>
      {items.length === 0 && <p className="text-slate-400">No shelter records available on this device or server yet.</p>}
      {items.map((s) => (
        <article key={s.shelter_id} className="rounded-xl bg-panel p-4">
          <h3 className="font-bold">{s.name}</h3>
          <p>Available: {s.available_capacity} / {s.capacity}</p>
          <p>Accessibility: {s.accessibility ? "Yes" : "Unknown"}</p>
          <p className="text-xs text-slate-400">{s.verification_status} · last updated {s.last_updated}</p>
        </article>
      ))}
    </section>
  );
}

function Queue() {
  const [items, setItems] = useState<QueuedSos[]>([]);
  const refresh = () => listQueue().then(setItems);
  useEffect(() => { refresh(); }, []);
  return (
    <section>
      <h2 className="text-2xl font-bold">{t("queue")}</h2>
      <button className="mt-3 rounded-lg bg-panel px-4 py-2" onClick={() => flushQueue().then(refresh)}>Retry now</button>
      <ul className="mt-4 space-y-3">
        {items.map((i) => (
          <li key={i.sos_id} className="rounded-xl bg-panel p-4">
            <p className="font-mono text-amber">{i.sos_id}</p>
            <p>{i.status}</p>
            <p className="text-sm text-slate-300">{i.honest_status_message}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

async function flushQueue() {
  const items = await listQueue();
  for (const item of items.filter((i) => i.status !== "DELIVERED")) {
    await updateQueued(item.sos_id, { status: "TRANSMITTING", attempts: item.attempts + 1 });
    const result = await sendSos({
      payload: item.payload,
      digital_signature: item.digital_signature,
      received_via: "internet",
    });
    if (result.acknowledgement) {
      await updateQueued(item.sos_id, { status: "DELIVERED", honest_status_message: result.statusMessage });
    } else {
      await updateQueued(item.sos_id, { status: "WAITING_FOR_COMMUNICATION", last_error: result.statusMessage, honest_status_message: result.statusMessage });
    }
  }
}

function Connectivity({ channels, mode }: { channels: ChannelStatus[]; mode: string }) {
  return (
    <section>
      <h2 className="text-2xl font-bold">{t("connectivity")}</h2>
      <StatusBadge mode={mode} />
      <ul className="mt-6 space-y-3">
        {channels.filter((c) => c.id !== "store_and_forward").map((c) => (
          <li key={c.id} className="rounded-xl bg-panel p-4">
            <p className="font-semibold">{c.available ? "✓" : "✗"} {c.id.replaceAll("_", " ")}</p>
            <p className="text-sm text-slate-300">{c.reason}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Dispatcher() {
  const [items, setItems] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
  const load = () => {
    api<{ items: any[] }>("/api/v1/incidents").then((d) => setItems(d.items)).catch(() => setItems([]));
    api("/api/v1/dashboard/metrics").then(setMetrics).catch(() => setMetrics(null));
  };
  useEffect(() => { load(); }, []);
  const act = async (id: string, path: string, body?: object) => {
    await api(`/api/v1/sos/${id}${path}`, { method: "POST", body: body ? JSON.stringify(body) : "{}" });
    load();
  };
  return (
    <section>
      <h2 className="text-2xl font-bold">{t("dispatcher")}</h2>
      {metrics && (
        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          <Metric label="Active" value={metrics.active_emergencies} />
          <Metric label="Critical" value={metrics.critical_emergencies} />
          <Metric label="Unassigned" value={metrics.unassigned_incidents} />
          <Metric label="Responding" value={metrics.responding} />
        </div>
      )}
      <p className="mt-2 text-xs text-slate-400">{metrics?.note}</p>
      <div className="mt-6 space-y-3">
        {items.map((s) => (
          <article key={s.sos_id} className="rounded-xl bg-panel p-4">
            <div className="flex justify-between">
              <p className="font-mono text-amber">{s.canonical_id || s.sos_id}</p>
              <span>{s.priority}</span>
            </div>
            <p>{s.emergency_type} · {s.lifecycle}</p>
            <p className="text-sm">{s.honest_status_message}</p>
            <p className="text-sm">People {s.people_count ?? "—"} · Injured {s.injured_count ?? "—"}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="rounded bg-amber px-3 py-2 text-ink" onClick={() => act(s.sos_id, "/acknowledge")}>{t("acknowledge")}</button>
              <button className="rounded bg-slate-700 px-3 py-2" onClick={() => api(`/api/v1/sos/${s.sos_id}/status`, { method: "PATCH", body: JSON.stringify({ lifecycle: "RESOLVED" }) }).then(load)}>{t("resolve")}</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl bg-panel p-4">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="text-2xl font-black">{value}</p>
    </div>
  );
}

function Responder() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => {
    api<{ items: any[] }>("/api/v1/incidents").then((d) => setItems(d.items.filter((i) => ["RESPONDER_ASSIGNED", "RESPONDER_EN_ROUTE", "RESPONDING"].includes(i.lifecycle)))).catch(() => setItems([]));
  }, []);
  const update = (id: string, lifecycle: string) => api(`/api/v1/sos/${id}/status`, { method: "PATCH", body: JSON.stringify({ lifecycle }) });
  return (
    <section className="space-y-3">
      <h2 className="text-2xl font-bold">Assigned incidents</h2>
      {items.map((s) => (
        <article key={s.sos_id} className="rounded-xl bg-panel p-4">
          <p className="font-mono">{s.sos_id}</p>
          <p>{s.emergency_type}</p>
          <div className="mt-2 flex gap-2">
            <button className="rounded bg-amber px-3 py-2 text-ink" onClick={() => update(s.sos_id, "RESPONDER_EN_ROUTE")}>En route</button>
            <button className="rounded bg-slate-700 px-3 py-2" onClick={() => update(s.sos_id, "RESPONDING")}>On scene</button>
            <button className="rounded bg-ok px-3 py-2" onClick={() => update(s.sos_id, "RESOLVED")}>Complete</button>
          </div>
        </article>
      ))}
    </section>
  );
}

function Profile({ session, onLogout }: { session: NonNullable<Session>; onLogout: () => void }) {
  return (
    <section>
      <h2 className="text-2xl font-bold">{t("profile")}</h2>
      <p className="mt-4">{session.name}</p>
      <p className="text-slate-400">{session.role}</p>
      <button className="mt-6 rounded-lg bg-panel px-4 py-2" onClick={onLogout}>Sign out</button>
    </section>
  );
}

function Settings({ lang, onLang }: { lang: Lang; onLang: (l: Lang) => void }) {
  return (
    <section>
      <h2 className="text-2xl font-bold">{t("settings")}</h2>
      <label className="mt-4 block">
        {t("language")}
        <select className="mt-2 w-full rounded-lg bg-panel p-3" value={lang} onChange={(e) => onLang(e.target.value as Lang)}>
          <option value="en">English</option>
          <option value="hi">हिन्दी</option>
          <option value="te">తెలుగు</option>
        </select>
      </label>
    </section>
  );
}

function Notifications() {
  return (
    <section>
      <h2 className="text-2xl font-bold">{t("notifications")}</h2>
      <p className="mt-3 text-slate-400">Online push requires a configured push provider. Offline alerts stay on this device.</p>
    </section>
  );
}
