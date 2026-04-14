Cluster相关接口
更新时间：2026-01-13
创建集群
描述

创建 CCE K8S 集群

请求结构

Plain Text复制
POST /v2/cluster HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
cluster	ClusterSpec	是	RequestBody 参数	集群配置
masters	List<InstanceSet>	否	RequestBody 参数	集群 Master 配置, 支持异构组合. 当集群类型为托管型时无需设置该参数
nodes	List<InstanceSet>	否	RequestBody 参数	集群 Worker 配置, 支持异构组合. 不设置此参数时将会创建仅有master的集群
options	CreateClusterOptions	是	RequestBody 参数	集群创建选项. 用户可以设置强制跳过网段冲突检查
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
clusterID	String	是	集群 ID
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例: 托管 Master 集群

设置 cluster.masterConfig 的 masterType 设为 managed
无需设置 masters 参数
其它参数参考 API 文档按需设置
Plain Text复制
POST /v2/cluster  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
    "cluster":{
        "clusterName":"test-open-types",
        "k8sVersion":"1.16.8",
        "runtimeType":"docker",
        "vpcID":"vpc-mwbgygrjb72w",
        "masterConfig":{
            "masterType":"managed",
            "clusterHA":1,
            "exposedPublic":false,
            "clusterBLBVPCSubnetID":"sbn-mnbvhnuupv1u",
            "managedClusterMasterOption":{
                "masterVPCSubnetZone":"zoneA"
            }
        },
		"containerNetworkConfig": {
			"mode": "kubenet",
			"lbServiceVPCSubnetID": "sbn-mnbvhnuupv1u",
			"clusterPodCIDR": "172.28.0.0/16",
			"clusterIPServiceCIDR": "172.31.0.0/16"
		},
		"k8sCustomConfig": {
			"kubeAPIQPS": 1000,
			"kubeAPIBurst": 2000
		}
    },
    "nodes":[
        {
            "instanceSpec":{
                "instanceName":"instance-name",
                "clusterRole":"node",
                "existed":false,
                "machineType":"BCC",
                "instanceType":"N3",
                "vpcConfig":{
                    "vpcID":"vpc-mwbgygrjb72w",
                    "vpcSubnetID":"sbn-mnbvhnuupv1u",
                    "availableZone":"zoneA",
                    "securityGroup": {
                      "customSecurityGroups": [],
                      "enableCCERequiredSecurityGroup": true,
                      "enableCCEOptionalSecurityGroup": true
                    }
                },
                "instanceResource":{
                    "cpu":4,
                    "mem":8,
                    "rootDiskSize":40,
                    "localDiskSize":0,
                    "cdsList":[]
                },
                "imageID":"m-gTpZ1k6n",
                "instanceOS":{
                    "imageType":"System",
                    "osType":"linux",
                    "osName":"CentOS",
                    "osVersion":"7.5",
                    "osArch":"x86_64 (64bit)"
                },
                "needEIP":false,
                "adminPassword":"test123!T",
                "instanceChargingType":"Postpaid",
                "runtimeType":"docker"
            },
            "count":1
        }
    ]
}
请求示例: 自定义 Master 集群

设置 cluster.masterConfig 的 masterType 设为 custom
设置 masters 参数
其它参数参考 API 文档按需设置
Plain Text复制
{
    "cluster":{
        "clusterName":"create-custom-cluster-reg",
        "description":"集群描述",
        "k8sVersion":"1.16.8",
        "runtimeType":"docker",
        "vpcID":"vpc-43zsdm46t9rp",
        "masterConfig":{
            "masterType":"custom",
            "exposedPublic":true,
            "clusterBLBVPCSubnetID":"sbn-vvqsb9b57f24"
        },
        "containerNetworkConfig":{
            "mode":"kubenet",
            "lbServiceVPCSubnetID":"sbn-vvqsb9b57f24",
            "nodePortRangeMin":50000,
            "nodePortRangeMax":51000,
            "clusterPodCIDR":"10.2.0.0/16",
            "clusterIPServiceCIDR":"172.16.0.0/16",
            "maxPodsPerNode":64,
            "kubeProxyMode":"ipvs"
        }
    },
    "masters":[
        {
            "instanceSpec":{
                "machineType":"BCC",
                "instanceType":"N3",
                "vpcConfig":{
                    "vpcSubnetID":"sbn-vvqsb9b57f24",
                    "securityGroup": {
                      "customSecurityGroups": [],
                      "enableCCERequiredSecurityGroup": true,
                      "enableCCEOptionalSecurityGroup": true
                    }
                },
                "instanceResource":{
                    "CPU":4,
                    "MEM":8
                },
                "instanceOS": {
                    "imageName": "7.5 x86_64 (64bit)",
                    "imageType": "System",
                    "osType": "linux",
                    "osName": "CentOS",
                    "osVersion": "7.5",
                    "osArch": "x86_64 (64bit)"
                },
                "adminPassword":"test123!T"
            },
            "count":1
        }
    ],
    "nodes":[
        {
            "instanceSpec":{
                "machineType":"BCC",
                "instanceType":"N3",
                "vpcConfig":{
                    "vpcSubnetID":"sbn-vvqsb9b57f24",
                    "securityGroupID":"g-k4tsm0id2g1n"
                },
                "instanceResource":{
                    "CPU":4,
                    "MEM":8,
                    "cdsList":[
                        {
                            "diskPath":"/data",
                            "storageType":"cloud_hp1",
                            "cdsSize":200
                        }
                    ]
                },
                "instanceOS": {
                    "imageName": "7.5 x86_64 (64bit)",
                    "imageType": "System",
                    "osType": "linux",
                    "osName": "CentOS",
                    "osVersion": "7.5",
                    "osArch": "x86_64 (64bit)"
                },
                "adminPassword":"test123!T"
            },
            "count":1
        }
    ]
}
请求示例: 已有实例

如果 Master 需要使用已有实例，设置 cluster.masterConfig 的 masterType 设为 custom
添加 Master 或 Node 机器配置时，设置 instanceSpec.existed 为 true 并设置 instanceSpec.existedOption.existedInstanceID 为希望使用的已有节点 ID
如果不希望重装系统，设置 instanceSpec.existedOption.rebuild 为 false 并务必保证机器密码正确，否则节点会因无法部署相关服务而创建失败
如果不希望重装系统，无需设置 instanceSpec.instanceOS 与 instanceSpec.machineType
其它参数参考 API 文档按需设置
Plain Text复制
{
    "cluster":{
        "clusterName":"create-existed-bcc-cluster-reg",
        "description":"集群描述",
        "k8sVersion":"1.16.8",
        "runtimeType":"docker",
        "vpcID":"vpc-43zsdm46t9rp",
        "masterConfig":{
            "masterType":"custom",
            "exposedPublic":true,
            "clusterBLBVPCSubnetID":"sbn-vvqsb9b57f24"
        },
        "containerNetworkConfig":{
            "mode":"kubenet",
            "lbServiceVPCSubnetID":"sbn-vvqsb9b57f24",
            "nodePortRangeMin":30000,
            "nodePortRangeMax":32768,
            "clusterPodCIDR":"10.0.0.0/16",
            "clusterIPServiceCIDR":"172.16.0.0/16",
            "maxPodsPerNode":256,
            "kubeProxyMode":"ipvs"
        }
    },
    "masters":[
        {
            "instanceSpec":{
                "existed":true,
                "existedOption":{
                    "existedInstanceID":"i-SxeBLkcN",
                    "rebuild":true
                },
                "machineType":"BCC",
                "instanceOS": {
                    "imageName": "7.5 x86_64 (64bit)",
                    "imageType": "System",
                    "osType": "linux",
                    "osName": "CentOS",
                    "osVersion": "7.5",
                    "osArch": "x86_64 (64bit)"
                },
                "adminPassword":"test123!T"
            }
        }
    ],
    "nodes":[
        {
            "instanceSpec":{
                "existed":true,
                "existedOption":{
                    "existedInstanceID":"i-M56Un1DO",
                    "rebuild":true
                },
                "machineType":"BCC",
                "instanceOS": {
                    "imageName": "7.5 x86_64 (64bit)",
                    "imageType": "System",
                    "osType": "linux",
                    "osName": "CentOS",
                    "osVersion": "7.5",
                    "osArch": "x86_64 (64bit)"
                },
                "adminPassword":"test123!T"
            }
        }
    ]
}
请求示例：挂载CDS
有时我们希望在新建节点的同时为节点挂载 1 到多个 CDS，此时在创建集群时，为节点设置 CDS 参数和相关挂载路径即可。示例如下。
需要注意的是，每个路径下只能挂载一个 CDS，但一个路径的子路径下可以挂载另一个 CDS，例如 /a 目录下仅可挂载一个 CDS，但 /a/b 目录下可以挂载另一个 CDS。
已有节点仅可挂载 CDS 到指定路径，不会新建 CDS。因此当已有节点试图挂载 CDS 到指定 Path 但找不到满足条件的 CDS 时，将会忽略相关 CDS 配置。

Plain Text复制
{
    ......
    
    "masters":[
        {
            "instanceSpec":{
                ......
                "instanceResource": {
                    "cdsList": [
                         {diskPath: "/home/cce", storageType: "cloud_hp1", cdsSize: 50}
                     ] 
                },
                ......
            }
        }
    ],
    "nodes":[
        {
            "instanceSpec":{
                ......
                "instanceResource": {
                    "cdsList": [
                         {diskPath: "/home/cce", storageType: "cloud_hp1", cdsSize: 60}
                     ] 
                },
                ......
            }
        }
    ]
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
x-bce-request-id: d2ce8f50-529a-4663-9265-ad08c94633c8
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8
{
    "clusterID": "cce-NqYwWEhu",
    "requestID": "d2ce8f50-529a-4663-9265-ad08c94633c8"
}
集群列表
描述

查询用户 CCE K8S 集群列表

请求结构

Plain Text复制
GET /v2/clusters  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
keywordType	String	否	Query 参数	集群模糊查询字段，可选 [ clusterName, clusterID ]，默认值为 clusterName
keyword	String	否	Query 参数	查询关键词，默认值为空字符串
orderBy	String	否	Query 参数	集群查询排序字段，可选 [ clusterName, clusterID, createdAt ]，默认值为 clusterName
order	String	否	Query 参数	排序方式，可选 [ ASC, DESC ], ASC 为升序，DESC 为降序，默认值为 ASC
pageNo	Integer	否	Query 参数	页码，默认值为1
pageSize	Integer	否	Query 参数	单页结果数，默认值为10
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
描述
描述
clusterPage	ClusterPage	是	集群分页查询返回结果
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
GET /v2/clusters?keywordType=clusterName&keyword=&orderBy=clusterID&order=ASC&pageNo=1&pageSize=10  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 97342dc7-29a1-4ed9-a75d-904bb293d295
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"clusterPage": {
		"keywordType": "clusterName",
		"keyword": "",
		"orderBy": "clusterID",
		"order": "ASC",
		"pageNo": 1,
		"pageSize": 10,
		"totalCount": 1,
		"clusterList": [
			{
				"spec": {
					"clusterID": "cce-shpdaa9l",
					"clusterName": "sdk-ccev2-test",
					"clusterType": "normal",
					"description": "",
					"k8sVersion": "1.16.8",
					"vpcID": "vpc-aj2rcjm084y5",
					"vpcCIDR": "192.168.0.0/16",
					"plugins": [
						"ip-masq-agent",
						"core-dns",
						"kube-proxy",
						"metrics-server",
						"nvidia-gpu"
					],
					"masterConfig": {
						"masterType": "managed",
						"clusterHA": 1,
						"clusterBLBVPCSubnetID": "sbn-0dizryuc81c0",
						"managedClusterMasterOption": {
							"masterVPCSubnetZone": "zoneA"
						}
					},
					"containerNetworkConfig": {
						"mode": "kubenet",
						"ipVersion": "ipv4",
						"lbServiceVPCSubnetID": "sbn-0dizryuc81c0",
						"nodePortRangeMin": 30000,
						"nodePortRangeMax": 32767,
						"clusterPodCIDR": "172.28.0.0/16",
						"clusterIPServiceCIDR": "172.31.0.0/16",
						"maxPodsPerNode": 128,
						"kubeProxyMode": "ipvs"
					}
				},
				"status": {
					"clusterBLB": {
						"id": "lb-1454d5c4",
						"vpcIP": "100.64.230.44",
						"eip": ""
					},
					"clusterPhase": "running",
					"nodeNum": 0
				},
				"createdAt": "2020-09-04T01:58:12Z",
				"updatedAt": "2020-09-04T02:00:37Z"
			}
		]
	},
	"requestID": "97342dc7-29a1-4ed9-a75d-904bb293d295"
}
集群详情
描述

查询指定集群详情

请求结构

Plain Text复制
GET /v2/cluster/{clusterID} HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
cluster	Cluster	是	集群详情查询结果
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
GET /v2/cluster/cce-zyt88sqy  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 928a21b5-d117-4a83-a274-fd7d6f413524
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"cluster": {
		"spec": {
			"clusterID": "cce-shpdaa9l",
			"clusterName": "sdk-ccev2-test",
			"clusterType": "normal",
			"description": "",
			"k8sVersion": "1.16.8",
			"vpcID": "vpc-aj2rcjm084y5",
			"vpcCIDR": "192.168.0.0/16",
			"plugins": [
				"ip-masq-agent",
				"core-dns",
				"kube-proxy",
				"metrics-server",
				"nvidia-gpu"
			],
			"masterConfig": {
				"masterType": "managed",
				"clusterHA": 1,
				"clusterBLBVPCSubnetID": "sbn-0dizryuc81c0",
				"managedClusterMasterOption": {
					"masterVPCSubnetZone": "zoneA"
				}
			},
			"containerNetworkConfig": {
				"mode": "kubenet",
				"ipVersion": "ipv4",
				"lbServiceVPCSubnetID": "sbn-0dizryuc81c0",
				"nodePortRangeMin": 30000,
				"nodePortRangeMax": 32767,
				"clusterPodCIDR": "172.28.0.0/16",
				"clusterIPServiceCIDR": "172.31.0.0/16",
				"maxPodsPerNode": 128,
				"kubeProxyMode": "ipvs"
			}
		},
		"status": {
			"clusterBLB": {
				"id": "lb-1454d5c4",
				"vpcIP": "100.64.230.44",
				"eip": ""
			},
			"clusterPhase": "running",
			"nodeNum": 0
		},
		"createdAt": "2020-09-04T01:58:12Z",
		"updatedAt": "2020-09-04T02:00:37Z"
	},
	"requestID": "928a21b5-d117-4a83-a274-fd7d6f413524"
}
删除集群
描述

删除指定集群

请求结构

Plain Text复制
DELETE /v2/cluster/{clusterID} HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
deleteResource	Boolean	否	Query 参数	是否删除相关资源（后付费公网IP和云磁盘），默认值为 false
deleteCDSSnapshot	Boolean	否	Query 参数	是否删除云磁盘快照，默认值为 false
moveOut	Boolean	否	Query 参数	集群删除是否保留节点，默认值为 false
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
DELETE /v2/cluster/cce-uqc4lju1?deleteResource=true&deleteCDSSnapshot=true  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 105ce04b-1a42-4f77-9d22-ab6f413f9d69
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
    "requestID": "105ce04b-1a42-4f77-9d22-ab6f413f9d69"
}
更新集群删除保护开关
描述

更新集群删除保护开关

请求结构

Plain Text复制
PUT /v2/cluster/{clusterID}/forbiddelete HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
forbidDelete	Boolean	是	RequestBody 参数	是否打开或关闭集群删除保护，true为打开，false为关闭
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
success	Boolean	是	请求是否成功
forbidDelete	Boolean	是	集群删除保护状态，true为打开，false为关闭
请求示例

Plain Text复制
PUT v2/cluster/cce-5gw06fjs/forbiddelete HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
    "forbidDelete": false
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 3d61a898-b804-4d6f-8c7c-b741d2ffbe45
Date: Wed, 11 Dec 2024 02:59:18 GMT
Content-Type: application/json;charset=UTF-8

{
    "success": true,
    "forbidDelete": true
}
获取集群事件步骤
描述

获取创建或删除过程中集群所处的事件步骤。

请求结构

Plain Text复制
GET /v2/event/cluster/{clusterID} HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必选
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必选
描述
status	String	是	事件类型
steps	List<Step>	是	集群操作步骤
requestID	String	是	请求ID
请求示例

Plain Text复制
GET v2/event/cluster/cce-j8pb3dm0  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 08eb305a-87fb-4360-8a27-42b9561edf4a
Date: Fri, 12 Aug 2022 03:10:30 GMT
Content-Type: application/json;charset=UTF-8

{
    "status": "created",
    "steps": [
        {
            "stepName": "创建基础证书",
            "stepStatus": "done",
            "ready": true,
            "startTime": "2022-07-12T09:23:07Z",
            "finishedTime": "2022-07-12T09:23:07Z",
            "retryCount": 1,
            "errInfo": {}
        },
        {
            "stepName": "创建 BLB",
            "stepStatus": "done",
            "ready": true,
            "startTime": "2022-07-12T09:23:07Z",
            "finishedTime": "2022-07-12T09:23:16Z",
            "costSeconds": 9,
            "retryCount": 1,
            "errInfo": {}
        },
        {
            "stepName": "创建 EIP",
            "stepStatus": "done",
            "ready": true,
            "startTime": "2022-07-12T09:23:16Z",
            "finishedTime": "2022-07-12T09:23:25Z",
            "costSeconds": 9,
            "retryCount": 1,
            "errInfo": {}
        },
        {
            "stepName": "创建 Master",
            "stepStatus": "done",
            "ready": true,
            "startTime": "2022-07-12T09:23:25Z",
            "finishedTime": "2022-07-12T09:23:54Z",
            "costSeconds": 29,
            "retryCount": 1,
            "errInfo": {}
        },
        {
            "stepName": "连通 APIServer",
            "stepStatus": "done",
            "ready": true,
            "startTime": "2022-07-12T09:23:54Z",
            "finishedTime": "2022-07-12T09:25:52Z",
            "costSeconds": 118,
            "retryCount": 2,
            "errInfo": {}
        },
        {
            "stepName": "部署 K8S 插件",
            "stepStatus": "done",
            "ready": true,
            "startTime": "2022-07-12T09:25:53Z",
            "finishedTime": "2022-07-12T09:26:34Z",
            "costSeconds": 41,
            "retryCount": 1,
            "errInfo": {}
        }
    ],
    "requestID": "562c76ee-c65f-4673-9574-89222f1cd210"
}
更新集群 APIServer 证书 SAN
描述

自定义 API Server 证书 SAN（Subject Alternative Name）。 用于在集群 API Server 服务端证书的 SAN 字段中添加自定义的 IP 或域名，以实现对客户端的访问控制。

请求结构

Plain Text复制
PUT /v2/cluster/{clusterID}/apiservercertsan HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
configureAPIServerCertSAN	ConfigureAPIServerCertSAN	是	Request Body 参数	APIServer 证书 SAN 配置对象
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
success	Boolean	是	操作是否成功
workflowID	String	是	创建的工作流 ID，可用于查询操作进度
请求示例

Plain Text复制
PUT /v2/cluster/cce-f7zeyx1u/apiservercertsan HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
	"configureAPIServerCertSAN": {
		"clusterID": "cce-f7zeyx1u",
		"apiServerCertSAN": [
			"api.example.com",
			"192.168.1.100",
			"custom.domain.com"
		]
	}
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 27f91a44-7257-48e7-a8d8-849f45a32da4
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"success": true,
	"workflowID": "wf-abc123xyz"
}
配置集群 KMS 落盘加密
描述

为集群开启或关闭 KMS（Key Management Service）落盘加密功能。此功能仅支持托管集群且 Kubernetes 版本需为 v1.29 及以上。

请求结构

Plain Text复制
PUT /v2/cluster/{clusterID}/kmsencryption HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
configureKMSEncryption	ConfigureKMSEncryption	是	Request Body 参数	KMS 加密配置对象
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
success	Boolean	是	操作是否成功
workflowID	String	是	创建的工作流 ID，可用于查询操作进度
请求示例（开启 KMS 加密）

Plain Text复制
PUT /v2/cluster/cce-f7zeyx1u/kmsencryption HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
	"configureKMSEncryption": {
		"action": "enable",
		"kmsKeyID": "kms-key-abc123xyz"
	}
}
请求示例（关闭 KMS 加密）

Plain Text复制
PUT /v2/cluster/cce-f7zeyx1u/kmsencryption HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
	"configureKMSEncryption": {
		"action": "disable"
	}
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 27f91a44-7257-48e7-a8d8-849f45a32da4
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"success": true,
	"workflowID": "wf-def456uvw"
}

Autoscaler相关接口
更新时间：2026-04-13
查询 Autoscaler 配置
描述

查询集群 Autoscaler 配置。

请求结构

Plain Text复制
GET /v2/autoscaler/{clusterID}  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其他特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	Path 参数	已存在的集群 ID
返回头域

除公共头域外，无其他特殊头域。

返回参数

参数名称
类型
是否必须
描述
autoscaler	Autoscaler	是	查询到的 Autoscaler 信息
requestID	String	是	请求 ID，问题定位时请提供该 ID
请求示例

Plain Text复制
GET /v2/autoscaler/cce-uqc4lju1 HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 6836119a-99e1-4448-b469-1199c3fb1b07
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
    "autoscaler": {
        "clusterID": "cce-uqc4lju1",
        "clusterName": "sdk-ccev2-test2",
        "caConfig": {
            "replicaCount": 2,
            "scaleDownEnabled": true,
            "scaleDownUtilizationThreshold": 50,
            "scaleDownGPUUtilizationThreshold": 50,
            "scaleDownUnneededTime": 10,
            "scaleDownDelayAfterAdd": 10,
            "maxEmptyBulkDelete": 10,
            "skipNodesWithLocalStorage": true,
            "skipNodesWithSystemPods": false,
            "expander": "random",
            "customConfigs": {
                "--node-deletion-delay-timeout": "3m"
            }
        }
    },
    "requestID": "41d2b661-fe2f-4454-a017-5060795a0ac6"
}
创建 Autoscaler
描述

创建集群 Autoscaler。

请求结构

Plain Text复制
POST /v2/autoscaler/{clusterID}  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其他特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	Path 参数	已存在的集群 ID
返回头域

除公共头域外，无其他特殊头域。

返回参数

参数名称
类型
是否必须
描述
requestID	String	是	请求 ID，问题定位时请提供该 ID
请求示例

Plain Text复制
POST /v2/autoscaler/cce-uqc4lju1 HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: b339ba19-1a26-49f5-9cec-74b5a7a080c6
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"requestID": "b339ba19-1a26-49f5-9cec-74b5a7a080c6"
}
更新 Autoscaler 配置
描述

更新集群 Autoscaler 配置。

请求结构

Plain Text复制
PUT /v2/autoscaler/{clusterID}  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其他特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	Path 参数	已存在的集群 ID
expander	String	是	Body 参数	自动扩缩容选组策略。可选值：random、most-pods、least-waste、priority。默认值为 random。
instanceGroups	List<ClusterAutoscalerInstanceGroup>	否	Body 参数	节点组的 Autoscaler 配置。用户无需输入此项内容。
kubeVersion	String	否	Body 参数	K8S 版本。为空时，后台会自动查询集群 K8S 版本号。
maxEmptyBulkDelete	Integer	否	Body 参数	最大并发缩容数
scaleDownDelayAfterAdd	Integer	否	Body 参数	扩容后缩容启动时延，单位为分钟
scaleDownEnabled	Boolean	否	Body 参数	是否启用缩容。默认值为 false。
scaleDownGPUUtilizationThreshold	Integer	否	Body 参数	GPU 缩容阈值百分比，取值范围为 (0, 100)。
scaleDownUnneededTime	Integer	否	Body 参数	缩容触发时延，单位为分钟。
scaleDownUtilizationThreshold	Integer	否	Body 参数	缩容阈值百分比，取值范围为 (0, 100)。
skipNodesWithLocalStorage	Boolean	否	Body 参数	是否跳过使用本地存储的节点。默认值为 true。
skipNodesWithSystemPods	Boolean	否	Body 参数	是否跳过有部署系统 Pod 的节点。默认值为 true。
customConfigs	Map<String,String>	否	Body 参数	用户自定义配置。
返回头域

除公共头域外，无其他特殊头域。

返回参数

参数名称
类型
是否必须
描述
requestID	String	是	请求 ID，问题定位时请提供该 ID
请求示例

Plain Text复制
PUT /v2/autoscaler/cce-br0i4kl5 HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
    "scaleDownEnabled": true,
    "scaleDownUtilizationThreshold": 50,
    "scaleDownGPUUtilizationThreshold": 50,
    "scaleDownUnneededTime": 10,
    "scaleDownDelayAfterAdd": 10,
    "maxEmptyBulkDelete": 10,
    "skipNodesWithLocalStorage": true,
    "skipNodesWithSystemPods": false,
    "expander": "random",
    "customConfigs": {
        "--node-deletion-delay-timeout": "3m"
    }
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 3d61a898-b804-4d6f-8c7c-b741d2ffbe45
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"requestID": "3d61a898-b804-4d6f-8c7c-b741d2ffbe45"
}

InstanceGroup相关接口
更新时间：2026-03-13
创建节点组
描述

创建节点组

请求结构

Plain Text复制
POST /v2/cluster/{clusterID}/instancegroup HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
instanceGroupName	String	是	Request Body 参数	节点组名称，不可为空
clusterRole	String	否	Request Body 参数	节点在集群中的角色. 目前仅支持Node类型阶段组, 默认值为node
shrinkPolicy	String	否	Request Body 参数	节点组收缩规则. 可选 [ Priority, Uniform]. 默认为 Priority. Priority 优先收缩掉节点优先值低的节点, Uniform 多子网平均缩容
updatePolicy	String	否	Request Body 参数	节点组更新规则. 可选 [ Rolling, Concurrency ]. 默认为 Concurrency. Concurrency 并发更新, Rolling 滚动更新. 该参数暂未启用
cleanPolicy	String	否	Request Body 参数	节点清理规则. 可选 [ Remain, Delete ]. 默认为 Delete.
instanceTemplate	InstanceTemplate	是	Request Body 参数	节点组的节点配置
replicas	Integer	是	Request Body 参数	节点组节点要求的副本数. 取值范围是自然数集
clusterAutoscalerSpec	ClusterAutoscalerSpec	否	Request Body 参数	集群自动伸缩配置
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
instanceGroupID	String	是	节点组 ID
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
POST /v2/cluster/cce-f7zeyx1u/instancegroup HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
	"clusterID": "cce-xxxxx",
	"replicas": 1,
	"instanceTemplates": [
		{
			"machineType": "BCC",
			"instanceType": "75",
			"instanceName": "",
			"vpcConfig": {
				"vpcSubnetID": "sbn-994weibx7nzq"
			},
			"instanceResource": {
				"CPU": 8,
				"MEM": 16,
				"rootDiskType": "enhanced_ssd_pl1",
				"rootDiskSize": 100,
                "rootDiskExtraIo": 1000,
				"cdsList": [],
				"machineSpec": "bcc.e1.c8m16",
				"specId": "e1"
			},
			"checkGPUDriver": false,
			"imageID": "5755c050-777a-xxxx",
			"userData": null,
			"instanceOS": {
				"imageType": "System"
			},
			"scaleDownDisabled": false,
			"isOpenHostnameDomain": false,
			"needEIP": false,
			"eipOption": {},
			"iamRole": null,
			"deployCustomConfig": {
				"cleanPolicy": "Delete",
				"relationTag": true,
				"enableCordon": false,
				"kubeletRootDir": "/var/lib/kubelet",
				"kubeReserved": {},
				"systemReserved": {},
				"preUserScript": "",
				"postUserScript": "",
				"postUserScriptFailedAutoCordon": false,
				"iamRole": null,
				"enableGpuShare": false,
				"securitySelectType": "already",
				"securityType": "normal",
				"remedyRule": "",
				"openRemedyRule": false,
				"containerdConfig": {
					"dataRoot": "/home/cce/containerd"
				}
			},
			"runtimeType": "containerd",
			"runtimeVersion": "2.1.2",
			"deploySetIDs": [],
			"labels": {
				"cce.baidubce.com/gpu-share-device-plugin": "disable"
			},
			"annotations": {},
			"tags": [],
			"taints": [],
			"relationTag": true,
			"instancePreChargingOption": {}
		}
	],
	"cleanPolicy": "Delete",
	"shrinkPolicy": "Priority",
	"clusterAutoscalerSpec": {
		"enabled": false,
		"minReplicas": 0,
		"maxReplicas": 1,
		"scalingGroupPriority": 0
	},
	"instanceGroupName": "test-openapi",
	"remedyRulesBinding": {
		"remedyRuleID": "",
		"enableCheckANDRemedy": false
	},
	"securityGroupType": "normal",
	"securityGroups": [
		{
			"id": "xxx",
			"name": "cce-vo5zav31xxx",
			"type": "normal"
		}
	],
	"iamRole": null
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: aef503ab-66e2-4b7f-9044-e922389ed03f
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"requestID": "aef503ab-66e2-4b7f-9044-e922389ed03f",
	"instanceGroupID": "cce-ig-dvej1d3y"
}
获取节点组详情
描述

获取节点组详情

请求结构

Plain Text复制
GET /v2/cluster/{clusterID}/instancegroup/{instanceGroupID} HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
instanceGroupID	String	是	URL 参数	节点组 ID
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
requestID	String	是	请求 ID, 问题定位提供该 ID
instanceGroup	InstanceGroup	是	查询到的节点组详情
请求示例

Plain Text复制
GET /v2/cluster/cce-47bqnhmj/instancegroup/cce-ig-796lmt7a  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 9ccdfbcf-f989-49e6-9701-6996dee804b1
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"requestID": "9ccdfbcf-f989-49e6-9701-6996dee804b1",
	"instanceGroup": {
		"spec": {
			"cceInstanceGroupID": "cce-ig-dvej1d3y",
			"instanceGroupName": "sdk-testcase",
			"clusterID": "cce-z6qjgcq7",
			"clusterRole": "node",
			"shrinkPolicy": "Priority",
			"updatePolicy": "Concurrency",
			"cleanPolicy": "Delete",
			"instanceTemplate": {
				"instanceName": "",
				"runtimeType": "docker",
				"runtimeVersion": "18.9.2",
				"clusterID": "cce-z6qjgcq7",
				"clusterRole": "node",
				"instanceGroupID": "cce-ig-dvej1d3y",
				"instanceGroupName": "sdk-testcase",
				"existedOption": {},
				"machineType": "BCC",
				"instanceType": "N3",
				"bbcOption": {},
				"vpcConfig": {
					"vpcID": "vpc-pi9fghaxcpnf",
					"vpcSubnetID": "sbn-ww1xf6a5fi88",
					"securityGroupID": "g-4mnvpnrfscm1",
					"vpcSubnetType": "BCC",
					"vpcSubnetCIDR": "192.168.16.0/24",
					"availableZone": "zoneA"
				},
				"instanceResource": {
					"cpu": 1,
					"mem": 4,
					"rootDiskType": "hp1",
					"rootDiskSize": 40
				},
				"imageID": "m-4Umtt2i5",
				"instanceOS": {
					"imageType": "System",
					"imageName": "centos-8u0-x86_64-20200601205040",
					"osType": "linux",
					"osName": "CentOS",
					"osVersion": "8.0",
					"osArch": "x86_64 (64bit)",
					"osBuild": "2020060100"
				},
				"eipOption": {},
				"instanceChargingType": "Postpaid",
				"instancePreChargingOption": {},
				"deleteOption": {
					"deleteResource": true,
					"deleteCDSSnapshot": true
				},
				"deployCustomConfig": {
					"dockerConfig": {},
					"preUserScript": "bHM=",
					"postUserScript": "bHM="
				},
				"labels": {
					"cluster-id": "cce-z6qjgcq7",
					"cluster-role": "node",
					"instance-group-id": "cce-ig-dvej1d3y"
				},
				"cceInstancePriority": 5
			},
			"replicas": 3,
			"clusterAutoscalerSpec": {
				"enabled": false,
				"minReplicas": 0,
				"maxReplicas": 0,
				"scalingGroupPriority": 0
			}
		},
		"status": {
			"readyReplicas": 3,
			"pause": {
				"paused": false,
				"reason": ""
			}
		},
		"createdAt": "2020-09-27T06:34:51Z"
	}
}
删除节点组
描述

删除节点组

请求结构

Plain Text复制
DELETE /v2/cluster/{clusterID}/instancegroup/{instanceGroupID} HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
instanceGroupID	String	是	URL 参数	节点组 ID
deleteInstances	Boolean	否	Query 参数	是否删除节点组内节点. 默认为false
releaseAllResource	Boolean	否	Query 参数	是否将该节点组中的节点移出集群，并释放虚机资源、后付费公网IP和云磁盘. 默认为false
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
DELETE /v2/cluster/cce-f7zeyx1u/instancegroup/cce-ig-dvej1d3y?deleteInstances=true  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: b1a9e426-c0ca-4668-a1d8-624c5000d365
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"requestID": "b1a9e426-c0ca-4668-a1d8-624c5000d365"
}
修改节点组节点自动扩缩容配置
描述

修改节点组节点自动扩缩容配置

请求结构

Plain Text复制
PUT /v2/cluster/{clusterID}/instancegroup/{instanceGroupID}/autoscaler HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
instanceGroupID	String	是	URL 参数	节点组 ID
enabled	Boolean	是	Request Body 参数	是否启用Autoscaler
minReplicas	Integer	是	Request Body 参数	最小副本数. 取值范围是自然数集.
maxReplicas	Integer	是	Request Body 参数	最大副本数. 取值范围是自然数集, 需大于minReplicas.
scalingGroupPriority	Integer	是	Request Body 参数	伸缩组优先级. 取值范围是自然数集.
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
PUT /v2/cluster/cce-f7zeyx1u/instancegroup/cce-ig-dvej1d3y/autoscaler  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
	"enabled": true,
	"minReplicas": 2,
	"maxReplicas": 5,
	"scalingGroupPriority": 1
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 27f91a44-7257-48e7-a8d8-849f45a32da4
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"requestID": "27f91a44-7257-48e7-a8d8-849f45a32da4"
}
修改节点组节点副本数
描述

修改节点组节点副本数

请求结构

Plain Text复制
PUT /v2/cluster/{clusterID}/instancegroup/{instanceGroupID}/replicas HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
instanceGroupID	String	是	URL 参数	节点组 ID
replicas	Integer	是	Request Body 参数	期望的节点组节点的副本数. 取值范围是自然数集.
instanceIDs	List	否	Request Body 参数	指定被添加或是优先被删除的节点 ID 集合
deleteInstance	Boolean	否	Request Body 参数	是否删除节点组收缩时被剔除的节点. 默认为 false. 此值的优先级高于节点组CleanPolicy, 被缩容节点使用该配置.
deleteOption	DeleteOption	否	Request Body 参数	修改指定节点删除选项.
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
PUT /v2/cluster/cce-f7zeyx1u/instancegroup/cce-ig-dvej1d3y/replicas  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
	"replicas": 1,
	"instanceIDs": null,
	"deleteInstance": true,
	"deleteOption": {
		"deleteResource": true,
		"deleteCDSSnapshot": true
	}
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 6f593304-6787-45ea-8e0f-426ee331cc8b
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"requestID": "6f593304-6787-45ea-8e0f-426ee331cc8b"
}
获取集群节点组列表
描述

获取集群的节点组列表

请求结构

Plain Text复制
GET /v2/cluster/{clusterID}/instancegroups HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
pageNo	Integer	否	Query 参数	查询页码序号. pageNo 或 pageSize 为0时会返回集群全部节点组
pageSize	Integer	否	Query 参数	查询结果每页条目数. pageNo 或 pageSize 为0时会返回集群全部节点组
keywordType	String	否	Query 参数	关键词搜索类型。可选 [ instanceGroupName, instanceGroupID ]
keyword	String	否	Query 参数	搜索关键词，配合 keywordType 使用
autoscalerEnabled	String	否	Query 参数	按自动伸缩状态过滤。设为 true 仅返回已开启自动伸缩的节点组
chargingType	String	否	Query 参数	按计费方式过滤。可选 [ Prepaid, Postpaid, bidding ]
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
page	ListInstanceGroupPage	是	节点组查询结果页
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
GET /v2/cluster/cce-f7zeyx1u/instancegroups?pageNo=1&pageSize=10  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 1a65cc49-f3da-4d66-b994-7d7cd6797af5
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"requestID": "1a65cc49-f3da-4d66-b994-7d7cd6797af5",
	"page": {
		"pageNo": 0,
		"pageSize": 0,
		"totalCount": 1,
		"list": [
			{
				"spec": {
					"cceInstanceGroupID": "cce-ig-dvej1d3y",
					"instanceGroupName": "sdk-testcase",
					"clusterID": "cce-z6qjgcq7",
					"clusterRole": "node",
					"shrinkPolicy": "Priority",
					"updatePolicy": "Concurrency",
					"cleanPolicy": "Delete",
					"instanceTemplate": {
						"instanceName": "",
						"runtimeType": "docker",
						"runtimeVersion": "18.9.2",
						"clusterID": "cce-z6qjgcq7",
						"clusterRole": "node",
						"instanceGroupID": "cce-ig-dvej1d3y",
						"instanceGroupName": "sdk-testcase",
						"existedOption": {},
						"machineType": "BCC",
						"instanceType": "N3",
						"bbcOption": {},
						"vpcConfig": {
							"vpcID": "vpc-pi9fghaxcpnf",
							"vpcSubnetID": "sbn-ww1xf6a5fi88",
							"securityGroupID": "g-4mnvpnrfscm1",
							"vpcSubnetType": "BCC",
							"vpcSubnetCIDR": "192.168.16.0/24",
							"availableZone": "zoneA"
						},
						"instanceResource": {
							"cpu": 1,
							"mem": 4,
							"rootDiskType": "hp1",
							"rootDiskSize": 40
						},
						"imageID": "m-4Umtt2i5",
						"instanceOS": {
							"imageType": "System",
							"imageName": "centos-8u0-x86_64-20200601205040",
							"osType": "linux",
							"osName": "CentOS",
							"osVersion": "8.0",
							"osArch": "x86_64 (64bit)",
							"osBuild": "2020060100"
						},
						"eipOption": {},
						"instanceChargingType": "Postpaid",
						"instancePreChargingOption": {},
						"deleteOption": {
							"deleteResource": true,
							"deleteCDSSnapshot": true
						},
						"deployCustomConfig": {
							"dockerConfig": {},
							"preUserScript": "bHM=",
							"postUserScript": "bHM="
						},
						"labels": {
							"cluster-id": "cce-z6qjgcq7",
							"cluster-role": "node",
							"instance-group-id": "cce-ig-dvej1d3y"
						},
						"cceInstancePriority": 5
					},
					"replicas": 3,
					"clusterAutoscalerSpec": {
						"enabled": false,
						"minReplicas": 0,
						"maxReplicas": 0,
						"scalingGroupPriority": 0
					}
				},
				"status": {
					"readyReplicas": 3,
					"pause": {
						"paused": false,
						"reason": ""
					}
				},
				"createdAt": "2020-09-27T06:34:51Z"
			}
		]
	}
}
创建扩容节点组任务
描述

创建扩容节点组任务。

请求结构

Plain Text复制
PUT /v2/cluster/{clusterID}/instancegroup/{instanceGroupID}/scaleup HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
instanceGroupID	String	是	URL 参数	节点组 ID
upToReplicas	Integer	是（upToReplicas和upReplicas两者填其一）	Query 参数	扩容节点组的目标副本数，如果选择该参数则必须大于节点组的当前副本数
upReplicas	Integer	是（upToReplicas和upReplicas两者填其一）	Query 参数	节点组扩容的副本数，如果选择该参数则必须大于0
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
描述
taskID	String	节点组扩容任务 ID
requestID	String	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
PUT /api/cce/service/v2/cluster/cce-jvyvb9al/instancegroup/cce-ig-glw5jb7x/scaleup?upToReplicas=4 HTTP/1.1
Host: cce.bj.baidubce.com
Content-Type: application/json
Authorization: authorization string
返回示例

Plain Text复制
{
    "requestID": "deb8d7b9-37b2-4fc2-b956-0db512c37b5e",
    "taskID": "task-cce-ig-glw5jb7x-scaleup-zibi4ixw"
}
创建缩容节点组任务
描述

创建缩容节点组任务。

请求结构

Plain Text复制
PUT /v2/cluster/{clusterID}/instancegroup/{instanceGroupID}/scaledown HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
instanceGroupID	String	是	URL 参数	节点组 ID
instancesToBeRemoved	List<String>	是	Request Body 参数	缩容节点组时计划从节点组移除的节点 ID 列表
k8sNodesToBeRemoved	List<String>	是	Request Body 参数	缩容节点组时计划从节点组移除的 K8s 节点名称列表。instancesToBeRemoved 和 k8sNodesToBeRemoved 至少填一个
cleanPolicy	String	是	Request Body 参数	缩容节点组时是否保留节点对应的实例, 可选 [Remain,Delete]
deleteOption	DeleteOption	否	Request Body 参数	修改指定节点删除选项。cleanPolicy为Delete时，需要设置该参数。
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
描述
taskID	String	节点组扩容任务 ID
requestID	String	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
PUT /api/cce/service/v2/cluster/cce-91xd2ojb/instancegroup/cce-ig-l68ajx08/scaledown?= HTTP/1.1
Host: cce.bj.baidubce.com
Content-Type: application/json
Authorization: authorization string

{
    "instancesToBeRemoved": [
        "cce-91xd2ojb-6y5feg8v",
        "cce-91xd2ojb-6y5feg8v"
    ],
    "cleanPolicy":"Delete",
    "deleteOption":{
        "moveOut":true,
        "deleteResource":false,
        "deleteCDSSnapshot":false
    }
}
返回示例

Plain Text复制
{
    "requestID": "deb8d7b9-37b2-4fc2-b956-0db512c37b5e",
    "taskID": "task-cce-ig-l68ajx08-scaledown-zibi4ixw"
}
移入已有节点
描述

移入已有节点到节点组中。

返回头域

除公共头域，无其它特殊头域。

请求结构

Plain Text复制
PUT  /v2/cluster/[clusterID]/instancegroup/[instanceGroupID]/attachInstances HTTP/1.1
Host: cce.bd.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	string	是	URL 参数	集群 ID，用于标识特定的集群。
instanceGroupID	string	是	URL 参数	节点组 ID，用于标识特定的节点组。
inCluster	bool	是	Request Body 参数	是否是集群内节点。
useInstanceGroupConfig	bool	是	Request Body 参数	针对集群外节点生效，设置为 true 将使用节点组配置。
useInstanceGroupConfigWithDiskInfo	bool	否	Request Body 参数	针对集群外节点生效，设置为 true 将使用节点组配置（含磁盘信息）。
installGpuDriver	bool	否	Request Body 参数	是否安装 GPU 驱动
existedInstances	List<InstanceSet>	否	Request Body 参数	配置集群外节点的详细信息。
existedInstancesInCluster	List<ExistedInstanceInCluster>	否	Request Body 参数	配置集群内节点的详细信息。
返回示例

Plain Text复制
{
    "requestID": "deb8d7b9-37b2-4fc2-b956-0db512c37b5e",
    "taskID": "task-cce-ig-l68ajx08-scaledown-zibi4ixw"
}
请求示例 移入集群外节点

Plain Text复制
PUT /api/cce/service/v2/cluster/cce-qfdlj5g9/instancegroup/cce-ig-iw245bl0/attachInstances HTTP/1.1
Host: cce.bd.baidubce.com
Authorization: authorization string

{
    "inCluster": false,
    "useInstanceGroupConfig": true,
    "existedInstances": [
        {
            "instanceSpec": {
                "sshKeyID": "k-FH1hIJ0h",
                "existed": true,
                "existedOption": {
                    "existedInstanceID": "i-oCnp4BG5",
                    "rebuild": true
                },
                "machineType": "BCC",
                "clusterRole": "node",
                "instanceOS": {
                    "imageType": "System"
                },
                "imageID": "m-PljC8e8k",
                "instanceResource": {
                    "cdsList": []
                }
            }
        }
    ]
}
移入集群内节点

Plain Text复制
PUT /api/cce/service/v2/cluster/cce-qfdlj5g9/instancegroup/cce-ig-iw245bl0/attachInstances HTTP/1.1
Host: cce.bd.baidubce.com
Authorization: authorization string

{
    "inCluster": true,
    "existedInstancesInCluster": [
        {
            "existedInstanceID": "i-oCnp4BG5"
        }
    ]
}
返回示例

Plain Text复制
{
    "requestID": "deb8d7b9-37b2-4fc2-b956-0db512c37b5e",
    "taskID": "task-cce-ig-l68ajx08-scaledown-zibi4ixw"
}
修改节点组节点缩容保护状态
描述

开启或关闭节点组中指定节点的缩容保护（Scale-Down Protection）。当 scaleDownDisabled 设为 true 时，这些节点将在自动伸缩过程中被跳过，不会被缩容；设为 false 时则恢复正常缩容行为。

请求结构

Plain Text复制
PUT /v2/cluster/{clusterID}/instanceScaleDown HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
Content-Type: application/json
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
instanceIDs	List<String>	是	Request Body 参数	需要修改缩容保护状态的节点 ID 列表（CCEInstanceID）
scaleDownDisabled	Boolean	是	Request Body 参数	是否开启缩容保护：true 开启（禁止被缩容），false 关闭
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
描述
failedInstances	List<Object>	修改失败的节点及原因列表，字段见下表
requestID	String	请求 ID, 问题定位提供该 ID
failedInstances 结构说明：

字段
类型
描述
instanceID	String	节点 ID
reason	String	失败原因说明
请求示例

Plain Text复制
PUT /api/cce/service/v2/cluster/cce-xyz123/instanceScaleDown HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
Content-Type: application/json

{
    "instanceIDs": [
        "cce-xyz123-abcd",
        "cce-xyz123-efgh"
    ],
    "scaleDownDisabled": true
}
返回示例

Plain Text复制
{
    "requestID": "123e4567-e89b-12d3-a456-426614174000",
    "failedInstances": []
}

Instance相关接口
更新时间：2026-04-09
CCE Instance OpenAPI
创建节点（集群扩容）
描述

为集群添加节点

请求结构

Plain Text复制
POST /v2/cluster/{clusterID}/instances  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群ID
无（RequestBody 为数组）	List<InstanceSet>	是	RequestBody 参数	为集群增加的节点列表
返回头域

除公共头域外，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
cceInstanceIDs	List	是	新增节点的 ID 列表
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例：新建 BCC

Plain Text复制
POST /v2/cluster/cce-f7zeyx1u/instances HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

[ {
  "instanceSpec" : {
    "instanceName" : "",
    "clusterRole" : "node",
    "existed" : false,
    "machineType" : "BCC",
    "instanceType" : "N3",
    "vpcConfig" : {
      "vpcID" : "vpc-mwbgygrjb72w",
      "vpcSubnetID" : "sbn-mnbvhnuupv1u",
      "availableZone" : "zoneA",
      "securityGroup": {
        "customSecurityGroups": [],
        "enableCCERequiredSecurityGroup": true,
        "enableCCEOptionalSecurityGroup": true
      }
    },
    "instanceResource" : {
      "cpu" : 1,
      "mem" : 4,
      "rootDiskSize" : 40,
      "localDiskSize" : 0,
      "cdsList" : [ ]
    },
    "imageID" : "m-gTpZ1k6n",
    "instanceOS" : {
      "imageType" : "System"
    },
    "needEIP" : false,
    "bid":false,
    "adminPassword" : "test123!T",
    "sshKeyName" : "k-3uvrdvVq",
    "instanceChargingType" : "Postpaid",
    "runtimeType" : "docker"
  },
  "count" : 1
} ]
请求示例：使用已有节点

添加 Node 机器配置时，设置 instanceSpec.existed 为 true 并设置 instanceSpec.existedOption.existedInstanceID 为希望使用的已有节点 ID
如果不希望重装系统，设置 instanceSpec.existedOption.rebuild 为 false 并务必保证机器密码正确，否则节点会因无法部署相关服务而创建失败
如果不希望重装系统，无需设置 instanceSpec.instanceOS 与 instanceSpec.machineType
其它参数参考 API 文档按需设置
Plain Text复制
[
    {
        "instanceSpec":{
            "existed":true,
            "existedOption":{
                "existedInstanceID":"i-M56Un1DO",
                "rebuild":true
            },
            "machineType":"BCC",
            "instanceOS": {
                "imageName": "7.5 x86_64 (64bit)",
                "imageType": "System",
                "osType": "linux",
                "osName": "CentOS",
                "osVersion": "7.5",
                "osArch": "x86_64 (64bit)"
            },
            "adminPassword":"test123!T"
     }     
]
请求示例：挂载CDS
有时我们希望在新建节点的同时为节点挂载 1 到多个 CDS，此时在创建节点时，为节点设置 CDS 参数和相关挂载路径即可。示例如下。

需要注意的是，每个路径下只能挂载一个 CDS，但一个路径的子路径下可以挂载另一个 CDS。例如，/a 目录下仅可挂载一个 CDS，但 /a/b 目录下可以挂载另一个 CDS。

已有节点仅可挂载 CDS 到指定路径，不会新建 CDS。因此当已有节点试图挂载 CDS 到指定路径但找不到满足条件的 CDS 时，将会忽略相关 CDS 配置。

Plain Text复制
[
        {
            "instanceSpec":{
                ......
                "instanceResource": {
                    "cdsList": [
                         {diskPath: "/home/cce", storageType: "cloud_hp1", cdsSize: 60}
                     ] 
                },
                ......
            }
        }
]
请求示例：新建 BBC

智能卡 BBC 需要使用普通子网，需要安全组 ID；非智能卡 BBC 需要使用 BBC 型子网，不能传安全组ID。

Plain Text复制
POST /v2/cluster/cce-f7zeyx1u/instances HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

[ {
  "instanceSpec" : {
    "instanceName" : "",
    "clusterRole" : "node",
    "existed" : false,
    "machineType" : "BBC",
    "vpcConfig" : {
      "vpcSubnetID" : "sbn-mnbvhnuupv1u",
      "securityGroupID" : "g-xh04bcdkq5n6"
    },
    "instanceResource" : {
      "rootDiskSize" : 100,
      "cdsList" : [ ]
    },
    "bbcOption": {
      "flavor": "BBC-G4-02S",
      "diskInfo": "NoRaid"
    },
    "imageID" : "m-zGnlzI5v",
    "instanceOS" : {
      "imageType" : "BbcSystem"
    },
    "adminPassword" : "test123!T",
    "instanceChargingType" : "Postpaid",
    "runtimeType" : "docker"
  },
  "count" : 1
} ]
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 58868d06-2e79-4d68-9f62-389e70f54996
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
    "cceInstanceIDs": [
        "cce-f7zeyx1u-7ombtu3j"
    ],
    "requestID": "58868d06-2e79-4d68-9f62-389e70f54996"
}
删除节点（集群缩容）
描述

为集群删除节点

请求结构

Plain Text复制
PUT /v2/cluster/{clusterID}/instances  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL参数	集群ID
deleteOption	DeleteOption	否	RequestBody 参数	删除选项. 为空时使用节点自身的 DeleteOption 配置
instanceIDs	List	是	RequestBody 参数	要删除的节点 ID 列表
scaleDown	Boolean	否	RequestBody 参数	是否同时减少被删除节点所在节点组的期望节点数
返回头域

除公共头域外，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
requestID	String	是	响应的请求的ID
请求示例：将节点从集群中移出后同时删除相关资源

Plain Text复制
PUT /v2/cluster/cce-f7zeyx1u/instances HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
    "instanceIDs": [
        "cce-f7zeyx1u-7ombtu3j"
    ],
    
    "deleteOption": {
        "moveOut": false,
        "deleteResource": true,
        "deleteCDSSnapshot": true
    }
}
请求示例：仅将节点从集群中移出

Plain Text复制
PUT /v2/cluster/cce-f7zeyx1u/instances HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
    "instanceIDs": [
        "cce-f7zeyx1u-7ombtu3j"
    ],
    
    "deleteOption": {
        "moveOut": true
    }
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 23a82d7e-954f-4539-b828-ce620eaa97b3
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
    "requestID": "23a82d7e-954f-4539-b828-ce620eaa97b3"
}
更新节点属性
描述

更新一个节点的某些配置信息。目前仅支持部分属性的更新。

请求结构

Plain Text复制
PUT /v2/cluster/{clusterID}/instance/{instanceID} HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
instanceID	String	是	URL 参数	节点 ID
labels	Map<String,String>	是	RequestBody 参数	节点的标签
annotations	Map<String,String>	否	RequestBody 参数	节点的注解
taints	List<Taint>	是	RequestBody 参数	节点的污点
cceInstancePriority	Integer	是	RequestBody 参数	节点的优先级
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
instance	Instance	是	节点的查询结果
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
PUT /v2/cluster/cce-oi0ihu53/instance/i-bn71n2eK  HTTP/1.1
Host: cce.hkg.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
    "labels": {
        "cluster-id": "cce-b3gzxpwg",
        "cluster-role": "node",
        "new-label-key": "new-label-value"
    },
    "taints": [
        {
            "key": "testKey",
            "value": "testValue",
            "effect": "NoSchedule"
        }
    ],
    "cceInstancePriority": 5
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 60dae0e8-8fa0-443c-a5d5-45b1e7beea68
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
    "instance": {
        "spec": {
            "cceInstanceID": "cce-oi0ihu53-pfmx3lu6",
            "instanceName": "cce-oi0ihu53-pfmx3lu6",
            "runtimeType": "docker",
            "runtimeVersion": "18.9.2",
            "clusterID": "cce-oi0ihu53",
            "clusterRole": "node",
            "userID": "eca97e148cb74e9683d7b7240829d1ff",
            "instanceGroupID": "",
            "instanceGroupName": "",
            "machineType": "BCC",
            "instanceType": "N3",
            "bbcOption": {},
            "vpcConfig": {
                "vpcID": "vpc-epyxw9mwjc18",
                "vpcSubnetID": "sbn-11gfqpsax4jn",
                "securityGroupID": "g-urmir67c35x3",
                "vpcSubnetType": "BCC",
                "VPCSubnetCIDR": "192.168.0.0/16",
                "VPCSubnetCIDRIPv6": "",
                "availableZone": "zoneA"
            },
            "instanceResource": {
                "cpu": 4,
                "mem": 12,
                "rootDiskType": "hp1",
                "rootDiskSize": 40
            },
            "deployCustomConfig": {
                "dockerConfig": {}
            },
            "imageID": "m-Yp443gTZ",
            "instanceOS": {
                "imageType": "System",
                "imageName": "centos-7u5-x86_64-20200601203742",
                "osType": "linux",
                "osName": "CentOS",
                "osVersion": "7.5",
                "osArch": "x86_64 (64bit)",
                "osBuild": "2020060100"
            },
            "needEIP": false,
            "eipOption": {},
            "sshKeyID": "",
            "instanceChargingType": "Postpaid",
            "deleteOption": {
                "deleteResource": true,
                "deleteCDSSnapshot": true
            },
            "labels": {
                "cluster-id": "cce-oi0ihu53",
                "cluster-role": "node"
            },
            "cceInstancePriority": 5
        },
        "status": {
            "machine": {
                "instanceID": "i-bn71n2eK",
                "instanceUUID": "60c466f2-929a-4cf9-af7c-52af00fa4476",
                "orderID": "0fe2237296b644da8ef2b215b4ff19c8",
                "vpcIP": "192.168.0.31"
            },
            "instancePhase": "running",
            "machineStatus": "ACTIVE"
        },
        "createdAt": "2020-09-15T06:43:20Z",
        "updatedAt": "2020-09-25T06:03:40Z"
    },
    "requestID": "60dae0e8-8fa0-443c-a5d5-45b1e7beea68"
}
获取节点详情
描述

获取一个节点的详细信息

请求结构

Plain Text复制
GET /v2/cluster/{clusterID}/instance/{instanceID} HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
instanceID	String	是	URL 参数	节点 ID
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
instance	Instance	是	节点的查询结果
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
GET /v2/cluster/cce-oi0ihu53/instance/i-bn71n2eK  HTTP/1.1
Host: cce.hkg.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: a13e8b5f-6878-4f1f-8746-3e986ee49a96
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
    "instance": {
        "spec": {
            "cceInstanceID": "cce-oi0ihu53-pfmx3lu6",
            "instanceName": "cce-oi0ihu53-pfmx3lu6",
            "runtimeType": "docker",
            "runtimeVersion": "18.9.2",
            "clusterID": "cce-oi0ihu53",
            "clusterRole": "node",
            "userID": "eca97e148cb74e9683d7b7240829d1ff",
            "instanceGroupID": "",
            "instanceGroupName": "",
            "machineType": "BCC",
            "instanceType": "N3",
            "bbcOption": {},
            "vpcConfig": {
                "vpcID": "vpc-epyxw9mwjc18",
                "vpcSubnetID": "sbn-11gfqpsax4jn",
                "securityGroupID": "g-urmir67c35x3",
                "vpcSubnetType": "BCC",
                "VPCSubnetCIDR": "192.168.0.0/16",
                "VPCSubnetCIDRIPv6": "",
                "availableZone": "zoneA"
            },
            "instanceResource": {
                "cpu": 4,
                "mem": 12,
                "rootDiskType": "hp1",
                "rootDiskSize": 40
            },
            "deployCustomConfig": {
                "dockerConfig": {}
            },
            "imageID": "m-Yp443gTZ",
            "instanceOS": {
                "imageType": "System",
                "imageName": "centos-7u5-x86_64-20200601203742",
                "osType": "linux",
                "osName": "CentOS",
                "osVersion": "7.5",
                "osArch": "x86_64 (64bit)",
                "osBuild": "2020060100"
            },
            "needEIP": false,
            "eipOption": {},
            "sshKeyID": "",
            "instanceChargingType": "Postpaid",
            "deleteOption": {
                "deleteResource": true,
                "deleteCDSSnapshot": true
            },
            "labels": {
                "cluster-id": "cce-oi0ihu53",
                "cluster-role": "node"
            },
            "cceInstancePriority": 5
        },
        "status": {
            "machine": {
                "instanceID": "i-bn71n2eK",
                "instanceUUID": "60c466f2-929a-4cf9-af7c-52af00fa4476",
                "orderID": "0fe2237296b644da8ef2b215b4ff19c8",
                "vpcIP": "192.168.0.31"
            },
            "instancePhase": "running",
            "machineStatus": "ACTIVE"
        },
        "createdAt": "2020-09-15T06:43:20Z",
        "updatedAt": "2020-09-24T08:27:21Z"
    },
    "requestID": "74a74b2e-f439-4147-b27a-f473e3576338"
}
获取集群节点列表
描述

请求集群节点列表

请求结构

Plain Text复制
GET /v2/cluster/{clusterID}/instances HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群ID
keywordType	String	否	Query 参数	集群模糊查询字段，可选 [ instanceName, instanceID, clusterRole]，默认值为 instanceName
keyword	String	否	Query 参数	查询关键词
orderBy	String	否	Query 参数	集群查询排序字段，可选 [ instanceName, instanceID, createdAt]，默认值为 instance_name
order	String	否	Query 参数	排序方式，可选 [ ASC, DESC ], ASC 为升序，DESC 为降序，默认值为 ASC
pageNo	Integer	否	Query 参数	页码，默认值为1，取值范围[1, 100000]
pageSize	Integer	否	Query 参数	单页结果数，默认值为10，取值范围[1, 100000]
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
instancePage	InstancePage	是	集群的节点查询结果
requestID	String	是	响应的请求的ID
请求示例

Plain Text复制
GET /v2/cluster/cce-f7zeyx1u/instances?keywordType=instanceName&keyword=&orderBy=createdAt&order=asc&pageNo=1&pageSize=10  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: a13e8b5f-6878-4f1f-8746-3e986ee49a96
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
    "instancePage": {
        "clusterID": "cce-f7zeyx1u",
        "keywordType": "instanceName",
        "keyword": "",
        "orderBy": "createdAt",
        "order": "ASC",
        "pageNo": 1,
        "pageSize": 10,
        "totalCount": 1,
        "instanceList": [
            {
                "spec": {
                    "cceInstanceID": "cce-f7zeyx1u-vbsry5uc",
                    "instanceName": "cce-f7zeyx1u-vbsry5uc",
                    "runtimeType": "docker",
                    "runtimeVersion": "18.9.2",
                    "clusterID": "cce-f7zeyx1u",
                    "clusterRole": "node",
                    "userID": "eca97e148cb74e9683d7b7240829d1ff",
                    "instanceGroupID": "",
                    "instanceGroupName": "",
                    "machineType": "BCC",
                    "instanceType": "N3",
                    "bbcOption": {},
                    "vpcConfig": {
                        "vpcID": "vpc-mwbgygrjb72w",
                        "vpcSubnetID": "sbn-mnbvhnuupv1u",
                        "securityGroupID": "g-xh04bcdkq5n6",
                        "vpcSubnetType": "BCC",
                        "VPCSubnetCIDR": "192.168.0.0/20",
                        "VPCSubnetCIDRIPv6": "",
                        "availableZone": "zoneA"
                    },
                    "instanceResource": {
                        "cpu": 1,
                        "mem": 4,
                        "rootDiskType": "hp1",
                        "rootDiskSize": 40
                    },
                    "deployCustomConfig": {
                        "dockerConfig": {}
                    },
                    "imageID": "m-gTpZ1k6n",
                    "instanceOS": {
                        "imageType": "System",
                        "imageName": "centos-7u3-x86_64-20191105104647",
                        "osType": "linux",
                        "osName": "CentOS",
                        "osVersion": "7.3",
                        "osArch": "x86_64 (64bit)",
                        "osBuild": "2019110600"
                    },
                    "needEIP": false,
                    "eipOption": {},
                    "sshKeyID": "",
                    "instanceChargingType": "Postpaid",
                    "deleteOption": {},
                    "labels": {
                        "cluster-id": "",
                        "cluster-role": "node"
                    }
                },
                "status": {
                    "machine": {
                        "instanceID": "i-HJitrtYn",
                        "orderID": "b49e015b819c4fd1887b8848c7a38025",
                        "vpcIP": "192.168.4.25"
                    },
                    "instancePhase": "running",
                    "machineStatus": "ACTIVE"
                },
                "createdAt": "2020-07-21T12:12:54Z",
                "updatedAt": "2020-07-21T12:15:00Z"
            }
        ]
    },
    "requestID": "a13e8b5f-6878-4f1f-8746-3e986ee49a96"
}
获取节点组节点列表
描述

获取节点组节点列表

请求结构

Plain Text复制
GET /v2/cluster/{clusterID}/instancegroup/{instanceGroupID}/instances HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
instanceGroupID	String	是	URL 参数	节点组 ID
pageNo	Integer	否	Query 参数	页码，默认值为1，取值范围[1, 100000]
pageSize	Integer	否	Query 参数	单页结果数，默认值为10，取值范围[1, 100000]
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
page	ListInstancesByInstanceGroupIDPage	是	集群的节点查询结果
requestID	String	是	响应的请求的 ID
请求示例

Plain Text复制
GET /v2/cluster/cce-47bqnhmj/instancegroup/cce-ig-796lmt7a/instances?pageNo=1&pageSize=10  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: d52c646c-207d-4630-95ba-0539124fd42b
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
    "requestID": "d52c646c-207d-4630-95ba-0539124fd42b",
    "page": {
        "pageNo": 0,
        "pageSize": 0,
        "totalCount": 3,
        "list": [
            {
                "spec": {
                    "cceInstanceID": "cce-z6qjgcq7-7dd7z1fc",
                    "instanceName": "cce-z6qjgcq7-7dd7z1fc",
                    "runtimeType": "docker",
                    "runtimeVersion": "18.9.2",
                    "clusterID": "cce-z6qjgcq7",
                    "clusterRole": "node",
                    "instanceGroupID": "cce-ig-dvej1d3y",
                    "instanceGroupName": "sdk-testcase",
                    "existedOption": {},
                    "machineType": "BCC",
                    "instanceType": "N3",
                    "bbcOption": {},
                    "vpcConfig": {
                        "vpcID": "vpc-pi9fghaxcpnf",
                        "vpcSubnetID": "sbn-ww1xf6a5fi88",
                        "vpcSubnetType": "BCC",
                        "availableZone": "zoneA"
                    },
                    "instanceResource": {
                        "cpu": 1,
                        "mem": 4,
                        "rootDiskType": "hp1",
                        "rootDiskSize": 40
                    },
                    "imageID": "m-4Umtt2i5",
                    "instanceOS": {
                        "imageType": "System",
                        "imageName": "centos-8u0-x86_64-20200601205040",
                        "osType": "linux",
                        "osName": "CentOS",
                        "osVersion": "8.0",
                        "osArch": "x86_64 (64bit)",
                        "osBuild": "2020060100"
                    },
                    "eipOption": {},
                    "instanceChargingType": "Postpaid",
                    "instancePreChargingOption": {},
                    "deleteOption": {
                        "deleteResource": true,
                        "deleteCDSSnapshot": true
                    },
                    "deployCustomConfig": {
                        "dockerConfig": {}
                    },
                    "labels": {
                        "cluster-id": "cce-z6qjgcq7",
                        "cluster-role": "node",
                        "instance-group-id": "cce-ig-dvej1d3y"
                    },
                    "cceInstancePriority": 5
                },
                "status": {
                    "machine": {
                        "instanceID": "i-HVq1GwKr",
                        "orderID": "71f6d4249aed4a08b2bc1470fefd6b2a",
                        "vpcIP": "192.168.16.33"
                    },
                    "instancePhase": "running",
                    "machineStatus": "ACTIVE"
                },
                "createdAt": "2020-09-27T06:35:04Z",
                "updatedAt": "2020-09-27T06:36:53Z"
            },
            {
                "spec": {
                    "cceInstanceID": "cce-z6qjgcq7-asf0p09i",
                    "instanceName": "cce-z6qjgcq7-asf0p09i",
                    "runtimeType": "docker",
                    "runtimeVersion": "18.9.2",
                    "clusterID": "cce-z6qjgcq7",
                    "clusterRole": "node",
                    "instanceGroupID": "cce-ig-dvej1d3y",
                    "instanceGroupName": "sdk-testcase",
                    "existedOption": {},
                    "machineType": "BCC",
                    "instanceType": "N3",
                    "bbcOption": {},
                    "vpcConfig": {
                        "vpcID": "vpc-pi9fghaxcpnf",
                        "vpcSubnetID": "sbn-ww1xf6a5fi88",
                        "vpcSubnetType": "BCC",
                        "availableZone": "zoneA"
                    },
                    "instanceResource": {
                        "cpu": 1,
                        "mem": 4,
                        "rootDiskType": "hp1",
                        "rootDiskSize": 40
                    },
                    "imageID": "m-4Umtt2i5",
                    "instanceOS": {
                        "imageType": "System",
                        "imageName": "centos-8u0-x86_64-20200601205040",
                        "osType": "linux",
                        "osName": "CentOS",
                        "osVersion": "8.0",
                        "osArch": "x86_64 (64bit)",
                        "osBuild": "2020060100"
                    },
                    "eipOption": {},
                    "instanceChargingType": "Postpaid",
                    "instancePreChargingOption": {},
                    "deleteOption": {
                        "deleteResource": true,
                        "deleteCDSSnapshot": true
                    },
                    "deployCustomConfig": {
                        "dockerConfig": {}
                    },
                    "labels": {
                        "cluster-id": "cce-z6qjgcq7",
                        "cluster-role": "node",
                        "instance-group-id": "cce-ig-dvej1d3y"
                    },
                    "cceInstancePriority": 5
                },
                "status": {
                    "machine": {
                        "instanceID": "i-RndUYlWF",
                        "orderID": "71f6d4249aed4a08b2bc1470fefd6b2a",
                        "vpcIP": "192.168.16.34"
                    },
                    "instancePhase": "running",
                    "machineStatus": "ACTIVE"
                },
                "createdAt": "2020-09-27T06:35:06Z",
                "updatedAt": "2020-09-27T06:36:58Z"
            },
            {
                "spec": {
                    "cceInstanceID": "cce-z6qjgcq7-ibtt74zc",
                    "instanceName": "cce-z6qjgcq7-ibtt74zc",
                    "runtimeType": "docker",
                    "runtimeVersion": "18.9.2",
                    "clusterID": "cce-z6qjgcq7",
                    "clusterRole": "node",
                    "instanceGroupID": "cce-ig-dvej1d3y",
                    "instanceGroupName": "sdk-testcase",
                    "existedOption": {},
                    "machineType": "BCC",
                    "instanceType": "N3",
                    "bbcOption": {},
                    "vpcConfig": {
                        "vpcID": "vpc-pi9fghaxcpnf",
                        "vpcSubnetID": "sbn-ww1xf6a5fi88",
                        "vpcSubnetType": "BCC",
                        "availableZone": "zoneA"
                    },
                    "instanceResource": {
                        "cpu": 1,
                        "mem": 4,
                        "rootDiskType": "hp1",
                        "rootDiskSize": 40
                    },
                    "imageID": "m-4Umtt2i5",
                    "instanceOS": {
                        "imageType": "System",
                        "imageName": "centos-8u0-x86_64-20200601205040",
                        "osType": "linux",
                        "osName": "CentOS",
                        "osVersion": "8.0",
                        "osArch": "x86_64 (64bit)",
                        "osBuild": "2020060100"
                    },
                    "eipOption": {},
                    "instanceChargingType": "Postpaid",
                    "instancePreChargingOption": {},
                    "deleteOption": {
                        "deleteResource": true,
                        "deleteCDSSnapshot": true
                    },
                    "deployCustomConfig": {
                        "dockerConfig": {}
                    },
                    "labels": {
                        "cluster-id": "cce-z6qjgcq7",
                        "cluster-role": "node",
                        "instance-group-id": "cce-ig-dvej1d3y"
                    },
                    "cceInstancePriority": 5
                },
                "status": {
                    "machine": {
                        "instanceID": "i-aRGKcLtv",
                        "orderID": "71f6d4249aed4a08b2bc1470fefd6b2a",
                        "vpcIP": "192.168.16.35"
                    },
                    "instancePhase": "running",
                    "machineStatus": "ACTIVE"
                },
                "createdAt": "2020-09-27T06:35:07Z",
                "updatedAt": "2020-09-27T06:37:02Z"
            }
        ]
    }
}
获取节点事件步骤
描述

获取创建或删除过程中节点所处的事件步骤,请求参数同时兼容cceInstanceID和instanceID

请求结构

Plain Text复制
GET /v2/event/instance/{instanceID} HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必选
参数位置
描述
instanceID	String	是	URL 参数	节点 ID
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必选
描述
status	String	是	事件类型
steps	List<Step>	是	集群操作步骤
requestID	String	是	请求ID
请求示例

Plain Text复制
GET /v2/event/instance/i-ezs9bmjY  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 08eb305a-87fb-4360-8a27-42b9561edf4a
Date: Fri, 12 Aug 2022 03:10:30 GMT
Content-Type: application/json;charset=UTF-8

{
    "status": "created",
    "steps": [
        {
            "stepName": "准备机器",
            "stepStatus": "done",
            "ready": true,
            "startTime": "2022-08-04T02:45:28Z",
            "finishedTime": "2022-08-04T02:45:56Z",
            "costSeconds": 28,
            "retryCount": 1,
            "errInfo": {}
        },
        {
            "stepName": "绑定安全组",
            "stepStatus": "done",
            "ready": true,
            "startTime": "2022-08-04T02:45:56Z",
            "finishedTime": "2022-08-04T02:45:57Z",
            "costSeconds": 1,
            "retryCount": 1,
            "errInfo": {}
        },
        {
            "stepName": "前置检查",
            "stepStatus": "done",
            "ready": true,
            "startTime": "2022-08-04T02:45:57Z",
            "finishedTime": "2022-08-04T02:48:38Z",
            "costSeconds": 161,
            "retryCount": 2,
            "errInfo": {}
        },
        {
            "stepName": "部署 K8S",
            "stepStatus": "done",
            "ready": true,
            "startTime": "2022-08-04T02:48:38Z",
            "finishedTime": "2022-08-04T02:49:20Z",
            "costSeconds": 42,
            "retryCount": 1,
            "errInfo": {}
        },
        {
            "stepName": "等待就绪",
            "stepStatus": "done",
            "ready": true,
            "startTime": "2022-08-04T03:40:41Z",
            "finishedTime": "2022-08-04T03:40:41Z",
            "retryCount": 1,
            "errInfo": {}
        }
    ],
    "requestID": "08eb305a-87fb-4360-8a27-42b9561edf4a"
}
同步节点元信息
描述

同步并更新集群下所有节点的IAAS配置信息。例如：用户变更BCC付费方式，可通过接口进行数据同步。

请求结构

Plain Text复制
POST /v2/sync/cluster/{clusterID}/instances  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必选
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必选
描述
clusterID	String	是	请求的集群ID
requestID	String	是	请求ID
请求示例

Plain Text复制
POST /v2/sync/cluster/cce-f7zeyx1u/instances HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 23a82d7e-954f-4539-b828-ce620eaa97b3
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
    "requestID": "23a82d7e-954f-4539-b828-ce620eaa97b3",
    "clusterID": "cce-f7zeyx1u"
}

Kubeconfig相关接口
更新时间：2025-06-06
查询集群KubeConfig
描述

查询集群 KubeConfig

请求结构

Plain Text复制
GET /v2/kubeconfig/{clusterID}/{type}  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL 参数	集群 ID
type	String	是	URL 参数	Kubeconfig 类型, 可选 [ vpc, public ], 分别表示使用 BLB VPCIP, 使用 BLB EIP.
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
kubeConfig	String	是	kubeconfig 内容
kubeConfigType	String	是	Kubeconfig 类型, 可选 [ vpc, public ], 分别表示使用 BLB VPCIP, 使用 BLB EIP.
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
GET /v2/kubeconfig/cce-br0i4kl5/vpc HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: f3da66d2-4c9f-40c9-aa5c-ab5b2d827361
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8


{
	"kubeConfigType": "vpc",
	"kubeConfig": "apiVersion: v1\nclusters:\n- cluster:\n    certificate-authority-data: LS0tLS1CRUdJTiBDRVJUSUZJQ3SUJBZ0lVQit0NWJteWcydjVHMHRFcnVEdTdMVWxQWnpNd0RRWUpLb1pJaHZjTkFRRUwKQlFBd1p6RUxNQWtHQTFVRUJoTUNRMDR4RURBT0JnTlZCQWdUQjBKbGFVcHBibWN4RURBT0JnTlZCQWNUQjBKbAphVXBwYm1jeERqQU1CZ05WQkFvVEJXcHdZV0Z6TVJRd0VnWURWUVFMRXd0amJHOTFaRzVoZEdsMlpURU9NQXdHCkExVUVBeE1GYW5CaFlYTXdIaGNOTWpBd09USTRNRFF5TURBd1doY05NalV3T1RJM01EUXlNREF3V2pCbk1Rc3cKQ1FZRFZRUUdFd0pEVGpFUU1BNEdBMVVFQ0JNSFFtVnBTbWx1WnpFUU1BNEdBMVVFQnhNSFFtVnBTbWx1WnpFTwpNQXdHQTFVRUNoTUZhbkJoWVhNeEZEQVNCZ05WQkFzVEMyTnNiM1ZrYm1GMGFYWmxNUTR3REFZRFZRUURFd1ZxCmNHRmhjekNDQVNJd0RRWUpLb1pJaHZjTkFRRUJCUUFEZ2dFUEFEQ0NBUW9DZ2dFQkFOWGl3SllPL3ZKMEY2RjMKUWZQN05YaEJ2ekJqMEdRdndjbnI2MHQ5WFFON1cwNFdQcUs2QStXZ2g2NE9UbWs4WGx4RDFEenEwSjErSWZHRwpWdXF6K0kwWjhDOE1ZTEtCWWRsNnlVME5Ya2x5dzRVSkJobVpyTnV2QnpTOXBFQjRrU00ra1d5cGpHOTJTdkZaCjhYM2g1SGx4SzM4L0VzVUxzTlBYWi9UV2dWSGNGazRMNG9BZ0R6bVYrZnV5dnpBOU90TnMrWCtOanBlRzV2ancKcFlCdm5ubFIwZ3ZmMnB4cnVuOVhJcFVKYlJnWUdBVFhXdXVRUnNER2dRRlQ0R2taczUvbWZUSzcrSno4ZkpDNgpCSDNoRWRGYUJ4UWg3ck9Udzg2Z2E4czlzYlBXUDFZc2tINTlXYnZpM1F5TmdsNkxQMFRsRDZKbE8wS2Qxa0VBClFpZ2lzQWtDQXdFQUFhTkNNRUF3RGdZRFZSMFBBUUgvQkFRREFnRUdNQThHQTFVZEV3RUIvd1FGTUFNQkFmOHcKSFFZRFZSME9CQllFRk9FMzY5b0ZJTnBxRi94aFV1TG5aV0VrRTh0R01BMEdDU3FHU0liM0RRRUJDd1VBQTRJQgpBUUJFQXhIVWQrZm5wWERyVXovS2VEeXk0MWlySGVSRUFobDNIaTI1U3ZmSTd2V2ROUVFBUDlmQmp6UysrQ0hoCmRHY0dZL3YyQWJCdW5kekJpV2tsbXlsWVgzR2Y0ZDArcTFXLzcyNVFXRFN5MjE0V2QvNHFOVCtJSWZXZTFtRlgKWmhLVlh0SjN2RldrUEIyYUo3Mld2M0htWDhZUzdqNmhtakhDYTIwT0RIOGloTjZ1bVZLbWd6T1FMLy9Keksyago0ZHQ3MVFaZVJ4cVlkRXVyMTdGLzdsUlRuRG9WaEFiT3A0aG5uZGVzMEc0RFBCbFcwZkFKbEVNeHlXNkhMT3dGCmJLcjlRekM3Y0Z0Y2hRNmxsVVVobnhCQW9QbXIra2NQcjFEVTRxQ1JOUVIvNUxxSk5YdWIyWm10NkdlN3BkRU8KSmZmbVFMYUVTYmJjaVNHWkRJQlpxOEY5Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K\n    server: https://100.64.230.48:6443\n  name: kubernetes\ncontexts:\n- context:\n    cluster: kubernetes\n    user: eca97e148cb74e9683d7b7240829d1\n  name: eca97e148cb74e9683d7b7240829d1@kubernetes\ncurrent-context: eca97e148cb74e9683d7b7240829d1@kubernetes\nkind: Config\npreferences: {}\nusers:\n- name: eca97e148cb74e9683d7b7240829d1\n  user:\n    client-certificate-data: LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCkSdjNYbDM0SmlxZ1dwUnF0alhWVE1zd0RRWUpLb1pJaHZjTkFRRUwKQlFBd1p6RUxNQWtHQTFVRUJoTUNRMDR4RURBT0JnTlZCQWdUQjBKbGFVcHBibWN4RURBT0JnTlZCQWNUQjBKbAphVXBwYm1jeERqQU1CZ05WQkFvVEJXcHdZV0Z6TVJRd0VnWURWUVFMRXd0amJHOTFaRzVoZEdsMlpURU9NQXdHCkExVUVBeE1GYW5CaFlYTXdJQmNOTWpBd09USTRNRFF5TWpBd1doZ1BNakV5TURBNU1EUXdOREl5TURCYU1JR2QKTVFzd0NRWURWUVFHRXdKRFRqRVFNQTRHQTFVRUNCTUhRbVZwU21sdVp6RVFNQTRHQTFVRUJ4TUhRbVZwU21sdQpaekVwTUNjR0ExVUVDaE1nWldOaE9UZGxNVFE0WTJJM05HVTVOamd6WkRkaU56STBNRGd5T1dReFptWXhGREFTCkJnTlZCQXNUQzJOc2IzVmtibUYwYVhabE1Ta3dKd1lEVlFRREV5QmxZMkU1TjJVeE5EaGpZamMwWlRrMk9ETmsKTjJJM01qUXdPREk1WkRGbVpqQ0NBU0l3RFFZSktvWklodmNOQVFFQkJRQURnZ0VQQURDQ0FRb0NnZ0VCQUsxYwpVQ01EdWg3VHVPUlkvMHhzRUZ4MFFTb3hhdWVPSGFuWE5FQ21GQUNwRjEvTmtoQjg4SENhQkhnRS9CYjJWWmUzCm5rOVpyZ3R4TEpJUzl5TUpMQ0lYVnRrVkpGd1NrODErdHgvL290QjF3MkxpWkUwZVFZeDBXU3FUcmgyNDIrN28KaGdDdWtQT0syQkVIa1p5bGtobXBtb3dEZXNTZlVCNG54T0h1djRwSFB0b0x6alhOR2grN1h1UHhzM21FR0NlVgpYUU1Pd1hhNk55YnRJQWpYaWk3YTV6YnRsdFJ5K1ZncWJKYVV6dlZMdjVnWVNRM0krdEZPU1BUeDlDMC91a0lyCjd5NUFpbElOVVB4U1d6NGI4amJiZjYwSU0yNCtrbUpjM1dYWWxZV2daK3BYMlFodUdFNXAxV3JGRWlWTEwrY2YKUWxYdTF1bWRMTmRmZEVFMGdaOENBd0VBQWFPQnFUQ0JwakFPQmdOVkhROEJBZjhFQkFNQ0JhQXdIUVlEVlIwbApCQll3RkFZSUt3WUJCUVVIQXdFR0NDc0dBUVVGQndNQ01Bd0dBMVVkRXdFQi93UUNNQUF3SFFZRFZSME9CQllFCkZBYVk2QVRvakxCOWhiNjVpSDJxOHJ6U0xrT1lNQjhHQTFVZEl3UVlNQmFBRk9FMzY5b0ZJTnBxRi94aFV1TG4KWldFa0U4dEdNQ2NHQTFVZEVRUWdNQjZIQkdSQUIyeUhCR1JBNWpDSEJHUkE1akdIQkdSSXVSMkhCS3dmQUFFdwpEUVlKS29aSWh2Y05BUUVMQlFBRGdnRUJBQThrcGpTeWpVekJDdkx0eC9lWTdUc0c3d0doMFpiVXRseWUrRmg2ClE5QzBodGtzZDJqT3MxRGNCQlRwK3kwdWRDTjdvQy9ab0FXZU0wMFRSeUF6bDc4VjdJZTg3MmVnbkFsQVZTSm4KdTdMVUZJSzJJUEZFalh4SHJ1Z0R2cklVeTgxa1doUHRxVXhQMnpMN1VIbU9rUTl0NC8xNCtHdW9lOTAwaC9xYgo3SWxmL3JrbFFHYnliTDY3TkhVYkg5S0FkVEVUNUI0VzlVRHN4emEreUZtaXYzT0ZJT3o4VU8wbkdYTkJxdnVLCjBaVTEvL2c3cmFjME9kbnVZaC81SzlIZkZNUW43R1EwWWthT2N3VDdCeGdvWlNrUUpsSWJSYkJ0YVZaaklTRDIKUUUvNkJLbklnSkVLUGgyZ25LWkU5OCt0SE1NVkhVbjRQSVBkU1M5cTJoM05Ddk09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K\n    client-key-data: LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQpNSUlFcEFJQkFBS0NBUUVBclZ4UUl3TzZIdE80NUZqL1RHd1FYSFJCS2pGcTU0NGRxZGMwUUtZVUFLa1hYODJTCkVIendjSm9FZUFUOEZ2WlZsN2VlVDFtdUMzRXNraEwzSXdrc0loZFcyUlVrWEJLVHpYNjNILytpMEhYRFl1SmsKVFI1QmpIUlpLcE91SGJqYjd1aUdBSzZRODRyWUVRZVJuS1dTR2FtYWpBTjZ4SjlRSGlmRTRlNi9pa2MrMmd2TwpOYzBhSDd0ZTQvR3plWVFZSjVWZEF3N0Jkcm8zSnUwZ0NOZUtMdHJuTnUyVzFITDVXQ3BzbHBUTzlVdS9tQmhKCkRjajYwVTVJOVBIMExUKzZRaXZ2TGtDS1VnMVEvRkpiUGh2eU50dC9yUWd6Ymo2U1lsemRaZGlWaGFCbjZsZloKQ0c0WVRtblZhc1VTSlVzdjV4OUNWZTdXNlowczExOTBRVFNCbndJREFRQUJBb0lCQUQ4b1ZubXJMZTkxS3ZMbQpDWHlLRWh2Y3JyRDBlQUlNSUhwejBMR016OVM5eGFvOWRtMVRWelZ1cHhvaWxzUzIwZEFJTVVDdloxejd5a1VkCmE3UHo3NFFzQkpQcHcrbFhTMG1lVkpEdnpSMHRDaFhJYk1vN3I1Mi85WXd4YVVtaXcxMXlrUDlHbWNCZ1lQOHoKUnJWUERMOFVyeDA3VjBxeXo3bHN1Nm1rRlZ3R3B2OUlUdE9ncE5PYXpwYWtJczkzNmhteHplMERvRG9IMUtVVgp1bUF3VmFvMXBpM0I0L05UMVhXSGNHb3BoYUw2OHl3WENuMG1HalBlN0NUZ2lidGZaVGhuZDlCTGtTQmlsUkxiClVmZzhKd0lZSldpVWswSWRHbUQwQWhlc3owQlNjNHJTZ1M1N011clBLTDJlQk5ySHk5bWtDYjg4SW9GZXY4bFQKMXpkeDRLRUNnWUVBM3FWTkt4UmFCckZFeGhXcHZsODB1KzJ1YTNXUVE0T01GR3daei8velZiaHlqcnY2S0VxZgplR29xVGlXdU1xRlRqMDk1MnprL0xrNzhlS0UyVVdkMW82R09PclNSZm9lOEhPZjR5MS80SmM5dDNYU3pLamtXCmNWaDhBMG1sd2drMDhpd0ZGbFJRKzRkN0R1c3pvMzBucGgvaUN1N2lXNHRDVUdvYlJpNUFSUlVDZ1lFQXgxVGcKSEQ5dklCU3p1MmF0UG5Jb3FJSFRwZDRiZmhxTkQ4TnJxRkl6aDBDaUVhMlo1OXN3QVZLUVZNNWdYMkRmWUVreQpFTTIyYzlaL1JuR0ljVEhiRU5ieXRRa1EyK0ozWnJjUVRNdVc0REc5d1JlQVd0YUttRi9pOXJoUzFRK05GZlhYCmRPL0VaNDE3cXdxZ0I5aFdsd1B0WFhQRU1sQlJKK2pKMjFtcVFPTUNnWUFXUmJyK2dENnhSTEo0amxvNHJSVjkKWnoxM2luOHdBY3pWamlyVzMrZmJ2MlBXVzMrZTREZ3J0NU1iMWpFaTUzaVFjWWJqSTBycXV3UU9uVEh0MnNldAo0czl6bC9TbUQ3WUZ2ajdwT1dSOWc4NmR4THJYa25ab1NFMi9sbko2Z3FsRlFKb1JyY1djSStWdmpKL1J6d2RVCld3UWx5OWZoQ0lGTndnK1FhYmdNTVFLQmdRQzVGMWdQQXR3MlJ1THFGaHF5aktDeWIvTk81dUpTZzJjUEJ5QlYKcVJiTjliZElnUklUbUpXSDlObXUxZi9wTVBQYTNiek9tNlpiQkFjbEsxRk9Bc1J2YTVqdGYrQ1d2VUN3TVRiQwppSjJ0eXFKdnhWbmJmN0lzY1lVNEljcFFxMk1QekR0b0N5Z3VHOU9FN0pYVEV4QzhvOW5xV0JBTHhFYkhyMEtaCkd6YWJqd0tCZ1FEYzhRS3M2KzBweGk1dUJweFVpenNxZTNCeS9SbXo4QU4vODliazh6USs4WHZVeDQ2djFXL2IKZnRZUTNCM0g1WkhQVmlnV09yVHJ4VlZodjVOajAzVlp6c21hK29TZTN1RlF2VFhhSGdsSG1Tc0VTalIwWlNMNgpVUkY0aGlzV2tOUnkwYWxSSzRPOFBjMkJyR2lKWTdzbFdzd3RRdzdSM3pVeHBZckp1d1dtLS0tLQo=\n",
	"requestID": "f3da66d2-4c9f-40c9-aa5c-ab5b2d827361"
}

Network相关接口
更新时间：2025-08-01
检查集群 ClusterIP 网段是否冲突
描述

检查集群 ClusterIP 网段是否冲突

请求结构

Plain Text复制
POST /v2/net/check_clusterip_cidr  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
ipVersion	String	是	RequestBody 参数	容器网络IP地址版本，可选[ipv4, ipv6, dualStack]
clusterIPCIDR	String	否	RequestBody 参数	Cluster IPv4 网段. IP版本为IPv4时必填
clusterIPCIDRIPv6	String	否	RequestBody 参数	Cluster IPv6 网段. IP版本为IPv6时必填
vpcID	String	是	RequestBody 参数	VPC ID
vpcCIDR	String	否	RequestBody 参数	VPC IPv4 网段. IP版本为IPv4时必填
vpcCIDRIPv6	String	否	RequestBody 参数	VPC IPv6 网段. IP版本为IPv6时必填
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
errMsg	String	否	错误信息
isConflict	String	是	是否冲突
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
POST /v2/net/check_clusterip_cidr  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
	"vpcID": "vpc-pi9fghaxcpnf",
	"vpcCIDR": "192.168.0.0/16",
	"vpcCIDRIPv6": "",
	"clusterIPCIDR": "172.31.0.0/16",
	"clusterIPCIDRIPv6": "",
	"ipVersion": "ipv4"
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: d1b66c3d-b16f-4ff2-bedf-af21f6bcd827
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"isConflict": false,
	"errMsg": "",
	"requestID": "40165eb4-0fc7-405e-bcdf-10ba2ffc1ee3"
}
检查集群容器网段是否冲突（VPC路由模式下使用）
描述

检查集群容器网段是否冲突（VPC路由模式下使用）

请求结构

Plain Text复制
POST /v2/net/check_container_network_cidr  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
ipVersion	String	否	RequestBody 参数	容器网络IP地址版本，默认值为 ipv4，可选 [ ipv4, ipv6, dualStack ]
clusterIPCIDR	String	否	RequestBody 参数	Cluster IPv4 网段. IP 版本为 IPv4 时必填
clusterIPCIDRIPv6	String	否	RequestBody 参数	Cluster IPv6 网段. IP 版本为 IPv6 时必填
containerCIDR	String	否	RequestBody 参数	容器网络 IPv4 网段. IP 版本为 IPv4 时必填
containerCIDRIPv6	String	否	RequestBody 参数	容器网络 IPv6 网段. IP 版本为 IPv6 时必填
maxPodsPerNode	Integer	是	RequestBody 参数	单节点最大容器组数量
vpcID	String	是	RequestBody 参数	VPC ID
vpcCIDR	String	否	RequestBody 参数	VPC IPv4 网段. IP版本为IPv4时必填
vpcCIDRIPv6	String	否	RequestBody 参数	VPC IPv6 网段. IP版本为IPv6时必填
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
clusterIPCIDRConflict	ClusterIPCIDRConflict	否	ClusterIP 网段冲突信息
containerCIDRConflict	ContainerCIDRConflict	否	容器网段冲突信息
errMsg	String	否	错误信息
isConflict	String	是	是否冲突
maxNodeNum	String	是	最大节点数量
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
POST /v2/net/check_container_network_cidr HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
	"vpcID": "vpc-pi9fghaxcpnf",
	"vpcCIDR": "192.168.0.0/16",
	"vpcCIDRIPv6": "",
	"containerCIDR": "172.28.0.0/16",
	"containerCIDRIPv6": "",
	"clusterIPCIDR": "172.31.0.0/16",
	"clusterIPCIDRIPv6": "",
	"maxPodsPerNode": 256,
	"ipVersion": "ipv4"
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: a2c5b12b-6005-4266-a8e8-f5b3d903a5c7
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"maxNodeNum": 256,
	"isConflict": false,
	"errMsg": "",
	"containerCIDRConflict": null,
	"clusterIPCIDRConflict": null,
	"requestID": "a2c5b12b-6005-4266-a8e8-f5b3d903a5c7"
}
推荐集群 ClusterIP 网段
描述

推荐集群 ClusterIP 网段

请求结构

Plain Text复制
POST /v2/net/recommend_clusterip_cidr  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterMaxServiceNum	Integer	是	RequestBody 参数	集群最大 Service 数量
ipVersion	String	否	RequestBody 参数	容器网络IP地址版本，默认值为 ipv4，可选 [ ipv4, ipv6, dualStack ]
containerCIDR	String	否	RequestBody 参数	容器网络 IPv4 网段. IP 版本为 IPv4 时必填
containerCIDRIPv6	String	否	RequestBody 参数	容器网络 IPv6 网段. IP 版本为 IPv6 时必填
privateNetCIDRs	List<String>	否	RequestBody 参数	IPv4私有网络地址段，可选 [ 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 ]
privateNetCIDRIPv6s	List<String>	否	RequestBody 参数	IPv6私有网络地址段，目前仅支持 [ fc00::/7 ]
vpcCIDR	String	否	RequestBody 参数	VPC IPv4 网段. IP版本为IPv4时必填
vpcCIDRIPv6	String	否	RequestBody 参数	VPC IPv6 网段. IP版本为IPv6时必填
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
errMsg	String	否	错误信息
isSuccess	Boolean	是	请求是否成功
recommendedClusterIPCIDRs	List<String>	否	推荐 Cluster IP 网段
recommendedClusterIPCIDRIPv6s	List<String>	否	推荐 Cluster IP 网段 IPv6
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
POST /v2/net/recommend_clusterip_cidr HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
	"vpcCIDR": "192.168.0.0/16",
	"vpcCIDRIPv6": "",
	"containerCIDR": "172.28.0.0/16",
	"containerCIDRIPv6": "",
	"clusterMaxServiceNum": 8,
	"privateNetCIDRs": [
		"172.16.0.0/12"
	],
	"privateNetCIDRIPv6s": null,
	"ipVersion": "ipv4"
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 79f1993e-fc76-41c3-8f20-a22bd1010324
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"recommendedClusterIPCIDRs": [
		"172.31.255.248/29",
		"172.31.255.240/29",
		"172.31.255.232/29",
		"172.31.255.224/29",
		"172.31.255.216/29"
	],
	"recommendedClusterIPCIDRIPv6s": null,
	"isSuccess": true,
	"errMsg": "",
	"requestID": "79f1993e-fc76-41c3-8f20-a22bd1010324"
}
推荐集群容器网段（VPC路由模式下使用）
描述

推荐集群容器网段（VPC路由模式下使用）

请求结构

Plain Text复制
POST /v2/net/recommend_container_cidr  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterMaxNodeNum	Integer	是	RequestBody 参数	集群最大节点数
ipVersion	String	否	RequestBody 参数	容器网络IP地址版本，默认值为 ipv4，可选 [ ipv4, ipv6, dualStack ]
k8sVersion	String	是	RequestBody 参数	集群的K8S版本
maxPodsPerNode	Integer	是	RequestBody 参数	单节点最大容器组数量
privateNetCIDRs	List<String>	否	RequestBody 参数	IPv4私有网络地址段，可选 [ 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 ]
privateNetCIDRIPv6s	List<String>	否	RequestBody 参数	IPv6私有网络地址段，目前仅支持 [ fc00::/7 ]
vpcID	String	是	RequestBody 参数	VPC ID
vpcCIDR	String	否	RequestBody 参数	VPC IPv4 网段. IP版本为IPv4时必填
vpcCIDRIPv6	String	否	RequestBody 参数	VPC IPv6 网段. IP版本为IPv6时必填
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
errMsg	String	否	错误信息
isSuccess	Boolean	是	请求是否成功
recommendedContainerCIDRs	List<String>	否	推荐容器网段
recommendedContainerCIDRIPv6s	List<String>	否	推荐容器网段 IPv6
requestID	String	是	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
POST /v2/net/recommend_container_cidr  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
	"vpcID": "vpc-pi9fghaxcpnf",
	"vpcCIDR": "192.168.0.0/16",
	"vpcCIDRIPv6": "",
	"clusterMaxNodeNum": 2,
	"maxPodsPerNode": 32,
	"privateNetCIDRs": [
		"172.16.0.0/12"
	],
	"privateNetCIDRIPv6s": null,
	"k8sVersion": "1.16.8",
	"ipVersion": "ipv4"
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 162b630e-38f9-4b31-addc-f89339058e70
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"recommendedContainerCIDRs": [
		"172.16.0.0/26",
		"172.16.0.64/26",
		"172.16.0.128/26",
		"172.16.0.192/26",
		"172.16.1.0/26"
	],
	"recommendedContainerCIDRIPv6s": null,
	"isSuccess": true,
	"errMsg": "",
	"requestID": "162b630e-38f9-4b31-addc-f89339058e70"
}
检查辅助网段是否与当前私有网络内已有路由冲突
描述

检查辅助网段是否与当前vpc内已有路由冲突

请求结构

Plain Text复制
POST /v2/net/check_auxiliaryip_cidr  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
ipVersion	String	是	RequestBody 参数	容器网络IP地址版本，可选[ipv4, ipv6, dualStack]
ContainerCIDR	String	否	RequestBody 参数	Container IPv4 网段. IP版本为IPv4时必填
ContainerCIDRIPv6	String	否	RequestBody 参数	Container IPv6 网段. IP版本为IPv6时必填
vpcID	String	是	RequestBody 参数	VPC ID
vpcCIDR	String	否	RequestBody 参数	VPC IPv4 网段. IP版本为IPv4时必填
vpcCIDRIPv6	String	否	RequestBody 参数	VPC IPv6 网段. IP版本为IPv6时必填
isEBPF	Bool	是	RequestBody 参数	集群是否启用了DataPath V2
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
errMsg	String	否	错误信息
isConflict	Bool	是	是否冲突
requestID	String	是	请求 ID, 问题定位提供该 ID
isAuxiliary	Bool	是	在启用DataPath V2时使用，用于判断是否为辅助网段
请求示例

Plain Text复制
POST /v2/net/check_auxiliaryip_cidr  HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
    "vpcID": "vpc-pi9fghaxcpnf",
    "vpcCIDR": "192.168.0.0/16",
    "vpcCIDRIPv6": "",
    "ContainerCIDR": "172.31.0.0/16",
    "ContainerCIDRIPv6": "",
    "ipVersion": "ipv4"
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: d1b66c3d-b16f-4ff2-bedf-af21f6bcd827
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
    "isConflict": false,
    "errMsg": "",
    "requestID": "d1b66c3d-b16f-4ff2-bedf-af21f6bcd827",
    "isAuxiliary": true
}

Task相关接口
更新时间：2026-03-23
获取任务列表
描述

获取任务列表

请求结构

Plain Text复制
GET /v2/tasks/{taskType} HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
taskType	String	是	Path 参数	任务类型，当前仅支持 InstanceGroupReplicas。
targetID	String	是	Query 参数	任务目标对象 ID，任务类型为 InstanceGroupReplicas 时，targetID 是目标节点组的 ID
operationType	String	否	Query 参数	操作类型，目前支持[ScalingUp, ScalingDown, Repair, ExistedScaleup]，ScalingUp表示扩容，ScalingDown表示缩容，Repair 表示修改期望节点数的伸缩处理，ExistedScaleup表示添加已有节点到节点组的处理
phase	String	否	Query 参数	任务状态，目前支持[Pending, Processing, Done, Aborted, Collecting]
order	String	否	Query 参数	排序方式，目前支持[ASC,DESC], 默认为DESC(降序)，如果传ASC需要保证orderBy非空才有效。
orderBy	String	否	Query 参数	排序字段，目前仅支持[startTime], 默认为startTime（创建时间）
pageNo	Integer	否	Query 参数	查询页码序号。 为0时不分页
pageSize	Integer	否	Query 参数	查询结果每页条目数。为0时不分页
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
描述
page	ListTaskPage	任务查询结果页
requestID	String	请求 ID, 问题定位提供该 ID
请求示例

Plain Text复制
GET /api/cce/service/v2/tasks/InstanceGroupReplicas?targetID=cce-ig-h5zc8dqu&pageNo=1&pageSize=2 HTTP/1.1
Host: cce.bj.baidubce.com
Content-Type: application/json
Authorization: authorization string
返回示例

JSON复制
{
    "requestID": "dc172e92-67b1-4697-97f7-ded9cccfa455",
    "page": {
        "pageNo": 1,
        "pageSize": 2,
        "totalCount": 5,
        "items": [
            {
                "id": "task-cce-ig-h5zc8dqu-scaleupexist-2w2snkxf",
                "type": "InstanceGroupReplicas",
                "description": "attach 4 instances to instancegroup",
                "startTime": "2025-04-11T11:39:40Z",
                "finishTime": "2025-04-11T11:47:09Z",
                "phase": "Done",
                "processes": [
                    {
                        "name": "MoveExistedInstanceIntoInstanceGroup",
                        "phase": "Done",
                        "startTime": "2025-04-11T19:39:41+08:00",
                        "finishTime": "2025-04-11T19:47:09+08:00",
                        "metrics": {
                            "cce-fm8eewfh-5v7gw5g2": "create_failed",
                            "cce-fm8eewfh-iw5kw5pu": "running",
                            "cce-fm8eewfh-l3f4lsbd": "running",
                            "cce-fm8eewfh-obgcevn2": "running"
                        }
                    }
                ]
            },
            {
                "id": "task-cce-ig-h5zc8dqu-scaledown-9xejb2fj",
                "type": "InstanceGroupReplicas",
                "description": "remove specified instances from instance group",
                "startTime": "2025-04-11T11:32:56Z",
                "finishTime": "2025-04-11T11:37:10Z",
                "phase": "Done",
                "processes": [
                    {
                        "name": "RemoveInstancesFromInstanceGroup",
                        "phase": "Done",
                        "startTime": "2025-04-11T19:32:56+08:00",
                        "finishTime": "2025-04-11T19:37:10+08:00",
                        "metrics": {
                            "cce-fm8eewfh-60cyxs3v": "Succeed",
                            "cce-fm8eewfh-djzjnidb": "Succeed",
                            "cce-fm8eewfh-nom6v0on": "Succeed",
                            "cce-fm8eewfh-qbdqj6aj": "Succeed"
                        }
                    }
                ]
            }
        ]
    }
}
查看任务详情
描述

查看任务详情

请求结构

Plain Text复制
GET /v2/task/{taskType}/{taskID} HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
taskType	String	是	Path 参数	任务类型，当前仅支持 InstanceGroupReplicas。
taskID	String	是	Path 参数	任务 ID。
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
描述
task	Task	任务详情
requestID	String	请求 ID, 问题定位提供该 ID
请求示例

Http复制
GET /api/cce/service/v2/task/InstanceGroupReplicas/task-cce-ig-h5zc8dqu-scaleupexist-2w2snkxf HTTP/1.1
Host: cce.bj.baidubce.com
Content-Type: application/json
Authorization: authorization string
返回示例

Plain Text复制
{
    "requestID": "58731113-1d37-49e8-8644-afbc55cee5ef",
    "task": {
        "id": "task-cce-ig-h5zc8dqu-scaleupexist-2w2snkxf",
        "type": "InstanceGroupReplicas",
        "description": "attach 4 instances to instancegroup",
        "startTime": "2025-04-11T11:39:40Z",
        "finishTime": "2025-04-11T11:47:09Z",
        "phase": "Done",
        "processes": [
            {
                "name": "MoveExistedInstanceIntoInstanceGroup",
                "phase": "Done",
                "startTime": "2025-04-11T19:39:41+08:00",
                "finishTime": "2025-04-11T19:47:09+08:00",
                "metrics": {
                    "cce-fm8eewfh-5v7gw5g2": "create_failed",
                    "cce-fm8eewfh-iw5kw5pu": "running",
                    "cce-fm8eewfh-l3f4lsbd": "running",
                    "cce-fm8eewfh-obgcevn2": "running"
                }
            }
        ]
    }
}

组件管理相关接口
更新时间：2023-07-06
组件管理相关接口
获取组件状态
获取组件的基本信息与状态。

如果已经安装，还会返回部署参数等信息。

请求结构

Plain Text复制
GET /v2/cluster/{ClusterID}/addon
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL参数	集群ID。
addons	String	否	Query参数	为空时查询所有组件的信息。查询多个组件时按逗号分隔，如cce-ingress-controller,cce-gpu-controller。取值参考文档末尾附录。
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
requestID	String	是	请求ID，问题定位提供该ID。
items	List<AddOnInfo>	否	组件查询结果。每个数组元素是一个组件的查询结果。
code	String	否	错误代码，仅在请求失败时存在。
message	String	否	错误信息，仅在请求失败时存在。
请求示例

Plain Text复制
GET /v2/cluster/cce-5e130ugt/addon?addons=cce-ingress-controller HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: aef503ab-66e2-4b7f-9044-e922389ed03f
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
    "items": [
        {
            "meta": {
                "name": "cce-ingress-controller",
                "type": "Networking",
                "latestVersion": "1.3.5",
                "shortIntroduction": "基于百度云应用型负载均衡产品（应用型BLB）实现K8S Ingress语义，提供七层网络负载均衡能力",
                "defaultParams": "\n# Default values for cce-ingress-controller\n# This is a YAML-formatted file.\n# Declare variables to be passed into your templates.\n\nClusterVersion: v2\nImageID: registry.baidubce.com/cce-plugin-dev/cce-ingress-controller:rc853b4b_20230117\n\nOpenCCEGatewayEndpoint:\nBLBOpenAPIEndpoint:\nEIPOpenAPIEndpoint:\nVPCEndpoint:\nCCEV2Endpoint:\nTagEndpoint:\n\nEIPPurchaseType:\n\nRegion:   # 集群地域\nClusterID: # 集群id\nConcurrentIngressSyncs: # 最多同时处理的 Service 的数量\nDefaultMaxRSCount: # 组件默认为 BLB 挂载的最大后端数\n",
                "installInfo": {
                    "allowInstall": true
                }
            },
            "instance": {
                "name": "cce-ingress-controller",
                "installedVersion": "2022.11.08.1552",
                "params": "# No Params",
                "status": {
                    "phase": "Running"
                },
                "uninstallInfo": {
                    "allowUninstall": true
                },
                "upgradeInfo": {
                    "allowUpgrade": false,
                    "nextVersion": "",
                    "message": "暂不支持升级版本"
                },
                "updateInfo": {
                    "allowUpdate": false,
                    "message": "不支持更新参数"
                }
            }
        }
    ],
    "requestID": "62709f56-3f0b-4fcc-86e0-c18547ba1ce7"
}
安装组件
向集群中安装组件。

每个组件需要的安装参数不同，部署参数均以字符串的形式传入。

请求结构

Plain Text复制
POST /v2/cluster/{ClusterID}/addon 
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL参数	集群ID。
name	String	是	Request Body参数	要安装的组件名称 。
params	String	否	Request Body参数	组件安装参数。每个组件需要的参数不同，请参照【附录】部分。部分组件不需要设置安装参数。
version	String	否	Request Body参数	要指定安装的组件版本。通常不需要设置该参数。
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
requestID	String	是	请求ID，问题定位提供该ID。
code	String	否	错误代码，仅在请求失败时存在。
message	String	否	错误信息，仅在请求失败时存在。
请求示例

Plain Text复制
POST /v2/cluster/cce-5e130ugt/addon HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
    "name": "cce-gpu-manager",
    "params": "EnableHook: true\nEnableSGPU: true\n\n"
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 6f593304-6787-45ea-8e0f-426ee331cc8b
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"requestID": "6f593304-6787-45ea-8e0f-426ee331cc8b"
}
卸载组件
卸载集群中已经安装的组件。

请求结构

Plain Text复制
DELETE /v2/cluster/{ClusterID}/addon 
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL参数	集群ID。
name	String	是	Request Body参数	要卸载的组件名称。
instanceName	String	否	Request Body参数	要卸载的组件实例名称。仅在允许多实例部署的组件中，用于指定要卸载的组件实例。通常不会使用到该字段。
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
requestID	String	是	请求ID，问题定位提供该ID。
code	String	否	错误代码，仅在请求失败时存在。
message	String	否	错误信息，仅在请求失败时存在。
请求示例

Plain Text复制
DELETE /v2/cluster/cce-5e130ugt/addon HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
    "name": "cce-ingress-controller"
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 6f593304-6787-45ea-8e0f-426ee331cc8b
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"requestID": "6f593304-6787-45ea-8e0f-426ee331cc8b"
}
更新组件部署参数
更新集群中已经安装的组件的部署参数。

请求结构

Plain Text复制
PUT /v2/cluster/{ClusterID}/addon 
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL参数	集群ID。
name	String	是	Request Body参数	要更新的组件名称。
instanceName	String	否	Request Body参数	要更新的组件实例名称。仅在允许多实例部署的组件中，用于指定要更新的组件实例。通常不会使用到该字段。
params	String	是	Request Body参数	要更新的部署参数。
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
requestID	String	是	请求ID，问题定位提供该ID。
code	String	否	错误代码，仅在请求失败时存在。
message	String	否	错误信息，仅在请求失败时存在。
请求示例

Plain Text复制
PUT /v2/cluster/cce-mehgoi9r/addon HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
    "name": "cce-hybrid-manager",
    "params": "A: a"
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 6f593304-6787-45ea-8e0f-426ee331cc8b
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"requestID": "6f593304-6787-45ea-8e0f-426ee331cc8b"
}
升级组件
升级集群中已经安装的组件的版本。

请求结构

Plain Text复制
POST /v2/cluster/{ClusterID}/addon/upgrade
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必须
参数位置
描述
clusterID	String	是	URL参数	集群ID。
name	String	是	Request Body参数	要升级的组件名称。
targetVersion	String	否	Request Body参数	升级的目标版本。通常不会使用到该字段，目标版本由后台自动决定。
instanceName	String	否	Request Body参数	要升级的组件实例名称。仅在允许多实例部署的组件中，用于指定要升级的组件实例。通常不会使用到该字段。
params	String	否	Request Body参数	要在升级时同时更新的参数。通常不会使用到该字段。
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
是否必须
描述
requestID	String	是	请求ID，问题定位提供该ID。
code	String	否	错误代码，仅在请求失败时存在。
message	String	否	错误信息，仅在请求失败时存在。
请求示例

Plain Text复制
POST /v2/cluster/cce-jx4l7afz/addon/upgrade HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de

{
    "name": "cce-npu-manager"
}
返回示例

Plain Text复制
HTTP/1.1 200 OK
X-Bce-Request-Id: 6f593304-6787-45ea-8e0f-426ee331cc8b
Date: Thu, 16 Mar 2020 06:29:48 GMT
Content-Type: application/json;charset=UTF-8

{
	"requestID": "6f593304-6787-45ea-8e0f-426ee331cc8b"
}
组件名称列表
组件名称
参数名称
CCE GPU Manager	cce-gpu-manager
CCE AI Job Scheduler	cce-volcano
CCE RDMA Device Plugin	cce-rdma-plugin
CCE PaddleFlow	cce-paddleflow
CCE Fluid	cce-fluid
CCE Deep Learning Frameworks Operator	cce-aibox
CCE Image Accelerate	cce-image-accelerate
CCE Hybrid Manager	cce-hybrid-manager
CCE Ingress NGINX Controller	cce-ingress-nginx-controller
CCE Ingress Controller	cce-ingress-controller
CCE CSI CDS Plugin	cce-csi-cds-plugin
CCE CSI BOS Plugin	cce-csi-bos-plugin
CCE CSI PFS Plugin	cce-csi-pfs-plugin
CCE NPU Manager	cce-npu-manager
CCE Log Operator	cce-log-operator
组件示例参数
CCE GPU Manager
YAML复制
EnableSGPU: false # true 使用内核态隔离，false 使用用户态隔离
GPUShareMemoryUnit: GiB # 显存共享资源上报单位 GiB/MiB
IgnoreDeviceType: false # 是否为不区分卡类型，默认 false 为上报资源中带有卡型号
CCE AI Job Scheduler
YAML复制
Binpack: true # Binpack: false 表示启用 spread
Reclaimgang: true # 是否开启队列内抢占
Preemptgang: true # 是否开启队列间抢占
CCE RDMA Device Plugin
该组件不需要用户设置参数

CCE PaddleFlow
YAML复制
global:
  PF_SELFED_DB_ENABLED: &selfd_mysql true
  PF_DB_DATABASE: &pf_db_database paddleflow
  PF_DB_HOST: &pf_db_host mysql-standalone
  PF_DB_PASSWORD: &mysqlpwd Paddle@2022
  PF_DB_USER: &pf_db_user root
  PF_DB_PORT: &pf_db_port 3306
  PF_SVC_TYPE: &pf_svc_type NodePort
  PF_SERVER_NODE_PORT: &pf_server_node_port 30999
  PF_LB_IP: &eip "0.0.0.0"
  CCE_LB_ID: "lb-12345678"
  CCE_LB_SBN_ID: "sbn-123456789123"
  CCE_LB_INTERNAL: true
  CCE_LB_POD_DERICT: false
  IMAGE_REPOSITORY: registry.baidubce.com/cce-plugin-dev/paddleflow

paddleflow-server:
  out_depend_msg:
    PF_DB_DATABASE: *pf_db_database
    PF_DB_HOST: *pf_db_host
    PF_DB_PASSWORD: *mysqlpwd
    PF_DB_PORT: *pf_db_port
    PF_DB_USER: *pf_db_user
  paddleflow_server:
    service:
      extra_usr_define_services:
        paddleflow-server:
          ports:
            port-0:
              nodePort: *pf_server_node_port
          loadBalancerIP: *eip
          type: *pf_svc_type


paddleflow-db-init:
  out_depend_msg:
    PF_DB_DATABASE: *pf_db_database
    PF_DB_HOST: *pf_db_host
    PF_DB_PASSWORD: *mysqlpwd
    PF_DB_PORT: *pf_db_port
    PF_DB_USER: *pf_db_user


mysql-replication:
  enabled: *selfd_mysql
  fullnameOverride: *pf_db_host
  nameOverride: *pf_db_host
  auth:
    rootPassword: *mysqlpwd
    database: *pf_db_database
    username: *pf_db_user
    password: *mysqlpwd
  primary:
    service:
      port: *pf_db_port
CCE Fluid
该组件不需要用户设置参数

CCE Deep Learning Frameworks Operator
YAML复制
TFOperatorEnable: false
MPIOperatorEnable: false
PyTorchOperatorEnable: false
PaddleOperatorEnable: false
MXNetOperatorEnable: false
AITrainingOperatorEnable: false
CCE Image Accelerate
该组件不需要用户设置参数

CCE Hybrid Manager
YAML复制
version:
  scheduler: 1.2.8
  hybridlet: 1.2.8

globalSLA:
  cpu:
    highPercent: 65
    bestEffortMaxCores: 60
  memory:
    highPercent: 80
    bestEffortMax: 60
  net:
    inHigh: 10000
    bestEffortInHigh: 10000
    outHigh: 10000
    bestEffortOutHigh: 10000
  coolDownSec: 10
  expulsionDelaySec: 60
  maxInstances: 256
CCE Ingress NGINX Controller
YAML复制
controller:
  ingressClass: ads
  kind: DaemonSet
  nodeSelector:
    instance-group-id: cce-ig-ubn1700b
  resources:
    limits:
      cpu: 0.5
      memory: 1024Mi
    requests:
      cpu: 0.25
      memory: 256Mi
  scope:
    enabled: false
    namespace: ""
  service:
    annotations:
      service.beta.kubernetes.io/cce-load-balancer-internal-vpc: true
  tolerations: []
fullnameOverride: ads-ngx-control
isArchArm64: false
CCE Ingress Controller
该组件不需要用户设置参数

CCE CSI CDS Plugin
YAML复制
maxVolumesPerNode: 5 # maxVolumesPerNode 集群中每个节点最大可以挂载的 CDS PV 数量
cluster:             # kubeletRootPath 用户节点 Kubelet 数据目录。要将集群所有节点出现过的数据目录都列在这里。如果节点没有特别修改过 kubelet 数据目录，这里可以不传。
  nodes:
    - kubeletRootPath: "/home/cce/kubelet"
      kubeletRootPathAffinity: true
    - kubeletRootPath: "/data/kubelet"
      kubeletRootPathAffinity: true
    - kubeletRootPath: "/var/lib/kubelet"
      kubeletRootPathAffinity: true
CCE CSI BOS Plugin
YAML复制
maxVolumesPerNode: 5 # maxVolumesPerNode 集群中每个节点最大可以挂载的 BOS PV 数量
cluster:             # kubeletRootPath 用户节点 Kubelet 数据目录。要将集群所有节点出现过的数据目录都列在这里。如果节点没有特别修改过 kubelet 数据目录，这里可以不传。
  nodes: 
  - kubeletRootPath: "/home/cce/kubelet"
    kubeletRootPathAffinity: true
  - kubeletRootPath: "/data/kubelet"
    kubeletRootPathAffinity: true
  - kubeletRootPath: "/var/lib/kubelet"
    kubeletRootPathAffinity: true
CCE CSI PFS Plugin
YAML复制
pfs:
  configEndpoint: ""     # configEndpoint PFS 连接地址和端口
  parentDir: /kubernetes # parentDir 代表CSI有权限读写的子路径，需要使用静态PV挂载的路径必须在这个路径之内。最大可以填 /，默认为 /kubernetes。挂载前需确认该路径已经对CCE集群机器授权。
nodes:                   # kubeletRootPath 用户节点 Kubelet 数据目录。要将集群所有节点出现过的数据目录都列在这里。如果节点没有特别修改过 kubelet 数据目录，这里可以不传。
  - kubeletRootPath: "/var/lib/kubelet"
    kubeletRootPathAffinity: true
  - kubeletRootPath: "/home/cce/kubelet"
    kubeletRootPathAffinity: true
  - kubeletRootPath: "/data/kubelet"
    kubeletRootPathAffinity: true
CCE NPU Manager
YAML复制
XPUUseSriov: false # 开启则使用硬件隔离切分，不支持虚机
XPUSriovNumVfs: 3  # 指定昆仑硬件切分的份数
CCE Log Operator
该组件不需要用户设置参数


附录
更新时间：2026-03-13
ClusterSpec
参数名称
类型
是否必须
描述
clusterID	String	否	集群ID. 创建集群时不需要传递此字段
clusterName	String	是	集群名称. 集群名称只能包含英文大小写字母、数字、-、.、和_ 名称长度不超过65个字符，不可为空
clusterType	String	否	集群类型，目前仅支持 normal. 默认值 normal
description	String	否	集群描述
k8sVersion	String	是	K8S版本号，可选 [ 1.18.9, 1.20.8, 1.21.14, 1.22.5, 1.24.4, 1.26.9 ]
runtimeType	String	否	容器运行时类型，可选 [docker, containerd, bci] 一般集群默认值 docker, Serverless集群默认为BCI
runtimeVersion	String	否	容器运行时的版本，目前仅支持18.9.2. 默认值18.9.2
vpcID	String	是	VPC ID
vpcCIDR	String	否	VPC 网段 创建集群时无需设置此值
vpcCIDRIPv6	String	否	VPC IPv6 网段 创建集群时无需设置此值
plugins	List<String>	否	插件列表 支持的插件包括 [ cce-ingress-controller，cluster-autoscaler，core-dns，core-dns-for-serverless，cronhpa，ip-masq-agent，kongming-nvidia，kube-proxy，kunlun-nvidia，metrics-adapter，metrics-server，network-inspector，nvidia-gpu，vpc-cni，vpc-route ] 其中core-dns、kube-proxy, metrics-server会在所有集群默认部署；容器网络模式为kubenet时会默认部署ip-masq-agent；GPU 共享型集群会默认部署kongming-nvidia，否则会部署nvidia-gpu； VPC路由模式CNI时会部署vpc-route，VPC辅助IP模式会部署vpc-cni；
masterConfig	MasterConfig	是	Master节点配置
containerNetworkConfig	ContainerNetworkConfig	是	容器网络配置
k8sCustomConfig	K8SCustomConfig	否	K8S自定义配置
PluginsConfig	map[string]PluginHelmConfig	否	插件 Helm 安装配置
ForbidDelete	bool	否	集群删除保护标识，true 表示开启删除保护不允许删除集群；false 表示关闭删除保护允许删除集群
ResourceChargingOption	ResourceChargingOption	否	IaaS资源付费选项
AuthenticateMode	string	否	APIServer 认证模式，可选x509、oidc
Tags	List<Tag>	否	标签
CreateClusterOptions
参数名称
类型
是否必须
描述
skipNetworkCheck	Boolean	否	是否强行跳过容器网络的检查
MasterConfig
参数名称
类型
是否必须
描述
masterType	String	是	Master 部署类型，新建可选 [ managedPro, containerizedCustom, serverless ] 。接口返回的可能值有：[ managed, managedPro, custom, containerizedCustom, serverless ] 。
clusterHA	Integer	否	Master 副本数，可选 [ 1, 3, 5, 2 ]. 对于托管型集群其值可选[ 1, 3 ],默认值为3. 对于Serverless集群其值仅可为2. 自定义集群无需设置此值.
exposedPublic	Boolean	否	是否向公网暴露
clusterBLBVPCSubnetID	String	否	集群的 BLB VPC 子网 ID. 托管型集群无需设置此值, 自定义集群必须设置此值.
managedClusterMasterOption	ManagedClusterMasterOption	否	托管型集群的 Master 节点选项. 仅在集群类型是托管型时需要设置.
serverlessMasterOption	ServerlessMasterOption	否	Serverless Master 节点选项. 仅在集群类型是Serverless时需要设置
ManagedClusterMasterOption
参数名称
类型
是否必须
描述
masterVPCSubnetZone	String	否	Master 所在的 VPC 子网区域，可选 [ zoneA, zoneB, zoneC, zoneD, zoneE, zoneF ]. 默认值为zoneA.
masterFlavor	String	否	托管集群规格，可选 [ L50, L200, L500, L1000, L3000, L5000 ]. 默认值为L50.
clusterBLBSource	String	否	集群Apiserver使用的BLB归属，默认值为USER.
ServerlessMasterOption
参数名称
类型
是否必须
描述
masterSecurityGroupID	String	否	集群master安全组，后台自动覆盖，用户无需手动填写
vkSecurityGroupID	String	是	集群中启动的bci实例的安全组
vkSubnets	List<VKSubnetType>	否	集群中启动的bci实例所在的子网列表，如果不传将会使用 clusterBLBVPCSubnetID
ContainerNetworkConfig
参数名称
类型
是否必须
描述
mode	String	是	容器的网络模式，可选 [ kubenet, vpc-cni, vpc-route-veth, vpc-route-ipvlan, vpc-route-auto-detect, vpc-secondary-ip-veth, vpc-secondary-ip-ipvlan, vpc-secondary-ip-auto-detect ]
eniVPCSubnetIDs	Map<String,List<String>>	否	ENI VPC 子网 ID
eniSecurityGroupID	String	否	ENI 安全组ID
ipVersion	String	否	容器IP类型，可选 [ipv4, ipv6, dualStack]，默认值ipv4
lbServiceVPCSubnetID	String	是	关联 BLB 所在子网 ID
nodePortRangeMax	Integer	否	指定 NodePort Service 的端口范围，默认值32767, 最大值65536
nodePortRangeMin	Integer	否	指定 NodePort Service 的端口范围，默认值30000, 最大值65536
clusterPodCIDR	String	否	集群 Pod IP 网段, 在 kubenet 网络模式下有效. 网络类型是VPC-CNI时自动使用VPC的CIDR
clusterPodCIDRIPv6	String	否	集群 Pod IPv6 网段, 在 kubenet 网络模式下有效.网络类型是VPC-CNI时自动使用VPC的CIDR
clusterIPServiceCIDR	String	否	Service ClusterIP 的网段. ipv4时设置
clusterIPServiceCIDRIPv6	String	否	Service ClusterIP 的 IPv6 网段. ipv6时设置
maxPodsPerNode	Integer	否	每个 Node 上最大的 Pod 数，默认值128
kubeProxyMode	String	否	kube-proxy 代理模式，可选 [ ipvs, iptables ]，默认值为 ipvs
K8SCustomConfig
参数名称
类型
是否必须
描述
masterFeatureGates	Map<String,Boolean>	否	自定义 MasterFeatureGates
nodeFeatureGates	Map<String,Boolean>	否	自定义 NodeFeatureGates
admissionPlugins	List<String>	否	自定义 AdmissionPlugins
pauseImage	String	否	自定义 PauseImage
kubeAPIQPS	Integer	否	自定义 KubeAPIQPS
kubeAPIBurst	Integer	否	自定义 KubeAPIBurst
schedulerPredicates	List<String>	否	自定义 SchedulerPredicates
schedulerPriorities	Map<String,Integer>	否	自定义 SchedulerPrioritiess
etcdDataPath	String	否	自定义 etcd 数据目录
InstanceSet
参数名称
类型
是否必须
描述
instanceSpec	InstanceSpec	是	节点配置信息
count	Integer	否	使用上述配置的节点数量. 当节点配置是已有节点时无需设置此值
InstanceSpec
参数名称
类型
是否必须
描述
cceInstanceID	String	否	用于 CCE 唯一标识 Instance 如果用户不指定: CCE 默认生成；如果用户指定: CCE 按照规则生成
instanceName	String	否	节点名称
runtimeType	String	否	容器运行时类型，可选 [containerd, docker] 一般默认值为containerd, 如何选型，请参见如何选择 Kubernetes 集群的容器运行时组件
runtimeVersion	String	否	容器运行时的版本，默认推荐次新版本
clusterID	String	否	集群 ID. 在创建集群时无需填写
clusterRole	String	否	节点在集群中的角色，可选 [ master, node ]. 创建集群时无需填写.
instanceGroupID	String	否	节点所属节点组 ID
instanceGroupName	String	否	节点所属节点组名称
masterType	String	否	Master 机器来源。可选 [ managedPro, containerizedCustom, serverless ] 。接口返回的可能值有：[ managed, managedPro, custom, containerizedCustom, serverless ]。
existed	Boolean	否	是否为已有节点. 仅在节点类型为已有节点时需要设置
existedOption	ExistedOption	否	已有实例相关配置. 仅在节点类型为已有节点时需要设置.
machineType	String	否	机器类型，可选 [ BCC, BBC, Metal, BCI ]. 用户无需设置此值. 对于Serverless自动设为BCI. 对于托管型集群的Master自动设为BCC. 其他新建节点自动设为BCC. 已有节点会根据其节点类型自动设为BCC或BBC
instanceType	String	否	机器规格，可选 [ N1, N2, N3, N4, N5, C1, C2, S1, G1, F1, ServerlessMaster ]. 详情参考：实例规格 仅自定义新建节点需要设置. 对于Serverless集群的Master自动设为ServerlessMaster. 对于托管型集群的Master使用DefaultMasterConfig中配置. 已有节点使用本节点的节点类型
deploySetID	String	否	部署集 ID
deploySetIDs	List<String>	否	多部署集 ID 列表
autoSnapshotID	String	否	自动快照策略ID
bbcOption	BBCOption	否	BBC 选项. 仅在节点类型为BBC类型已有节点时需要设置
hpasOption	HPASOption	否	HPAS 机型选项。machineType 为 HPAS 时需要设置
becOption	BECOption	否	BEC 机型选项。machineType 为 BEC 时需要设置
aiInfraOption	AIInfraOption	否	AI 基础设施选项
ultraServerOption	UltraServerOption	否	超节点选项
vpcConfig	VPCConfig	否	VPC 选项. 新建BCC节点时和新建Serverless Master时需要设置. 托管型Master节点组自动使用Master Config配置. 已有节点自动使用自身VPC配置.
instanceResource	InstanceResource	否	集群规格相关配置. 新建BCC节点时必须设置. 托管型Master节点组自动使用后台默认配置. 已有节点自动使用自身资源配置.
imageID	String	否	新建BCC节点和已有节点需要重装系统时时需要设置 imageID 和 InstanceOS 二者中的其中一个. 优先使用 ImageID, 如果用户传入 InstanceOS 信息, 由后台计算 ImageID.
instanceOS	InstanceOS	否	新建BCC节点和已有节点需要重装系统时时需要设置 imageID 和 InstanceOS 二者中的其中一个. 优先使用 ImageID, 如果用户传入 InstanceOS 信息, 由后台计算 ImageID.
needEIP	Boolean	否	机器是否需要EIP
relationTag	Boolean	否	是否将该节点上的tag应用到与该节点绑定的其他资源上，例如cds盘，默认为false
userData	String	否	节点自定义数据, 支持安装驱动。因为传输API请求时，不会加密所设置的UserData，建议不要以明文方式传入机密的信息，例如密码和私钥等。如果必须传入，建议加密后，然后以Base64的方式编码后再传入，在节点内部以同样的方式反解密
eipOption	EIPOption	否	EIP 选项. needEIP为True时必须设置.
adminPassword	String	否	管理员密码. 不设置时将由系统自动生成. 已有BCC节点在不重装系统时必须设置. 密码要求8～32位字符, 仅限且必须包含字母、数字和指定符号 !@#$%^*()
sshKeyID	String	否	SSH Key ID
instanceChargingType	String	否	节点计费方式，可选 [ Prepaid, Postpaid, bidding ]. 新建节点、托管型集群Master节点、Serverless节点默认且仅限为后付费. 已有节点支持预付费或后付费
instancePreChargingOption	InstancePreChargingOption	否	节点预付费选项. 预付费节点需要设置.
deleteOption	DeleteOption	否	删除节点选项.
deployCustomConfig	DeployCustomConfig	否	自定义部署选项
tags	List<Tag>	否	节点 Tag 列表.
labels	Map<String,String>	否	节点 Label 列表. 后台会节点自动添加cluster-id和cluster-role两个label
taints	List<Taint>	否	节点 Taint 列表
annotations	Map<String,String>	否	节点 annotations 列表
bid	Boolean	否	是否开启竞价，默认为 false
bidOption	BidOption	否	竞价实例选项，bid=true 时为必填项
isOpenHostnameDomain	Boolean	否	是否自动生成hostname domain
ehcClusterId	String	否	ehc集群ID
iamRole	IAMRole	否	实例级别 IAM 角色
kataType	String	否	Kata 容器类型
kataVersion	String	否	Kata 容器版本
checkGPUDriver	Boolean	否	是否开启 GPU 驱动检查
nvidiaContainerToolkitVersion	String	否	NVIDIA Container Toolkit 组件版本
xpuContainerToolkitVersion	String	否	XPU Container Toolkit 组件版本
scaleDownDisabled	Boolean	否	节点缩容保护。设为 true 时在自动伸缩过程中被跳过
ExistedOption
参数名称
类型
是否必须
描述
existedInstanceID	String	是	现有节点 ID
rebuild	Boolean	否	是否重装系统，默认为true，即重装系统
BBCOption
参数名称
类型
是否必须
描述
reserveData	Boolean	是	是否保留数据
raidID	String	否	磁盘阵列类型 ID；reserveData=false 时必填, reserveData=true 时不生效
sysDiskSize	Integer	否	系统盘分配大小，单位 GB；reserveData=false 时必填, reserveData=true 时不生效
flavor	String	否	套餐ID，例：BBC-G4-02S
diskInfo	String	否	磁盘阵列类型，例：Raid5, 不支持 raid 的 bbc，设置为 NoRaid。
VPCConfig
参数名称
类型
是否必须
描述
vpcID	String	否	VPC ID. 为空时使用集群的VPC ID
vpcSubnetID	String	否	VPC 子网 ID. 新建节点必须设置此值. 已有节点无需设置.
securityGroupID	String	是	安全组 ID. 新建节点如果没有设置 securityGroup 必须设置此值. 已有节点无需设置.
securityGroupType	String	否	安全组类型，可选[normal，enterprise]，默认为 normal
securityGroup	SecurityGroup	否	安全组信息. 新建 BCC 推荐设置. 已有节点无需设置.
vpcSubnetType	String	否	VPC 子网类型，可选 [ BBC, BCC ]. 创建集群时无需设置，后台根据子网ID自动设置.
vpcSubnetCIDR	String	否	VPC 子网网段. 创建集群时无需设置，后台根据子网ID自动设置.
vpcSubnetCIDRIPv6	String	否	VPC IPv6 子网网段. 创建集群时无需设置，后台根据子网ID自动设置.
availableZone	String	否	可用区，可选 [ zoneA, zoneB, zoneC, zoneD, zoneE, zoneF ]. 创建集群时无需设置，后台根据子网ID自动设置.
optionalSubnetIDs	List	否	可选子网 ID 列表，支持多子网创建节点.
SecurityGroup
参数名称
类型
是否必须
描述
customSecurityGroups	String 数组	否	用户指定的安全组，将被绑定到节点上
enableCCERequiredSecurityGroup	bool	否	是否绑定 CCE 默认安全组到节点上
enableCCEOptionalSecurityGroup	bool	否	是否绑定 CCE 可选安全组到节点上
InstanceResource
参数名称
类型
是否必须
描述
cpu	Integer	否	CPU 核数. 新建节点必须设置此字段
mem	Integer	否	内存大小，单位GB. 新建节点必须设置此字段
rootDiskType	String	否	根磁盘类型，可选 [ hp1, cloud_hp1, hdd, local, sata, ssd ]. 新建节点默认为hp1 已有节点和其本身属性一致. 更多详情参考：CDS磁盘性能 与 CDS磁盘类型参数
rootDiskSize	Integer	否	根磁盘大小，单位GB. 默认值为40
localDiskSize	Integer	否	本地磁盘大小，GPU 机器必须指定，单位 GB
cdsList	List<CDSConfig>	否	CDS 列表，默认第一块盘作为 docker 和 kubelet 数据盘
ephemeralDiskList	List<EphemeralDiskConfig>	否	CDS 列表，默认第一块盘作为 docker 和 kubelet 数据盘
gpuType	String	否	GPU 类型，可选 [ V100-32, V100-16, P40, P4, K40, DLCard ]. 详情参考: GPU卡详情 节点类型为G1时必须设定
gpuCount	Integer	否	GPU 数量. 节点类型为G1时必须设定
machineSpec	String	是	机器规格，必填参数
cpuThreadConfig	String	否	调整每物理核的线程数（vCPU），本质上对应各处理器的超线程能力是否启用。
取值范围：1、2
注意：
1. 默认情况下，百度智能云实例按照默认值 2 配置。
2. 仅Intel第七代以上、AMD第三代以上的裸金属实例规格支持设置 CPU 线程数。
3. 实例创建后该参数配置不可修改。
numaConfig	String	否	调整CPU的NUMA配置，对于不同处理器平台取值有不同含义。
1. Intel平台：0代表关闭NUMA特性，1代表开启NUMA特性。
2. AMD平台：主要影响NPS(Nodes Per Socket)的配置，可取值0、1、2、4、auto，分别对应NPS0、NPS1、NPS2、NPS4以及自动。
注意：
1. 默认情况下，百度智能云实例按照开启NUMA优化（Intel实例）、NPS1（AMD实例），也即默认值 1 配置。
2. 仅Intel第七代以上、AMD第三代以上的裸金属实例规格支持设置NUMA选项。
3. 实例创建后该参数配置不可修改。
EphemeralDiskConfig
参数名称
类型
是否必须
描述
diskPath	String	是	磁盘路径
storageType	String	是	存储类型，可选 [ Local_PV_NVME, Local_PV_SSD, Local_PV_HDD, ephemeral, local, local_nvme,nvme,local_ssd,local_hdd ] 更多详情参考：BCC磁盘类型
sizeInGB	Integer	是	磁盘空间大小
dataDevice	String	否	数据设备标识符，用于指定磁盘对应的数据设备
CDSConfig
参数名称
类型
是否必须
描述
diskPath	String	是	磁盘路径
storageType	String	是	存储类型，可选 [ hp1, cloud_hp1, hdd, local, sata, ssd ] 更多详情参考：CDS磁盘性能 与 CDS磁盘类型参数
cdsSize	Integer	是	磁盘空间大小
snapshotID	String	否	快照ID，支持从快照创建磁盘
dataDevice	String	否	数据设备标识符，用于指定磁盘对应的数据设备
InstanceOS
参数名称
类型
是否必须
描述
imageType	String	是	镜像类型。取值范围包括 [ All, System, Custom, Integration, Sharing, GpuBccSystem, GpuBccCustom, BbcSystem, BbcCustom ]
imageName	String	是	镜像名字。例如ubuntu-14.04.1-server-amd64-201506171832
osType	String	是	操作系统类型，可选 [ linux, windows ]
osName	String	是	操作系统名字，可选 [ CentOS, Ubuntu, Windows Server, Debian, opensuse ]
osVersion	String	是	操作系统版本，例如14.04.1 LTS
osArch	String	是	操作系统架构。例如x86_64 (64bit)
osBuild	String	否	镜像创建时间信息，例如2015061700
EIPOption
参数名称
类型
是否必须
描述
eipName	String	是	EIP 名称
eipChargeType	String	是	EIP的计费方式，可选 [ ByTraffic, ByBandwidth ]
eipPurchaseType	String	否	EIP线路类型，可选[BGP(标准型BGP),BGP_S(增强型BGP),ChinaTelcom,ChinaUnicom,ChinaMobile]，默认标准BGP。
eipBandwidth	Integer	是	EIP 带宽. 按带宽计费取值范围是1-200. 按流量计费取值范围是1-1000
InstancePreChargingOption
参数名称
类型
是否必须
描述
purchaseTime	Integer	是	购买时间
purchaseTimeUnit	String	是	购买时间单位
autoRenew	Boolean	是	是
autoRenewTimeUnit	String	是	续费单位
autoRenewTime	Integer	是	续费时间
DeleteOption
参数名称
类型
是否必须
描述
moveOut	Boolean	否	是否移出节点，true表示仅将节点移出集群，false表示将节点删除。创建集群时新建节点默认为false， 加入已有节点默认为true。
deleteResource	Boolean	否	是否删除相关资源。创建集群时新建节点默认为true，加入已有节点默认为false。
deleteCDSSnapshot	Boolean	否	是否删除CDS快照。创建集群时新建节点默认为true，加入已有节点默认为false。
drainNode	Boolean	否	是否进行节点排水。
rebuild	Boolean	否	是否重建节点。
batchRefundResource	Boolean	否	是否批量退费。
DeployCustomConfig
参数名称
类型
是否必须
描述
dockerConfig	DockerConfig	否	Docker 相关配置
containerdConfig	ContainerdConfig	否	Containerd 相关配置
kubeletRootDir	String	否	kubelet 数据目录
registryPullQPS	Integer	否	每秒钟可以执行的镜像仓库拉取操作限值。 此值必须为非负整数，将其设置为 0 表示没有限值
registryBurst	Integer	否	突发性镜像拉取的上限值，允许镜像拉取临时上升到所指定数量，不能超过 registryPullQPS 所设置的约束。此值必须是非负整数。只有 registryPullQPS 参数值大于 0 时才会使用此设置
podPidsLimit	Integer	否	每个 Pod 中可使用的 PID 个数上限
eventRecordQPS	Integer	否	每秒钟可创建的事件个数上限。此值必须为非负整数，将其设置为 0 表示没有限值
eventBurst	Integer	否	突发性事件创建的上限值，允许事件创建临时上升到所指定数量，不过仍然不超过 eventRecordQPS 所设置的约束。此值必须为非负整数，只有 eventRecordQPS > 0 时才会使用此设置
kubeAPIQPS	Integer	否	与 Kubernetes API 服务器通信时的 QPS 限制（每秒查询数）
kubeAPIBurst	Integer	否	与 Kubernetes API 服务器通信时突发的流量限制，此值必须为非负整数
maxPods	Integer	否	节点 kubelet 上运行的 Pod 个数上限。此值必须为非负整数
cpuManagerPolicy	string	否	要使用的cpuManagerPolicy策略名称，可选[none，static]，默认值为none
topologyManagerScope	string	否	拓扑管理器作用域，可选[pod，container],默认值为container
topologyManagerPolicy	string	否	拓扑管理器策略名称，可选[none，best-effort，restricted，single-numa-node]，默认值为none
cpuCFSQuota	Boolean	否	是否为设置了CPU限制的容器实施CPU CFS配额约束
postUserScriptFailedAutoCordon	Boolean	否	部署时执行脚本失败后是否自动封锁节点
kubeletBindAddressType	string	否	kubelet绑定地址类型，可选[all，local，hostip]，默认值为hostip
EnableResourceReserved	Boolean	否	是否开启资源预留
kubeReserved	Map<String,String>	否	资源预留配额，例如 { cpu: 100m, memory: 1000Mi }
enableCordon	Boolean	否	是否封锁节点
preUserScript	String	否	部署前执行脚本, 前端 base64编码后传参
postUserScript	String	否	部署后执行脚本, 前端 base64编码后传参
kataConfig	KataConfig	否	Kata 容器相关配置
resolvConf	String	否	容器内使用的 DNS 解析配置文件。默认值：/etc/resolv.conf
allowedUnsafeSysctls	String	否	设置允许使用的非安全的 sysctl 或 sysctl 通配符
serializeImagePulls	Boolean	否	串行拉取镜像。默认值：true
evictionHard	Map<String,String>	否	硬性驱逐门限
evictionSoft	Map<String,String>	否	软性驱逐阈值
evictionSoftGracePeriod	Map<String,String>	否	驱逐宽限期，需已设置 evictionSoft
containerLogMaxFiles	Integer	否	容器的日志文件个数上限。此值必须大于等于 2，且容器运行时需为 containerd。默认值：5
containerLogMaxSize	String	否	容器日志文件轮换生成新文件的最大阈值。容器运行时需为 containerd
featureGates	Map<String,Boolean>	否	实验性特性的特性开关组
readOnlyPort	Integer	否	kubelet 无鉴权只读端口
cpuCFSQuotaPeriod	Integer	否	设置 CPU CFS 配额周期值。默认值：100ms
DockerConfig
参数名称
类型
是否必须
描述
dockerDataRoot	String	否	自定义 docker 数据目录
registryMirrors	List<String>	否	自定义 RegistryMirrors
insecureRegistries	List<String>	否	自定义 InsecureRegistries
dockerLogMaxSize	String	否	docker日志大小，默认值为 20m
dockerLogMaxFile	String	否	docker日志保留数，默认值为 10
dockerBIP	String	否	docker0网桥网段，默认值为 169.254.30.1/28
ContainerdConfig
参数名称
类型
是否必须
描述
dataRoot	String	否	自定义 containerd 数据目录
registryMirrors	List<String>	否	自定义 RegistryMirrors
insecureRegistries	List<String>	否	自定义 InsecureRegistries
Tag
参数名称
类型
是否必须
描述
tagKey	String	是	Tag Key
tagValue	String	是	Tag Value
Taint
参数名称
类型
是否必须
描述
effect	String	是	当Pod不容忍 Taint 时的行为，可选 [ NoSchedule, PreferNoSchedule, NoExecute ]
key	String	是	Taint Key
timeAdded	Date-time	否	添加污点的时间点，只有effect为NoExecute时使用
value	String	是	Taint Value
BidOption
参数名称
类型
是否必须
描述
bidMode	String	是	竞价模式，可取值：MARKET_PRICE_BID (随市场价出价)，(用户主动出价)
bidPrice	String	否	竞价实例出价，bidMode=MARKET_PRICE_BID为必填项
bidTimeout	Integer	是	竞价超时（单位：分钟），当超过此时间仍未竞价成功将自动取消订单并清理实例
bidReleaseEIP	Boolean	否	竞价实例被抢占释放时是否级联删除 EIP，默认为 false
bidReleaseCDS	Boolean	否	竞价实例被抢占释放时是否级联删除 CDS，默认为 false
ClusterPage
参数名称
类型
描述
keywordType	String	集群模糊查询字段，可选 [ clusterName, clusterID ]
keyword	String	查询关键词
orderBy	String	集群查询排序字段，可选 [ clusterName, clusterID, createdAt ]
order	String	排序方式，可选 [ ASC, DESC ]
pageNo	Integer	页码
pageSize	Integer	单页结果数
totalCount	Integer	集群总数量
clusterList	List<Cluster>	查询到的集群列表
Cluster
参数名称
类型
描述
spec	ClusterSpec	集群属性
status	ClusterStatus	集群状态
createdAt	String	创建时间
updatedAt	String	更新时间
ClusterStatus
参数名称
类型
描述
clusterBLB	BLB	集群的BLB
clusterPhase	String	集群状态，可选 [ pending, provisioning, provisioned, running, create_failed, deleting, deleted, delete_failed ]
nodeNum	Integer	节点数量
BLB
参数名称
类型
描述
id	String	BLB ID
vpcIP	String	VPC IP 地址
eip	String	EIP 地址
VKSubnetType
参数名称
类型
是否必须
描述
availableZone	String	是	可用区名称
subnetID	String	是	子网 ID
InstancePage
参数名称
类型
描述
clusterID	String	集群的ID
keywordType	String	集群模糊查询字段，可选 [ clusterName, clusterID ]
keyword	String	查询关键词
orderBy	String	集群查询排序字段，可选 [ clusterName, clusterID, createdAt ]
order	String	排序方式，可选 [ ASC, DESC ]
pageNo	Integer	页码
pageSize	Integer	单页结果数
totalCount	Integer	节点总数
instanceList	List<Instance>	节点列表
Instance
参数名称
类型
描述
createdAt	String	节点创建时间
spec	InstanceSpec	节点的配置
status	InstanceStatus	节点的状态
updatedAt	String	节点更新时间
InstanceStatus
参数名称
类型
描述
instancePhase	String	节点的状态，可选 [ pending, provisioning, provisioned, running, create_failed, deleting, deleted, delete_failed ] 。pending, provisioning, provisioned 均表示创建中状态。
machine	Machine	虚拟机信息
machineStatus	String	BBC虚机状态，可选 [ ACTIVE, BUILD, REBUILD, DELETED, SNAPSHOT, DELETE_SNAPSHOT, VOLUME_RESIZE, ERROR, EXPIRED, REBOOT, RECHARGE, SHUTOFF, STOPPED, UNKNOWN ]
Machine
参数名称
类型
描述
eip	String	EIP IP地址
instanceID	String	对应节点ID
instanceName	String	对应节点名称
mountList	List<MountConfig>	磁盘挂载信息列表
orderID	String	订单号
vpcIP	String	VPC IP 地址
vpcIPIPv6	String	VPC IPv6地址
k8sNodeName	String	K8S NodeName, 使用 IP 或 Hostname
MountConfig
参数名称
类型
描述
cdsID	String	CDS磁盘ID
cdsSize	Integer	CDS磁盘大小
device	String	设备路径. 如/dev/vdb
diskPath	String	磁盘路径. 如/data
storageType	String	磁盘存储类型，可选 [ hp1, cloud_hp1, hdd, local, sata, ssd ]. 更多详情参考：CDS磁盘性能 与 CDS磁盘类型参数
ListInstancesByInstanceGroupIDPage
参数名称
类型
描述
pageNo	Integer	页码
pageSize	Integer	单页结果数
totalCount	Integer	节点总数
list	List<Instance>	节点列表
InstanceGroup
参数名称
类型
描述
spec	InstanceGroupSpec	节点组的配置
status	InstanceGroupStatus	节点组的状态
createdAt	String	节点组的创建时间
InstanceGroupSpec
参数名称
类型
描述
cceInstanceGroupID	String	节点组 ID
instanceGroupName	String	节点组名称
clusterID	String	集群ID
clusterRole	String	节点在集群中的角色，目前节点组仅支持nod. 默认值为 node
shrinkPolicy	String	节点组收缩规则. 可选 [ Priority, Priority ].
updatePolicy	String	节点组更新规则. 可选 [ Rolling, Concurrency].
cleanPolicy	String	节点清理规则. 可选 [ Remain, Delete ].
instanceTemplate	InstanceTemplate	节点配置
instanceTemplates	InstanceTemplate[]	多模版节点配置
replicas	Integer	节点副本数
clusterAutoscalerSpec	ClusterAutoscalerSpec	集群的自动伸缩配置
iamRole	IamRole	节点组绑定的IAM角色
remedyRulesBinding	RemedyRulesBinding	节点组自愈规则绑定
securityGroups	SecurityGroupV2[]	节点组级别安全组列表
securityGroupType	String	安全组类型。可选 [ normal, enterprise ]，默认为 normal
customNodeNameEnabled	Boolean	是否启用自定义节点名称规则。默认为 false
customNodeNameRule	String	节点组的自定义节点名称规则
InstanceTemplate
此结构等同于InstanceSpec，参见InstanceSpec

ClusterAutoscalerSpec
参数名称
类型
描述
enabled	Boolean	是否启用Autoscaler
minReplicas	Integer	最小副本数. 取值范围是自然数集.
maxReplicas	Integer	最大副本数. 取值范围是自然数集, 需大于minReplicas.
scalingGroupPriority	Integer	伸缩组优先级. 取值范围是自然数集.
InstanceGroupStatus
参数名称
类型
描述
readyReplicas	Integer	节点组中处于 Ready 状态的节点数
pause	Pause	节点组的暂停状态
Pause
参数名称
类型
描述
paused	Boolean	节点组是否处于暂停状态
reason	String	节点组处于暂停状态的原因
ListInstanceGroupPage
参数名称
类型
描述
pageNo	Integer	页码
pageSize	Integer	单页结果数
totalCount	Integer	节点组总数
list	List<InstanceGroup>	节点组列表
Autoscaler
参数名称
类型
描述
clusterID	String	集群 ID
clusterName	String	集群名称
caConfig	ClusterAutoscalerConfig	节点组列表
ClusterAutoscalerConfig
参数名称
类型
描述
expander	String	自动扩缩容选组的策略. 可选 [ random, most-pods, least-waste, priority ], 默认值为 random.
instanceGroups	List<ClusterAutoscalerInstanceGroup>	节点组的 Autoscaler 配置. 用户无需输入此项内容.
kubeVersion	String	K8S 版本. 为空时后台会自动查询集群K8S版本号.
maxEmptyBulkDelete	Integer	最大并发缩容数
replicaCount	Integer	预期副本数量
scaleDownDelayAfterAdd	Integer	扩容后缩容启动时延, 单位为分钟
scaleDownEnabled	Boolean	是否启动缩容. 默认值为false
scaleDownGPUUtilizationThreshold	Integer	GPU缩容阈值百分比, 取值范围（0, 100）.
scaleDownUnneededTime	Integer	缩容触发时延，单位为分钟.
scaleDownUtilizationThreshold	Integer	缩容阈值百分比, 取值范围（0, 100）.
skipNodesWithLocalStorage	Boolean	是否跳过使用本地存储的节点, 默认值为 true.
skipNodesWithSystemPods	Boolean	是否跳过有部署系统 Pod 的节点, 默认值为 true.
ClusterAutoscalerInstanceGroup
参数名称
类型
描述
instanceGroupID	String	节点组 ID
minReplicas	String	最小副本数
maxReplicas	String	最大副本数
priority	String	优先级
ContainerCIDRConflict
参数名称
类型
描述
conflictCluster	ConflictCluster	与容器网段冲突的VPC内集群，当且仅当 NetworkConflictType 为 ContainerCIDRAndExistedClusterContainerCIDRConflict 不为 nil
conflictNodeCIDR	ConflictNodeCIDR	与容器网段冲突的节点网段，当且仅当 NetworkConflictType 为 ContainerCIDRAndNodeCIDRConflict 不为 nil
conflictType	String	网络冲突类型，可选 [ ContainerCIDRAndNodeCIDR, ContainerCIDRAndExistedClusterContainerCIDR, ContainerCIDRAndVPCRoute, ClusterIPCIDRAndNodeCIDR, ClusterIPCIDRAndContainerCIDR ]
conflictVPCRoute	ConflictVPCRoute	与容器网段冲突的VPC路由，当且仅当 NetworkConflictType 为 ContainerCIDRAndVPCRouteConflict 不为 nil
ClusterIPCIDRConflict
参数名称
类型
描述
conflictContainerCIDR	ConflictContainerCIDR	容器网段冲突信息
conflictNodeCIDR	ConflictNodeCIDR	节点网段冲突信息
conflictType	String	网络冲突类型，可选 [ ContainerCIDRAndNodeCIDR, ContainerCIDRAndExistedClusterContainerCIDR, ContainerCIDRAndVPCRoute, ClusterIPCIDRAndNodeCIDR, ClusterIPCIDRAndContainerCIDR ]
ConflictCluster
参数名称
类型
描述
clusterID	String	集群ID
containerCIDR	String	冲突的容器网段
ConflictContainerCIDR
参数名称
类型
描述
containerCIDR	String	冲突的容器网段
ConflictNodeCIDR
参数名称
类型
描述
nodeCIDR	String	冲突的节点网段
ConflictVPCRoute
参数名称
类型
描述
routeRule	RouteRule	冲突的 VPC 路由
RouteRule
参数名称
类型
描述
routeRuleId	String	路由规则 ID
routeTableId	String	路由表 ID
sourceAddress	String	源地址
destinationAddress	String	目的地址
nexthopId	String	下一跳 ID
nexthopType	String	下一跳类型
description	String	描述
ListTaskPage
参数名称
类型
描述
pageNo	Integer	页码
pageSize	Integer	单页结果数
totalCount	Integer	任务总数
items	List<Task>	任务列表
Task
参数名称
类型
描述
id	String	任务 ID
type	String	任务类型
description	String	任务描述
startTime	String	任务开始时间
finishTime	String	任务结束时间
phase	String	任务所处阶段, 可能取值[Pending, Processing, Done, Aborted, Collecting]
processes	List<TaskProcess>	任务进展列表
errMessage	String	任务错误信息
TaskProcess
参数名称
类型
描述
name	String	任务进展名称
phase	String	任务进展所处阶段, 可能取值[Pending, Processing, Done, Aborted]
startTime	String	任务进展开始时间
finishTime	String	任务进展结束时间
metrics	Map<String, String>	任务进展采集项，根据不同任务有不同的采集项
subProcesses	List<TaskProcess>	任务进展的子进展列表
errMessage	String	错误信息
Step
参数名称
类型
描述
stepName	String	步骤名称
stepStatus	String	步骤状态，可选 [ todo, doing, paused, done, failed]
ready	Boolean	是否准备就绪
startTime	String	步骤开始时间
finishedTime	String	步骤结束时间
costSeconds	integer	步骤花费时间
retryCount	integer	重试次数
errorInfo	ReconcileResponse	失败详情
ReconcileResponse
参数名称
类型
描述
code	string	响应码
message	String	响应信息
traceID	String	请求 ID, 问题定位提供该 ID
suggestion	integer	建议信息
AddOnInfo
参数名称
类型
描述
meta	Meta	组件基础信息
instance	AddOnInstance	组件安装信息。如果组件未安装，该字段为空值。
multiInstances	List<AddOnInstance>	如果组件允许多实例部署，则为该组件全部部署实例。通常不会使用到该字段。
Meta
参数名称
类型
描述
name	String	组件名称
type	String	组件类型。包括CloudNativeAI、Networking、HybridSchedule、Image、Storage、Observability
latestVersion	String	组件的最新版本
shortIntroduction	String	组件简介
defaultParams	String	组件默认部署参数
installInfo	InstallInfo	组件是否可以安装
AddOnInstance
参数名称
类型
描述
name	String	组件名称
installedVersion	String	已安装组件的版本
params	String	组件的部署参数
status	AddonInstanceStatus	组件状态
uninstallInfo	UninstallInfo	组件是否允许卸载
upgradeInfo	UpgradeInfo	组件是否允许升级
updateInfo	UpdateInfo	组件是否允许更新部署参数
AddonInstanceStatus
参数名称
类型
描述
phase	String	组件当前的状态
code	String	组件状态异常时，其错误码内容
message	String	组件状态异常时，其错误详情
traceID	String	组件状态异常时，其故障ID
InstallInfo
参数名称
类型
描述
allowInstall	String	组件是否允许安装
message	String	如果不允许安装，该字段为原因
UninstallInfo
参数名称
类型
描述
allowUninstall	String	组件是否允许卸载
message	String	如果不允许卸载，该字段为原因
UpgradeInfo
参数名称
类型
描述
allowUpgrade	String	组件是否允许升级
nextVersion	String	如果允许升级，其目标升级版本
message	String	如果不允许升级，该字段为原因
ResourceChargingOption
参数名称
类型
描述
ChargingType	String	后付费或预付费
PurchaseTime	int	预付费才生效：单位月，12 = 12 月
PurchaseTimeUnit	String	预付费时间单位
AutoRenew	bool	是否自动续费
AutoRenewTime	String	自动续费时长，12 = 12 个月
AutoRenewTimeUnit	String	续费单位：月
PluginHelmConfig
参数名称
类型
描述
PluginType	String	插件类型(插件名称)，非必要
PluginName	String	插件别名，非必要
ChartVersion	String	使用的Chart版本，非必要
ChartName	string	插件在云端的ChartName，非必要
Namespaces	String	插件部署到哪个命名空间，非必要
Description	String	描述，非必要
Values	String	取决于插件，系统插件传空值即可
MachineSpecStatus
参数名称
类型
描述
machineSpec	String	规格套餐
status	String	套餐状态，Adapted(已适配), Unadapted(暂未适配), NotSupported(不支持)
ExistedInstanceInCluster
参数名称
类型
描述
existedInstanceID	String	bcc 实例 id
InspectionItemInfo
字段
类型
描述
itemNameZH	String	巡检项解释说明/异常原因
itemId	String	正常
result	String	巡检结果，
正常：normal
异常：abnormal
未知：unknown
effect	String	异常影响
suggestion	String	修复建议
grade	String	风险级别:
正常：normal
低风险：lowRisk
中风险：mediumRisk
高风险：highRisk
composedResult	String	复合结果:
正常：normal
低风险：lowRisk
中风险：mediumRisk
高风险：highRisk
InspectionTaskInfo
字段
类型
描述
taskId	String	巡检任务ID
inspectionType	String	巡检类型，
自动
手动
inspectionStatus	String	巡检结果
inspectStartTime	Datetime	巡检开始时间: "2024-05-14T11:06:11Z"
inspectEndTime	Datetime	巡检结束时间: "2024-05-14T11:07:11Z"
InspectionConfig
参数名称
类型
是否必需
isInspectionEnabled	Boolean	是
inspectionFrequency	String	是
SubscriptionConfig
参数名称
类型
是否必需
描述
isSubscriptionEnabled	Boolean	是	CCE集群ID
deliveryFrequency	String	是	发送报告频率
receiveMethod	List	是	接收方式
ReceiveAddr
字段
类型
描述
ReceiveAddr	List<[3]String>	发送方式: 发送方式、发送地址、描述。
ItemDetail
字段
类型
描述
itemID	Int	巡检项ID
description	String	巡检项描述
status	String	巡检项状态，
开启：true
关闭：false
itemNameCN	String	巡检项中文名称
ReporterTypeConfig
字段
类型
描述
reporterType	String	报告类型
reportTypeName	String	报告类型名称
urlPrefix	String	报告 webhook 前缀
Target
参数名称
类型
是否必须
描述
nodeName	String	是	节点名/Pod所在节点名，
注意：节点诊断支持批量选择多个节点，但是每次最多选择20个节点。
namespace	String	Pod诊断必须	Pod的命名空间，仅支持单个命名空间
podName	String	Pod诊断必须	Pod名，仅支持单个Pod
ExistedOption
参数名称
类型
是否必须
描述
existedTask	Bool	是	是否重试
taskId	String	是	重试的诊断任务ID
DiagnosisTaskInfo
参数名称
类型
是否必须
描述
taskId	String	是	诊断任务ID
diagnosisType	String	是	诊断类型，
Pod
node
result	String	是	任务结果，
状态成功：succeeded
诊断中: doing
诊断失败: failed
startTime	DateTime	是	任务开始时间
endTime	DateTime	是	任务结束时间
target	Target	是	诊断目标对象
taskPhases	List	是	任务阶段状态
TaskPhase
参数名称
类型
是否必须
描述
phaseId	Integer	是	阶段ID
phaseResult	String	是	阶段状态，
doing
succeeded
failed
phaseTime	DateTime	是	阶段的开始时间
phaseName	String	是	阶段名称
errorMessage	String	否	错误信息
GetDiagnosisReportDetailResponse
参数名称
类型
是否必须
描述
taskId	String	是	诊断任务ID
diagnosisType	String	是	诊断类型，
pod
node
completed	Bool	是	诊断报告是否完成
taskResult	String	是	诊断任务结果
健康：normal
异常: abnormal
诊断中: doing
诊断失败: failed
startTime	DateTime	是	任务开始时间
endTime	DateTime	否	任务结束时间
itemsCount	Integer	是	任务执行的诊断项数量
target	Target	是	诊断目标对象
reportItems	Map<Category, Map<ItemName, DiagnosisReportItem> >	是	诊断项列表
conclusion	Conclusion	是	诊断结论
DiagnosisReportItem
参数名称
类型
是否必须
描述
itemId	Integer	是	诊断项ID
result	bool	是	诊断是否通过，
通过：true，
不通过：false
composedResult	String	是	复合结果：result+grade
value	String	是	诊断项结果信息： 诊断项正常：Normal，诊断项异常：错误信息
exactMessage	String	是	错误信息
itemNameZH	String	是	诊断项中文名
description	String	是	诊断项描述
suggestion	String	是	诊断项修复建议
grade	String	是	诊断项等级，
警告: warning
异常 error
enable	Bool	否	诊断项是否启用
Conclusion
参数名称
类型
是否必须
描述
result	String	是	是否有异常，
正常：normal
异常：abnormal
失败：failed
problem	String	是	问题
cause	String	是	原因分析
suggestion	String	是	建议
ConfigureAPIServerCertSAN
参数名称
类型
是否必须
描述
clusterID	String	是	集群 ID（需与 URL 参数中的 clusterID 一致）
apiServerCertSAN	List<String>	是	新的证书 SAN 列表，支持域名或 IP 地址格式
ConfigureKMSEncryption
参数名称
类型
是否必须
描述
action	String	是	操作类型，可选值：enable（开启）、disable（关闭）
kmsKeyID	String	条件必须	KMS 密钥 ID。当 action 为 enable 时必填
HPASOption
参数名称
类型
是否必须
描述
appType	String	否	应用类型
appPerformanceLevel	String	否	应用性能等级
name	String	否	名称
description	String	否	描述
BECOption
参数名称
类型
是否必须
描述
becRegion	String	否	BEC 区域
becCity	String	否	BEC 城市
becServiceProvider	String	否	BEC 运营商
AIInfraOption
参数名称
类型
是否必须
描述
serverLessRelayIP	String	否	Serverless 中IP
serverLessRelayPW	String	否	Serverless 中密码
hostsFile	String	否	Hosts 文件配置
templateID	String	否	模板 ID
clusterName	String	否	Infra 集群名称
UltraServerOption
参数名称
类型
是否必须
描述
ultraServerID	String	否	超节点ID
IAMRole
参数名称
类型
是否必须
描述
roleName	String	否	IAM 角色名称
roleID	String	否	IAM 角色 ID
SecurityGroupV2
参数名称
类型
是否必须
描述
name	String	否	安全组名称
type	String	否	安全组类型
id	String	否	安全组 ID
RemedyRulesBinding
参数名称
类型
是否必须
描述
remedyRuleID	String	否	修复规则 ID
enableCheckANDRemedy	Boolean	否	是否启用检查与修复
KataConfig
参数名称
类型
是否必须
描述
dataRoot	String	否	自定义 kata 数据目录

集群巡检接口
更新时间：2026-03-23
文档内容
获取最近一次集群巡检报告详情
描述：
获取最近一次集群巡检报告详情

请求结构

Plain Text复制
GET /v2/cluster/{clusterId}/inspection_latest_report HTTP/1.1
Host: cce.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必需
参数位置
描述
clusterId	String	是	Path	CCE集群ID
返回头域

除公共头域外，无其它特殊头域。

返回参数

参数名称
类型
描述
reportItems	map	巡检项详细信息列表
inspectStartTime	DateTime	巡检开始时间
reportDeliveryStatus	List	报告发送状态
inspectionItemsCount	Integer	巡检项数量
taskId	String	巡检任务ID
请求示例

Plain Text复制
GET /v2/cluster/{clusterId}/inspection_latest_report  HTTP/1.1
Host: cce.bd.baidubce.com
ContentType: application/json
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
 Content-Type: application/json; charset=utf-8
 Date: Thu, 28 Jul 2022 03:25:43 GMT
 X-Bce-Gateway-Region: BJ
 X-Bce-Request-Id: b42840ec-a200-49c9-86bd-58687b7009bb
{
    "taskId": "cce-h6gt3az6-20241023-6998ebdd",
    "inspectionItemsCount": 8,
    "reportItems": {
        "cluster risks": {
            "ClusterAuditEnabled": {
                "itemNameZH": "审计日志是否开启",
                "itemId": 30004,
                "result": "normal",
                "effect": "检查审计日志是否开启。",
                "suggestion": "开启集群审计。",
                "grade": "lowRisk",
                "composedResult": "normal"
            },
            "CoreDNSHighAvailability": {
                "itemNameZH": "CoreDNS 高可用",
                "itemId": 30008,
                "result": "normal",
                "effect": "检查 CoreDNS 组件的副本数是否 > 2，且不同副本部署在不同的节点中。如未达到预期要求，则 CoreDNS 不具备高可用性，存在单点失效风险。当节点宕机或重启的时，CoreDNS 将无法提供服务，影响业务正常运行。",
                "suggestion": "检查 CoreDNS 副本状态，保持 2 个以上副本，并将副本打散到不同的节点上。",
                "grade": "mediumRisk",
                "composedResult": "normal"
            },
            "CoreDNSReplicas": {
                "itemNameZH": "CoreDNS 组件状态",
                "itemId": 30006,
                "result": "normal",
                "effect": "检查 CoreDNS 组件是否为 非 Running 状态。该组件异常会导致集群内 DNS 解析错误，无法通过 Service 名称进行访问。",
                "suggestion": "检查 CoreDNS 组件状态，排除异常原因。",
                "grade": "highRisk",
                "composedResult": "normal"
            },
            "WorkNodeReadyNumber": {
                "itemNameZH": "集群worker node (ready)数量",
                "itemId": 30005,
                "result": "normal",
                "effect": "检查集群中 Worker 节点的数量是否 < 2 个。单个节点的集群存在单点失效问题。",
                "suggestion": "添加节点。",
                "grade": "highRisk",
                "composedResult": "normal"
            }
        },
        "resource quota": {
            "CDSCapacityTBQuota": {
                "itemNameZH": "CDS容量紧张",
                "itemId": 10006,
                "result": "normal",
                "effect": "集群所在地域的CDS磁盘使用量占总容量（TB）是否大于95%。",
                "suggestion": "增加CDS容量配额。",
                "grade": "highRisk",
                "composedResult": "normal"
            },
            "VpcRouteRuleQuota": {
                "itemNameZH": "VPC路由规则数",
                "itemId": 10001,
                "result": "normal",
                "effect": "VPC内剩余路由表条目配额少于5条。VPC路由模式下，集群每个节点都会消耗一条路由表规则，当路由表规则耗尽后，集群内无法添加新节点。VPC-ENI模式下，集群不使用VPC路由表。",
                "suggestion": "增加VPC路由规则配额。",
                "grade": "highRisk",
                "composedResult": "normal"
            }
        },
        "resource status": {
            "NodeNotReady": {
                "itemNameZH": "节点状态",
                "itemId": 50001,
                "result": "normal",
                "effect": "检查集群中是否存在 NotReady 的节点。如果节点状态异常，会导致 Pod 无法被调度到该节点上。",
                "suggestion": "查看节点状态，必要时新增或删除节点。",
                "grade": "highRisk",
                "composedResult": "normal"
            },
            "WorkloadReplicas": {
                "itemNameZH": "Workload 副本数",
                "itemId": 50002,
                "result": "normal",
                "effect": "检查工作负载的期望副本数和实际副本数是否一致。如不一致，则不满足高可靠性要求。",
                "suggestion": "检查副本数异常工作负载，排除异常原因，更新副本数。",
                "grade": "mediumRisk",
                "composedResult": "normal"
            }
        }
    },
    "inspectStartTime": "2024-10-23T03:05:01+08:00",
    "reportDeliveryStatus": {
        "receiveMethod": []
    }
}
获取集群巡检报告详情
描述：
获取集群巡检报告详情

请求结构

Plain Text复制
GET /v2/cluster/{clusterId}/inspection/{taskId}/report HTTP/1.1
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必需
参数位置
描述
clusterId	String	是	Path	CCE集群ID
taskId	String	是	Path	巡检任务ID
返回头域

除公共头域外，无其它特殊头域。

返回参数

参数名称
类型
描述
reportItems	InspectionItemInfo	巡检项详细信息列表
inspectStartTime	DateTime	巡检开始时间
reportDeliveryStatus	List	报告发送状态
inspectionItemsCount	Integer	巡检项数量
taskId	String	巡检任务ID
请求示例

Plain Text复制
GET /v2/cluster/{clusterId}/inspection/{taskId}/report  HTTP/1.1
Host: cce.bd.baidubce.com
ContentType: application/json
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
 Content-Type: application/json; charset=utf-8
 Date: Thu, 28 Jul 2022 03:25:43 GMT
 X-Bce-Gateway-Region: BJ
 X-Bce-Request-Id: b42840ec-a200-49c9-86bd-58687b7009bb
{
    "taskId": "cce-h6gt3az6-20241023-6998ebdd",
    "inspectionItemsCount": 8,
    "reportItems": {
        "cluster risks": {
            "ClusterAuditEnabled": {
                "itemNameZH": "审计日志是否开启",
                "itemId": 30004,
                "result": "normal",
                "effect": "检查审计日志是否开启。",
                "suggestion": "开启集群审计。",
                "grade": "lowRisk",
                "composedResult": "normal"
            },
            "CoreDNSHighAvailability": {
                "itemNameZH": "CoreDNS 高可用",
                "itemId": 30008,
                "result": "normal",
                "effect": "检查 CoreDNS 组件的副本数是否 > 2，且不同副本部署在不同的节点中。如未达到预期要求，则 CoreDNS 不具备高可用性，存在单点失效风险。当节点宕机或重启的时，CoreDNS 将无法提供服务，影响业务正常运行。",
                "suggestion": "检查 CoreDNS 副本状态，保持 2 个以上副本，并将副本打散到不同的节点上。",
                "grade": "mediumRisk",
                "composedResult": "normal"
            },
            "CoreDNSReplicas": {
                "itemNameZH": "CoreDNS 组件状态",
                "itemId": 30006,
                "result": "normal",
                "effect": "检查 CoreDNS 组件是否为 非 Running 状态。该组件异常会导致集群内 DNS 解析错误，无法通过 Service 名称进行访问。",
                "suggestion": "检查 CoreDNS 组件状态，排除异常原因。",
                "grade": "highRisk",
                "composedResult": "normal"
            },
            "WorkNodeReadyNumber": {
                "itemNameZH": "集群worker node (ready)数量",
                "itemId": 30005,
                "result": "normal",
                "effect": "检查集群中 Worker 节点的数量是否 < 2 个。单个节点的集群存在单点失效问题。",
                "suggestion": "添加节点。",
                "grade": "highRisk",
                "composedResult": "normal"
            }
        },
        "resourceQuota": {
            "CDSCapacityTBQuota": {
                "itemNameZH": "CDS容量紧张",
                "itemId": 10006,
                "result": "normal",
                "effect": "集群所在地域的CDS磁盘使用量占总容量（TB）是否大于95%。",
                "suggestion": "增加CDS容量配额。",
                "grade": "highRisk",
                "composedResult": "normal"
            },
            "VpcRouteRuleQuota": {
                "itemNameZH": "VPC路由规则数",
                "itemId": 10001,
                "result": "normal",
                "effect": "VPC内剩余路由表条目配额少于5条。VPC路由模式下，集群每个节点都会消耗一条路由表规则，当路由表规则耗尽后，集群内无法添加新节点。VPC-ENI模式下，集群不使用VPC路由表。",
                "suggestion": "增加VPC路由规则配额。",
                "grade": "highRisk",
                "composedResult": "normal"
            }
        },
        "resourceStatus": {
            "NodeNotReady": {
                "itemNameZH": "节点状态",
                "itemId": 50001,
                "result": "normal",
                "effect": "检查集群中是否存在 NotReady 的节点。如果节点状态异常，会导致 Pod 无法被调度到该节点上。",
                "suggestion": "查看节点状态，必要时新增或删除节点。",
                "grade": "highRisk",
                "composedResult": "normal"
            },
            "WorkloadReplicas": {
                "itemNameZH": "Workload 副本数",
                "itemId": 50002,
                "result": "normal",
                "effect": "检查工作负载的期望副本数和实际副本数是否一致。如不一致，则不满足高可靠性要求。",
                "suggestion": "检查副本数异常工作负载，排除异常原因，更新副本数。",
                "grade": "mediumRisk",
                "composedResult": "normal"
            }
        }
    },
    "inspectStartTime": "2024-10-23T03:05:01+08:00",
    "reportDeliveryStatus": {
        "receiveMethod": []
    }
}
获取集群巡检报告列表
描述：
获取集群巡检报告列表

请求结构
Http复制
GET /v2/cluster/{clusterId}/inspections?pageSize=10&pageNo=1 HTTP/1.1
请求参数
参数名称
类型
是否必需
参数位置
描述
实例值
pageSize	Integer	否	Query	分页查询巡检实例列表时每页返回的记录数，取值范围为 1~100，默认值为 10	10
pageNo	Integer	否	Query	分页查询巡检实例列表的页码，默认值为 1	1
order	String	否	Query	巡检实例列表排序方式，默认值为 desc	desc、asc
orderBy	String	否	Query	巡检实例列表排序字段，默认值为巡检开始时间	inspectStartTime、inspectEndTime
inspectionType	String	否	Query	巡检类型	manual、automatic
InspectionStatus	String	否	Query	巡检状态	inspecting、normal、hasRisks、inspectionFailed
clusterId	String	是	Path	集群 ID	cce-xxxxxxxx
返回头域

除公共头域外，无其它特殊头域。

返回参数

参数名称
类型
描述
orderBy	String	巡检实例列表排序依据字段: 默认巡检开始时间
order	String	巡检实例列表排序方式：desc倒序（默认），asc升序
pageNo	Integer	实例列表分页当前页码数
pageSize	Integer	当前页巡检实例个数
totalCount	Integer	巡检实例总个数
reportAbstract	List	巡检实例列表
请求示例

Plain Text复制
GET /v2/cluster/{clusterId}/inspections？pageSize=10&pageNo=1  HTTP/1.1
Host: cce.bd.baidubce.com
ContentType: application/json
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
 Content-Type: application/json; charset=utf-8
 Date: Thu, 28 Jul 2022 03:25:43 GMT
 X-Bce-Gateway-Region: BJ
 X-Bce-Request-Id: b42840ec-a200-49c9-86bd-58687b7009bb
{
    "order": "desc",
    "orderBy": "inspectStartTime",
    "pageNo": 1,
    "pageSize": 10,
    "reportAbstract": [
        {
            "inspectEndTime": "2024-09-05T21:05:07+08:00",
            "inspectStartTime": "2024-09-05T21:05:07+08:00",
            "inspectionStatus": "normal",
            "inspectionType": "manual",
            "taskId": "cce-4734rtn5-20240905-3a642706"
        },
        {
            "inspectEndTime": "2024-09-05T21:05:07+08:00",
            "inspectStartTime": "1971-01-01T00:00:01+08:00",
            "inspectionStatus": "normal",
            "inspectionType": "manual",
            "taskId": "cce-4734rtn5-20240905-3a642705"
        }
    ],
    "totalCount": 2
}
获取集群配置
描述：
获取集群自动巡检和订阅配置

请求结构

Plain Text复制
GET /v2/cluster/{clusterId}/inspection_plan HTTP/1.1
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必需
参数位置
描述
clusterId	String	是	Path	CCE集群ID
返回头域

除公共头域外，无其它特殊头域。

返回参数

参数名称
类型
是否必需
描述
ipectionConfig	InspectionConfig	是	巡检配置
subscriptionConfig	SubscriptionConfig	是	订阅配置
ReceiveMethod

字段
类型
描述
receiveMethod	List<[3]String>	发送方式:["email", "123@baidu.com", "这是描述"]
请求示例
Http复制
GET /v2/cluster/cce-fzqqpie4/inspection_plan HTTP/1.1
Host: cce.bj.baidubce.com
Content-Type: application/json
Authorization: bce-auth-v1/{accessKeyId}/{timestamp}/{expirationPeriodInSeconds}/host/{signature}
返回示例

Plain Text复制
 Content-Type: application/json; charset=utf-8
 Date: Thu, 28 Jul 2022 03:25:43 GMT
 X-Bce-Gateway-Region: BJ
 X-Bce-Request-Id: b42840ec-a200-49c9-86bd-58687b7009bb
{    
    "inspectionConfig":{
        "isInspectionEnabled": true,
        "inspectionFrequency": "00 08 * 1",
        
     }
     "subscriptionConfig":{
        "isSubscriptionEnabled": true
        "subscriptionFrequency": "00 08 * 1",
        "receiveMethod": {
            ["email", "123@baidu.com", "这是描述"],
            ["email", "123@baidu.com", "这是描述"],
            ["email", "123@baidu.com", "这是描述"]
      }
}
更新集群巡检配置
描述：
更新集群自动巡检和订阅配置

请求结构

Plain Text复制
PUT /v2/cluster/{clusterId}/inspection_plan HTTP/1.1
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必需
参数位置
描述
clusterId	String	是	Path	CCE集群ID
请求Body体

参数名称
类型
是否必需
参数位置
描述
inspectionConfig	InspectionConfig	是	RequestBody	巡检配置
subscriptionConfig	SubscriptionConfig	是	RequestBody	订阅配置
ReceiveMethod

字段
类型
描述
receiveMethod	List	发送方式:["email", "123@baidu.com", "这是描述"]
返回头域

除公共头域，无其它特殊头域。

返回参数

无

请求示例

Plain Text复制
PUT /v2/cluster/{clusterId}/inspection_plan  HTTP/1.1
Host: cce.bd.baidubce.com
ContentType: application/json
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
{	
    "inspectionConfig":{
        "isInspectionEnabled": true,
        "inspectionFrequency": "00 08 * 1",
        
     },
     "subscriptionConfig":{
        "isSubscriptionEnabled": true
        "subscriptionFrequency": "00 08 * 1",
        "receiveMethod": [
            ["email", "123@baidu.com", "这是描述"],
            ["email", "123@baidu.com", "这是描述"],
            ["email", "123@baidu.com", "这是描述"]
        ]
      }
}
返回示例

Plain Text复制
 Content-Type: application/json; charset=utf-8
 Date: Thu, 28 Jul 2022 03:25:43 GMT
 X-Bce-Gateway-Region: BJ
 X-Bce-Request-Id: b42840ec-a200-49c9-86bd-58687b7009bb
获取集群巡检报告发送配置
描述
查询巡检报告通知方式配置信息

请求方法 GET

请求路径： /v2/cluster/{clusterId}/inspection_reporter_type

请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必需
参数位置
描述
clusterId	String	是	Path	CCE集群ID
返回头域

除公共头域外，无其它特殊头域。

返回参数

参数名
类型
描述
reporterTypeList	ReporterTypeConfig	报告发生类型配置
请求示例

Plain Text复制
GET /v2/cluster/{clusterId}/inspection_report_config  HTTP/1.1
Host: cce.bj.baidubce.com
ContentType: application/json
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
 Content-Type: application/json; charset=utf-8
 Date: Thu, 28 Jul 2022 03:25:43 GMT
 X-Bce-Gateway-Region: BJ
 X-Bce-Request-Id: b42840ec-a200-49c9-86bd-58687b7009bb
{
    "reporterTypeList": [
        {
            "reporterType": "dingTalk",
            "reportTypeName": "钉钉",
            "urlPrefix": "https://oapi.dingtalk.com/robot/send?access_token="
        },
        {
            "reporterType": "lark",
            "reportTypeName": "飞书",
            "urlPrefix": "https://open.feishu.cn/open-apis/bot/v2/hook/"
        },
        {
            "reporterType": "infoflow",
            "reportTypeName": "如流",
            "urlPrefix": "http://api.im.baidu.com/api/msg/groupmsgsend?access_token="
        },
        {
            "reporterType": "weCom",
            "reportTypeName": "企业微信",
            "urlPrefix": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key="
        }
    ]
}
获取集群巡检项列表
描述
获取集群巡检项详细信息

请求结构
Http复制
GET /v2/cluster/{clusterId}/inspection_items HTTP/1.1
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必需
参数位置
描述
clusterId	String	是	Path	CCE集群ID
返回头域

除公共头域外，无其它特殊头域。

返回参数

参数名称
类型
描述
inspectionItems	InspectionItemInfo	巡检项列表:巡检项类别对应整数代号与该类别下的巡检项映射
InspectionItem	InspectionItemInfo	每个类别下的巡检项英文名称与具体巡检项内容
请求示例

Plain Text复制
GET /v2/cluster/{clusterId}/inspection_items  HTTP/1.1
Host: cce.bd.baidubce.com
ContentType: application/json
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
 Content-Type: application/json; charset=utf-8
 Date: Thu, 28 Jul 2022 03:25:43 GMT
 X-Bce-Gateway-Region: BJ
 X-Bce-Request-Id: b42840ec-a200-49c9-86bd-58687b7009bb
{
        "clusterRisks": {
            "BCCPostpayInstanceQuota": {
                "itemID": 10005,
                "description": "集群所在地域的后付费BCC实例数是否大于95%。",
                "status": true,
                "itemNameZH": "BCC按需付费配额紧张"
            },
            "BLBInstanceQuota": {
                "itemID": 10004,
                "description": "集群所在地域可创建的BLB实例数量是否小于5。BLB配额不足可能影响service、ingress的创建。",
                "status": true,
                "itemNameZH": "BLB实例配额紧张"
            },
            "CDSCapacityTBQuota": {
                "itemID": 10006,
                "description": "集群所在地域的CDS磁盘使用量占总容量（TB）是否大于95%。",
                "status": true,
                "itemNameZH": "CDS容量紧张"
            },
            "VpcRouteRuleQuota": {
                "itemID": 10001,
                "description": "VPC内剩余路由表条目配额少于5条。VPC路由模式下，集群每个节点都会消耗一条路由表规则，当路由表规则耗尽后，集群内无法添加新节点。VPC-ENI模式下，集群不使用VPC路由表。",
                "status": true,
                "itemNameZH": "VPC路由规则数"
            }
        }
}
判断是否有巡检中的任务
描述
判断当前集群中是否有运行中的集群巡检任务

请求结构

Plain Text复制
GET /v2/cluster/{clusterId}/inspection_is_running HTTP/1.1
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必需
参数位置
描述
clusterId	String	是	Path	CCE集群ID
返回头域

除公共头域外，无其它特殊头域。

返回参数

参数名称
类型
描述
示例值
isExist	Bool	是否存在巡检中Task	true/false
请求示例

Plain Text复制
GET /v2/cluster/{clusterId}/inspection_is_running HTTP/1.1
Host: cce.bd.baidubce.com
ContentType: application/json
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
 Content-Type: application/json; charset=utf-8
 Date: Thu, 28 Jul 2022 03:25:43 GMT
 X-Bce-Gateway-Region: BJ
 X-Bce-Request-Id: b42840ec-a200-49c9-86bd-58687b7009bb
{
    false
}
发起集群巡检
描述
发起集群巡检任务

请求结构

Plain Text复制
POST /v2/cluster/{clusterId}/inspection HTTP/1.1
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必需
参数位置
描述
clusterId	String	是	Path	CCE集群ID
返回头域

除公共头域外，无其它特殊头域。

返回参数

参数名称
类型
描述
taskId	String	报告ID
请求示例

Plain Text复制
POST /v2/cluster/{clusterId}/inspection  HTTP/1.1
Host: cce.bd.baidubce.com
ContentType: application/json
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2019-03-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
 Content-Type: application/json; charset=utf-8
 Date: Thu, 28 Jul 2022 03:25:43 GMT
 X-Bce-Gateway-Region: BJ
 X-Bce-Request-Id: b42840ec-a200-49c9-86bd-58687b7009bb
{
    "taskId": "123456"
}
返回错误码
错误码
http code
说明
cce.warning.AccessDenied	403	权限不足
cce.warning.InvalidParam	400	无效请求参数
cce.warning.NoSuchObject	404	未找到资源
cce.warning.MalformedJSON	400	请求参数解析失败
cce.warning.ClusterNotFound	404	集群未找到
cce.warning.IAMUnauthorized	403	鉴权失败
cce.warning.OperationNotAllowed	403	鉴权失败
cce.error.InternalServerError	500	所有未定义的其他错误。