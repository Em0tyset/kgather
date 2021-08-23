# coding=utf-8
# @Time: 2021/8/19
# @Author:em0ty
# 批量获取memcached数据

import socket
import argparse
import time

out_file = ""
screen = ""

def write(content):
    if screen:
        print(content)
    with open(out_file,"a") as f:
        f.write(content)


def get_datas(client,end='END'):
    datas = ''
    while True:
        tmp = client.recv(1024)
        datas = datas + tmp.decode()
        if datas.strip().endswith(end):
            break
    datas = datas.strip().split('\n')
    return datas[:-1]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--ip", help='ip，默认为127.0.0.1',default='127.0.0.1')
    parser.add_argument("-p", "--port", help='端口，默认为11211', default=11211, type=int)
    parser.add_argument("-l", "--limit", help='每个slab查询最大数据量，默认是100条，输入0代表获取全部', default=100, type=int)
    parser.add_argument("-o", "--out", help='输出文件，默认为./{ip}_{port}_{time}.txt',default="")
    parser.add_argument("-s", "--screen", help='结果同时输出到屏幕', action="store_true")
    args = parser.parse_args()

    ip = args.ip
    port = args.port
    limit = args.limit
    out_file = args.out
    screen = args.screen
    if out_file == '':
        out_file = time.strftime("{ip}_{port}_%Y-%m-%d_%H-%M-%S_out.txt", time.localtime()).format(ip=ip,port=str(port))

    print('[+] memcached连接地址：',ip,port)
    # 请求超时
    socket.setdefaulttimeout(5)
    address = (ip,port)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(address)

    # 获取版本
    client.send('version\r\n'.encode())
    version = client.recv(1024)
    write('memcached版本：'+version.decode())

    # 获取slabs和items数量
    slbas_result = set()
    client.send('stats items\r\n'.encode())
    slbas = get_datas(client)

    for slab in slbas:
        item = slab.split(' ')
        if item[1].strip().endswith('number'):
            slab_id = item[1].split(':')[1].strip()
            item_sum = item[2].strip()
            slbas_result.add((slab_id,item_sum))
    write('slab数量：{slab_sum}\n'.format(slab_sum=str(len(slbas_result))))

    # 获取slab下的key
    write("开始获取数据，每个slab最大获取数量：{limit}\n".format(limit=str(limit)))
    for slab in slbas_result:
        keys_result = []
        slab_id = slab[0]
        item_sum = slab[1]
        write("slab_id：{slab_id}，item数量：{item_sum}\n".format(
            slab_id=slab_id,item_sum=item_sum
        ))
        client.send('stats cachedump {slab_id} {limit}\r\n'.format(
            slab_id=slab_id,limit=limit
        ).encode())
        tmp_keys = get_datas(client)
        for tmp_key in tmp_keys:
            keys_result.append(tmp_key.split(' ')[1])
        for key in keys_result:
            client.send('get {key}\r\n'.format(key=key).encode())
            tmp_value = get_datas(client)
            value = tmp_value[1].strip()
            bit = tmp_value[0].strip().split(' ')[-1]
            write("key: {key} 大小：{bit}字节\nvalue={value} \n\n\n\n".format(
                key=key,bit=bit,value=value
            ))
        write('---------------slab split----------------')

    # 退出
    client.send('quit\r\n'.encode())
    client.close()
    print("收集完毕，结果输出到文件：",out_file)