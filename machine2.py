###测向节点###
#根据主控节点下发的目标状态和信号参数生成阵列接收数据
#分别完成两个测向站的阵列信号处理
#实现波束的形成、频谱分析、双波束比辐侧向
#将每个时刻两个站的测角结果通过TCP/IP协议发送给主控节点

import numpy as np
import matplotlib.pyplot as plt
import socket,math,time,threading

class calculator():
    def __init__(self):
        pass
    
    def calculate(self):
        return np.random.uniform(0,360)  #测试用,应编写程序根据主控节点的参数生成阵列接收数据并计算测角结果
    
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
    calculator = calculator()
    sender = sender()
    hostip = socket.gethostbyname(socket.gethostname())
    targetip = "10.68.194.42" #测试用ip地址,应编写程序使此ip地址在程序运行后手动输入
    simulated_angle = calculator.calculate()
    sender.send(target = targetip,ip = hostip,angle = simulated_angle,time = time.time(),port = 9999)
    