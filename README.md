#  kgather
一组对kubernetes集群进行批量信息收集的脚本，帮助在kubernetes集群渗透中快速获取有用信息。

k8s_nodes_info_gather：通过Deamonset对集群内所有node均创建一个挂载根目录的pod，通过chroot实现在node上的信息收集。过程如下：
1. 获取所有node的基础信息
2. 创建Daemonset，设置tolerations的key为空，operator为Exists，表示可以接受任意污点，这样Daemonset会在所有的node都创建一个pod，包括master，并且挂载node的根目录到pod中。
3. 获取Daemonset下的所有pod，遍历在每个pod中执行命令，并且chroot 到挂载的根目录，相当于在node上执行命令。


k8s_pods_info_gather：对集群内所有pod执行一组命令，进行信息收集。过程如下：
1. 获取所有pods
2. 遍历对每个pod执行一组命令。


# 使用
对所有node执行信息收集：把kubectl和k8s_nodes_info_gather.py放置同一目录
```
python3 k8s_nodes_info_gather.py
```

对所有pod执行信息收集：把kubectl和k8s_pods_info_gather.py放置同一目录
```
python3 k8s_pods_info_gather.py
```

需要自定义执行的命令的，可以修改脚本中的cmds。
