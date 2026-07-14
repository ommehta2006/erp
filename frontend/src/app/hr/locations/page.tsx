"use client";

import Link from "next/link";
import type { MouseEvent, ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

type ErpRecord = { id: string; data: Record<string, string>; status: string };
type GeofenceDashboard = {
  stats: Record<string, number>;
  work_locations: ErpRecord[];
  geofences: ErpRecord[];
  assignments: ErpRecord[];
  validation_results: ErpRecord[];
};
type MapConfig = {
  tile_url_template: string;
  attribution: string;
  default_center: { latitude: string; longitude: string; zoom: string };
  radius_rules: Record<string, string>;
};
type GeocodeResult = { label: string; latitude: string; longitude: string; type: string; importance: string; bounding_box: string[] };

const DEFAULT_MAP_CONFIG: MapConfig = {
  tile_url_template: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
  attribution: "OpenStreetMap contributors",
  default_center: { latitude: "19.076000", longitude: "72.877700", zoom: "15" },
  radius_rules: {
    minimum_radius_meters: "10",
    maximum_radius_meters: "5000",
    default_radius_meters: "150",
    high_security_radius_meters: "50",
    temporary_site_radius_meters: "250",
  },
};

const DEFAULT_LOCATION = {
  location_name: "",
  location_type: "Factory",
  company: "FactoryPulse",
  branch: "Main",
  full_address: "",
  city: "",
  state: "",
  country: "India",
  latitude: "",
  longitude: "",
  geofence_type: "Circular",
  geofence_radius_meters: "150",
  allowed_gps_accuracy_meters: "50",
  time_zone: "Asia/Kolkata",
};

const DEFAULT_GEOFENCE = {
  location_id: "",
  geofence_type: "Circular",
  center_latitude: "",
  center_longitude: "",
  radius_meters: "150",
  allowed_accuracy_meters: "50",
  boundary_version: "1",
  polygon_coordinates: "",
};

const DEFAULT_TEST = { location_id: "", latitude: "", longitude: "", accuracy: "10" };
const DEFAULT_ASSIGNMENT = { employee_code: "", location_id: "", shift: "General", assignment_type: "Primary" };

function authHeaders() {
  const token = localStorage.getItem("factorypulse_token") || "";
  return { Authorization: `Bearer ${token}` };
}

async function fetchDashboard() {
  const response = await fetch(`${API_BASE}/api/v1/hr/geofence-dashboard`, { headers: authHeaders() });
  if (!response.ok) throw new Error("Work location API failed");
  return (await response.json()) as GeofenceDashboard;
}

async function fetchMapConfig() {
  const response = await fetch(`${API_BASE}/api/v1/hr/map-config`, { headers: authHeaders() });
  if (!response.ok) return DEFAULT_MAP_CONFIG;
  return (await response.json()) as MapConfig;
}

async function searchAddress(value: string) {
  const response = await fetch(`${API_BASE}/api/v1/hr/geocode?q=${encodeURIComponent(value)}&limit=5`, { headers: authHeaders() });
  if (!response.ok) throw new Error("Address search failed");
  return ((await response.json()).results || []) as GeocodeResult[];
}

async function reverseGeocode(latitude: string, longitude: string) {
  const response = await fetch(`${API_BASE}/api/v1/hr/reverse-geocode?latitude=${encodeURIComponent(latitude)}&longitude=${encodeURIComponent(longitude)}`, { headers: authHeaders() });
  if (!response.ok) throw new Error("Reverse geocode failed");
  return await response.json() as { label: string; address: Record<string, string> };
}

async function postJson(path: string, payload: Record<string, string | number>) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Request failed");
  }
  return response.json();
}

function numeric(value: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function lonToTileX(longitude: number, zoom: number) {
  return ((longitude + 180) / 360) * (2 ** zoom);
}

function latToTileY(latitude: number, zoom: number) {
  const rad = latitude * Math.PI / 180;
  return ((1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2) * (2 ** zoom);
}

function tileXToLon(x: number, zoom: number) {
  return (x / (2 ** zoom)) * 360 - 180;
}

function tileYToLat(y: number, zoom: number) {
  const n = Math.PI - (2 * Math.PI * y) / (2 ** zoom);
  return (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)));
}

function tileUrl(template: string, z: number, x: number, y: number) {
  return template.replace("{z}", String(z)).replace("{x}", String(x)).replace("{y}", String(y));
}

function tone(status: string) {
  if (["Inside Fence", "Active", "Approved", "Passed"].includes(status)) return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (["Pending", "Pending Approval"].includes(status)) return "border-amber-200 bg-amber-50 text-amber-800";
  if (["Outside Fence", "Accuracy Rejected", "Failed", "Rejected"].includes(status)) return "border-rose-200 bg-rose-50 text-rose-800";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

export default function HrLocationsPage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<GeofenceDashboard | null>(null);
  const [mapConfig, setMapConfig] = useState<MapConfig>(DEFAULT_MAP_CONFIG);
  const [locationForm, setLocationForm] = useState(DEFAULT_LOCATION);
  const [geofenceForm, setGeofenceForm] = useState(DEFAULT_GEOFENCE);
  const [testForm, setTestForm] = useState(DEFAULT_TEST);
  const [assignmentForm, setAssignmentForm] = useState(DEFAULT_ASSIGNMENT);
  const [testResult, setTestResult] = useState<Record<string, string> | null>(null);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [addressQuery, setAddressQuery] = useState("");
  const [addressResults, setAddressResults] = useState<GeocodeResult[]>([]);
  const [mapZoom, setMapZoom] = useState(15);
  const [mapMessage, setMapMessage] = useState("");

  const load = () => {
    const token = localStorage.getItem("factorypulse_token");
    if (!token) {
      router.push("/login");
      return;
    }
    Promise.all([fetchDashboard(), fetchMapConfig()])
      .then(([body, config]) => {
        setMapConfig(config);
        setMapZoom(clamp(Number(config.default_center.zoom) || 15, 3, 19));
        setDashboard(body);
        const firstLocation = body.work_locations[0]?.data;
        if (firstLocation) {
          const locationId = firstLocation.location_id || "";
          setGeofenceForm((current) => ({
            ...current,
            location_id: current.location_id || locationId,
            center_latitude: current.center_latitude || firstLocation.latitude || "",
            center_longitude: current.center_longitude || firstLocation.longitude || "",
            radius_meters: current.radius_meters || firstLocation.geofence_radius_meters || "150",
            allowed_accuracy_meters: current.allowed_accuracy_meters || firstLocation.allowed_gps_accuracy_meters || "50",
          }));
          setTestForm((current) => ({ ...current, location_id: current.location_id || locationId }));
          setAssignmentForm((current) => ({ ...current, location_id: current.location_id || locationId }));
        } else {
          setLocationForm((current) => current.latitude && current.longitude ? current : ({
            ...current,
            latitude: config.default_center.latitude,
            longitude: config.default_center.longitude,
            geofence_radius_meters: config.radius_rules.default_radius_meters || current.geofence_radius_meters,
          }));
          setGeofenceForm((current) => current.center_latitude && current.center_longitude ? current : ({
            ...current,
            center_latitude: config.default_center.latitude,
            center_longitude: config.default_center.longitude,
            radius_meters: config.radius_rules.default_radius_meters || current.radius_meters,
          }));
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Work location API failed"));
  };

  useEffect(load, [router]);

  const locations = useMemo(() => {
    const value = query.trim().toLowerCase();
    if (!value) return dashboard?.work_locations || [];
    return (dashboard?.work_locations || []).filter((item) =>
      [item.data.location_name, item.data.location_id, item.data.city, item.data.location_type, item.status].join(" ").toLowerCase().includes(value),
    );
  }, [dashboard, query]);

  const locationOptions = dashboard?.work_locations || [];
  const selectedLocation = locationOptions.find((item) => item.data.location_id === geofenceForm.location_id)?.data;
  const latestValidations = (dashboard?.validation_results || []).slice(0, 8);

  async function createLocation() {
    setBusy("location");
    setError("");
    setNotice("");
    try {
      const payload = {
        ...locationForm,
        latitude: numeric(locationForm.latitude),
        longitude: numeric(locationForm.longitude),
        geofence_radius_meters: numeric(locationForm.geofence_radius_meters),
        allowed_gps_accuracy_meters: numeric(locationForm.allowed_gps_accuracy_meters),
      };
      const body = await postJson("/api/v1/hr/work-locations", payload);
      const locationId = body.item?.data?.location_id || "";
      setNotice("Work location saved with audit history.");
      setLocationForm(DEFAULT_LOCATION);
      setGeofenceForm((current) => ({
        ...current,
        location_id: locationId,
        center_latitude: String(payload.latitude),
        center_longitude: String(payload.longitude),
        radius_meters: String(payload.geofence_radius_meters),
        allowed_accuracy_meters: String(payload.allowed_gps_accuracy_meters),
      }));
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save location");
    } finally {
      setBusy("");
    }
  }

  async function createGeofence() {
    setBusy("geofence");
    setError("");
    setNotice("");
    try {
      await postJson("/api/v1/hr/geofences", {
        ...geofenceForm,
        center_latitude: numeric(geofenceForm.center_latitude),
        center_longitude: numeric(geofenceForm.center_longitude),
        radius_meters: numeric(geofenceForm.radius_meters),
        allowed_accuracy_meters: numeric(geofenceForm.allowed_accuracy_meters),
      });
      setNotice("Geofence saved with boundary version and audit history.");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save geofence");
    } finally {
      setBusy("");
    }
  }

  async function testGeofence() {
    setBusy("test");
    setError("");
    setNotice("");
    try {
      const result = await postJson("/api/v1/hr/geofences/test", {
        location_id: testForm.location_id,
        latitude: numeric(testForm.latitude),
        longitude: numeric(testForm.longitude),
        accuracy: numeric(testForm.accuracy),
      });
      setTestResult(result);
      setNotice("Coordinate tested by backend geofence engine.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not test coordinate");
    } finally {
      setBusy("");
    }
  }

  async function assignLocation() {
    setBusy("assignment");
    setError("");
    setNotice("");
    try {
      await postJson("/api/v1/hr/location-assignments", assignmentForm);
      setNotice("Employee location assignment saved.");
      setAssignmentForm(DEFAULT_ASSIGNMENT);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not assign location");
    } finally {
      setBusy("");
    }
  }

  function placeMarker(latitude: number, longitude: number, source = "Map point selected") {
    const lat = latitude.toFixed(8);
    const lon = longitude.toFixed(8);
    setLocationForm((current) => ({ ...current, latitude: lat, longitude: lon }));
    setGeofenceForm((current) => ({ ...current, center_latitude: lat, center_longitude: lon }));
    setTestForm((current) => ({ ...current, latitude: lat, longitude: lon }));
    setMapMessage(`${source}: ${lat}, ${lon}`);
  }

  async function runAddressSearch() {
    if (addressQuery.trim().length < 2) return;
    setBusy("search");
    setError("");
    try {
      const results = await searchAddress(addressQuery.trim());
      setAddressResults(results);
      if (results[0]) {
        placeMarker(numeric(results[0].latitude), numeric(results[0].longitude), "Address matched");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Address search failed");
    } finally {
      setBusy("");
    }
  }

  async function fillAddressFromMarker() {
    const latitude = geofenceForm.center_latitude || locationForm.latitude;
    const longitude = geofenceForm.center_longitude || locationForm.longitude;
    if (!latitude || !longitude) return;
    setBusy("reverse");
    setError("");
    try {
      const result = await reverseGeocode(latitude, longitude);
      const address = result.address || {};
      setLocationForm((current) => ({
        ...current,
        full_address: result.label || current.full_address,
        city: address.city || address.town || address.village || current.city,
        state: address.state || current.state,
        country: address.country || current.country,
      }));
      setMapMessage("Reverse geocode filled the address fields.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reverse geocode failed");
    } finally {
      setBusy("");
    }
  }

  function useCurrentLocation() {
    if (!navigator.geolocation) {
      setError("Browser location is not available.");
      return;
    }
    setBusy("gps");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        placeMarker(position.coords.latitude, position.coords.longitude, `Current location (${Math.round(position.coords.accuracy)}m accuracy)`);
        setBusy("");
      },
      () => {
        setError("Could not read current location permission from browser.");
        setBusy("");
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 },
    );
  }

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <Link href="/hr" className="text-sm font-semibold text-teal-700">HR Command Center</Link>
            <h1 className="mt-1 text-2xl font-semibold">Work Locations & Geofences</h1>
            <p className="text-sm text-slate-500">Create factory locations, geofence boundaries, employee assignments, and backend coordinate tests.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/hr/attendance" className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-700 hover:border-indigo-600">Attendance</Link>
            <Link href="/hr/employees" className="rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 text-sm font-medium text-teal-700 hover:border-teal-600">Employees</Link>
            <Link href="/departments/hr?module=work_locations" className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">Raw Table</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
        {notice ? <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{notice}</div> : null}

        <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-7">
          <Stat label="Locations" value={dashboard?.stats.work_locations || 0} />
          <Stat label="Active" value={dashboard?.stats.active_locations || 0} />
          <Stat label="Geofences" value={dashboard?.stats.geofences || 0} />
          <Stat label="Assignments" value={dashboard?.stats.assignments || 0} />
          <Stat label="Out Of Fence" value={dashboard?.stats.out_of_fence_attempts || 0} />
          <Stat label="Pending" value={dashboard?.stats.pending_approval || 0} />
          <Stat label="Failed GPS" value={dashboard?.stats.failed_validations || 0} />
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-[1fr_420px]">
          <section className="space-y-4">
            <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <p className="text-sm font-semibold text-teal-700">Interactive geofence map</p>
                  <h2 className="mt-1 text-2xl font-semibold">Place, preview, and verify the factory boundary</h2>
                  <p className="mt-1 text-sm text-slate-600">Tiles and geocoding are provider-configurable from the backend. Marker changes update the live save/test forms.</p>
                </div>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <input value={addressQuery} onChange={(event) => setAddressQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") runAddressSearch(); }} placeholder="Search address or site" className="h-11 rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700 sm:w-72" />
                  <button onClick={runAddressSearch} disabled={busy === "search"} className="rounded-lg bg-teal-700 px-3 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50">{busy === "search" ? "Searching..." : "Search"}</button>
                </div>
              </div>
              <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
                <GeofenceMap
                  config={mapConfig}
                  latitude={numeric(geofenceForm.center_latitude || locationForm.latitude || mapConfig.default_center.latitude)}
                  longitude={numeric(geofenceForm.center_longitude || locationForm.longitude || mapConfig.default_center.longitude)}
                  radius={numeric(geofenceForm.radius_meters || locationForm.geofence_radius_meters || mapConfig.radius_rules.default_radius_meters)}
                  zoom={mapZoom}
                  onZoom={setMapZoom}
                  onPlace={placeMarker}
                />
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-2">
                    <button onClick={useCurrentLocation} disabled={busy === "gps"} className="rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 text-sm font-semibold text-teal-800 hover:border-teal-600 disabled:opacity-50">{busy === "gps" ? "Reading..." : "Current GPS"}</button>
                    <button onClick={fillAddressFromMarker} disabled={busy === "reverse"} className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-semibold text-indigo-800 hover:border-indigo-600 disabled:opacity-50">{busy === "reverse" ? "Reading..." : "Fill address"}</button>
                    <button onClick={() => placeMarker(numeric(selectedLocation?.latitude || mapConfig.default_center.latitude), numeric(selectedLocation?.longitude || mapConfig.default_center.longitude), "Recentered")} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:border-slate-500">Recenter</button>
                    <button onClick={() => setTestForm((current) => ({ ...current, latitude: geofenceForm.center_latitude, longitude: geofenceForm.center_longitude }))} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:border-slate-500">Use for test</button>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                    <div className="font-semibold text-slate-800">Radius rules</div>
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      <Metric label="Minimum" value={`${mapConfig.radius_rules.minimum_radius_meters}m`} />
                      <Metric label="Maximum" value={`${mapConfig.radius_rules.maximum_radius_meters}m`} />
                      <Metric label="Default" value={`${mapConfig.radius_rules.default_radius_meters}m`} />
                      <Metric label="High security" value={`${mapConfig.radius_rules.high_security_radius_meters}m`} />
                    </div>
                  </div>
                  {mapMessage ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs font-medium text-emerald-800">{mapMessage}</div> : null}
                  {addressResults.length ? (
                    <div className="max-h-52 space-y-2 overflow-y-auto">
                      {addressResults.map((result) => (
                        <button key={`${result.latitude}-${result.longitude}-${result.label}`} onClick={() => placeMarker(numeric(result.latitude), numeric(result.longitude), "Address selected")} className="w-full rounded-lg border border-slate-200 bg-white p-3 text-left text-xs text-slate-700 hover:border-teal-600">
                          <span className="font-semibold text-slate-900">{result.type || "Location"}</span>
                          <span className="mt-1 block">{result.label}</span>
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-teal-700">Location board</p>
                  <h2 className="mt-1 text-2xl font-semibold">Factory-approved work locations</h2>
                  <p className="mt-1 text-sm text-slate-600">Each card is backed by Supabase records and used by employee attendance validation.</p>
                </div>
                <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search location" className="h-11 rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700 md:w-80" />
              </div>

              <div className="mt-4 grid gap-3 lg:grid-cols-2">
                {locations.length === 0 ? (
                  <div className="rounded-lg border border-slate-100 bg-slate-50 p-4 text-sm text-slate-500">No work locations yet.</div>
                ) : locations.map((item) => {
                  const geofence = dashboard?.geofences.find((geo) => geo.data.location_id === item.data.location_id);
                  const assignmentCount = (dashboard?.assignments || []).filter((assignment) => assignment.data.location_id === item.data.location_id).length;
                  return (
                    <button
                      key={item.id}
                      onClick={() => {
                        setGeofenceForm((current) => ({
                          ...current,
                          location_id: item.data.location_id || "",
                          center_latitude: item.data.latitude || "",
                          center_longitude: item.data.longitude || "",
                          radius_meters: geofence?.data.radius_meters || item.data.geofence_radius_meters || current.radius_meters,
                          allowed_accuracy_meters: geofence?.data.allowed_accuracy_meters || item.data.allowed_gps_accuracy_meters || current.allowed_accuracy_meters,
                        }));
                        setTestForm((current) => ({ ...current, location_id: item.data.location_id || "" }));
                        setAssignmentForm((current) => ({ ...current, location_id: item.data.location_id || "" }));
                      }}
                      className="rounded-lg border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-teal-600 hover:shadow-md"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="font-semibold">{item.data.location_name}</h3>
                          <p className="mt-1 text-sm text-slate-500">{item.data.location_id} / {item.data.location_type}</p>
                        </div>
                        <span className={`rounded-lg border px-2 py-1 text-xs font-semibold ${tone(item.status)}`}>{item.status}</span>
                      </div>
                      <p className="mt-3 line-clamp-2 text-sm text-slate-600">{item.data.full_address}</p>
                      <div className="mt-4 grid grid-cols-3 gap-2 border-t border-slate-100 pt-3">
                        <Metric label="Radius" value={`${geofence?.data.radius_meters || item.data.geofence_radius_meters || 0}m`} />
                        <Metric label="Accuracy" value={`${geofence?.data.allowed_accuracy_meters || item.data.allowed_gps_accuracy_meters || 0}m`} />
                        <Metric label="Assigned" value={String(assignmentCount)} />
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-lg font-semibold">Recent backend validations</h2>
              <div className="mt-3 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                    <tr>
                      <th className="p-3">Employee</th>
                      <th className="p-3">Location</th>
                      <th className="p-3">Distance</th>
                      <th className="p-3">Accuracy</th>
                      <th className="p-3">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {latestValidations.length === 0 ? (
                      <tr><td className="p-4 text-slate-500" colSpan={5}>No validation records yet.</td></tr>
                    ) : latestValidations.map((item) => (
                      <tr key={item.id} className="border-t border-slate-100">
                        <td className="p-3">{item.data.employee_code || "HR test"}</td>
                        <td className="p-3">{item.data.location_id}</td>
                        <td className="p-3">{item.data.distance_meters}m</td>
                        <td className="p-3">{item.data.accuracy_meters}m</td>
                        <td className="p-3"><span className={`rounded-lg border px-2 py-1 text-xs font-semibold ${tone(item.data.geofence_status || item.status)}`}>{item.data.geofence_status || item.status}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          <aside className="space-y-4">
            <Panel title="Create Work Location" action="Save location" busy={busy === "location"} onSubmit={createLocation}>
              <Input label="Location Name" value={locationForm.location_name} onChange={(value) => setLocationForm({ ...locationForm, location_name: value })} />
              <Select label="Location Type" value={locationForm.location_type} options={["Factory", "Warehouse", "Office", "Site", "Remote Approved", "Temporary Site"]} onChange={(value) => setLocationForm({ ...locationForm, location_type: value })} />
              <Input label="Full Address" value={locationForm.full_address} onChange={(value) => setLocationForm({ ...locationForm, full_address: value })} />
              <div className="grid grid-cols-2 gap-3">
                <Input label="City" value={locationForm.city} onChange={(value) => setLocationForm({ ...locationForm, city: value })} />
                <Input label="State" value={locationForm.state} onChange={(value) => setLocationForm({ ...locationForm, state: value })} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Input label="Latitude" value={locationForm.latitude} onChange={(value) => setLocationForm({ ...locationForm, latitude: value })} />
                <Input label="Longitude" value={locationForm.longitude} onChange={(value) => setLocationForm({ ...locationForm, longitude: value })} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Input label="Radius Meters" value={locationForm.geofence_radius_meters} onChange={(value) => setLocationForm({ ...locationForm, geofence_radius_meters: value })} />
                <Input label="GPS Accuracy" value={locationForm.allowed_gps_accuracy_meters} onChange={(value) => setLocationForm({ ...locationForm, allowed_gps_accuracy_meters: value })} />
              </div>
            </Panel>

            <Panel title="Create Geofence" action="Save geofence" busy={busy === "geofence"} onSubmit={createGeofence}>
              <Select label="Location" value={geofenceForm.location_id} options={locationOptions.map((item) => item.data.location_id).filter(Boolean)} onChange={(value) => {
                const next = locationOptions.find((item) => item.data.location_id === value)?.data;
                setGeofenceForm({
                  ...geofenceForm,
                  location_id: value,
                  center_latitude: next?.latitude || geofenceForm.center_latitude,
                  center_longitude: next?.longitude || geofenceForm.center_longitude,
                });
              }} />
              {selectedLocation ? <p className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600">{selectedLocation.location_name} / {selectedLocation.full_address}</p> : null}
              <Select label="Type" value={geofenceForm.geofence_type} options={["Circular", "Polygon"]} onChange={(value) => setGeofenceForm({ ...geofenceForm, geofence_type: value })} />
              <div className="grid grid-cols-2 gap-3">
                <Input label="Center Latitude" value={geofenceForm.center_latitude} onChange={(value) => setGeofenceForm({ ...geofenceForm, center_latitude: value })} />
                <Input label="Center Longitude" value={geofenceForm.center_longitude} onChange={(value) => setGeofenceForm({ ...geofenceForm, center_longitude: value })} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Input label="Radius" value={geofenceForm.radius_meters} onChange={(value) => setGeofenceForm({ ...geofenceForm, radius_meters: value })} />
                <Input label="Allowed Accuracy" value={geofenceForm.allowed_accuracy_meters} onChange={(value) => setGeofenceForm({ ...geofenceForm, allowed_accuracy_meters: value })} />
              </div>
              <Input label="Polygon JSON" value={geofenceForm.polygon_coordinates} onChange={(value) => setGeofenceForm({ ...geofenceForm, polygon_coordinates: value })} placeholder='[{"lat":23.1,"lng":72.5}]' />
            </Panel>

            <Panel title="Test Coordinate" action="Run backend test" busy={busy === "test"} onSubmit={testGeofence}>
              <Select label="Location" value={testForm.location_id} options={locationOptions.map((item) => item.data.location_id).filter(Boolean)} onChange={(value) => setTestForm({ ...testForm, location_id: value })} />
              <div className="grid grid-cols-2 gap-3">
                <Input label="Latitude" value={testForm.latitude} onChange={(value) => setTestForm({ ...testForm, latitude: value })} />
                <Input label="Longitude" value={testForm.longitude} onChange={(value) => setTestForm({ ...testForm, longitude: value })} />
              </div>
              <Input label="Accuracy Meters" value={testForm.accuracy} onChange={(value) => setTestForm({ ...testForm, accuracy: value })} />
              {testResult ? (
                <div className={`rounded-lg border p-3 text-sm ${tone(testResult.geofence_status || "")}`}>
                  <div className="font-semibold">{testResult.geofence_status}</div>
                  <div className="mt-1 text-xs">Distance {testResult.distance_meters}m / Radius {testResult.radius_meters}m / Accuracy {testResult.accuracy_meters}m</div>
                </div>
              ) : null}
            </Panel>

            <Panel title="Assign Employee" action="Assign location" busy={busy === "assignment"} onSubmit={assignLocation}>
              <Input label="Employee Code or Email" value={assignmentForm.employee_code} onChange={(value) => setAssignmentForm({ ...assignmentForm, employee_code: value })} />
              <Select label="Location" value={assignmentForm.location_id} options={locationOptions.map((item) => item.data.location_id).filter(Boolean)} onChange={(value) => setAssignmentForm({ ...assignmentForm, location_id: value })} />
              <div className="grid grid-cols-2 gap-3">
                <Input label="Shift" value={assignmentForm.shift} onChange={(value) => setAssignmentForm({ ...assignmentForm, shift: value })} />
                <Select label="Type" value={assignmentForm.assignment_type} options={["Primary", "Temporary", "Shift Specific", "Project"]} onChange={(value) => setAssignmentForm({ ...assignmentForm, assignment_type: value })} />
              </div>
            </Panel>
          </aside>
        </div>
      </section>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <div className="text-xs font-medium text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  );
}

function GeofenceMap({
  config,
  latitude,
  longitude,
  radius,
  zoom,
  onZoom,
  onPlace,
}: {
  config: MapConfig;
  latitude: number;
  longitude: number;
  radius: number;
  zoom: number;
  onZoom: (value: number) => void;
  onPlace: (latitude: number, longitude: number, source?: string) => void;
}) {
  const mapRef = useRef<HTMLDivElement | null>(null);
  const safeLat = clamp(latitude || numeric(config.default_center.latitude), -85, 85);
  const safeLon = clamp(longitude || numeric(config.default_center.longitude), -180, 180);
  const safeZoom = clamp(Math.round(zoom || numeric(config.default_center.zoom) || 15), 3, 19);
  const centerX = lonToTileX(safeLon, safeZoom);
  const centerY = latToTileY(safeLat, safeZoom);
  const tileCount = 2 ** safeZoom;
  const metersPerPixel = Math.cos(safeLat * Math.PI / 180) * 40075016.686 / (tileCount * 256);
  const radiusPx = clamp(radius / Math.max(metersPerPixel, 0.01), 14, 420);
  const tiles = [];
  for (let dx = -2; dx <= 2; dx += 1) {
    for (let dy = -2; dy <= 2; dy += 1) {
      const rawX = Math.floor(centerX) + dx;
      const x = ((rawX % tileCount) + tileCount) % tileCount;
      const y = clamp(Math.floor(centerY) + dy, 0, tileCount - 1);
      tiles.push({ x, y, left: (rawX - centerX) * 256 + 320, top: (y - centerY) * 256 + 240 });
    }
  }

  function handleClick(event: MouseEvent<HTMLDivElement>) {
    const rect = mapRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = centerX + (event.clientX - rect.left - rect.width / 2) / 256;
    const y = centerY + (event.clientY - rect.top - rect.height / 2) / 256;
    onPlace(tileYToLat(y, safeZoom), tileXToLon(x, safeZoom), "Map click");
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-slate-900">
      <div ref={mapRef} onClick={handleClick} className="relative h-[420px] cursor-crosshair overflow-hidden sm:h-[480px]">
        {tiles.map((tile) => (
          <div
            key={`${safeZoom}-${tile.x}-${tile.y}`}
            className="absolute h-64 w-64 bg-cover bg-center"
            style={{ left: tile.left, top: tile.top, backgroundImage: `url(${tileUrl(config.tile_url_template, safeZoom, tile.x, tile.y)})` }}
          />
        ))}
        <div
          className="pointer-events-none absolute left-1/2 top-1/2 rounded-full border-2 border-teal-500 bg-teal-400/15 shadow-[0_0_0_1px_rgba(255,255,255,0.65)]"
          style={{ width: radiusPx * 2, height: radiusPx * 2, transform: "translate(-50%, -50%)" }}
        />
        <div className="pointer-events-none absolute left-1/2 top-1/2 h-7 w-7 -translate-x-1/2 -translate-y-full rounded-full border-2 border-white bg-rose-600 shadow-lg">
          <div className="absolute left-1/2 top-full h-3 w-1 -translate-x-1/2 bg-rose-600" />
        </div>
        <div className="absolute left-3 top-3 flex overflow-hidden rounded-lg border border-white/70 bg-white shadow-sm">
          <button onClick={(event) => { event.stopPropagation(); onZoom(clamp(safeZoom + 1, 3, 19)); }} className="h-9 w-10 border-r border-slate-200 text-lg font-semibold text-slate-800 hover:bg-slate-50">+</button>
          <button onClick={(event) => { event.stopPropagation(); onZoom(clamp(safeZoom - 1, 3, 19)); }} className="h-9 w-10 text-lg font-semibold text-slate-800 hover:bg-slate-50">-</button>
        </div>
        <div className="absolute bottom-3 left-3 rounded-lg bg-white/95 px-3 py-2 text-xs text-slate-700 shadow-sm">
          {safeLat.toFixed(6)}, {safeLon.toFixed(6)} / z{safeZoom} / {Math.round(radius)}m
        </div>
      </div>
      <div className="flex items-center justify-between gap-3 border-t border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300">
        <span>Click map to place marker. Radius preview uses configured meters-per-pixel at this latitude.</span>
        <span className="shrink-0">{config.attribution}</span>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="truncate text-sm font-semibold">{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}

function Panel({ title, action, busy, onSubmit, children }: { title: string; action: string; busy: boolean; onSubmit: () => void; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="font-semibold">{title}</h2>
      <div className="mt-3 space-y-3">{children}</div>
      <button disabled={busy} onClick={onSubmit} className="mt-4 w-full rounded-lg bg-slate-950 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50">
        {busy ? "Working..." : action}
      </button>
    </section>
  );
}

function Input({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-teal-700" />
    </label>
  );
}

function Select({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-teal-700">
        <option value="">Select</option>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}
