import AsyncStorage from "@react-native-async-storage/async-storage";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import * as LocalAuthentication from "expo-local-authentication";
import * as Location from "expo-location";
import { StatusBar } from "expo-status-bar";
import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View
} from "react-native";

const API_BASE = "https://erp-production-8664.up.railway.app";
const TOKEN_KEY = "factorypulse_token";
const USER_KEY = "factorypulse_user";
const STATUSES = ["Open", "Active", "Pending", "Approved", "Rejected", "Completed", "Closed", "On Hold", "Critical"];

type User = { email: string; name: string; role: string };
type DepartmentCard = { id: string; name: string; record_count: number; module_count: number };
type PriorityWork = { department: string; resource: string; title: string; status: string };
type MobileSummary = {
  database: string;
  stats: { departments: number; modules: number; records: number };
  priority_work: PriorityWork[];
  departments: DepartmentCard[];
};
type EmployeeSummary = {
  employee_code: string;
  attendance: { checked_in: boolean; date: string; day_in_time: string; day_out_time: string; late_mark: boolean; late_after_time: string; records_today: number };
  attendance_policy: Record<string, string>;
  assignment: Record<string, string> | null;
  work_location: Record<string, string> | null;
  calendar: AttendanceCalendar;
  leave: { pending: number; approved: number; balances: Record<string, string>[] };
  salary: { latest: Record<string, string> | null; count: number };
  notifications: { unread: number; latest: Record<string, string> | null };
  tracking: { last_location: Record<string, string> | null; ping_count: number };
};
type AttendanceCalendar = {
  month: string;
  present: number;
  absent: number;
  leave: number;
  holiday: number;
  days: { date: string; day: number; status: string }[];
};
type EmployeeHistory = {
  items: RecordItem[];
  legacy_items: RecordItem[];
  location_events: RecordItem[];
  biometric_events: RecordItem[];
  correction_requests: RecordItem[];
};
type Department = {
  id: string;
  name: string;
  modules: Module[];
};
type Module = {
  resource: string;
  label: string;
  fields: string[];
  count: number;
  items: RecordItem[];
};
type RecordItem = { id: string; resource?: string; data: Record<string, string>; status: string };
type SalarySlip = {
  id: string;
  period: string;
  gross_pay: string;
  deductions: string;
  net_pay: string;
  payment_date: string;
  status: string;
  lines: { component_name: string; component_type: string; amount: string }[];
};
type SalaryDashboard = { items: SalarySlip[]; latest: SalarySlip | null; totals: { gross_pay: number; deductions: number; net_pay: number } };
type NotificationDashboard = { items: RecordItem[]; unread: number };
type Screen =
  | { name: "home" }
  | { name: "work" }
  | { name: "departments" }
  | { name: "department"; id: string }
  | { name: "create"; departmentId: string; module: Module }
  | { name: "profile" };

const QUICK_ACTIONS = [
  { title: "Day In / Out", departmentId: "hr", resource: "attendance", icon: "finger-print", preset: { status: "Open" } },
  { title: "Apply Leave", departmentId: "hr", resource: "leave_requests", icon: "calendar", preset: { status: "Pending" } },
  { title: "Expense Claim", departmentId: "hr", resource: "expense_claims", icon: "receipt", preset: { status: "Pending" } },
  { title: "Safety Incident", departmentId: "quality", resource: "incidents", icon: "warning", preset: { status: "Critical" } },
  { title: "Maintenance Task", departmentId: "maintenance", resource: "maintenance_work_orders", icon: "construct", preset: { status: "Open" } },
  { title: "Gate Pass", departmentId: "security", resource: "gate_passes", icon: "shield-checkmark", preset: { status: "Open" } },
  { title: "Vehicle Check", departmentId: "security", resource: "vehicle_inspections", icon: "car", preset: { status: "Open" } },
  { title: "Water Log", departmentId: "environment", resource: "water_usage", icon: "water", preset: { status: "Open" } }
] as const;

function pretty(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function keyboardFor(field: string): "default" | "email-address" | "numeric" {
  const lowered = field.toLowerCase();
  if (lowered.includes("email")) return "email-address";
  if (["amount", "budget", "spent", "quantity", "percent", "score", "weight", "tonnage", "kwh", "litres", "kl", "ph", "bod", "cod"].some((token) => lowered.includes(token))) return "numeric";
  return "default";
}

function isDateLike(field: string) {
  const lowered = field.toLowerCase();
  return lowered.includes("date") || lowered.includes("until") || lowered.includes("due");
}

function requiredFields(fields: string[]) {
  return fields.filter((field) => field !== "status").slice(0, 2);
}

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [booting, setBooting] = useState(true);
  const [screen, setScreen] = useState<Screen>({ name: "home" });

  useEffect(() => {
    async function restore() {
      const savedToken = await AsyncStorage.getItem(TOKEN_KEY);
      const savedUser = await AsyncStorage.getItem(USER_KEY);
      setToken(savedToken);
      setUser(savedUser ? JSON.parse(savedUser) : null);
      setBooting(false);
    }
    restore().catch(() => setBooting(false));
  }, []);

  async function signIn(email: string, password: string) {
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.trim(), password })
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || "Invalid credentials or backend unavailable");
    }
    const data = await response.json();
    await AsyncStorage.setItem(TOKEN_KEY, data.token);
    await AsyncStorage.setItem(USER_KEY, JSON.stringify(data.user));
    setToken(data.token);
    setUser(data.user);
    setScreen({ name: "home" });
  }

  async function signOut() {
    await AsyncStorage.multiRemove([TOKEN_KEY, USER_KEY]);
    setToken(null);
    setUser(null);
    setScreen({ name: "home" });
  }

  if (booting) {
    return <LoadingScreen label="Starting FactoryPulse" />;
  }

  if (!token || !user) {
    return <LoginScreen onSignIn={signIn} />;
  }

  return (
    <SafeAreaView style={styles.shell}>
      <StatusBar style="light" />
      {screen.name === "home" && <HomeScreen token={token} user={user} navigate={setScreen} />}
      {screen.name === "work" && <WorkScreen token={token} navigate={setScreen} />}
      {screen.name === "departments" && <DepartmentListScreen token={token} navigate={setScreen} />}
      {screen.name === "department" && <DepartmentScreen token={token} departmentId={screen.id} navigate={setScreen} />}
      {screen.name === "create" && <CreateRecordScreen token={token} departmentId={screen.departmentId} module={screen.module} navigate={setScreen} />}
      {screen.name === "profile" && <ProfileScreen user={user} onSignOut={signOut} navigate={setScreen} />}
      <BottomNav current={screen.name} navigate={setScreen} />
    </SafeAreaView>
  );
}

function LoadingScreen({ label }: { label: string }) {
  return (
    <SafeAreaView style={styles.loading}>
      <ActivityIndicator color="#14b8a6" size="large" />
      <Text style={styles.loadingText}>{label}</Text>
    </SafeAreaView>
  );
}

function LoginScreen({ onSignIn }: { onSignIn: (email: string, password: string) => Promise<void> }) {
  const [email, setEmail] = useState("admin@gmail.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit() {
    setError("");
    if (!email.includes("@")) {
      setError("Enter a valid email address.");
      return;
    }
    if (!password.trim()) {
      setError("Password is required.");
      return;
    }
    setLoading(true);
    try {
      await onSignIn(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.loginShell}>
      <StatusBar style="light" />
      <LinearGradient colors={["#0f172a", "#0f766e"]} style={styles.loginHero}>
        <Text style={styles.brand}>FactoryPulse</Text>
        <Text style={styles.loginTitle}>Sugar Factory Employee ERP</Text>
        <Text style={styles.loginSubtitle}>Attendance, leave, safety, maintenance, gate control, and department records from the live ERP API.</Text>
      </LinearGradient>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.loginPanel}>
        <Text style={styles.panelTitle}>Employee Sign In</Text>
        <Input label="Email" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" />
        <Input label="Password" value={password} onChangeText={setPassword} secureTextEntry />
        {error ? <Text style={styles.errorText}>{error}</Text> : null}
        <Pressable style={[styles.primaryButton, loading && styles.disabledButton]} onPress={submit} disabled={loading}>
          {loading ? <ActivityIndicator color="#ffffff" /> : <Text style={styles.primaryButtonText}>Sign in to ERP</Text>}
        </Pressable>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function HomeScreen({ token, user, navigate }: { token: string; user: User; navigate: (screen: Screen) => void }) {
  const { data, loading, error, refresh } = useApi<MobileSummary>(token, "/api/mobile/summary");

  return (
    <ScreenScroll refresh={refresh} loading={loading}>
      <LinearGradient colors={["#0f172a", "#164e63"]} style={styles.heroCard}>
        <Text style={styles.heroEyebrow}>Live Sugar Factory ERP</Text>
        <Text style={styles.heroTitle}>Good shift, {user.name || user.email}</Text>
        <Text style={styles.heroCopy}>Connected to {data?.database || "ERP"} with full mobile workflows for factory employees.</Text>
        <View style={styles.statsRow}>
          <StatPill label="Departments" value={String(data?.stats.departments || 0)} />
          <StatPill label="Modules" value={String(data?.stats.modules || 0)} />
          <StatPill label="Records" value={String(data?.stats.records || 0)} />
        </View>
      </LinearGradient>

      {error ? <ErrorBanner message={error} /> : null}

      <SectionHeader title="Quick Actions" action="All departments" onPress={() => navigate({ name: "departments" })} />
      <View style={styles.quickGrid}>
        {QUICK_ACTIONS.map((action) => (
          <Pressable
            key={action.resource}
            style={styles.quickCard}
            onPress={() => action.resource === "attendance" || action.resource === "leave_requests" ? navigate({ name: "work" }) : navigate({ name: "department", id: action.departmentId })}
          >
            <Ionicons name={action.icon} size={24} color="#0f766e" />
            <Text style={styles.quickTitle}>{action.title}</Text>
            <Text style={styles.quickMeta}>{pretty(action.resource)}</Text>
          </Pressable>
        ))}
      </View>

      <SectionHeader title="Priority Work" />
      {(data?.priority_work || []).length === 0 ? (
        <EmptyState title="No priority work" body="Open, pending, critical, and held records will appear here." />
      ) : data?.priority_work.map((item, index) => <PriorityCard key={`${item.resource}-${index}`} item={item} />)}

      <SectionHeader title="Department Access" />
      {data?.departments.map((department) => (
        <Pressable key={department.id} style={styles.departmentRow} onPress={() => navigate({ name: "department", id: department.id })}>
          <View style={styles.departmentIcon}><Text style={styles.departmentInitial}>{department.name.slice(0, 1)}</Text></View>
          <View style={styles.flex}>
            <Text style={styles.departmentName}>{department.name}</Text>
            <Text style={styles.departmentMeta}>{department.module_count} modules · {department.record_count} records</Text>
          </View>
          <Ionicons name="chevron-forward" size={18} color="#64748b" />
        </Pressable>
      ))}
    </ScreenScroll>
  );
}

function WorkScreen({ token, navigate }: { token: string; navigate: (screen: Screen) => void }) {
  const { data, loading, error, refresh } = useApi<EmployeeSummary>(token, "/api/mobile/employee/summary");
  const { data: history, loading: historyLoading, error: historyError, refresh: refreshHistory } = useApi<EmployeeHistory>(token, "/api/v1/employee/attendance/history");
  const { data: salary, loading: salaryLoading, error: salaryError, refresh: refreshSalary } = useApi<SalaryDashboard>(token, "/api/v1/employee/salary-slips");
  const { data: notifications, loading: notificationsLoading, error: notificationsError, refresh: refreshNotifications } = useApi<NotificationDashboard>(token, "/api/v1/employee/notifications");
  const [busy, setBusy] = useState(false);
  const [leaveType, setLeaveType] = useState("Casual Leave");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [reason, setReason] = useState("");
  const [correctionDate, setCorrectionDate] = useState("");
  const [correctionIn, setCorrectionIn] = useState("");
  const [correctionOut, setCorrectionOut] = useState("");
  const [correctionReason, setCorrectionReason] = useState("");
  const [tracking, setTracking] = useState(false);
  const trackingInterval = Math.max(Number(data?.attendance_policy?.tracking_interval_minutes || 5), 1);
  const attendanceRows = history?.items?.length ? history.items : history?.legacy_items || [];

  useEffect(() => {
    if (!tracking || !data?.attendance.checked_in) return;
    const timer = setInterval(() => {
      pingLocation(token, "working_hours").catch(() => undefined);
    }, trackingInterval * 60 * 1000);
    return () => clearInterval(timer);
  }, [data?.attendance.checked_in, token, tracking, trackingInterval]);

  async function attendanceAction(kind: "day-in" | "day-out") {
    setBusy(true);
    try {
      await requireThumb();
      const location = await currentLocation();
      const response = await fetch(`${API_BASE}/api/mobile/employee/${kind}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          shift: "General",
          latitude: location?.coords.latitude,
          longitude: location?.coords.longitude,
          accuracy: location?.coords.accuracy,
        })
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Attendance action failed");
      }
      if (kind === "day-in") setTracking(true);
      if (kind === "day-out") setTracking(false);
      refresh();
      refreshHistory();
      refreshNotifications();
    } catch (err) {
      Alert.alert("Attendance", err instanceof Error ? err.message : "Attendance action failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleTracking() {
    if (tracking) {
      setTracking(false);
      return;
    }
    try {
      await requestBackgroundTrackingPermission();
      setTracking(true);
      await pingLocation(token, "working_hours");
      refresh();
    } catch (err) {
      Alert.alert("Location tracking", err instanceof Error ? err.message : "Location permission failed");
    }
  }

  async function submitLeave() {
    if (!fromDate || !toDate || !reason.trim()) {
      Alert.alert("Leave request", "From date, to date, and reason are required.");
      return;
    }
    setBusy(true);
    try {
      const response = await fetch(`${API_BASE}/api/mobile/employee/leave`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ leave_type: leaveType, from_date: fromDate, to_date: toDate, reason })
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Leave apply failed");
      }
      setReason("");
      Alert.alert("Leave request", "Leave request saved to ERP for approval.");
      refresh();
      refreshHistory();
      refreshNotifications();
    } catch (err) {
      Alert.alert("Leave request", err instanceof Error ? err.message : "Leave apply failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitCorrection() {
    if (!correctionDate.trim() || !correctionReason.trim()) {
      Alert.alert("Correction request", "Attendance date and reason are required.");
      return;
    }
    setBusy(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/employee/attendance/correction`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          attendance_date: correctionDate,
          requested_day_in_time: correctionIn,
          requested_day_out_time: correctionOut,
          reason: correctionReason,
          requested_changes: `Day In ${correctionIn || "-"} / Day Out ${correctionOut || "-"}`,
        })
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Correction request failed");
      }
      setCorrectionIn("");
      setCorrectionOut("");
      setCorrectionReason("");
      Alert.alert("Correction request", "Request submitted to HR for approval.");
      refreshHistory();
      refreshNotifications();
    } catch (err) {
      Alert.alert("Correction request", err instanceof Error ? err.message : "Correction request failed");
    } finally {
      setBusy(false);
    }
  }

  async function markNotificationRead(notificationId: string) {
    setBusy(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/employee/notifications/read`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ notification_id: notificationId })
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Notification update failed");
      }
      refreshNotifications();
      refresh();
    } catch (err) {
      Alert.alert("Notifications", err instanceof Error ? err.message : "Notification update failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScreenScroll refresh={() => { refresh(); refreshHistory(); refreshSalary(); refreshNotifications(); }} loading={loading || historyLoading || salaryLoading || notificationsLoading}>
      <TopBar title="Employee Work" subtitle="Attendance, leave, salary, calendar and location controls" />
      {error ? <ErrorBanner message={error} /> : null}
      {historyError ? <ErrorBanner message={historyError} /> : null}
      {salaryError ? <ErrorBanner message={salaryError} /> : null}
      {notificationsError ? <ErrorBanner message={notificationsError} /> : null}

      <LinearGradient colors={data?.attendance.checked_in ? ["#065f46", "#0f766e"] : ["#0f172a", "#334155"]} style={styles.attendanceCard}>
        <View style={styles.moduleHeader}>
          <View>
            <Text style={styles.attendanceLabel}>Today</Text>
            <Text style={styles.attendanceTitle}>{data?.attendance.checked_in ? "Checked In" : data?.attendance.day_out_time ? "Shift Completed" : "Ready for Day In"}</Text>
          </View>
          <Ionicons name="finger-print" size={34} color="#ccfbf1" />
        </View>
        <View style={styles.attendanceTimes}>
          <TimeTile label="Day In" value={data?.attendance.day_in_time || "--:--"} tone="green" />
          <TimeTile label="Day Out" value={data?.attendance.day_out_time || "--:--"} tone="blue" />
          <TimeTile label="Late" value={data?.attendance.late_mark ? "Yes" : "No"} tone={data?.attendance.late_mark ? "red" : "green"} />
        </View>
        <Text style={styles.policyText}>Late after {data?.attendance.late_after_time || data?.attendance_policy?.late_after_time || "HR policy"} - tracking every {trackingInterval} min</Text>
        <Text style={styles.policyText}>Location: {data?.work_location?.location_name || "No active HR geofence assignment"}</Text>
        <View style={styles.actionRow}>
          <Pressable style={[styles.lightButton, busy && styles.disabledButton]} disabled={busy} onPress={() => attendanceAction("day-in")}>
            <Text style={styles.lightButtonText}>Thumb Day In</Text>
          </Pressable>
          <Pressable style={[styles.lightButton, busy && styles.disabledButton]} disabled={busy} onPress={() => attendanceAction("day-out")}>
            <Text style={styles.lightButtonText}>Thumb Day Out</Text>
          </Pressable>
        </View>
        <Pressable style={styles.trackButton} onPress={toggleTracking}>
          <Ionicons name={tracking ? "location" : "location-outline"} size={18} color="#ffffff" />
          <Text style={styles.trackButtonText}>{tracking ? "Working-hours location tracking active" : "Enable working-hours location tracking"}</Text>
        </Pressable>
      </LinearGradient>

      <SectionHeader title="Notifications" action={`${notifications?.unread || data?.notifications?.unread || 0} unread`} />
      {(notifications?.items || []).length === 0 ? (
        <EmptyState title="No notifications" body="Attendance, leave, payroll, and HR updates will appear here from the live ERP." />
      ) : notifications?.items.slice(0, 4).map((item) => (
        <Pressable
          key={item.id}
          style={[styles.notificationCard, item.data.read_status === "Unread" && styles.notificationUnread]}
          onPress={() => markNotificationRead(item.data.notification_id || item.id)}
        >
          <View style={styles.flex}>
            <Text style={styles.notificationTitle}>{item.data.title || pretty(item.data.notification_type || "Notification")}</Text>
            <Text style={styles.notificationBody}>{item.data.message || "ERP notification"}</Text>
          </View>
          <Text style={styles.notificationStatus}>{item.data.read_status || "Unread"}</Text>
        </Pressable>
      ))}

      <SectionHeader title="This Month" />
      <View style={styles.calendarStats}>
        <CountTile label="Present" value={data?.calendar.present || 0} color="#16a34a" />
        <CountTile label="Absent" value={data?.calendar.absent || 0} color="#dc2626" />
        <CountTile label="Leave" value={data?.calendar.leave || 0} color="#9333ea" />
        <CountTile label="Holiday" value={data?.calendar.holiday || 0} color="#0284c7" />
      </View>
      <CalendarGrid days={data?.calendar.days || []} />

      <SectionHeader title="Attendance History" />
      {(attendanceRows || []).length === 0 ? (
        <EmptyState title="No attendance records" body="Day In, Day Out, and HR-approved corrections will appear here from the live ERP." />
      ) : attendanceRows.slice(0, 5).map((item) => (
        <View key={item.id} style={styles.historyRow}>
          <View style={styles.flex}>
            <Text style={styles.historyTitle}>{item.data.attendance_date || item.data.date || "Attendance"}</Text>
            <Text style={styles.historyMeta}>
              In {item.data.day_in_time || item.data.check_in || "--:--"} - Out {item.data.day_out_time || item.data.check_out || "--:--"}
            </Text>
            <Text style={styles.historyMeta}>{item.data.day_in_geofence_status || item.data.gps_area || "Location evidence pending"}</Text>
          </View>
          <Text style={styles.historyStatus}>{item.status || item.data.attendance_status || item.data.status || "Open"}</Text>
        </View>
      ))}

      <SectionHeader title="Correction Request" />
      <View style={styles.largeCard}>
        <Text style={styles.cardMeta}>Pending {history?.correction_requests?.filter((item) => ["Open", "Pending", "Pending Approval"].includes(item.status)).length || 0} requests</Text>
        <Input label="Attendance date" value={correctionDate} onChangeText={setCorrectionDate} placeholder="YYYY-MM-DD" />
        <Input label="Requested Day In" value={correctionIn} onChangeText={setCorrectionIn} placeholder="HH:MM" />
        <Input label="Requested Day Out" value={correctionOut} onChangeText={setCorrectionOut} placeholder="HH:MM" />
        <Input label="Reason" value={correctionReason} onChangeText={setCorrectionReason} placeholder="GPS issue, official travel, missing punch..." />
        <Pressable style={[styles.primaryButton, busy && styles.disabledButton]} disabled={busy} onPress={submitCorrection}>
          <Text style={styles.primaryButtonText}>Submit Correction</Text>
        </Pressable>
      </View>

      <SectionHeader title="Leave" />
      <View style={styles.largeCard}>
        <Text style={styles.cardMeta}>Pending {data?.leave.pending || 0} · Approved {data?.leave.approved || 0}</Text>
        <View style={styles.statusRow}>
          {["Casual Leave", "Sick Leave", "Earned Leave", "Comp Off"].map((type) => (
            <Pressable key={type} style={[styles.statusChip, leaveType === type && styles.statusChipActive]} onPress={() => setLeaveType(type)}>
              <Text style={[styles.statusChipText, leaveType === type && styles.statusChipTextActive]}>{type}</Text>
            </Pressable>
          ))}
        </View>
        <Input label="From date" value={fromDate} onChangeText={setFromDate} placeholder="YYYY-MM-DD" />
        <Input label="To date" value={toDate} onChangeText={setToDate} placeholder="YYYY-MM-DD" />
        <Input label="Reason" value={reason} onChangeText={setReason} placeholder="Reason for leave" />
        <Pressable style={[styles.primaryButton, busy && styles.disabledButton]} disabled={busy} onPress={submitLeave}>
          <Text style={styles.primaryButtonText}>Apply Leave</Text>
        </Pressable>
      </View>

      <SectionHeader title="Salary" />
      <View style={styles.largeCard}>
        {data?.salary.latest ? (
          <>
            <Text style={styles.cardTitle}>{data.salary.latest.period || "Latest salary slip"}</Text>
            <Text style={styles.salaryAmount}>₹{data.salary.latest.net_pay || "0"}</Text>
            <Text style={styles.cardMeta}>Gross ₹{data.salary.latest.gross_pay || "0"} · Deductions ₹{data.salary.latest.deductions || "0"}</Text>
          </>
        ) : (
          <Text style={styles.mutedText}>No salary slip released yet. HR payroll records will appear here from the live ERP.</Text>
        )}
      </View>

      <SectionHeader title="Salary Details" action={`${salary?.items.length || 0} slips`} />
      <View style={styles.largeCard}>
        {salary?.latest ? (
          <>
            <Text style={styles.cardTitle}>{salary.latest.period || "Latest payroll period"}</Text>
            <Text style={styles.salaryAmount}>Rs. {salary.latest.net_pay || "0"}</Text>
            <Text style={styles.cardMeta}>Gross Rs. {salary.latest.gross_pay || "0"} . Deductions Rs. {salary.latest.deductions || "0"}</Text>
            {salary.latest.lines.map((line) => (
              <View key={`${line.component_name}-${line.component_type}`} style={styles.salaryLine}>
                <Text style={styles.salaryLineName}>{line.component_name}</Text>
                <Text style={styles.salaryLineAmount}>Rs. {line.amount}</Text>
              </View>
            ))}
            <View style={styles.salaryTotals}>
              <CountTile label="Slips" value={salary.items.length} color="#0f766e" />
              <CountTile label="YTD Net" value={Math.round(salary.totals.net_pay)} color="#0284c7" />
            </View>
          </>
        ) : (
          <Text style={styles.mutedText}>Detailed salary slips will appear after Finance generates payroll in the ERP.</Text>
        )}
      </View>

      <Pressable style={styles.secondaryButton} onPress={() => navigate({ name: "department", id: "hr" })}>
        <Text style={styles.secondaryButtonText}>Open Full HR Workspace</Text>
      </Pressable>
    </ScreenScroll>
  );
}

async function requireThumb() {
  const compatible = await LocalAuthentication.hasHardwareAsync();
  const enrolled = await LocalAuthentication.isEnrolledAsync();
  if (!compatible || !enrolled) {
    throw new Error("Fingerprint or device lock is not enrolled on this phone.");
  }
  const result = await LocalAuthentication.authenticateAsync({
    promptMessage: "Confirm with thumb",
    fallbackLabel: "Use device passcode",
    disableDeviceFallback: false,
  });
  if (!result.success) throw new Error("Thumb verification cancelled or failed.");
}

async function currentLocation() {
  const permission = await Location.requestForegroundPermissionsAsync();
  if (permission.status !== "granted") {
    throw new Error("Location permission is required for day-in/day-out.");
  }
  return Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
}

async function requestBackgroundTrackingPermission() {
  const foreground = await Location.requestForegroundPermissionsAsync();
  if (foreground.status !== "granted") {
    throw new Error("Location permission is required for working-hours tracking.");
  }
  const background = await Location.requestBackgroundPermissionsAsync();
  if (background.status !== "granted") {
    throw new Error("Background location permission is required for working-hours tracking.");
  }
}

async function pingLocation(token: string, event: string) {
  const location = await currentLocation();
  await fetch(`${API_BASE}/api/mobile/employee/location`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      latitude: location.coords.latitude,
      longitude: location.coords.longitude,
      accuracy: location.coords.accuracy,
      event,
    })
  });
}

function DepartmentListScreen({ token, navigate }: { token: string; navigate: (screen: Screen) => void }) {
  const { data, loading, error, refresh } = useApi<MobileSummary>(token, "/api/mobile/summary");
  const [query, setQuery] = useState("");
  const departments = useMemo(() => {
    const value = query.trim().toLowerCase();
    if (!value) return data?.departments || [];
    return (data?.departments || []).filter((item) => item.name.toLowerCase().includes(value));
  }, [data, query]);

  return (
    <ScreenScroll refresh={refresh} loading={loading}>
      <TopBar title="Departments" subtitle="Browse every ERP department" />
      <TextInput style={styles.searchInput} placeholder="Search department" value={query} onChangeText={setQuery} />
      {error ? <ErrorBanner message={error} /> : null}
      {departments.map((department) => (
        <Pressable key={department.id} style={styles.largeCard} onPress={() => navigate({ name: "department", id: department.id })}>
          <Text style={styles.cardTitle}>{department.name}</Text>
          <Text style={styles.cardMeta}>{department.module_count} modules · {department.record_count} records</Text>
        </Pressable>
      ))}
    </ScreenScroll>
  );
}

function DepartmentScreen({ token, departmentId, navigate }: { token: string; departmentId: string; navigate: (screen: Screen) => void }) {
  const { data, loading, error, refresh } = useApi<Department>(token, `/api/departments/${departmentId}`);
  const [query, setQuery] = useState("");
  const modules = useMemo(() => {
    const value = query.trim().toLowerCase();
    if (!value) return data?.modules || [];
    return (data?.modules || []).filter((module) => `${module.label} ${module.resource}`.toLowerCase().includes(value));
  }, [data, query]);

  return (
    <ScreenScroll refresh={refresh} loading={loading}>
      <BackHeader title={data?.name || "Department"} onBack={() => navigate({ name: "departments" })} />
      <TextInput style={styles.searchInput} placeholder="Search module" value={query} onChangeText={setQuery} />
      {error ? <ErrorBanner message={error} /> : null}
      {modules.map((module) => (
        <View key={module.resource} style={styles.moduleCard}>
          <View style={styles.moduleHeader}>
            <View>
              <Text style={styles.cardTitle}>{module.label}</Text>
              <Text style={styles.cardMeta}>{module.count} records · {module.fields.length} fields</Text>
            </View>
            <Pressable style={styles.smallButton} onPress={() => navigate({ name: "create", departmentId, module })}>
              <Text style={styles.smallButtonText}>Create</Text>
            </Pressable>
          </View>
          {module.items.slice(0, 3).map((item) => <RecordPreview key={item.id} module={module} item={item} />)}
          {module.items.length === 0 ? <Text style={styles.mutedText}>No records yet. Create one from the live API.</Text> : null}
        </View>
      ))}
    </ScreenScroll>
  );
}

function CreateRecordScreen({ token, departmentId, module, navigate }: { token: string; departmentId: string; module: Module; navigate: (screen: Screen) => void }) {
  const initial = useMemo(() => ({ status: "Open", ...QUICK_ACTIONS.find((action) => action.resource === module.resource)?.preset }), [module.resource]);
  const [form, setForm] = useState<Record<string, string>>(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const required = requiredFields(module.fields);

  function validate() {
    const missing = required.filter((field) => !form[field]?.trim());
    if (missing.length) return `Required fields missing: ${missing.map(pretty).join(", ")}`;
    const status = form.status;
    if (status && !STATUSES.includes(status)) return "Choose a valid status.";
    for (const field of module.fields) {
      const value = form[field]?.trim();
      if (!value) continue;
      const lowered = field.toLowerCase();
      if (lowered.includes("email") && (!value.includes("@") || !value.split("@")[1]?.includes("."))) return `${pretty(field)} must be a valid email.`;
      if (keyboardFor(field) === "numeric" && Number.isNaN(Number(value))) return `${pretty(field)} must be numeric.`;
      if (lowered.includes("percent") && (Number(value) < 0 || Number(value) > 100)) return `${pretty(field)} must be 0 to 100.`;
      if (lowered === "ph" && (Number(value) < 0 || Number(value) > 14)) return "pH must be 0 to 14.";
    }
    return "";
  }

  async function submit() {
    setError("");
    const validation = validate();
    if (validation) {
      setError(validation);
      return;
    }
    setSaving(true);
    try {
      const payload = Object.fromEntries(Object.entries(form).filter(([, value]) => value.trim() !== ""));
      const response = await fetch(`${API_BASE}/api/modules/${module.resource}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ data: payload })
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Save failed");
      }
      Alert.alert("Saved", `${module.label} record saved to ERP database.`, [
        { text: "OK", onPress: () => navigate({ name: "department", id: departmentId }) }
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.flex}>
      <ScreenScroll>
        <BackHeader title={`Create ${module.label}`} onBack={() => navigate({ name: "department", id: departmentId })} />
        <Text style={styles.formHint}>Fields marked * are required. All records are posted to the live FactoryPulse API.</Text>
        {error ? <ErrorBanner message={error} /> : null}
        {module.fields.map((field) => (
          <View key={field} style={styles.fieldBlock}>
            <Text style={styles.inputLabel}>{pretty(field)} {required.includes(field) ? "*" : ""}</Text>
            {field === "status" ? (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.statusRow}>
                {STATUSES.map((status) => (
                  <Pressable key={status} style={[styles.statusChip, form.status === status && styles.statusChipActive]} onPress={() => setForm((current) => ({ ...current, status }))}>
                    <Text style={[styles.statusChipText, form.status === status && styles.statusChipTextActive]}>{status}</Text>
                  </Pressable>
                ))}
              </ScrollView>
            ) : (
              <TextInput
                style={styles.textInput}
                value={form[field] || ""}
                onChangeText={(value) => setForm((current) => ({ ...current, [field]: value }))}
                keyboardType={keyboardFor(field)}
                placeholder={isDateLike(field) ? "YYYY-MM-DD" : `Enter ${pretty(field).toLowerCase()}`}
                autoCapitalize={field.toLowerCase().includes("email") ? "none" : "sentences"}
              />
            )}
          </View>
        ))}
        <Pressable style={[styles.primaryButton, saving && styles.disabledButton]} onPress={submit} disabled={saving}>
          {saving ? <ActivityIndicator color="#ffffff" /> : <Text style={styles.primaryButtonText}>Save to ERP</Text>}
        </Pressable>
      </ScreenScroll>
    </KeyboardAvoidingView>
  );
}

function ProfileScreen({ user, onSignOut, navigate }: { user: User; onSignOut: () => Promise<void>; navigate: (screen: Screen) => void }) {
  return (
    <ScreenScroll>
      <TopBar title="Employee Control" subtitle="Account, access, and live ERP connection" />
      <View style={styles.profileCard}>
        <View style={styles.avatar}><Text style={styles.avatarText}>{user.email.slice(0, 1).toUpperCase()}</Text></View>
        <Text style={styles.profileName}>{user.name || "FactoryPulse Employee"}</Text>
        <Text style={styles.profileMeta}>{user.email}</Text>
        <Text style={styles.roleBadge}>{user.role}</Text>
      </View>
      <View style={styles.largeCard}>
        <Text style={styles.cardTitle}>Employee capabilities</Text>
        {["Attendance and shift records", "Leave, expenses, and approvals", "Safety and incident reporting", "Maintenance requests", "Gate and vehicle controls", "Department module creation"].map((item) => (
          <View key={item} style={styles.checkRow}>
            <Ionicons name="checkmark-circle" size={18} color="#0f766e" />
            <Text style={styles.checkText}>{item}</Text>
          </View>
        ))}
      </View>
      <Pressable style={styles.secondaryButton} onPress={() => navigate({ name: "departments" })}><Text style={styles.secondaryButtonText}>Open ERP Departments</Text></Pressable>
      <Pressable style={styles.dangerButton} onPress={onSignOut}><Text style={styles.dangerButtonText}>Sign out</Text></Pressable>
    </ScreenScroll>
  );
}

function useApi<T>(token: string, path: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    fetch(`${API_BASE}${path}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (response) => {
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(body.detail || `API failed: ${response.status}`);
        }
        return response.json();
      })
      .then((json) => { if (!cancelled) setData(json); })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : "API request failed"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [path, tick, token]);

  return { data, loading, error, refresh: () => setTick((value) => value + 1) };
}

function ScreenScroll({ children, refresh, loading }: { children: React.ReactNode; refresh?: () => void; loading?: boolean }) {
  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.scrollContent}
      refreshControl={refresh ? <RefreshControl refreshing={Boolean(loading)} onRefresh={refresh} /> : undefined}
    >
      {children}
      <View style={{ height: 88 }} />
    </ScrollView>
  );
}

function BottomNav({ current, navigate }: { current: Screen["name"]; navigate: (screen: Screen) => void }) {
  const items = [
    { key: "home", label: "Home", icon: "home", screen: { name: "home" } as Screen },
    { key: "work", label: "Work", icon: "finger-print", screen: { name: "work" } as Screen },
    { key: "departments", label: "ERP", icon: "grid", screen: { name: "departments" } as Screen },
    { key: "profile", label: "Control", icon: "person-circle", screen: { name: "profile" } as Screen }
  ];
  return (
    <View style={styles.bottomNav}>
      {items.map((item) => {
        const active = current === item.key || (current === "department" && item.key === "departments") || (current === "create" && item.key === "departments");
        return (
          <Pressable key={item.key} style={styles.navItem} onPress={() => navigate(item.screen)}>
            <Ionicons name={item.icon as keyof typeof Ionicons.glyphMap} size={22} color={active ? "#0f766e" : "#64748b"} />
            <Text style={[styles.navLabel, active && styles.navLabelActive]}>{item.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

function Input(props: React.ComponentProps<typeof TextInput> & { label: string }) {
  const { label, ...inputProps } = props;
  return (
    <View style={styles.fieldBlock}>
      <Text style={styles.inputLabel}>{label}</Text>
      <TextInput style={styles.textInput} placeholderTextColor="#94a3b8" {...inputProps} />
    </View>
  );
}

function TopBar({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <View style={styles.topBar}>
      <Text style={styles.screenTitle}>{title}</Text>
      <Text style={styles.screenSubtitle}>{subtitle}</Text>
    </View>
  );
}

function BackHeader({ title, onBack }: { title: string; onBack: () => void }) {
  return (
    <View style={styles.backHeader}>
      <Pressable style={styles.backButton} onPress={onBack}><Ionicons name="arrow-back" size={20} color="#0f172a" /></Pressable>
      <Text style={styles.screenTitle}>{title}</Text>
    </View>
  );
}

function SectionHeader({ title, action, onPress }: { title: string; action?: string; onPress?: () => void }) {
  return (
    <View style={styles.sectionHeader}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {action ? <Pressable onPress={onPress}><Text style={styles.sectionAction}>{action}</Text></Pressable> : null}
    </View>
  );
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.statPill}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

function PriorityCard({ item }: { item: PriorityWork }) {
  return (
    <View style={styles.priorityCard}>
      <View style={styles.flex}>
        <Text style={styles.priorityTitle}>{item.title}</Text>
        <Text style={styles.priorityMeta}>{item.department} · {pretty(item.resource)}</Text>
      </View>
      <Text style={styles.priorityStatus}>{item.status}</Text>
    </View>
  );
}

function TimeTile({ label, value, tone }: { label: string; value: string; tone: "green" | "blue" | "red" }) {
  const color = tone === "green" ? "#bbf7d0" : tone === "blue" ? "#bae6fd" : "#fecaca";
  return (
    <View style={styles.timeTile}>
      <Text style={styles.timeLabel}>{label}</Text>
      <Text style={[styles.timeValue, { color }]}>{value}</Text>
    </View>
  );
}

function CountTile({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <View style={styles.countTile}>
      <Text style={[styles.countValue, { color }]}>{value}</Text>
      <Text style={styles.countLabel}>{label}</Text>
    </View>
  );
}

function CalendarGrid({ days }: { days: AttendanceCalendar["days"] }) {
  const colors: Record<string, string> = {
    present: "#16a34a",
    absent: "#dc2626",
    leave: "#9333ea",
    holiday: "#0284c7",
    weekly_off: "#64748b",
  };
  return (
    <View style={styles.calendarGrid}>
      {days.map((day) => (
        <View key={day.date} style={[styles.calendarDay, { backgroundColor: colors[day.status] || "#94a3b8" }]}>
          <Text style={styles.calendarDayText}>{day.day}</Text>
        </View>
      ))}
    </View>
  );
}

function RecordPreview({ module, item }: { module: Module; item: RecordItem }) {
  const firstFields = module.fields.filter((field) => field !== "status").slice(0, 3);
  return (
    <View style={styles.recordPreview}>
      {firstFields.map((field) => (
        <Text key={field} style={styles.recordLine}><Text style={styles.recordLabel}>{pretty(field)}:</Text> {item.data[field] || "-"}</Text>
      ))}
    </View>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return <Text style={styles.errorBanner}>{message}</Text>;
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <View style={styles.emptyState}>
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.emptyBody}>{body}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  shell: { flex: 1, backgroundColor: "#f1f5f9" },
  flex: { flex: 1 },
  loading: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#0f172a" },
  loadingText: { marginTop: 12, color: "#cbd5e1", fontWeight: "600" },
  loginShell: { flex: 1, backgroundColor: "#f8fafc" },
  loginHero: { paddingHorizontal: 24, paddingTop: 46, paddingBottom: 34 },
  brand: { color: "#99f6e4", fontSize: 14, fontWeight: "800", letterSpacing: 0 },
  loginTitle: { marginTop: 12, color: "white", fontSize: 30, fontWeight: "800", lineHeight: 36 },
  loginSubtitle: { marginTop: 12, color: "#ccfbf1", fontSize: 15, lineHeight: 22 },
  loginPanel: { flex: 1, marginTop: -14, borderTopLeftRadius: 24, borderTopRightRadius: 24, backgroundColor: "#f8fafc", padding: 20 },
  panelTitle: { marginBottom: 14, color: "#0f172a", fontSize: 22, fontWeight: "800" },
  scroll: { flex: 1, backgroundColor: "#f1f5f9" },
  scrollContent: { padding: 16 },
  heroCard: { borderRadius: 22, padding: 18 },
  attendanceCard: { borderRadius: 22, padding: 18 },
  attendanceLabel: { color: "#ccfbf1", fontSize: 12, fontWeight: "800", textTransform: "uppercase" },
  attendanceTitle: { marginTop: 4, color: "white", fontSize: 24, fontWeight: "900" },
  attendanceTimes: { flexDirection: "row", gap: 8, marginTop: 16 },
  policyText: { color: "#d1fae5", fontSize: 12, fontWeight: "700", marginTop: 12 },
  timeTile: { flex: 1, borderRadius: 14, backgroundColor: "rgba(255,255,255,0.12)", padding: 10 },
  timeLabel: { color: "#cbd5e1", fontSize: 11, fontWeight: "700" },
  timeValue: { marginTop: 5, fontSize: 16, fontWeight: "900" },
  actionRow: { flexDirection: "row", gap: 10, marginTop: 14 },
  lightButton: { flex: 1, minHeight: 46, borderRadius: 14, alignItems: "center", justifyContent: "center", backgroundColor: "rgba(255,255,255,0.92)" },
  lightButtonText: { color: "#0f172a", fontSize: 13, fontWeight: "900" },
  trackButton: { marginTop: 12, minHeight: 42, borderRadius: 14, borderWidth: 1, borderColor: "rgba(255,255,255,0.2)", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8 },
  trackButtonText: { color: "white", fontSize: 12, fontWeight: "800" },
  calendarStats: { flexDirection: "row", gap: 8, marginBottom: 10 },
  countTile: { flex: 1, borderRadius: 14, backgroundColor: "white", padding: 10, borderWidth: 1, borderColor: "#e2e8f0" },
  countValue: { fontSize: 19, fontWeight: "900" },
  countLabel: { color: "#64748b", fontSize: 11, fontWeight: "700" },
  calendarGrid: { flexDirection: "row", flexWrap: "wrap", gap: 6, borderRadius: 18, backgroundColor: "white", padding: 12, borderWidth: 1, borderColor: "#e2e8f0" },
  calendarDay: { width: 34, height: 34, borderRadius: 10, alignItems: "center", justifyContent: "center" },
  calendarDayText: { color: "white", fontSize: 12, fontWeight: "900" },
  historyRow: { flexDirection: "row", alignItems: "center", gap: 12, borderRadius: 16, backgroundColor: "white", padding: 14, borderWidth: 1, borderColor: "#e2e8f0", marginBottom: 8 },
  historyTitle: { color: "#0f172a", fontSize: 14, fontWeight: "900" },
  historyMeta: { marginTop: 3, color: "#64748b", fontSize: 12 },
  historyStatus: { overflow: "hidden", borderRadius: 10, backgroundColor: "#e0f2fe", paddingHorizontal: 8, paddingVertical: 5, color: "#0369a1", fontSize: 12, fontWeight: "900" },
  notificationCard: { flexDirection: "row", alignItems: "center", gap: 12, borderRadius: 16, backgroundColor: "white", padding: 14, borderWidth: 1, borderColor: "#e2e8f0", marginBottom: 8 },
  notificationUnread: { borderColor: "#0f766e", backgroundColor: "#f0fdfa" },
  notificationTitle: { color: "#0f172a", fontSize: 14, fontWeight: "900" },
  notificationBody: { marginTop: 3, color: "#64748b", fontSize: 12, lineHeight: 17 },
  notificationStatus: { overflow: "hidden", borderRadius: 10, backgroundColor: "#ccfbf1", paddingHorizontal: 8, paddingVertical: 5, color: "#0f766e", fontSize: 12, fontWeight: "900" },
  salaryAmount: { marginTop: 8, color: "#0f766e", fontSize: 30, fontWeight: "900" },
  salaryLine: { marginTop: 10, flexDirection: "row", justifyContent: "space-between", gap: 12, borderTopWidth: 1, borderTopColor: "#f1f5f9", paddingTop: 10 },
  salaryLineName: { color: "#334155", fontSize: 13, fontWeight: "800" },
  salaryLineAmount: { color: "#0f172a", fontSize: 13, fontWeight: "900" },
  salaryTotals: { flexDirection: "row", gap: 8, marginTop: 12 },
  heroEyebrow: { color: "#99f6e4", fontSize: 12, fontWeight: "800", textTransform: "uppercase" },
  heroTitle: { marginTop: 8, color: "white", fontSize: 26, fontWeight: "800", lineHeight: 31 },
  heroCopy: { marginTop: 8, color: "#cbd5e1", fontSize: 14, lineHeight: 20 },
  statsRow: { flexDirection: "row", gap: 8, marginTop: 16 },
  statPill: { flex: 1, borderRadius: 14, backgroundColor: "rgba(255,255,255,0.1)", padding: 12 },
  statValue: { color: "white", fontSize: 20, fontWeight: "800" },
  statLabel: { marginTop: 2, color: "#cbd5e1", fontSize: 11 },
  sectionHeader: { marginTop: 22, marginBottom: 10, flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  sectionTitle: { color: "#0f172a", fontSize: 18, fontWeight: "800" },
  sectionAction: { color: "#0f766e", fontSize: 13, fontWeight: "800" },
  quickGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  quickCard: { width: "48%", minHeight: 112, borderRadius: 18, backgroundColor: "white", padding: 14, borderWidth: 1, borderColor: "#e2e8f0" },
  quickTitle: { marginTop: 10, color: "#0f172a", fontSize: 15, fontWeight: "800" },
  quickMeta: { marginTop: 4, color: "#64748b", fontSize: 12 },
  priorityCard: { flexDirection: "row", alignItems: "center", gap: 12, borderRadius: 16, backgroundColor: "white", padding: 14, borderWidth: 1, borderColor: "#e2e8f0", marginBottom: 8 },
  priorityTitle: { color: "#0f172a", fontSize: 14, fontWeight: "800" },
  priorityMeta: { marginTop: 3, color: "#64748b", fontSize: 12 },
  priorityStatus: { overflow: "hidden", borderRadius: 10, backgroundColor: "#fef3c7", paddingHorizontal: 8, paddingVertical: 5, color: "#92400e", fontSize: 12, fontWeight: "800" },
  departmentRow: { flexDirection: "row", alignItems: "center", gap: 12, borderRadius: 16, backgroundColor: "white", padding: 14, borderWidth: 1, borderColor: "#e2e8f0", marginBottom: 8 },
  departmentIcon: { width: 42, height: 42, borderRadius: 12, alignItems: "center", justifyContent: "center", backgroundColor: "#ccfbf1" },
  departmentInitial: { color: "#0f766e", fontSize: 18, fontWeight: "900" },
  departmentName: { color: "#0f172a", fontSize: 15, fontWeight: "800" },
  departmentMeta: { marginTop: 2, color: "#64748b", fontSize: 12 },
  topBar: { marginBottom: 16 },
  screenTitle: { color: "#0f172a", fontSize: 24, fontWeight: "900" },
  screenSubtitle: { marginTop: 4, color: "#64748b", fontSize: 14 },
  searchInput: { height: 46, borderRadius: 14, backgroundColor: "white", borderWidth: 1, borderColor: "#e2e8f0", paddingHorizontal: 14, color: "#0f172a", marginBottom: 12 },
  largeCard: { borderRadius: 18, backgroundColor: "white", padding: 16, borderWidth: 1, borderColor: "#e2e8f0", marginBottom: 10 },
  cardTitle: { color: "#0f172a", fontSize: 16, fontWeight: "900" },
  cardMeta: { marginTop: 4, color: "#64748b", fontSize: 13 },
  backHeader: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 14 },
  backButton: { width: 40, height: 40, borderRadius: 12, alignItems: "center", justifyContent: "center", backgroundColor: "white", borderWidth: 1, borderColor: "#e2e8f0" },
  moduleCard: { borderRadius: 18, backgroundColor: "white", padding: 14, borderWidth: 1, borderColor: "#e2e8f0", marginBottom: 10 },
  moduleHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 },
  smallButton: { borderRadius: 12, backgroundColor: "#0f766e", paddingHorizontal: 14, paddingVertical: 9 },
  smallButtonText: { color: "white", fontSize: 13, fontWeight: "800" },
  mutedText: { marginTop: 12, color: "#64748b", fontSize: 13 },
  recordPreview: { marginTop: 10, borderTopWidth: 1, borderTopColor: "#f1f5f9", paddingTop: 10 },
  recordLine: { color: "#334155", fontSize: 13, lineHeight: 19 },
  recordLabel: { fontWeight: "800", color: "#0f172a" },
  formHint: { marginBottom: 12, color: "#64748b", fontSize: 13, lineHeight: 19 },
  fieldBlock: { marginBottom: 14 },
  inputLabel: { marginBottom: 7, color: "#0f172a", fontSize: 13, fontWeight: "800" },
  textInput: { minHeight: 48, borderRadius: 14, borderWidth: 1, borderColor: "#cbd5e1", backgroundColor: "white", paddingHorizontal: 14, color: "#0f172a" },
  statusRow: { gap: 8, paddingVertical: 2 },
  statusChip: { borderRadius: 12, borderWidth: 1, borderColor: "#cbd5e1", backgroundColor: "white", paddingHorizontal: 12, paddingVertical: 9 },
  statusChipActive: { borderColor: "#0f766e", backgroundColor: "#ccfbf1" },
  statusChipText: { color: "#475569", fontWeight: "700" },
  statusChipTextActive: { color: "#0f766e" },
  primaryButton: { minHeight: 50, borderRadius: 15, alignItems: "center", justifyContent: "center", backgroundColor: "#0f766e", marginTop: 8 },
  primaryButtonText: { color: "white", fontSize: 15, fontWeight: "900" },
  secondaryButton: { minHeight: 48, borderRadius: 15, alignItems: "center", justifyContent: "center", backgroundColor: "#0f172a", marginTop: 12 },
  secondaryButtonText: { color: "white", fontSize: 15, fontWeight: "900" },
  dangerButton: { minHeight: 48, borderRadius: 15, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: "#fecaca", backgroundColor: "#fff1f2", marginTop: 12 },
  dangerButtonText: { color: "#be123c", fontSize: 15, fontWeight: "900" },
  disabledButton: { opacity: 0.6 },
  errorText: { marginBottom: 10, color: "#be123c", fontSize: 13, fontWeight: "700" },
  errorBanner: { overflow: "hidden", borderRadius: 14, backgroundColor: "#fee2e2", color: "#991b1b", padding: 12, marginBottom: 12, fontSize: 13, fontWeight: "700" },
  emptyState: { borderRadius: 16, borderWidth: 1, borderColor: "#e2e8f0", backgroundColor: "white", padding: 16 },
  emptyTitle: { color: "#0f172a", fontSize: 15, fontWeight: "900" },
  emptyBody: { marginTop: 4, color: "#64748b", fontSize: 13, lineHeight: 18 },
  profileCard: { alignItems: "center", borderRadius: 22, backgroundColor: "white", borderWidth: 1, borderColor: "#e2e8f0", padding: 22 },
  avatar: { width: 72, height: 72, borderRadius: 22, alignItems: "center", justifyContent: "center", backgroundColor: "#0f766e" },
  avatarText: { color: "white", fontSize: 30, fontWeight: "900" },
  profileName: { marginTop: 12, color: "#0f172a", fontSize: 20, fontWeight: "900" },
  profileMeta: { marginTop: 4, color: "#64748b", fontSize: 13 },
  roleBadge: { overflow: "hidden", marginTop: 12, borderRadius: 12, backgroundColor: "#ccfbf1", color: "#0f766e", paddingHorizontal: 10, paddingVertical: 6, fontSize: 12, fontWeight: "900" },
  checkRow: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 10 },
  checkText: { color: "#334155", fontSize: 14 },
  bottomNav: { position: "absolute", left: 12, right: 12, bottom: 12, flexDirection: "row", borderRadius: 24, backgroundColor: "white", borderWidth: 1, borderColor: "#e2e8f0", padding: 8, shadowColor: "#0f172a", shadowOpacity: 0.12, shadowRadius: 18, shadowOffset: { width: 0, height: 8 }, elevation: 6 },
  navItem: { flex: 1, alignItems: "center", justifyContent: "center", paddingVertical: 6 },
  navLabel: { marginTop: 2, color: "#64748b", fontSize: 11, fontWeight: "800" },
  navLabelActive: { color: "#0f766e" }
});
