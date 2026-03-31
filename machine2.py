###测向节点###
#根据主控节点下发的目标状态和信号参数生成阵列接收数据
#分别完成两个测向站的阵列信号处理
#实现波束的形成、频谱分析、双波束比辐侧向
#将每个时刻两个站的测角结果通过TCP/IP协议发送给主控节点==>部分完成

import numpy as np
import matplotlib.pyplot as plt
import socket,math,time,threading,json
from scipy.signal import find_peaks
from random import randint

c = 299792458

class base():
    def __init__(self,id:int,element:int = 8,ele_distance:float = 1.0,host_id:str = "127.0.0.1"):
        self.element_num = element
        self._ele_distance = ele_distance
        self._id = id
        self.host_id = host_id

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
    
    def signal_construct(self,target:int,theta:list,s:list=[1,1,1]):
        X = []
        alpha = []
        #y = []
        for i in range(len(theta)):
            Xi,alphai = self.signal_construct_one(i,theta[i],s[i])
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
    
    def find_peak_angles(self, Xt, search_range=(-60, 60), step=0.1, min_prominence=0.15):
        """
        参数:
        Xt: 接收信号快拍 (阵列协方差矩阵或数据向量)
        search_range: 搜索范围，默认 (-60, 60)
        step: 搜索步长，越小精度越高但计算越慢
        min_prominence: 最小相对显著度 (0-1)，用于过滤噪声和小杂波
                    值越大，筛选越严格，只留最强峰；值越小，越容易检测到弱目标
        """
        # 1. 扫描全空域，计算空间谱
        thetas = np.arange(search_range[0], search_range[1], step)
        powers = []
        
        for theta in thetas:
            a = self.generate_alpha(theta)
            # 波束形成权值
            response = np.dot(a.conjugate(), Xt)
            # 功率谱
            power = np.abs(response) ** 2
            powers.append(power)
        
        powers = np.array(powers)
        
        # 2. 设置动态阈值
        # 这里的逻辑是：只要峰值高度超过“最高峰的 min_prominence 倍”，就算作有效目标
        # 比如 min_prominence=0.1，意味着只要高度超过最高峰的 10%，就被认为是目标
        global_max_power = np.max(powers)
        height_threshold = global_max_power * min_prominence
        
        # 3. 使用 find_peaks 寻找所有局部最大值
        # prominence: 显著度，防止把噪声毛刺当成目标
        # distance: 两个峰之间至少间隔多少个点，防止重复检测同一个目标
        # height: 只有高于阈值的峰才会被保留
        peak_indices, properties = find_peaks(
            powers, 
            height=height_threshold, 
            prominence=height_threshold * 0.5, # 显著度设为阈值的一半
            distance=int(5 / step)             # 假设目标最小间隔 5 度
        )
        
        # 4. 提取角度
        detected_angles = thetas[peak_indices]
        
        # 5. 按能量从大到小排序（可选，方便查看）
        # 根据 properties['peak_heights'] 进行排序
        sorted_indices = np.argsort(properties['peak_heights'])[::-1]
        final_angles = detected_angles[sorted_indices]
        final_powers = powers[peak_indices][sorted_indices]
        
        print(final_angles)
        
        
        
        # 可视化验证
        plt.figure(figsize=(10, 5))
        plt.plot(thetas, powers, label='Beam Pattern Power')
        for i in range(len(final_angles)):
            plt.axvline(final_angles[i], color='r', linestyle='--', label=f'Peak @ {final_angles[i]:.2f}°')
        plt.xlabel('Angle (deg)')
        plt.ylabel('Power')
        plt.title('Sum Beam Pattern - Finding Peak')
        plt.legend()
        plt.grid(True)
        plt.show()
        return final_angles, final_powers
    
    def measure_angle_local_search(self, Xt:np.ndarray, coarse_angle:float|np.float32, search_width=10):
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
        y1_actual = np.dot(w_sum.conjugate().T, Xt)
        y2_actual = np.dot(w_diff.conjugate().T, Xt)
        if np.abs(y1_actual) < 1e-10:
            return coarse_angle  # 返回粗略角度作为估计结果
        # 这里用差/和的比值，比 (F1-F2)/(F1+F2) 更敏感
        # 且利用复数相位判断方向
        ratio_actual = y2_actual / y1_actual 
        #b = np.abs(ratio_actual)
        
        # 3. 局部扫描生成理论曲线 k(theta) (公式 3-2)
        thetas = np.linspace(coarse_angle - search_width, coarse_angle + search_width, 1000)
        k_values = []
        
        for theta in thetas:
            a = self.generate_alpha(theta)
            # 使用同样的偏置权向量计算理论响应
            F1 = np.abs(np.dot(w_sum.conjugate(), a))
            F2 = np.abs(np.dot(w_diff.conjugate(), a))
            
            # 理论比值
            '''
            if np.abs(F1) >1e-10:
                ratio_theory = F2 / F1 # 对应差/和
                error = np.abs(ratio_actual-ratio_theory)
                if error < min_error:
                    min_error = error
                    estimated_angle = theta
                    '''
            if F1 > 1e-10:
                k = F2 / F1
            else:
                k = 0
            k_values.append(k)
        k_values = np.array(k_values)

        # 4. 查表匹配
        min_idx = np.argmin(np.abs(k_values - ratio_actual))
        estimated_angle = thetas[min_idx]
        
        # 5. 符号修正（利用相位）
        #if np.angle(ratio_actual) < 0:
             # 如果相位为负，说明在左边，需要微调（这里简化处理，主要靠查表）
             #pass 

        print(f"中心角度: {coarse_angle:.2f}°")
        print(f"实测比值 b: {np.abs(ratio_actual):.4f}")
        print(f"估计角度: {estimated_angle:.2f}°")
        
        return estimated_angle
    
    def send_data(self,send_interval=0.1,ip:str = "127.0.0.1", angle:np.ndarray = np.zeros(0),t:np.ndarray = np.zeros(0),port:int = 9999):
        '''
        **send_interval**:发送数据的时间间隔，单位为秒\n
        **ip**:主控节点的ip地址\n
        **angle**:测角结果\n
        **t**:对应的时间戳\n
        **port**:主控节点监听的端口号\n
        **注意**:其中angle为目标方向与x轴正方向的夹角
        '''
        try:
            self.machine = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.machine.connect((self.host_id,port))
            for i in range(len(angle)):
                message = {
                    "station_id": ip,
                    "target_id": 0,
                    "timestamp": t[i],
                    "angle": angle[i]
                }
                print(f"向主控节点{self.host_id}发送数据: {message}")
                message = json.dumps(message)
                self.machine.send(message.encode("utf-8"))
                time.sleep(send_interval)
        except Exception as e:
            print(f"发送数据时发生错误: {e}")
        finally:
            try:
                self.machine.close()
            except Exception as e:
                print(f"关闭连接时发生错误: {e}")
            print("数据发送完成，连接已关闭。")
    
    def start_signal_processing(self,target_num:int = 1,**params):
        '''开始信号处理流程\n
        1.根据主控节点下发的目标状态和信号参数生成阵列接收数据\n
        2.完成波束的形成、频谱分析、双波束比辐侧向\n
        3.将每个时刻两个站的测角结果通过TCP/IP协议发送给主控节点\n
        params:{
            0:{},
            1:{},
            ...}'''
        try:
            self.machine = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.machine.connect((self.host_id,params.get('port',9999)))
        except Exception as e:
            print(f"连接主控节点时发生错误: {e}")
            return
        config = self.machine.recv(1024) #等待主控节点发送开始信号
        config = json.loads(config.decode("utf-8"))
        print(f"接收到主控节点的配置: {config}")
        cal = calculator()
        t = np.arange(0, params.get('SDuration',10), 1/params.get('Sr',1000))
        real_angle = []
        estimated_angle = []
        estimated_angles = {}
        for target_id in sorted(params.keys()):
            t,positions = cal.calculate(params.get(target_id,{}))
            for i in range(len(t)):
                real_angle.append(np.degrees(np.atan2(positions[i][1],positions[i][0])))
                Xt = self.signal_construct(i,real_angle[i],s=[1,1,1])
                ma,mp = self.find_peak_angles(Xt)
                ###这里逻辑有点乱
                ###现在写的是按目标编号逐个生成实际角度，然后生成实际角度，再生成测量的角度，按编号分类，统一打包发给主控节点；
                ###但实际应该是按编号逐个生成实际角度和波形，再生成某一时刻测量到的角度和波形，把测量的角度和波形按时间打包发给主控节点，主控节点根据波形给角度标号
                if len(ma) > 0:
                    anglei = self.measure_angle_local_search(Xt,ma[0])
                    estimated_angle.append((anglei,t[i]))##这样得到的estimated_angle是一个列表，包含了该目标在每个时刻的测量角度(列表)和对应的时间戳的元组
                else:
                    estimated_angle.append(0)
                estimated_angles[str(target_id)]=(estimated_angle) #这样操作之后，得到的estimated_angles是一个字典，键是目标编号，值是一个列表，包含了该目标在每个时刻的测量角度
                estimated_angle.clear()
        self.send_data(ip = self.host_id,angle = np.array(estimated_angles),t = t,port = params.get('port',9999))
        
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
    def emision(self,function,modulation_type:str = 'CW',freq:float = c/2,**params):
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
            

def start_simulation(base_num:int = 2,element_num:list = [8,8],ele_distance:list = [1.0,1.0],host_id:str = "127.0.0.1",tport  = 9999):
    bases = []
    bases_thread = []
    for i in range(base_num):
        bases.append(base(i,element_num[i],ele_distance[i],host_id))
        bases_thread.append(threading.Thread(
            target=bases[i].start_signal_processing,
            kwargs = {
                "port":tport,
            }
        ))
        bases_thread[i].start()
    for i in range(base_num):
        bases_thread[i].join()
        
##测试脚本如下
if __name__ == "__main__":
    '''
    s = sender()
    hostip = socket.gethostbyname(socket.gethostname())
    targetip = "10.68.194.42" #测试用ip地址,应编写程序使此ip地址在程序运行后手动输入
    simulated_angle = calculator.calculate()
    s.send(target = targetip,ip = hostip,angle = simulated_angle,time = time.time(),port = 9999)
    '''
    '''
    cal = calculator()
    cal.calculate(freq = 1,loc = [0,0],v = [1,1],a=[1,1])
    cal.calculate(motion_type= 'circle',center = [0,0],radius = 1,theta = 0,w = 1)
    '''
    ''''''
    '''
    b = base(1,8,1)
    real = [randint(-55,-20),randint(-20,20),randint(20,55)]
    Xt = b.signal_construct(0,real)
    ma,mp = b.find_peak_angles(Xt)
    angle = []
    for a in range(len(ma)):
        anglei = b.measure_angle_local_search(Xt,ma[a])
        angle.append(anglei)
    print(real)
    print(np.array(angle))
    '''
    start_simulation(host_id=socket.gethostbyname(socket.gethostname()))