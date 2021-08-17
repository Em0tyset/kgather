# coding=utf-8
# @Time: 2021/8/17
# @Author: em0ty
# 对集群内所有pod执行一组命令，进行信息收集

import os
import time
import argparse

# 命令列表，需要执行的命令在这里添加。
cmds = [
    "pwd",
    "ls -al",
    "mount",
    "cat ~/.bash_history",
    "env",
    "whoami",
    "cat /etc/passwd",
    "ps -ef",
    "netstat -atunp",
    "ls -al /tmp",
 ]
config = ""
out_file = ""
screen = ""
test = ""

# 把结果写入文件
def write_results(results):
    with open(out_file, "a") as f:
        for result in results:
            f.writelines(result + "\n")

# 获取pods信息
def get_pods():
    result = []
    cmd = "kubectl --kubeconfig {config} get pods -A -o wide --field-selector status.phase=Running".format(
        config=config)
    try:
        cmd_out = os.popen(cmd).read().strip()
        if screen:
            print("执行命令：", cmd)
            print("输出结果：", cmd_out)
        tmps = cmd_out.split("\n")
        for tmp in tmps[1:]:
            while "  " in tmp:
                tmp = tmp.replace("  ", " ")
            data = tmp.split(" ")
            result.append(
                {
                    "namespace":data[0],
                    "name":data[1],
                    "node":data[6]
                }
            )
        return result
    except Exception as e:
        print(e)
        print("[-]    获取pods失败")
        os._exit(-1)

def pods_info_gatehr(pods):
    cmd_tpl = "kubectl --kubeconfig {config}  -n {namespace}  exec {pod_name} -- {cmd}"
    for pod in pods:
        namespace = pod["namespace"]
        pod_name = pod["name"]
        node = pod["node"]
        results = []
        if test:
            for tmp_cmd in cmds:
                cmd = cmd_tpl.format(config=config, namespace=namespace,
                                     pod_name=pod_name, cmd=tmp_cmd)
                print("执行命令：", cmd)
        else:
            write_results(["[+]开始收集：pod:{pod_name},node:{node},namespace:{namespace}的信息".format(
                pod_name=pod_name, node=node, namespace=namespace
            )])
            for tmp_cmd in cmds:
                cmd = cmd_tpl.format(config=config, namespace=namespace,
                                     pod_name=pod_name,cmd=tmp_cmd)
                try:
                    cmd_out = os.popen(cmd).read()
                    if screen:
                        print("执行命令：", cmd)
                        print("输出结果：", cmd_out)
                    result = "pod:{pod_name}，namespace:{namespace}，node:{node}\n命令：{cmd}\n结果：\n{cmd_out}".format(
                        pod_name=pod_name,
                        namespace=namespace,
                        node=node,
                        cmd=tmp_cmd,
                        cmd_out=cmd_out)
                except Exception as e:
                    result = "pod_name:{pod_name}，namespace:{namespace}，node:{node}执行命令出错：{cmd}".format(
                        pod_name=pod_name,
                        namespace=namespace,
                        node=node,
                        cmd=tmp_cmd
                    )
                results.append(result)
            write_results(results)
            print("[+]   完成pod:{pod_name}，namespace:{namespace}，node:{node}的信息获取".format(
                pod_name=pod_name,namespace=namespace,node=node))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config",
                        help='kubeconfig配置文件位置，默认使用~/.kube/config',
                        default="~/.kube/config")
    parser.add_argument("-o", "--out", help='输出文件，默认为./{time}_podinfo_out.txt',
                        default=time.strftime("%Y-%m-%d_%H:%M:%S_podinfo_out.txt", time.localtime()))
    parser.add_argument("-s", "--screen", help='结果同时输出到屏幕', action="store_true")
    parser.add_argument("-t", "--test", help='测试模式，仅输出收集信息的命令不实际执行，判断命令是否正确。', action="store_true")
    args = parser.parse_args()

    config = args.config
    out_file = args.out
    screen = args.screen
    test = args.test
    print("[+] 开始 ")
    pods = get_pods()
    print("[+] 获取到running状态的pods个数：",len(pods))
    pods_info_gatehr(pods)
    if test:
        print("[+]  测试模式结束")
    else:
        print("[+]  结果已输出到文件：", out_file)