####主控节点###
#负责系统参数和调制参数的设置
#负责目标运动轨迹的生成
#负责辐射源波形的生成
#接收两个侧向站上传的测角结果==>已经实现从一个侧向站接收。考虑通过多线程同时接收两个侧向站的测角结果
#进行双站交叉定位==>calculator.calculate()函数已经实现根据角度计算目标坐标,应继续编写程序将角度数据从接收到的数据中取出传递给给该数据。目前计划将两个测向节点的数据分别存储在两个列表中，根据时间戳的先后顺序排序并依次取出进行交叉定位,如果某个时刻只有一个测向站的数据则暂不进行定位，后续再进行插值处理。
#显示真实轨迹与定位轨迹==>部分完成
#统计并分析定位误差

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path
import socket,math,time
plt.rcParams['font.family'] = 'SimHei'
class reciever():  #接收器类，负责监听并接收从测向节点发送过来的数据
    def __init__(self):
        pass
    
    def listen(self,**kwargs):
        machine = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        machine.bind(("0.0.0.0",kwargs.get("port",9999)))
        machine.listen(2)
        while True:
            machine2,addr = machine.accept()
            data = machine2.recv(1024)
            print(f"revFrom{addr}Data: {data.decode()}")
    
class calculator(): #计算器类，负责根据测向节点上传的测角结果进行交叉定位以及误差分析等其它计算功能
    def __init__(self):
        self.reciever = reciever()
        
    
    def calculate(self,angle1:float,angle2:float,distance:float = 100.0):
        '''**distance**:两个测向站之间的距离\n
        **angle1**:测向站1的测角结果\n
        **angle2**:测向站2的测角结果\n
        **返回值**:目标的坐标(x,y)\n
        该坐标为假设angle1来自坐标为(0,0)的测向站,angle2来自坐标为(distance,0)的测向站时的计算结果。
        '''
        try:
            x = distance*math.tan(angle1)/(math.tan(angle1)-math.tan(angle2))
            y = x/math.tan(angle1)
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
    cal = calculator()
    location = cal.calculate(angle1 = math.radians(30.0),angle2 = math.radians(300.0),distance = 100.0)
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