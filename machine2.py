###测向节点###
#根据主控节点下发的目标状态和信号参数生成阵列接收数据
#分别完成两个测向站的阵列信号处理
#实现波束的形成、频谱分析、双波束比辐侧向
#将每个时刻两个站的测角结果通过TCP/IP协议发送给主控节点==>部分完成

import numpy as np
import matplotlib.pyplot as plt
import socket,math,time,threading
from scipy.interpolate import make_interp_spline
import time

c = 299792458

class base():
    def __init__(self,number:int,element:int = 8,ele_distance:float = 1.0):
        self.element_num = element
        self._ele_distance = ele_distance
        self._number = number

    def generate_alpha(self,theta:float|np.float32,lamda:float = 2.0,):
        alpha = np.ones(self.element_num, dtype=complex)
        for i in range(self.element_num-1):
            alpha[i+1]=alpha[i]*np.exp(1j*2*np.pi*self._ele_distance*np.sin(np.radians(theta))/lamda)
        return alpha
    
    def generate_weights(self):
        """生成和波束与差波束的权向量"""
        M = self.element_num
        # 和波束权向量：全1
        w_sum = np.ones(M, dtype=complex)
        # 差波束权向量：前半部分为1，后半部分为-1
        w_diff = np.ones(M, dtype=complex)
        mid = M // 2
        w_diff[mid:] = -1
        return w_sum, w_diff
    
    def signal_construct_one(self,target_number:int,theta:float,s:float,lamda:float = 2.0,):
        alpha = self.generate_alpha(theta,lamda)
        X = alpha*s
        print('X',target_number,X)
        return X,alpha
    
    def Gauss_noise_gen(self,snr_db=None, signal_power=1.0):
        """
        生成高斯噪声
        :param snr_db: 信噪比 (dB),如果为None则生成标准噪声
        :param signal_power: 信号功率，用于计算噪声功率
        """
        noise_real = np.random.randn(self.element_num)
        noise_imag = np.random.randn(self.element_num)
        noise = (noise_real + 1j * noise_imag) / np.sqrt(2)
        return noise
    
    def show_sum_pattern(self, Xt: np.ndarray):
        """绘制和波束方向图"""
        y = []
        thetas = np.linspace(-60, 60, 1200)
        for theta in thetas:
            alpha = self.generate_alpha(theta)
            # 和波束：权向量为全 1 或导向矢量本身
            # F = a^H * Xt
            response = np.dot(alpha.T.conjugate(), Xt)
            y.append(np.abs(response))

        plt.figure(figsize=(10, 6))
        plt.plot(thetas, y, label='Sum Beam (Original)')
        plt.title('Sum Beam Pattern')
        plt.xlabel('Angle (degrees)')
        plt.ylabel('Amplitude')
        plt.grid(True)
        plt.legend()
        plt.show()

    def show_difference_pattern(self, Xt: np.ndarray):
        y_diff = []
        thetas = np.linspace(-60, 60, 1200)

        for theta in thetas:
            alpha = self.generate_alpha(theta)
            w_diff = np.ones(self.element_num, dtype=complex)
            mid_point = self.element_num // 2
            w_diff[mid_point:] = -1
            response = np.dot(w_diff.conjugate(), alpha)

            y_diff.append(np.abs(response))

        plt.figure(figsize=(10, 6))
        plt.plot(thetas, y_diff, label='Difference Beam', color='red')
        plt.title('Difference Beam Pattern')
        plt.xlabel('Angle (degrees)')
        plt.ylabel('Amplitude')
        plt.grid(True)
        plt.legend()
        plt.show()
    
    def signal_construct(self,target:int,theta:list):
        X = []
        alpha = []
        y = []
        for i in range(len(theta)):
            Xi,alphai = self.signal_construct_one(i,theta[i],1)
            X.append(Xi)
            alpha.append(alphai)
        Xt=np.zeros(self.element_num, dtype=complex)
        for i in range(len(theta)):
            Xt+=X[i]
        print('Xt before',Xt)
        Xt = Xt+self.Gauss_noise_gen(1)
        print('Xt after',Xt)
        '''
        for i in range(len(theta)):
            yi = np.dot(alpha[i].T.conjugate() , Xt)
            y.append(yi)
            print("y",i,yi)
            '''
        #self.show_sum_pattern(Xt)
        #self.show_difference_pattern(Xt)
        return Xt#,y
    
    def find_peak_angle(self, Xt, search_range=(-60, 60), step=0.1):
        """
        寻找和波束能量最大的角度（修正版）
        """
        thetas = np.arange(search_range[0], search_range[1], step)
        powers = []
        
        for theta in thetas:
            a = self.generate_alpha(theta)
            # 关键：计算接收信号 Xt 在该角度的投影能量
            # 这相当于用 a(theta) 去“匹配” Xt
            response = np.dot(a.conjugate(), Xt)
            power = np.abs(response) ** 2
            powers.append(power)
        
        # 找到最大值的索引
        max_idx = np.argmax(powers)
        peak_angle = thetas[max_idx]
        
        # 可视化验证
        plt.figure(figsize=(10, 5))
        plt.plot(thetas, powers, label='Beam Pattern Power')
        plt.axvline(peak_angle, color='r', linestyle='--', label=f'Peak @ {peak_angle:.2f}°')
        plt.xlabel('Angle (deg)')
        plt.ylabel('Power')
        plt.title('Sum Beam Pattern - Finding Peak')
        plt.legend()
        plt.grid(True)
        plt.show()
        
        return peak_angle
    
    def measure_angle_local_search(self, Xt, coarse_angle, search_width=10):
        """
        修正版：使用偏置差波束
        """
        # 1. 动态生成指向 coarse_angle 的和波束与差波束
        # 关键：差波束的零点现在对准了 coarse_angle，这样斜率最大
        w_sum = self.generate_alpha(coarse_angle) # 和波束指向目标
        
        # 生成差波束：在 w_sum 的基础上，后半部分乘 -1
        w_diff = w_sum.copy()
        mid = self.element_num // 2
        w_diff[mid:] = -w_diff[mid:]

        # 2. 计算实际信号的和差比 b (公式 3-3)
        y1_actual = np.dot(w_sum.conjugate(), Xt)
        y2_actual = np.dot(w_diff.conjugate(), Xt)
        
        # 这里用差/和的比值，比 (F1-F2)/(F1+F2) 更敏感
        # 且利用复数相位判断方向
        ratio_actual = y2_actual / y1_actual 
        b = np.abs(ratio_actual)
        
        # 3. 局部扫描生成理论曲线 k(theta) (公式 3-2)
        thetas = np.linspace(coarse_angle - search_width, coarse_angle + search_width, 1000)
        k_values = []
        
        for theta in thetas:
            a = self.generate_alpha(theta)
            # 使用同样的偏置权向量计算理论响应
            F1 = np.abs(np.dot(w_sum.conjugate(), a))
            F2 = np.abs(np.dot(w_diff.conjugate(), a))
            
            # 理论比值
            if F1 != 0:
                k = F2 / F1 # 对应差/和
            else:
                k = 0
            k_values.append(k)

        # 4. 查表匹配
        min_idx = np.argmin(np.abs(np.array(k_values) - b))
        estimated_angle = thetas[min_idx]
        
        # 5. 符号修正（利用相位）
        if np.angle(ratio_actual) < 0:
             # 如果相位为负，说明在左边，需要微调（这里简化处理，主要靠查表）
             pass 

        print(f"中心角度: {coarse_angle:.2f}°")
        print(f"实测比值 b: {b:.4f}")
        print(f"估计角度: {estimated_angle:.2f}°")
        
        return estimated_angle
class calculator():
    def __init__(self):
        pass
    
    def calculate(self,motion_type = 'line',**params):
        '''motion_type:目标运动类型，可选'line'直线运动或'circle'匀速圆周运动\n
        params:其它参数。如果运动类型为'line',则需要给出'loc':初位置,'a'加速度和'v'初速度,两个量都是二维列表向量;如果运动类型为'circle',则需要给出给出参数'center'圆心坐标,'radius':半径,'theta':初相位和'w':角速度\n
        此外,还可以提供:'Sr':'采样率'等参数'''
        #return np.random.uniform(0,360)  #测试用,应编写程序根据主控节点的参数生成阵列接收数据并计算测角结果
        time_span = params.get('SDuration',10)
        Sr = params.get('Sr', 1000)
        t_axis = np.arange(0, time_span, 1/Sr)
        if motion_type == "line":
            #模拟目标运动为直线运动，生成一连串位置坐标
            loc = np.array(params['loc'])
            v = params['v']
            a = params['a']
            positions = loc.reshape(1,2) + np.outer(t_axis , v) + 0.5 * np.outer(t_axis**2 , a)
            print(positions)
        elif motion_type == "circle":
            #模拟目标运动为圆周运动
            center = np.array(params['center'])
            radius = params['radius']
            w = params['w']
            theta0 = params['theta']
            positions = center.reshape(2,1) + radius*np.array([np.cos(theta0+w*t_axis),np.sin(theta0+w*t_axis)])
            positions = positions.T
            print(positions)
        return t_axis,positions
    def emision(self,modulation_type:str = 'CW',freq:float = c/2,**params):
        '''modulation_type:调制方式，可选'CW','AM'或'FM'\n
        freq:发射频率\n
        提供:'Cf':载频,\n
        'Bw':'带宽',\n
        'f':'调制频率',\n
        'SDuration':'信号时长'\n
        'Sr':'采样率'\n
        'm':调制指数(AM)\n
        'beta'调制指数(FM)\n
        等参数'''
        Bw = params.get('Bw', 100)
        f_mod = params.get('f', 10)
        Cf = params.get('Cf', 1e9)
        Sr = params.get('Sr', 1000)
        time_span = params.get('SDuration',10)
        t = np.arange(0, time_span, 1/Sr)
        if modulation_type == "CW":
            #模拟连续波信号
            #以余弦信号为例
            signal = np.cos(2 * np.pi * freq * t)
        elif modulation_type == "AM":
            #模拟幅度调制信号
            m = 0.5 
            # 调制波 (包络)
            modulating_wave = 1 + m * np.cos(2 * np.pi * f_mod * t)
            # 载波
            carrier_wave = np.cos(2 * np.pi * freq * t)
            # 相乘得到 AM 信号
            signal = modulating_wave * carrier_wave
        elif modulation_type == "FM":
            #模拟频率调制信号
            beta = 5.0 
            # 瞬时相位 = 载波相位 + 调制引起的相位偏移
            phase = 2 * np.pi * freq * t + beta * np.sin(2 * np.pi * f_mod * t)
            signal = np.cos(phase)
        return t,signal
class sender():
    def __init__(self):
        pass
    
    def send(self,target:str,**data:dict):
        '''
        **target**:主控节点的IP地址\n
        **data**:可添加测向节点的IP地址、测向结果、时间戳、端口号\n
        ```
        ip = target_ip, angle = measured_angle,time = time.time(),port = target_port\n
        ```
        **注意**:其中angle为目标方向与x轴正方向的夹角
        '''
        print(f"向主控节点{target}发送数据: {data}")
        machine = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        machine.connect((target,data.get("port",9999)))
        machine.send(str(data).encode())
        
##测试脚本如下
if __name__ == "__main__":
    '''
    s = sender()
    hostip = socket.gethostbyname(socket.gethostname())
    targetip = "10.68.194.42" #测试用ip地址,应编写程序使此ip地址在程序运行后手动输入
    simulated_angle = calculator.calculate()
    s.send(target = targetip,ip = hostip,angle = simulated_angle,time = time.time(),port = 9999)
    '''
    cal = calculator()
    cal.calculate(freq = 1,loc = [0,0],v = [1,1],a=[1,1])
    cal.calculate(motion_type= 'circle',center = [0,0],radius = 1,theta = 0,w = 1)
    '''
    b = base(1,8,1)
    Xt = b.signal_construct(0,[-50,5,40])
    ma = b.find_peak_angle(Xt)
    angle = b.measure_angle_local_search(Xt,ma)
    print(angle)
    '''