####主控节点###
#负责系统参数和调制参数的设置
#负责目标运动轨迹的生成
#负责辐射源波形的生成
#接收两个侧向站上传的测角结果==>已经实现从一个侧向站接收。考虑通过多线程同时接收两个侧向站的测角结果
#进行双站交叉定位==>calculator.calculate()函数已经实现根据角度计算目标坐标,应继续编写程序将角度数据从接收到的数据中取出传递给给该数据。目前计划将两个测向节点的数据分别存储在两个列表中，根据时间戳的先后顺序排序并依次取出进行交叉定位,如果某个时刻只有一个测向站的数据则暂不进行定位，后续再进行插值处理。
#显示真实轨迹与定位轨迹
#统计并分析定位误差

import numpy as np
import matplotlib.pyplot as plt
import socket,math,time

class reciever():
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
    
class calculator():
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
        
def drawplt():
    '''绘制目标的真实轨迹和定位轨迹'''
    pass

###测试脚本如下
if __name__ == "__main__":
    print("主控节点正在运行,ip地址为:",socket.gethostbyname(socket.gethostname()))
    #reciever.listen(port = 9999)
    calculator = calculator()
    location = calculator.calculate(angle1 = math.radians(30.0),angle2 = math.radians(300.0),distance = 100.0)
    print("目标的坐标为:",location)