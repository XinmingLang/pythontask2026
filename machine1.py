import copy
import json
import math
import socket
import threading
import time
from typing import Any, Dict, Optional

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import numpy as np
import matplotlib.figure as mpl_figure


# ========================= 系统配置 =========================
class SystemConfig:
    def __init__(self,**params):
        self.target_num = params.get("activated_target_num", 3)

        self.station_distance = params.get("point_0",{"station_spacing":2000.0}).get("station_spacing",2000.0)
        self.station_angle_diff = 0.0

        self.array_elem_num = params.get("point_0",{"array_num":8}).get("array_num",8)
        self.array_spacing = params.get("element_spacing",6)

        self.angle_range = (-60.0, 60.0)
        self.data_update_interval = 0.5

        self.radiation_params = {
            0: params.get("target_0",{
                "fc_if":25000.0,
                "fc_rf":1.5e9,
                "sample_rate":200000.0,
                "mod_type":"AM",
                "mod_freq":5000.0,
                "amplitude":1.0,
                "snr":20.0,
                "signal_duration":0.02
            }),
            1: params.get("target_1",{
                "fc_if": 32000.0,
                "fc_rf": 1.2e9,
                "sample_rate": 200000.0,
                "mod_type": "FM",
                "mod_freq": 3000.0,
                "amplitude": 1.1,
                "snr": 18.0,
                "signal_duration": 0.02
            }),
            2: params.get("target_2",{
                "fc_if": 18000.0,
                "fc_rf": 0.9e9,
                "sample_rate": 200000.0,
                "mod_type": "CW",
                "mod_freq": 1000.0,
                "amplitude": 0.95,
                "snr": 16.0,
                "signal_duration": 0.02
            })
        }

        self.motion_params = {
            0: params.get("target_0",{
                "motion_mode": "line",
                "start_pos": (30000.0, 30000.0),
                "velocity": 2500.0,
                "direction": 35.0,
                "total_time": 10.0
            }),
            1: params.get("target_1",{
                "motion_mode": "arc",
                "arc_center": (20000.0, 40000.0),
                "arc_radius": 12000.0,
                "arc_omega": 0.5,
                "arc_phase0": -math.pi / 2,
                "total_time": 10.0
            }),
            2: params.get("target_2",{
                "motion_mode": "line",
                "start_pos": (10000.0, 50000.0),
                "velocity": 1800.0,
                "direction": -20.0,
                "total_time": 10.0
            })
        }
        print("[SystemConfig] 系统配置已初始化:\n", json.dumps(self.to_dict(), indent=2))
    def update(self,**params):
        self.target_num = params.get("activated_target_num", 3)

        self.station_distance = params.get("point_0",{"station_spacing":2000.0}).get("station_spacing",2000.0)
        self.station_angle_diff = 0.0

        self.array_elem_num = params.get("point_0",{"array_num":8}).get("array_num",8)
        self.array_spacing = params.get("element_spacing",6)

        self.angle_range = (-60.0, 60.0)
        self.data_update_interval = 0.5

        self.radiation_params = {
            0: params.get("target_0",{
                "fc_if":25000.0,
                "fc_rf":1.5e9,
                "sample_rate":200000.0,
                "mod_type":"AM",
                "mod_freq":5000.0,
                "amplitude":1.0,
                "snr":20.0,
                "signal_duration":0.02
            }),
            1: params.get("target_1",{
                "fc_if": 32000.0,
                "fc_rf": 1.2e9,
                "sample_rate": 200000.0,
                "mod_type": "FM",
                "mod_freq": 3000.0,
                "amplitude": 1.1,
                "snr": 18.0,
                "signal_duration": 0.02
            }),
            2: params.get("target_2",{
                "fc_if": 18000.0,
                "fc_rf": 0.9e9,
                "sample_rate": 200000.0,
                "mod_type": "CW",
                "mod_freq": 1000.0,
                "amplitude": 0.95,
                "snr": 16.0,
                "signal_duration": 0.02
            })
        }

        self.motion_params = {
            0: params.get("target_0",{
                "motion_mode": "line",
                "start_pos": (30000.0, 30000.0),
                "velocity": 2500.0,
                "direction": 35.0,
                "total_time": 10.0
            }),
            1: params.get("target_1",{
                "motion_mode": "arc",
                "arc_center": (20000.0, 40000.0),
                "arc_radius": 12000.0,
                "arc_omega": 0.5,
                "arc_phase0": -math.pi / 2,
                "total_time": 10.0
            }),
            2: params.get("target_2",{
                "motion_mode": "line",
                "start_pos": (10000.0, 50000.0),
                "velocity": 1800.0,
                "direction": -20.0,
                "total_time": 10.0
            })
        }
        print("[SystemConfig] 系统配置已更新:\n", json.dumps(self.to_dict(), indent=2))
    def print_config(self):
        print("========== 系统配置 ==========")
        print(f"目标数: {self.target_num}")
        print(f"站间距: {self.station_distance} m")
        print(f"站2朝向差: {self.station_angle_diff} deg")
        print(f"阵元数: {self.array_elem_num}")
        print(f"阵元间距: {self.array_spacing}")
        print(f"测角范围: {self.angle_range}")
        print(f"数据更新时间: {self.data_update_interval} s")
        print("辐射源参数:")
        for tid, p in self.radiation_params.items():
            print(f"  目标{tid}: {p}")
        print("运动参数:")
        for tid, p in self.motion_params.items():
            print(f"  目标{tid}: {p}")
        print("================================\n")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_num": self.target_num,
            "station_distance": self.station_distance,
            "station_angle_diff": self.station_angle_diff,
            "array_elem_num": self.array_elem_num,
            "array_spacing": self.array_spacing,
            "angle_range": list(self.angle_range),
            "data_update_interval": self.data_update_interval,
            "radiation_params": self.radiation_params,
            "motion_params": self.motion_params
        }


# ========================= 目标轨迹生成 =========================
class TargetSimulator:
    def __init__(self, config: SystemConfig):
        self.config = config

    def generate_single_target_track(self, target_id):
        p = self.config.motion_params[target_id]
        dt = self.config.data_update_interval
        total_time = p["total_time"]

        track = []
        t = 0.0

        while t <= total_time + 1e-9:
            if p["motion_mode"] == "line":
                x0, y0 = p["start_pos"]
                v = p["velocity"]
                theta = math.radians(p["direction"])
                x = x0 + v * math.cos(theta) * t
                y = y0 + v * math.sin(theta) * t

            elif p["motion_mode"] == "arc":
                cx, cy = p["arc_center"]
                r = p["arc_radius"]
                w = p["arc_omega"]
                phi0 = p["arc_phase0"]
                phi = phi0 + w * t
                x = cx + r * math.cos(phi)
                y = cy + r * math.sin(phi)
            else:
                raise ValueError(f"未知运动模式: {p['motion_mode']}")

            track.append(((x, y), round(t, 3), target_id))
            t += dt

        return track

    def generate_all_targets_track(self):
        all_track = []
        single_tracks = {}

        for target_id in range(self.config.target_num):
            track = self.generate_single_target_track(target_id)
            single_tracks[target_id] = track
            all_track.extend(track)

        all_track.sort(key=lambda x: x[1])
        return all_track, single_tracks

    def export_tracks_dict(self) -> Dict[str, Any]:
        _, single_tracks = self.generate_all_targets_track()
        result: Dict[str, Any] = {}

        for target_id, track in single_tracks.items():
            result[str(target_id)] = []
            for item in track:
                pos, ts, tid = item
                x, y = pos
                result[str(target_id)].append({
                    "x": x,
                    "y": y,
                    "timestamp": ts,
                    "target_id": tid
                })

        return result


# ========================= 接收端 =========================
class Receiver:
    def __init__(self, host=socket.gethostbyname(socket.gethostname()), port=9999):
        self.host = host
        self.port = port
        self.server: Optional[socket.socket] = None
        self.running = False
        self.lock = threading.Lock()

        self.data: Dict[int, Dict[int, list]] = {}

        self.machine2_socket: Optional[socket.socket] = None
        self.machine2_connected_event = threading.Event()

    def listen(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        self.running = True
        print(f"[Machine1-Receiver] 正在监听 {self.host}:{self.port}")

        while self.running:
            try:
                client, addr = self.server.accept()
                print(f"[Machine1-Receiver] 收到连接: {addr}")
                self.machine2_socket = client
                self.machine2_connected_event.set()
                threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"[Machine1-Receiver] 监听异常: {e}")
                break
        self.server.close()

    def handle_client(self, client: socket.socket):
        buffer = ""
        while self.running:
            try:
                data = client.recv(4096)
                if not data:
                    break

                buffer += data.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    if line == "READY":
                        print("[Machine1-Receiver] 机器2已就绪")
                        continue

                    try:
                        msg = json.loads(line)
                        self.store_message(msg)
                    except Exception:
                        print(f"[Machine1-Receiver] 收到非JSON消息: {line}")

            except Exception as e:
                print(f"[Machine1-Receiver] 客户端处理异常: {e}")
                break

        try:
            client.close()
        except Exception:
            pass

    def wait_for_machine2(self, timeout=None):
        return self.machine2_connected_event.wait(timeout=timeout)

    def send_json_to_machine2(self, obj: Dict[str, Any]) -> None:
        if self.machine2_socket is None:
            raise RuntimeError("机器2尚未连接，无法发送数据")
        msg = json.dumps(obj) + "\n"
        self.machine2_socket.sendall(msg.encode("utf-8"))

    def send_start_command(self):
        start_msg = {"type": "START"}
        self.send_json_to_machine2(start_msg)
        print("[Machine1] 已通知机器2开始发送数据")

    def store_message(self, msg):
        station_id = int(msg["station_id"])
        target_id = int(msg["target_id"])
        timestamp = float(msg["timestamp"])
        angle = float(msg["angle"])
        snr = float(msg.get("snr", 0.0))

        with self.lock:
            if target_id not in self.data:
                self.data[target_id] = {}
            if station_id not in self.data[target_id]:
                self.data[target_id][station_id] = []

            self.data[target_id][station_id].append({
                "timestamp": timestamp,
                "angle": angle,
                "snr": snr
            })

    def get_data(self):
        with self.lock:
            return copy.deepcopy(self.data)

    def stop(self):
        self.running = False
        try:
            if self.machine2_socket is not None:
                self.machine2_socket.close()
        except Exception:
            pass

        try:
            if self.server is not None:
                self.server.close()
        except Exception:
            pass


# ========================= 双站定位 =========================
class Locator:
    def __init__(self, config: SystemConfig):
        self.config = config

    @staticmethod
    def _intersect_two_lines(p1, theta1_deg, p2, theta2_deg):
        t1 = math.radians(theta1_deg)
        t2 = math.radians(theta2_deg)

        x1, y1 = p1
        x2, y2 = p2

        d1x, d1y = math.sin(t1), math.cos(t1)
        d2x, d2y = math.sin(t2), math.cos(t2)

        A = np.array([[d1x, -d2x], [d1y, -d2y]], dtype=float)
        b = np.array([x2 - x1, y2 - y1], dtype=float)

        det = np.linalg.det(A)
        if abs(det) < 1e-8:
            return None

        sol = np.linalg.solve(A, b)
        a = sol[0]

        x = x1 + a * d1x
        y = y1 + a * d1y
        return x, y

    def multi_target_locate(self, receiver: Receiver):
        raw = receiver.get_data()
        print(f"[Locator] 获取原始数据: {json.dumps(raw, indent=2)}")
        result = {}

        station1_pos = (0.0, 0.0)
        station2_pos = (self.config.station_distance, 0.0)

        for target_id, station_dict in raw.items():
            if 1 not in station_dict or 2 not in station_dict:
                continue

            s1_list = station_dict[1]
            s2_list = station_dict[2]

            s1_map = {round(item["timestamp"], 3): item for item in s1_list}
            s2_map = {round(item["timestamp"], 3): item for item in s2_list}

            common_ts = sorted(set(s1_map.keys()) & set(s2_map.keys()))
            target_result = []

            for ts in common_ts:
                a1 = s1_map[ts]["angle"]
                a2 = s2_map[ts]["angle"]
                a2_global = a2 - self.config.station_angle_diff

                est = self._intersect_two_lines(station1_pos, a1, station2_pos, a2_global)
                if est is None:
                    continue

                x, y = est
                target_result.append((ts, x, y, a1, a2))

            result[target_id] = target_result

        return result


# ========================= 误差分析 =========================
class ErrorAnalyzer:
    def __init__(self, config: SystemConfig, target_simulator: TargetSimulator):
        self.config = config
        self.target_simulator = target_simulator
        self.all_true_track, self.single_true_tracks = self.target_simulator.generate_all_targets_track()

    def multi_target_error_analysis(self, locate_result):
        error_result = {}
        error_stats = {}

        for target_id, est_list in locate_result.items():
            true_track = self.single_true_tracks[target_id]
            true_map = {round(item[1], 3): item[0] for item in true_track}

            one_target_errors = []
            err_values = []

            for item in est_list:
                ts, est_x, est_y, a1, a2 = item
                if round(ts, 3) not in true_map:
                    continue

                true_x, true_y = true_map[round(ts, 3)]
                err = math.hypot(est_x - true_x, est_y - true_y)

                one_target_errors.append((ts, true_x, true_y, est_x, est_y, err, a1, a2))
                err_values.append(err)

            error_result[target_id] = one_target_errors

            if len(err_values) > 0:
                arr = np.array(err_values)
                error_stats[target_id] = {
                    "count": len(arr),
                    "mean": float(np.mean(arr)),
                    "rmse": float(np.sqrt(np.mean(arr ** 2))),
                    "max": float(np.max(arr)),
                    "min": float(np.min(arr))
                }
            else:
                error_stats[target_id] = {
                    "count": 0, "mean": None, "rmse": None, "max": None, "min": None
                }

        return error_result, error_stats

    def print_error_stats(self, error_stats):
        print("\n========== 误差统计 ==========")
        for target_id, s in error_stats.items():
            print(f"目标 {target_id}:")
            print(f"  点数  : {s['count']}")
            print(f"  均值  : {s['mean']:.3f} m" if s["mean"] is not None else "  均值  : None")
            print(f"  RMSE  : {s['rmse']:.3f} m" if s["rmse"] is not None else "  RMSE  : None")
            print(f"  最大值: {s['max']:.3f} m" if s["max"] is not None else "  最大值: None")
            print(f"  最小值: {s['min']:.3f} m" if s["min"] is not None else "  最小值: None")
        print("==============================\n")


# ========================= 可视化 =========================
class ResultVisualizer(FigureCanvasQTAgg):
    def __init__(self, config: SystemConfig, error_analyzer: ErrorAnalyzer):
        self.config = config
        self.error_analyzer = error_analyzer

        plt.rcParams['figure.figsize'] = (18, 7)
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['font.size'] = 11
        plt.rcParams['font.family'] = 'SimHei'

        self.station_colors = {1: "#6C49F7", 2: "#C60707"}
        self.target_colors = {0: "#2121BA", 1: "#AF1807", 2: "#006400"}
        self.stat_colors = ["#FF6B6B", "#4ECDC4", "#45B7D1"]
        
        fig = mpl_figure.Figure()
        super().__init__(fig)
        self.figure.patch.set_facecolor('white')
        

    def draw_all_figures(self, error_result, save_path=None):
        #fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
        self.figure.clear()
        ax1 = self.figure.add_subplot(121)
        ax2 = self.figure.add_subplot(122)

        ax1.scatter(0, 0, c="#6C49F7", marker='^', s=250, label='Station 1',
                    edgecolors='white', linewidths=1.5, zorder=10)
        ax1.scatter(self.config.station_distance / 1e3, 0, c="#C60707", marker='^', s=250, label='Station 2',
                    edgecolors='white', linewidths=1.5, zorder=10)

        color_pairs = [
            ("#2121BA", '#00D9FF'),
            ("#AF1807", '#FFD700'),
            ('#006400', '#FF4DFF')
        ]

        all_x = [0, self.config.station_distance / 1e3]
        all_y = [0]

        for idx, target_id in enumerate(range(self.config.target_num)):
            true_color, est_color = color_pairs[idx % len(color_pairs)]

            true_track = self.error_analyzer.single_true_tracks.get(target_id, [])
            if len(true_track) > 0:
                true_x = [item[0][0] / 1e3 for item in true_track]
                true_y = [item[0][1] / 1e3 for item in true_track]

                all_x.extend(true_x)
                all_y.extend(true_y)

                ax1.plot(true_x, true_y, linestyle='-', color=true_color, linewidth=2.1,
                         alpha=1.0, label=f'Target {target_id} True', zorder=2)
                ax1.scatter(true_x[0], true_y[0], c=true_color, s=80, marker='o', zorder=8)
                ax1.scatter(true_x[-1], true_y[-1], c=true_color, s=80, marker='s', zorder=8)

            if target_id in error_result and len(error_result[target_id]) > 0:
                est_x = [item[3] / 1e3 for item in error_result[target_id]]
                est_y = [item[4] / 1e3 for item in error_result[target_id]]

                all_x.extend(est_x)
                all_y.extend(est_y)

                ax1.plot(est_x, est_y, linestyle='--', color=est_color, linewidth=1.2,
                         alpha=0.85, label=f'Target {target_id} Est', zorder=4)
                ax1.scatter(est_x, est_y, s=35, marker='o', edgecolors='black',
                            linewidths=0.8, facecolors='none', color=est_color, zorder=5)

        ax1.set_xlabel("X (km)")
        ax1.set_ylabel("Y (km)")
        ax1.set_title("Multi-Target True Track vs Estimated Track")
        ax1.grid(True, linestyle='--', alpha=0.35)
        ax1.legend(fontsize=9, loc='upper left', frameon=True)
        ax1.set_aspect('equal', adjustable='box')

        error_colors = {0: "#D91C1C", 1: "#3A3AC5", 2: "#1EDB1E"}

        for target_id, err_data in sorted(error_result.items()):
            if len(err_data) == 0:
                continue
            ts = [item[0] for item in err_data]
            err = [item[5] for item in err_data]

            color = error_colors.get(target_id, '#333333')
            ax2.plot(ts, err, linewidth=2.8, color=color, label=f"Target {target_id}", zorder=2)
            ax2.scatter(ts, err, c=color, s=20, edgecolors='white', linewidths=0.45, zorder=3)

        ax2.set_xlabel("Time (s)")
        ax2.set_ylabel("Position Error (m)")
        ax2.set_title("Positioning Error Over Time")
        ax2.grid(True, linestyle='--', alpha=0.35)
        ax2.legend(fontsize=10, loc='best', frameon=True)

        #plt.tight_layout()
        self.figure.tight_layout()

        if save_path is not None:
            self.figure.savefig(save_path, dpi=300, bbox_inches='tight')

        #plt.show(block=False)
        self.draw()

    def draw_error_stat_bar(self, error_stats, save_path=None):
        self.figure.clear()
        target_ids = sorted([t for t in error_stats.keys() if error_stats[t]["count"] > 0])

        means = [error_stats[t]["mean"] for t in target_ids]
        rmses = [error_stats[t]["rmse"] for t in target_ids]
        maxs = [error_stats[t]["max"] for t in target_ids]

        x = np.arange(len(target_ids))
        width = 0.25

        #plt.plot(figsize=(10, 6))
        ax = self.figure.add_subplot(111)
        ax.bar(x - width, means, width, label="平均误差", color=self.stat_colors[0], edgecolor='black', linewidth=0.5)
        ax.bar(x, rmses, width, label="RMSE", color=self.stat_colors[1], edgecolor='black', linewidth=0.5)
        ax.bar(x + width, maxs, width, label="最大误差", color=self.stat_colors[2], edgecolor='black', linewidth=0.5)

        if len(means) > 0 and max(means) > 0:
            for i, v in enumerate(means):
                if v is not None and v > 0:
                    plt.text(i - width, v + max(means) * 0.01, f"{v:.1f}", ha='center', fontsize=9)

        if len(rmses) > 0 and max(rmses) > 0:
            for i, v in enumerate(rmses):
                if v is not None and v > 0:
                    plt.text(i, v + max(rmses) * 0.01, f"{v:.1f}", ha='center', fontsize=9)

        if len(maxs) > 0 and max(maxs) > 0:
            for i, v in enumerate(maxs):
                if v is not None and v > 0:
                    plt.text(i + width, v + max(maxs) * 0.01, f"{v:.1f}", ha='center', fontsize=9)

        ax.set_xlabel("目标编号", fontsize=12)
        ax.set_ylabel("误差 (m)", fontsize=12)
        ax.set_title("多目标定位误差统计对比", fontsize=14, fontweight='bold')
        ax.set_xticks(x, [f"目标 {t}" for t in target_ids])
        ax.legend(fontsize=11)
        ax.grid(axis='y', alpha=0.3)
        self.figure.tight_layout()

        if save_path:
            self.figure.savefig(save_path, dpi=300, bbox_inches='tight')
        #plt.show(block=False)
        self.draw()

    def draw_beam_time_waveform(self, save_path=None):
        self.figure.clear() 
        axes = self.figure.subplots(3, 2)
        self.figure.suptitle("波束输出时域波形图（目标×测向站）", fontsize=14, fontweight='bold')
        axes = axes.ravel()

        for tid in range(self.config.target_num):
            p = self.config.radiation_params[tid]
            t = np.linspace(
                0,
                p["signal_duration"],
                int(p["sample_rate"] * p["signal_duration"]),
                endpoint=False
            )

            if p["mod_type"] == "AM":
                sig = p["amplitude"] * np.cos(2 * np.pi * p["fc_if"] * t) * 0.5 * (
                    1 + np.cos(2 * np.pi * p["mod_freq"] * t)
                )
            elif p["mod_type"] == "FM":
                sig = p["amplitude"] * np.cos(
                    2 * np.pi * p["fc_if"] * t + 2 * np.pi * p["mod_freq"] * t
                )
            else:  # CW
                sig = p["amplitude"] * np.cos(2 * np.pi * p["fc_if"] * t)

            sig += np.random.randn(len(sig)) * (p["amplitude"] / (10 ** (p["snr"] / 10)))

            for sid in [1, 2]:
                idx = tid * 2 + (sid - 1)
                axes[idx].plot(t[:1000], sig[:1000], color=self.station_colors[sid], linewidth=1.2)
                axes[idx].set_title(
                    f"目标{tid} | 站{sid} | {p['mod_type']} | {p['fc_if'] / 1000:.0f}kHz",
                    fontsize=10
                )
                axes[idx].set_xlabel("时间 (s)", fontsize=9)
                axes[idx].set_ylabel("信号幅度", fontsize=9)
                axes[idx].grid(True, alpha=0.3)

        self.figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.96))
        if save_path:
            self.figure.savefig(save_path, dpi=300, bbox_inches='tight')
        #plt.show(block=False)
        self.draw()

    def draw_beam_spectrum(self, nfft=1024, save_path=None):
        self.figure.clear()
        axes = self.figure.subplots(3, 2)
        self.figure.suptitle("波束输出频谱图（FFT）", fontsize=14, fontweight='bold')
        axes = axes.ravel()

        for tid in range(self.config.target_num):
            p = self.config.radiation_params[tid]
            t = np.linspace(
                0,
                p["signal_duration"],
                int(p["sample_rate"] * p["signal_duration"]),
                endpoint=False
            )

            if p["mod_type"] == "AM":
                sig = p["amplitude"] * np.cos(2 * np.pi * p["fc_if"] * t) * 0.5 * (
                    1 + np.cos(2 * np.pi * p["mod_freq"] * t)
                )
            elif p["mod_type"] == "FM":
                sig = p["amplitude"] * np.cos(
                    2 * np.pi * p["fc_if"] * t + 2 * np.pi * p["mod_freq"] * t
                )
            else:  # CW
                sig = p["amplitude"] * np.cos(2 * np.pi * p["fc_if"] * t)

            sig += np.random.randn(len(sig)) * (p["amplitude"] / (10 ** (p["snr"] / 10)))

            sig_cut = sig[:nfft]
            sig_pad = np.pad(sig_cut, (0, max(0, nfft - len(sig_cut))), mode='constant')

            f = np.fft.fftfreq(nfft, 1 / p["sample_rate"])
            Y = 20 * np.log10(np.abs(np.fft.fft(sig_pad)) + 1e-8)

            f_pos = f[:nfft // 2] / 1000
            Y_pos = Y[:nfft // 2]

            for sid in [1, 2]:
                idx = tid * 2 + (sid - 1)
                axes[idx].plot(f_pos, Y_pos, color=self.station_colors[sid], linewidth=1.2)
                axes[idx].axvline(
                    p["fc_if"] / 1000,
                    color='red',
                    linestyle='--',
                    linewidth=1.0,
                    label=f'载频{p["fc_if"] / 1000:.0f}kHz'
                )
                axes[idx].set_title(f"目标{tid} | 站{sid} | {p['mod_type']}", fontsize=10)
                axes[idx].set_xlabel("频率 (kHz)", fontsize=9)
                axes[idx].set_ylabel("幅度 (dB)", fontsize=9)
                axes[idx].grid(True, alpha=0.3)
                axes[idx].legend(fontsize=8)

        self.figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.96))
        if save_path:
            self.figure.savefig(save_path, dpi=300, bbox_inches='tight')
        #plt.show(block=False)
        self.draw()


# ========================= 机器1主控 =========================
class Machine1Master:
    def __init__(self, receiver_port=9999,**params):
        self.config = SystemConfig(**params)
        self.target_simulator = TargetSimulator(self.config)
        self.receiver = Receiver(port=receiver_port)
        self.locator = Locator(self.config)
        self.error_analyzer = ErrorAnalyzer(self.config, self.target_simulator)
        self.visualizer = ResultVisualizer(self.config, self.error_analyzer)

    def generate_demo_data(self):
        """生成演示数据，无需机器2"""
        _, single_tracks = self.target_simulator.generate_all_targets_track()
        error_result = {}
        error_stats = {}

        demo_err = [
            (680.2, 712.5, 920.8, 480.5),
            (430.5, 461.2, 610.3, 290.1),
            (840.9, 872.3, 1080.5, 620.7)
        ]

        for tid in range(self.config.target_num):
            track = single_tracks[tid]
            est_data = [
                (
                    item[1],
                    item[0][0],
                    item[0][1],
                    item[0][0] + np.random.randint(300, 800),
                    item[0][1] + np.random.randint(300, 800),
                    demo_err[tid][0] + np.random.randint(-50, 50),
                    0,
                    0
                )
                for item in track
            ]
            error_result[tid] = est_data
            error_stats[tid] = {
                "count": len(track),
                "mean": demo_err[tid][0],
                "rmse": demo_err[tid][1],
                "max": demo_err[tid][2],
                "min": demo_err[tid][3]
            }
        return error_result, error_stats

    def start(self):
        print("========== 机器1启动 ==========")
        self.config.print_config()

        recv_thread = threading.Thread(target=self.receiver.listen, daemon=True)
        recv_thread.start()

        print("[Machine1] 等待机器2连接...（超时10秒进入演示模式）")
        ok = self.receiver.wait_for_machine2(timeout=10)

        if not ok:
            print("[Machine1] 未检测到机器2，使用仿真数据演示绘图")
            error_result, error_stats = self.generate_demo_data()
        else:
            print("[Machine1] 机器2已连接，准备发送真实数据...")

            config_msg = {
                "type": "CONFIG",
                "data": self.config.to_dict()
            }
            self.receiver.send_json_to_machine2(config_msg)
            print("[Machine1] 已发送 CONFIG")

            tracks_msg = {
                "type": "TRACKS",
                "data": self.target_simulator.export_tracks_dict()
            }
            self.receiver.send_json_to_machine2(tracks_msg)
            print("[Machine1] 已发送 TRACKS")

            time.sleep(0.5)
            self.receiver.send_start_command()

            total_time = max(self.config.motion_params[tid]["total_time"] for tid in self.config.motion_params)
            wait_time = total_time + 3.0
            print(f"[Machine1] 开始接收数据，等待约 {wait_time:.1f}s ...")
            time.sleep(wait_time)

            print("[Machine1] 执行定位...")
            locate_result = self.locator.multi_target_locate(self.receiver)

            print("[Machine1] 误差分析...")
            error_result, error_stats = self.error_analyzer.multi_target_error_analysis(locate_result)

        self.error_analyzer.print_error_stats(error_stats)

        print("[Machine1] 绘制轨迹与误差图...")
        self.visualizer.draw_all_figures(error_result)

        print("[Machine1] 绘制误差统计柱状图...")
        self.visualizer.draw_error_stat_bar(error_stats)

        print("[Machine1] 绘制波束时域波形...")
        self.visualizer.draw_beam_time_waveform()

        print("[Machine1] 绘制波束频谱...")
        self.visualizer.draw_beam_spectrum()

        self.stop()

    def stop(self):
        self.receiver.stop()
        print("========== 机器1停止 ==========")


if __name__ == "__main__":
    master = Machine1Master(receiver_port=9999)
    master.start()
