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
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path
import socket,math,time

# 设置 matplotlib 中文字体，避免绘图中文乱码
plt.rcParams['font.family'] = 'SimHei'

class receiver():
    """
    Receiver类负责:
    1. 在主控节点上开启TCP服务器
    2. 接收来自两个测向站上传的数据
    3. 将测向站1和测向站2的数据分别存储到不同列表中
    4. 提供线程锁，避免多线程环境下数据冲突
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
    
    def listen(self,**kwargs):
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




class calculator():
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
        
def drawplt(track:list):
    '''绘制目标的真实轨迹?和定位轨迹\n根据传入的二维坐标和时间戳数据绘制目标的运动轨迹和定位轨迹\n
    **track**:一个包含目标坐标和时间戳的二维数组,每行包含一个坐标(x,y)和对应的时间戳\n结构为 [[(x1, y1), t1], [(x2, y2), t2], ...]\n
    '''
    points = np.array([p[0] for p in track])
    x = points[:, 0]
    y = points[:, 1]
    
    # 2. 计算向量 (U, V)
    # U 是 x 方向的变化量，V 是 y 方向的变化量
    # 我们计算 current_point 到 next_point 的差值
    # np.diff 计算相邻元素的差值，结果会比原数组少一个，所以最后要补一个 0
    U = np.diff(x)
    V = np.diff(y)
    
    # 为了让最后一个点也有箭头（或者不显示），我们在数组末尾补 0
    # 这样 U, V 的长度就和 x, y 一致了
    U = np.append(U, 0)
    V = np.append(V, 0)
    
    # 3. 创建画布
    plt.figure(figsize=(10, 8))
    
    # 4. 绘制箭头 (核心代码)
    # angles='xy': 箭头角度根据数据坐标计算
    # scale_units='xy': 缩放单位与数据坐标一致
    # scale=1: 1:1 还原向量长度 (如果箭头太长太密，可以调大这个数值，比如 scale=5)
    # width: 箭头的粗细
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

###测试脚本如下
if __name__ == "__main__":
    '''
    print("主控节点正在运行,ip地址为:",socket.gethostbyname(socket.gethostname()))
    #reciever.listen(port = 9999)
    calculator = calculator()
    location = calculator.calculate(angle1 = math.radians(30.0),angle2 = math.radians(300.0),distance = 100.0)
    print("目标的坐标为:",location)
    '''
    '''
    test_track = []
    for t in range(0, 100):
        angle = t * 0.1
        # 半径随时间增大，形成螺旋
        r = 5 + 0.05 * t 
        x = r * math.cos(angle)
        y = r * math.sin(angle)
        test_track.append([(x, y), t])

    # 调用函数
    drawplt(test_track)
    '''