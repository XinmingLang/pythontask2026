####主控节点###
#负责系统参数和调制参数的设置
#负责目标运动轨迹的生成
#负责辐射源波形的生成
#接收两个侧向站上传的测角结果==>已经实现从一个侧向站接收。考虑通过多线程同时接收两个侧向站的测角结果
#进行双站交叉定位==>calculator.calculate()函数已经实现根据角度计算目标坐标,应继续编写程序将角度数据从接收到的数据中取出传递给给该数据。目前计划将两个测向节点的数据分别存储在两个列表中，根据时间戳的先后顺序排序并依次取出进行交叉定位,如果某个时刻只有一个测向站的数据则暂不进行定位，后续再进行插值处理。
#显示真实轨迹与定位轨迹
#统计并分析定位误差

import numpy as np
import threading as Threading
import json 
import math
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path
import socket,math,time

# 设置 matplotlib 中文字体，避免绘图中文乱码
plt.rcParams['font.family'] = 'SimHei'

# =========================
# 1. 接收模块
# =========================
class receiver():
    """
    Receiver类负责:
    1. 在主控节点上开启TCP服务器
    2. 接收来自两个测向站上传的数据
    (JSON格式,包含测向站编号、目标编号、时间戳、测角结果,示例:{"station_id": 1, "target_id": 0, "timestamp": 1.0, "angle": 0.5236})
    3. 解析 JSON
    4. 将测向站1和测向站2的数据分别存储到不同列表中
    5. 提供线程锁，避免多线程环境下数据冲突
    """

    # host: 主控节点监听地址，0.0.0.0表示监听本机所有网卡
    # port: TCP监听端口，测向节点需要连接到该端口发送测角数据
    def __init__(self,host="0.0.0.0",port=9999):
        
        self.host = host
        self.port = port
        
        #TCP服务器socket
        self.server = None
        
        #标记监听状态
        self.Running = False
        
        # 分站存储测角数据
        # 每个元素都是一个字典，例如：
        # {
        #   "station_id": 1,
        #   "target_id": 0,
        #   "timestamp": 1.0,
        #   "angle": 0.5236
        # }
        self.station1_data = []
        self.station2_data = []

        #两个点分别保护两个列表
        self.lock1 = Threading.Lock()
        self.lock2 = Threading.Lock()
    
    def listen(self):
        """
        启动TCP监听服务
        主线程或后台线程调用本函数后，主控节点开始等待测向站连接
        """
        self.server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

        # 允许端口快速复用，避免程序重启后端口被占用
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        #绑定监听地址和端口
        self.server.bind((self.host,self.port))

        #开始监听,最多运行5个排队连接
        self.server.listen(5)
        self.Running = True
        
        print(f"[主控节点] 正在监听 {self.host}:{self.port}")

        #持续接受客户端连接
        while self.Running:
            '''
            accept()函数会等待并返回一个客户端连接,返回值是一个元组,包含客户端socket对象和客户端地址。
            client: 客户端socket对象
            addr: 客户端地址
            '''
            client,addr = self.server.accept()


            print(f"[主控节点] 已连接 {addr}")
        
            '''
            每接入一个客户端，就开启新线程处理客户端连接
            target: 新线程执行的函数
            args: 传递给新线程的参数
            daemon: 新线程是否为守护线程,如果为True,则主线程结束,新线程也会结束
            '''
            Threading.Thread(target=self.handle_client,args=(client,addr),daemon=True).start()
        
    def handle_client(self, client, addr):
        '''
        处理单个客户端连接
        每个测向站连接后，主控节点会在一个独立线程里持续接收它发来的数据
        '''
        buffer = ""
        while True:
            try:
                # 每次最多接收1024字节
                data = client.recv(1024)

                # 如果收到空数据，表示客户端断开连接
                if not data:
                    break

                # 累积到缓冲区
                buffer += data.decode()

                # 这里假设每条JSON数据后面都带一个 '\n'
                # 这样可以防止一次recv收到多条消息，或者一条消息分多次收到
                while '\n' in buffer:
                    # 按行拆分
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()

                    if not line:
                        continue

                    try:
                        # 将JSON字符串转成Python字典
                        msg = json.loads(line)

                        # 存储到对应测向站的数据列表中
                        self.store_data(msg)

                        print(f"[接收] 来自{addr}: {msg}")
                    except json.JSONDecodeError:
                        print(f"[接收] JSON解析失败: {line}")

            except Exception as e:
                print(f"[接收] 客户端{addr}异常: {e}")
                break

        client.close()
        print(f"[主控节点] 连接关闭: {addr}")
    

    def store_data(self, msg:dict):
        '''
        按站号将数据存入 station1_data 或 station2_data
        并按时间戳排序，方便后续配对
        '''
        
        # station_id: 测向站编号，1表示站1，2表示站2
        station_id = msg.get("station_id", None) 

        # 如果是1号测向站的数据
        if station_id == 1:
            # 加锁，避免多线程环境下数据冲突
            with self.lock1:

                # appending data to list
                self.station1_data.append(msg)

                # sorting data by timestamp
                self.station1_data.append(msg)
                
                # 按timestamp升序排列
                self.station1_data.sort(key=lambda x: x["timestamp"])
                # timestamp: 当前测角对应的时刻，用于双站数据时间匹配

        # 如果是2号测向站的数据
        elif station_id == 2:
            with self.lock2:
                self.station2_data.append(msg)
                # 按timestamp升序排列
                self.station2_data.sort(key=lambda x: x["timestamp"])

        else:
            print(f"[接收] 未知站号: {msg}")



# =========================
# 2. 定位计算模块
# =========================
class calculator():
    """
    负责：双站交叉定位
    """
    def __init__(self):
        self.reciever = receiver()
        
    
    def calculate(self,angle1:float,angle2:float,distance:float = 100.0):
        '''**distance**:两个测向站之间的距离\n
        **angle1**:测向站1的测角结果\n
        **angle2**:测向站2的测角结果\n
        **返回值**:目标的坐标(x,y)\n
        该坐标为假设angle1来自坐标为(0,0)的测向站,angle2来自坐标为(distance,0)的测向站时的计算结果。
        '''
        try:
            x = distance*math.tan(angle1)/(math.tan(angle1)-math.tan(angle2))
            y = x*math.tan(angle1)
            return (x,y)
        except ZeroDivisionError:
            print("测角结果异常,无法计算目标坐标")
            return None

# =========================
# 3. 真实轨迹生成模块
# =========================
class TargetSimulator:
    """
    目标轨迹生成类

    功能：
    1. 生成直线运动轨迹
    2. 生成圆弧/圆周运动轨迹
    3. 根据用户自定义函数生成任意轨迹
    4. 根据给定离散点生成轨迹
    5. 根据初始位置、初始速度和加速度生成运动轨迹
    6. 绘制轨迹方向图
    """

    def __init__(self):
        pass

    def generate_line_track(self, start_pos=(20, 50), velocity=(1.0, 0.5), total_time=30, dt=0.5):
        """
        生成人工目标的直线运动轨迹

        参数：
        start_pos  : 初始位置 (x0, y0)
        velocity   : 速度向量 (vx, vy)
        total_time : 总仿真时长，单位:秒
        dt         : 时间采样间隔，单位:秒

        返回：
        track : 轨迹列表
        结构为：
        [
            [(x1, y1), t1],
            [(x2, y2), t2],
            ...
        ]
        """
        track = []

        x0, y0 = start_pos
        vx, vy = velocity

        t = 0.0
        while t <= total_time:
            # 直线匀速运动公式
            x = x0 + vx * t
            y = y0 + vy * t

            track.append([(x, y), round(t, 3)])
            t += dt

        return track

    def generate_arc_track(self, center=(50, 50), radius=30, omega=0.05, phase0=0.0, total_time=30, dt=0.5):
        """
        生成圆弧/圆周运动轨迹

        参数：
        center     : 圆心坐标 (cx, cy)
        radius     : 圆周运动半径
        omega      : 角速度
        phase0     : 初始相位角
        total_time : 总仿真时长
        dt         : 时间采样间隔

        返回：
        track : 轨迹列表
        """
        track = []

        cx, cy = center

        t = 0.0
        while t <= total_time:
            # 当前时刻目标在圆上的角度
            angle = phase0 + omega * t

            # 圆周参数方程
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)

            track.append([(x, y), round(t, 3)])
            t += dt

        return track

    def generate_custom_track(self, path_func, total_time=30, dt=0.5):
        """
        根据用户自定义函数生成任意轨迹

        参数：
        path_func  : 用户自定义轨迹函数
                     输入 t,输出 (x, y)
                     例如：
                     def my_path(t):
                         x = 2 * t
                         y = 20 * math.sin(0.2 * t) + 50
                         return x, y

        total_time : 总仿真时长
        dt         : 时间采样间隔

        返回：
        track : 轨迹列表
        """
        track = []

        t = 0.0
        while t <= total_time:
            x, y = path_func(t)
            track.append([(x, y), round(t, 3)])
            t += dt

        return track

    def generate_track_from_points(self, points, dt=0.5):
        """
        根据给定离散点序列生成轨迹

        参数：
        points : 坐标点列表
                 例如 [(x1, y1), (x2, y2), (x3, y3), ...]
        dt     : 相邻两个轨迹点之间的时间间隔

        返回：
        track : 带时间戳的轨迹列表
        """
        track = []

        for i, p in enumerate(points):
            t = round(i * dt, 3)
            track.append([p, t])

        return track

    def generate_motion_track(self, start_pos=(0, 0), start_vel=(1, 1), accel_func=None, total_time=30, dt=0.5):
        """
        根据运动学模型生成轨迹

        参数：
        start_pos  : 初始位置 (x0, y0)
        start_vel  : 初始速度 (vx0, vy0)
        accel_func : 加速度函数
                     输入参数：(t, x, y, vx, vy)
                     返回参数：(ax, ay)
                     如果为 None,则默认为匀速运动
        total_time : 总仿真时长
        dt         : 时间步长

        返回：
        track : 带时间戳的轨迹列表
        """
        track = []

        x, y = start_pos
        vx, vy = start_vel
        t = 0.0

        while t <= total_time:
            # 先记录当前位置
            track.append([(x, y), round(t, 3)])

            # 获取当前时刻加速度
            if accel_func is None:
                ax, ay = 0.0, 0.0
            else:
                ax, ay = accel_func(t, x, y, vx, vy)

            # 更新速度
            vx += ax * dt
            vy += ay * dt

            # 更新位置
            x += vx * dt
            y += vy * dt

            # 时间推进
            t += dt

        return track      
    def drawplt(track:list):
        '''绘制目标的真实轨迹和定位轨迹\n根据传入的二维坐标和时间戳数据绘制目标的运动轨迹和定位轨迹\n
        **track**:一个包含目标坐标和时间戳的二维数组,每行包含一个坐标(x,y)和对应的时间戳\n结构为 [[(x1, y1), t1], [(x2, y2), t2], ...]\n
        '''
        points = np.array([p[0] for p in track])
        x = points[:, 0]
        y = points[:, 1]
    
        '''
        2. 计算向量 (U, V)
        # U 是 x 方向的变化量,V 是 y 方向的变化量
        # 我们计算 current_point 到 next_point 的差值
        # np.diff 计算相邻元素的差值，结果会比原数组少一个，所以最后要补一个 0
        '''
        U = np.diff(x)
        V = np.diff(y)
    
        # 为了让最后一个点也有箭头（或者不显示），我们在数组末尾补 0
        # 这样 U, V 的长度就和 x, y 一致了
        U = np.append(U, 0)
        V = np.append(V, 0)
    
        # 3. 创建画布
        plt.figure(figsize=(10, 8))
    
        ''' 4. 绘制箭头 (核心代码)
        # angles='xy': 箭头角度根据数据坐标计算
        # scale_units='xy': 缩放单位与数据坐标一致
        # scale=1: 1:1 还原向量长度 (如果箭头太长太密，可以调大这个数值，比如 scale=5)
        # width: 箭头的粗细
        '''
        step = 3
        plt.quiver(x[::step], y[::step], U[::step], V[::step], 
               angles='xy', 
               scale_units='xy', 
               scale=1, 
               width=0.005, 
               color='blue', 
               alpha=0.6,
               label='运动方向向量')
    
        # 5. 绘制轨迹连线 (可选，为了看清整体路径)
        plt.plot(x, y, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='原始轨迹')
    
        # 6. 标记起点和终点
        plt.scatter(x[0], y[0], color='green', s=100, label='起点', zorder=5)
        plt.scatter(x[-1], y[-1], color='red', s=100, label='终点', zorder=5)
    
        # 7. 图表美化
        plt.title('目标轨迹流向图 (点变为方向箭头)', fontsize=16)
        plt.xlabel('X 坐标')
        plt.ylabel('Y 坐标')
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend()
        plt.axis('equal')
    
        plt.show()
        

# =========================
# 4. 主控节点核心流程
# =========================
class MasterNode:
    """
    主控节点类，负责整个系统的总控逻辑：
    1. 启动网络接收
    2. 保存真实轨迹
    3. 对两个测向站数据进行时间配对
    4. 调用定位函数计算目标位置
    5. 计算误差并保存
    6. 绘制结果图
    """
    def __init__(self, port=9999, station_distance=100.0, time_tolerance=0.3):
        """
        初始化主控节点

        参数：
        port             : 主控节点监听端口
        station_distance : 两个测向站之间的距离
        time_tolerance   : 两站数据时间匹配容差，单位秒
                           当两个站的时间戳差值小于该值时，认为属于同一时刻数据
        """
        
        # 网络参数
        self.port = port  # 主控节点监听端口

        
        # 测向站部署参数
        # 默认将两个测向站放在 x 轴上：
        # 站1在 (0, 0)
        # 站2在 (station_distance, 0)
        self.station_distance = station_distance
        self.station1_pos = (0.0, 0.0)
        self.station2_pos = (station_distance, 0.0)

        # 时间戳匹配容差
        self.time_tolerance = time_tolerance

        # 分别缓存两个测向站上传的数据
        # 数据格式示例：
        # {
        #     "station_id": 1,
        #     "target_id": 0,
        #     "timestamp": 10.5,
        #     "angle": 0.785
        # }
        self.station1_buffer = []
        self.station2_buffer = []

        # 保存定位结果轨迹
        # 结构：
        # [
        #     [(x1, y1), t1],
        #     [(x2, y2), t2],
        #     ...
        # ]
        self.estimated_track = []

        # 保存真实轨迹（可选）
        # 若做仿真，则可提前设置真实轨迹
        self.true_track = []
    
        # 保存误差数据
        # 结构：
        # [
        #     [error1, t1],
        #     [error2, t2],
        #     ...
        # ]
        self.error_list = []
        
        # 线程锁
        # 用于多线程接收数据时保护共享缓冲区
        self.lock = Threading.Lock()
        
        # 运行标志
        self.running = False
        
        # 轨迹模拟器对象
        # 需要外部已有 TargetSimulator 类
        self.simulator = TargetSimulator()

    def set_true_track(self, track):
        """
        设置真实轨迹

        参数：
        track : 真实轨迹列表
                格式为：
                [
                    [(x1, y1), t1],
                    [(x2, y2), t2],
                    ...
                ]
        """
        self.true_track = track    

    def calculate_position(self, angle1, angle2):
        """
        根据双站测角结果计算目标位置

        参数：
        angle1 : 1号测向站测得的方位角(弧度)
        angle2 : 2号测向站测得的方位角(弧度)

        返回：
        (x, y) : 计算得到的目标坐标
        若两条测向线接近平行，则返回 None

        说明：
        假设：
        - 测向站1坐标为 (x1, y1)
        - 测向站2坐标为 (x2, y2)
        - 每个测向站给出一条射线方向

        射线方程可写为：
        站1:P1 + t1 * d1
        站2:P2 + t2 * d2
        
        其中：
        P1: (x1, y1)
        P2: (x2, y2)
        t1: 1号测向站测得的距离/测向站1到目标的距离
        t2: 2号测向站测得的距离/测向站2到目标的距离
        d1: 1号测向站的射线方向向量
        d2: 2号测向站的射线方向向量 
        d1 = (cos(angle1), sin(angle1))
        d2 = (cos(angle2), sin(angle2))

        通过解线性方程组得到交点
        """
        x1, y1 = self.station1_pos
        x2, y2 = self.station2_pos

        # 两条测向射线的方向向量
        d1x = math.cos(angle1)
        d1y = math.sin(angle1)
        d2x = math.cos(angle2)
        d2y = math.sin(angle2)

        # 构造二维线性方程组
        # P1 + t1*d1 = P2 + t2*d2
        #
        # 即：
        # t1*d1x - t2*d2x = x2 - x1
        # t1*d1y - t2*d2y = y2 - y1
        #
        # 写成矩阵形式 A * [t1, t2]^T = b
        A = np.array([
            [d1x, -d2x],
            [d1y, -d2y]
        ])

        b = np.array([
            x2 - x1,
            y2 - y1
        ])

        # 如果矩阵接近奇异，说明两条测向线接近平行，交点不稳定
        det = np.linalg.det(A)
        if abs(det) < 1e-8:
            return None

        # 求解参数 t1 和 t2
        t1, t2 = np.linalg.solve(A, b)

        # 用站1的射线计算交点坐标
        x = x1 + t1 * d1x
        y = y1 + t1 * d1y

        return (x, y)
    
    def get_true_position_by_time(self, t):
        """
        根据时刻 t 获取真实位置

        参数：
        t : 查询时刻

        返回：
        ((x, y), t) : 时刻 t 对应的真实位置
        若无真实轨迹，则返回 None

        说明：
        为了适配任意轨迹，这里采用“线性插值”方式：
        1. 若 t 小于最早时间，返回第一个点
        2. 若 t 大于最晚时间，返回最后一个点
        3. 若 t 位于两个轨迹点之间，则按时间比例进行线性插值
        """
        if not self.true_track:
            return None

        # 若只有一个轨迹点，则直接返回
        if len(self.true_track) == 1:
            return self.true_track[0][0], self.true_track[0][1]

        # 提取所有时间戳
        times = [item[1] for item in self.true_track]

        # 查询时间早于轨迹起点
        if t <= times[0]:
            return self.true_track[0][0], self.true_track[0][1]

        # 查询时间晚于轨迹终点
        if t >= times[-1]:
            return self.true_track[-1][0], self.true_track[-1][1]

        # 遍历相邻轨迹点，寻找 t 所在的时间区间
        for i in range(len(self.true_track) - 1):
            (x1, y1), t1 = self.true_track[i]
            (x2, y2), t2 = self.true_track[i + 1]

            if t1 <= t <= t2:
                # 避免分母为0
                if abs(t2 - t1) < 1e-12:
                    return (x1, y1), t1

                # 线性插值比例
                alpha = (t - t1) / (t2 - t1)

                # 对 x 和 y 分别插值
                x = x1 + alpha * (x2 - x1)
                y = y1 + alpha * (y2 - y1)

                return (x, y), t

        return None
    
    def compute_error(self, est_pos, t):
        """
        计算定位结果在时刻 t 的误差

        参数：
        est_pos : 定位得到的位置 (x, y)
        t       : 定位时刻

        返回：
        error : 欧氏距离误差
        若真实轨迹不存在，则返回 None
        """
        #true_result: ((x, y), t)
        true_result = self.get_true_position_by_time(t)
        if true_result is None:
            return None

        #ttrue_pos: (x, y)
        #ttrue_time: t
        true_pos, true_time = true_result

        ex, ey = est_pos
        tx, ty = true_pos

        # 欧氏距离误差
        error = math.sqrt((ex - tx) ** 2 + (ey - ty) ** 2)
        return error
    
    def add_measurement(self, data):
        """
        将收到的测向数据加入对应缓冲区，并尝试匹配定位

        参数：
        data : 单条测向数据，格式示例：
               {
                   "station_id": 1,
                   "target_id": 0,
                   "timestamp": 10.5,
                   "angle": 0.785
               }
        """
        with self.lock:
            data = data.copy()

            # 角度制 -> 弧度制
            data["angle"] = math.radians(data["angle"])
            
            station_id = data["station_id"]

            # 按测向站编号分别存入不同缓冲区
            if station_id == 1:
                self.station1_buffer.append(data)
            elif station_id == 2:
                self.station2_buffer.append(data)
            else:
                print(f"[警告] 未知测向站编号: {station_id}")
                return

            # 新数据进入后，尝试做时间匹配与定位
            self.try_match_and_locate()

    def try_match_and_locate(self):
        """
        尝试从两个缓冲区(station1_buffer, station2_buffer)中寻找时间戳匹配的数据对，并进行定位

        匹配规则：
        - 若 station1 的某条数据与 station2 的某条数据时间差小于 time_tolerance
        - 则认为这两条数据对应同一时刻目标，可用于定位

        处理流程：
        1. 查找可匹配数据对
        2. 执行双站测向交汇计算
        3. 保存定位轨迹
        4. 如有真实轨迹，则计算误差
        5. 从缓冲区删除已使用的数据
        """
        matched_i = None
        matched_j = None

        # 遍历两个缓冲区，寻找第一对满足时间匹配条件的数据
        for i, d1 in enumerate(self.station1_buffer):
            for j, d2 in enumerate(self.station2_buffer):
                t1 = d1["timestamp"]
                t2 = d2["timestamp"]

                if abs(t1 - t2) <= self.time_tolerance:
                    matched_i = i
                    matched_j = j
                    break
            if matched_i is not None:
                break

        # 若没找到匹配对，则直接返回
        if matched_i is None or matched_j is None:
            return

        # 取出匹配到的两条数据
        d1 = self.station1_buffer.pop(matched_i)
        d2 = self.station2_buffer.pop(matched_j)

        # 取两个时间戳的平均值作为本次定位时刻
        t_est = round((d1["timestamp"] + d2["timestamp"]) / 2.0, 3)

        # 取出测向角度
        angle1 = d1["angle"]
        angle2 = d2["angle"]

        # 执行双站交汇定位
        pos = self.calculate_position(angle1, angle2)

        if pos is None:
            print(f"[定位失败] t={t_est:.3f} 两条测向线接近平行")
            return

        # 保存定位结果
        self.estimated_track.append([pos, t_est])

        # 若存在真实轨迹，则计算误差
        error = self.compute_error(pos, t_est)
        if error is not None:
            self.error_list.append([error, t_est])
            print(f"[定位成功] t={t_est:.3f}, est={pos}, error={error:.3f}")
        else:
            print(f"[定位成功] t={t_est:.3f}, est={pos}")

    def handle_client(self, conn, addr):
        """
        处理单个客户端连接

        参数：
        conn : 客户端socket连接对象
        addr : 客户端地址

        说明：
        约定客户端按行发送 JSON 数据，每行一条消息。
        例如：
        {"station_id":1,"target_id":0,"timestamp":0.5,"angle":0.785}
        """
        print(f"[连接建立] 来自 {addr}")

        buffer = ""

        try:
            # 循环接收数据
            while self.running:
                #从TCP连接中最多读取4096字节数据，返回的是bytes类型
                data = conn.recv(4096)
                
                # 若没有数据，则跳出循环
                if not data:
                    break

                # 将接收到的字节流解码后累加到缓冲字符串
                buffer += data.decode("utf-8")

                # 按换行符分割，逐行解析 JSON
                while "\n" in buffer:
                    #把buffer从第一处\n开始分割，返回分割后的两部分，第一部分是json字符串，第二部分是剩余的buffer
                    line, buffer = buffer.split("\n", 1)
                    
                    #去掉首位的空白字符
                    line = line.strip()

                    #若行为空，则跳过
                    if not line:
                        continue
                    
                    # 解析json字符串，并将结果存入msg变量中
                    try:
                        msg = json.loads(line)        #将json字符串转换成python字典
                        self.add_measurement(msg)     #将测向数据存入缓冲区
                    except json.JSONDecodeError:
                        print(f"[JSON解析失败] 数据内容: {line}")
                    except Exception as e:
                        print(f"[数据处理异常] {e}")

        except Exception as e:
            print(f"[连接异常] {addr} -> {e}")

        finally:
            conn.close()
            print(f"[连接关闭] {addr}")

    def start(self):
        """
        启动主控节点监听服务

        功能：
        1. 创建 TCP 服务器
        2. 监听指定端口
        3. 接收测向站连接
        4. 为每个连接创建处理线程
        """
        self.running = True

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 允许端口快速复用，避免程序重启时端口占用
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # 监听所有网卡地址
        server.bind(("0.0.0.0", self.port))
        server.listen(5)

        print(f"[主控节点启动] 监听端口 {self.port}")
        print(f"[测向站位置] station1={self.station1_pos}, station2={self.station2_pos}")

        try:
            while self.running:
                conn, addr = server.accept()   #conn:客户端socket连接对象,addr:客户端地址
                print(f"[新连接] 来自 {addr}")
                # 为每个新连接创建独立线程
                #target:客户端处理函数,args:参数元组
                #daemon:是否为守护线程，默认True
                t = Threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True)
                t.start()

        except KeyboardInterrupt:
            print("\n[主控节点] 收到中断信号，准备停止")
        except Exception as e:
            print(f"[主控节点异常] {e}")
        finally:
            self.running = False
            server.close()
            print("[主控节点已关闭]")

    
    def stop(self):
        """
        停止主控节点
        """
        self.running = False

    
    def draw_result(self):
        """
        绘制最终结果图

        绘制内容：
        1. 真实轨迹与定位轨迹对比图
        2. 定位误差随时间变化曲线
        3. 额外调用 TargetSimulator.drawplt() 绘制真实轨迹流向图
        """
        plt.figure(figsize=(12, 6))    # 设置绘图窗口大小

        # =========================
        # 左图：真实轨迹与定位轨迹
        # =========================
        plt.subplot(1, 2, 1)          # 将画布分为1行2列，并选中第1个子图用于绘制真实轨迹与定位轨迹

        # 绘制真实轨迹
        if self.true_track:
            
            #提取轨迹中的坐标点，并用np.array()转化为Numpy数组，方便后续索引
            true_points = np.array([item[0] for item in self.true_track])
            
            plt.plot(
                true_points[:, 0],   #所有点的x坐标
                true_points[:, 1],   #所有点的y坐标
                'g-',                #线条颜色为绿色，线型为连续
                linewidth=2,         #线宽为2
                label='真实轨迹'      #图例标签为“真实轨迹”
            )

        # 绘制定位轨迹
        if self.estimated_track:
            est_points = np.array([item[0] for item in self.estimated_track])
            plt.plot(
                est_points[:, 0],
                est_points[:, 1],
                'ro--',
                markersize=4,
                linewidth=1.5,
                label='定位轨迹'
            )

        # 标记两个测向站位置
        plt.scatter(
            self.station1_pos[0], self.station1_pos[1],
            c='blue', s=120, marker='^', label='测向站1'
        )
        plt.scatter(
            self.station2_pos[0], self.station2_pos[1],
            c='purple', s=120, marker='^', label='测向站2'
        )

        plt.title("真实轨迹与定位轨迹")
        plt.xlabel("X 坐标")
        plt.ylabel("Y 坐标")
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.axis("equal")
        plt.legend()

        # =========================
        # 右图：误差曲线
        # =========================
        plt.subplot(1, 2, 2)

        if self.error_list:
            times = [item[1] for item in self.error_list]    #提取误差列表中的时间戳
            errors = [item[0] for item in self.error_list]   #提取误差列表中的误差值

            plt.plot(times, errors, 'b-o', linewidth=1.5, markersize=4, label='定位误差')
            plt.title("定位误差随时间变化")
            plt.xlabel("时间 / s")
            plt.ylabel("误差")
            plt.grid(True, linestyle='--', alpha=0.5)
            plt.legend()
        else:
            plt.title("暂无误差数据")
            plt.xlabel("时间 / s")
            plt.ylabel("误差")
            plt.grid(True, linestyle='--', alpha=0.5)

        plt.tight_layout()
        plt.show()

        # =========================
        # 单独绘制真实轨迹流向图
        # =========================
        if self.true_track:
            self.simulator.drawplt(self.true_track)

    def print_summary(self):
        """
        打印结果统计信息
        """
        print("\n========== 定位结果统计 ==========")
        print(f"定位点数量: {len(self.estimated_track)}")

        if self.error_list:
            errors = [item[0] for item in self.error_list]
            print(f"平均误差: {np.mean(errors):.3f}")
            print(f"最大误差: {np.max(errors):.3f}")
            print(f"最小误差: {np.min(errors):.3f}")
        else:
            print("暂无误差统计数据")

        print("=================================\n")


def simulate_station_sender(station_id, station_pos, track, host="127.0.0.1", port=9999, send_interval=0.1, angle_noise_std=0.0):
    """
    模拟测向站发送测角数据到主控节点

    参数：
    station_id       : 测向站编号，例如 1 或 2
    station_pos      : 测向站坐标 (xs, ys)
    track            : 目标真实轨迹
                       格式为：
                       [
                           [(x1, y1), t1],
                           [(x2, y2), t2],
                           ...
                       ]
    host             : 主控节点 IP 地址
    port             : 主控节点端口
    send_interval    : 每次发送之间的等待时间，单位秒
                       这里只是控制模拟发送速度，不一定等于轨迹时间间隔
    angle_noise_std  : 测角高斯噪声标准差，单位：弧度
                       若为 0.0,则表示无噪声

    功能说明：
    - 该函数会遍历真实轨迹中的每一个点
    - 对每个轨迹点，计算“目标相对于当前测向站”的方位角
    - 然后把测角数据以 JSON 格式发送给主控节点

    发送数据格式：
    {
        "station_id": 1,
        "target_id": 0,
        "timestamp": 0.5,
        "angle": 0.785
    }

    注意：
    angle 使用的是“弧度制”
    """
    xs, ys = station_pos

    try:
        # 创建 TCP 客户端 socket
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 连接主控节点
        client.connect((host, port))
        print(f"[测向站{station_id}] 已连接主控节点 {host}:{port}")

        # 逐个轨迹点发送测角数据
        for item in track:
            # item 结构为 [(x, y), t]
            (x, y), t = item

            # 计算目标相对测向站的方位角
            # atan2 返回弧度值，范围通常为 [-pi, pi]
            angle = math.atan2(y - ys, x - xs)

            # 若设置了测角噪声，则叠加高斯噪声
            if angle_noise_std > 0:
                angle += np.random.normal(0, angle_noise_std)

            # 组织发送数据
            msg = {
                "station_id": station_id,
                "target_id": 0,
                "timestamp": t,
                "angle": angle   # 单位：弧度
            }

            # 转成 JSON 字符串，并在末尾补换行符
            # 主控节点按“每行一条 JSON”进行解析
            data = json.dumps(msg) + "\n"

            # 发送给主控节点
            client.sendall(data.encode("utf-8"))

            print(f"[测向站{station_id}] 发送数据: t={t:.3f}, angle(rad)={angle:.4f}, angle(deg)={math.degrees(angle):.2f}")

            # 控制发送节奏，模拟连续上传
            time.sleep(send_interval)

    except Exception as e:
        print(f"[测向站{station_id}] 发送异常: {e}")

    finally:
        try:
            client.close()
        except:
            pass
        print(f"[测向站{station_id}] 已关闭连接")


def custom_path_segment(t):
    """
    分段轨迹函数示例

    参数：
    t : 时间

    返回：
    (x, y) : 时刻 t 对应的目标位置

    轨迹说明：
    1. 前8秒做直线运动
    2. 8~16秒做圆弧运动
    3. 16秒之后继续直线运动
    """
    if t < 8:
        # 第一段：直线运动
        x = 10 + 2.0 * t
        y = 20 + 1.0 * t

    elif t < 16:
        # 第二段：圆弧运动
        theta = 0.4 * (t - 8)
        x = 26 + 15 * math.cos(theta)
        y = 28 + 15 * math.sin(theta)

    else:
        # 第三段：继续直线运动
        x = 26 + 15 + 1.2 * (t - 16)
        y = 28 + 0.5 * (t - 16)

    return x, y


if __name__ == "__main__":
    """
    主程序说明：

    运行流程：
    1. 创建主控节点 MasterNode
    2. 生成目标真实轨迹
    3. 将真实轨迹设置给主控节点，用于误差评估
    4. 启动主控节点服务端
    5. 启动两个模拟测向站，分别发送测角数据
    6. 等待数据发送和处理完成
    7. 输出定位统计结果
    8. 绘制轨迹与误差图
    """

    # ======================================================
    # 1. 创建主控节点
    # ======================================================
    master = MasterNode(
        port=9999,              # 主控节点监听端口
        station_distance=100.0, # 两个测向站间距
        time_tolerance=0.3      # 时间戳匹配容差
    )

    # ======================================================
    # 2. 选择并生成真实轨迹
    #    你可以自由切换下面几种生成方式
    # ======================================================

    # ---------- 方式A：直线轨迹 ----------
    # true_track = master.simulator.generate_line_track(
    #     start_pos=(20, 80),
    #     velocity=(2.0, -0.8),
    #     total_time=20,
    #     dt=0.5
    # )

    # ---------- 方式B：圆弧轨迹 ----------
    # true_track = master.simulator.generate_arc_track(
    #     center=(60, 60),
    #     radius=25,
    #     omega=0.15,
    #     phase0=0.0,
    #     total_time=20,
    #     dt=0.5
    # )

    # ---------- 方式C：任意自定义轨迹 ----------
    true_track = master.simulator.generate_custom_track(
        path_func=custom_path_segment,
        total_time=25,
        dt=0.5
    )

    # ---------- 方式D：离散点轨迹 ----------
    # points = [
    #     (10, 10),
    #     (15, 18),
    #     (20, 25),
    #     (30, 35),
    #     (45, 40),
    #     (55, 32),
    #     (65, 20)
    # ]
    # true_track = master.simulator.generate_track_from_points(points, dt=0.5)

    # ---------- 方式E：基于运动学模型的轨迹 ----------
    # def accel_func(t, x, y, vx, vy):
    #     if t < 10:
    #         return (0.05, 0.02)
    #     else:
    #         return (-0.03, 0.01)
    #
    # true_track = master.simulator.generate_motion_track(
    #     start_pos=(0, 0),
    #     start_vel=(2, 1),
    #     accel_func=accel_func,
    #     total_time=20,
    #     dt=0.5
    # )

    # ======================================================
    # 3. 将真实轨迹设置给主控节点
    #    后续主控节点可根据它计算误差
    # ======================================================
    master.set_true_track(true_track)

    # ======================================================
    # 4. 启动主控节点服务端
    #    放到后台线程中运行，避免阻塞主线程
    # ======================================================
    master_thread = Threading.Thread(target=master.start, daemon=True)
    master_thread.start()

    # 略微等待，确保服务端已成功启动
    time.sleep(1.0)

    # ======================================================
    # 5. 启动两个模拟测向站
    #    它们会根据真实轨迹逐点计算测角，并发送给主控节点
    # ======================================================

    # 测向站1线程
    station1_thread = Threading.Thread(
        target=simulate_station_sender,
        args=(
            1,                  # station_id
            master.station1_pos,# station_pos
            true_track          # 真实轨迹
        ),
        kwargs={
            "host": "127.0.0.1",
            "port": 9999,
            "send_interval": 0.1,
            "angle_noise_std": 0.01   # 弧度噪声，可改成 0.0 表示无噪声
        },
        daemon=True
    )

    # 测向站2线程
    station2_thread = Threading.Thread(
        target=simulate_station_sender,
        args=(
            2,
            master.station2_pos,
            true_track
        ),
        kwargs={
            "host": "127.0.0.1",
            "port": 9999,
            "send_interval": 0.1,
            "angle_noise_std": 0.01
        },
        daemon=True
    )

    # 启动两个测向站线程
    station1_thread.start()
    station2_thread.start()

    # ======================================================
    # 6. 等待两个测向站发送完成
    # ======================================================
    station1_thread.join()
    station2_thread.join()

    # 再额外等待一小会，让主控节点处理完最后残留的数据
    time.sleep(1.0)

    # ======================================================
    # 7. 打印结果统计
    # ======================================================
    master.print_summary()

    # ======================================================
    # 8. 绘制结果图
    # ======================================================
    master.draw_result()

    # ======================================================
    # 9. 停止主控节点
    # ======================================================
    master.stop()

    print("[主程序结束]")
