###测向节点###
#根据主控节点下发的目标状态和信号参数生成阵列接收数据
#分别完成两个测向站的阵列信号处理
#实现波束的形成、频谱分析、双波束比辐侧向
#将每个时刻两个站的测角结果通过TCP/IP协议发送给主控节点==>部分完成

import numpy as np
import socket,math,time,threading
import time

c = 299792458

class base():
    def __init__(self,number:int,element:int = 8,ele_distance:float = 1.0):
        self.element_num = element
        self._ele_distance = ele_distance
        self._number = number

    def signal_construct_one(self,target_number:int,theta:float,s:float,lamda:float = 2.0,):
        alpha = np.ones(self.element_num, dtype=complex)
        for i in range(self.element_num-1):
            alpha[i+1]=alpha[i]*np.exp(1j*2*math.pi*self._ele_distance*math.sin(math.radians(theta))/lamda)
        print(alpha)
        X = alpha*s
        return X
    
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
    
    def signal_construct(self,target:int,theta:list):
        X = []
        for i in range(len(theta)):
            X.append(self.signal_construct_one(target,theta[i],1))
        print(X)
        Xt=np.zeros(self.element_num, dtype=complex)
        for i in range(len(theta)):
            Xt+=X[i]
        print(Xt)
        Xt = Xt+self.Gauss_noise_gen(10)
        print(Xt)
        return Xt
class calculator():
    def __init__(self):
        pass
    
    def calculate(self,motion_type = "line",freq:float = c/2,modulation_type:str = 'CW',**params):
        '''motion_type:目标运动类型，可选'line'或'circle'\n
        freq:发射频率\n
        modulation_type:调制方式，可选'CW','AM'或'FM'\n
        params:其它参数。如果运动类型为'line',则需要给出'loc':初位置,和'v'初速度,两个量都是二维向量;如果运动类型为'circle',则需要给出给出参数'center'圆心坐标,'radius':半径和'w':角速度\n
        此外,还可以提供:'Cf':载频,\n
        'Sr':'采样率',\n
        'Bw':'带宽',\n
        'f':'调制频率',\n
        'SDuration':'信号时长'\n
        等参数'''
        #return np.random.uniform(0,360)  #测试用,应编写程序根据主控节点的参数生成阵列接收数据并计算测角结果
        if type == "line":
            #模拟目标运动为直线运动
            pass
        if type == "circle":
            #模拟目标运动为圆周运动
            pass
            
        if modulation_type == "CW":
            #模拟连续波信号
            pass
        if modulation_type == "AM":
            #模拟幅度调制信号
            pass
        if modulation_type == "FM":
            #模拟频率调制信号
            pass
    
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
        **注意**:其中angle为以正北为基准,向东为正方向转过的角度。
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
    cal.calculate(motion_type= 'line',freq = 1,modulation_type = 'FM',loc = (0,0),v = (1,1))
    b = base(1,8,1)
    b.signal_construct(0,[30,45,60])
    