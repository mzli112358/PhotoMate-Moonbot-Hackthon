import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type Waypoint = {
  id: string;
  name: string;
  description?: string;
  pose?: number[];
};

export type RobotPose = {
  x?: number;
  y?: number;
  yaw_deg?: number;
  qx?: number;
  qy?: number;
  qz?: number;
  qw?: number;
};

export type RobotStatus = {
  mock?: boolean;
  localized?: boolean;
  navigation_status?: string;
  pose?: RobotPose;
  message?: string;
  target_spot_id?: string | null;
};

type LogEntry = {
  id: number;
  text: string;
};

type HackthonContextValue = {
  connected: boolean;
  status: RobotStatus | null;
  waypoints: Waypoint[];
  logs: LogEntry[];
  activeSpotId: string | null;
  goToSpot: (spotId: string) => Promise<void>;
  stopNavigation: () => Promise<void>;
};

const HackthonContext = createContext<HackthonContextValue | null>(null);

export function HackthonBridgeProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<RobotStatus | null>(null);
  const [waypoints, setWaypoints] = useState<Waypoint[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [selectedSpotId, setSelectedSpotId] = useState<string | null>(null);

  const log = useCallback((line: string) => {
    const ts = new Date().toLocaleTimeString();
    setLogs((items) => [{ id: Date.now(), text: `[${ts}] ${line}` }, ...items].slice(0, 24));
  }, []);

  useEffect(() => {
    let alive = true;

    fetch("/api/waypoints")
      .then((res) => {
        if (!res.ok) throw new Error("waypoints failed");
        return res.json();
      })
      .then((items: Waypoint[]) => {
        if (alive) setWaypoints(items);
      })
      .catch((err) => log(`航点加载失败: ${String(err.message || err)}`));

    fetch("/api/robot/status")
      .then((res) => (res.ok ? res.json() : null))
      .then((snap: RobotStatus | null) => {
        if (alive && snap) setStatus(snap);
      })
      .catch(() => undefined);

    return () => {
      alive = false;
    };
  }, [log]);

  useEffect(() => {
    let closedByCleanup = false;
    let retryTimer: number | undefined;
    let ws: WebSocket | null = null;

    const connect = () => {
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${window.location.host}/ws/pose`);

      ws.onopen = () => {
        setConnected(true);
        log("WebSocket 已连接");
      };

      ws.onmessage = (ev) => {
        try {
          setStatus(JSON.parse(ev.data));
        } catch {
          // Ignore malformed frames from development restarts.
        }
      };

      ws.onerror = () => {
        setConnected(false);
      };

      ws.onclose = () => {
        setConnected(false);
        if (!closedByCleanup) {
          log("连接断开，3 秒后重连");
          retryTimer = window.setTimeout(connect, 3000);
        }
      };
    };

    connect();

    return () => {
      closedByCleanup = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      ws?.close();
    };
  }, [log]);

  const goToSpot = useCallback(
    async (spotId: string) => {
      setSelectedSpotId(spotId);
      log(`请求导航 -> ${spotId}`);
      const res = await fetch("/api/navigation/go", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ spot_id: spotId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const message = data.detail || `导航失败 ${res.status}`;
        log(message);
        throw new Error(message);
      }
      log(data.message || "已启动导航");
    },
    [log],
  );

  const stopNavigation = useCallback(async () => {
    const res = await fetch("/api/navigation/stop", { method: "POST" });
    const data = await res.json().catch(() => ({}));
    log(data.message || "已停止导航");
  }, [log]);

  const activeSpotId = status?.target_spot_id || selectedSpotId;

  const value = useMemo(
    () => ({
      connected,
      status,
      waypoints,
      logs,
      activeSpotId,
      goToSpot,
      stopNavigation,
    }),
    [activeSpotId, connected, goToSpot, logs, status, stopNavigation, waypoints],
  );

  return <HackthonContext.Provider value={value}>{children}</HackthonContext.Provider>;
}

export function useHackthonBridge() {
  const value = useContext(HackthonContext);
  if (!value) {
    throw new Error("useHackthonBridge must be used inside HackthonBridgeProvider");
  }
  return value;
}
