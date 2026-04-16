查询实例列表
更新时间：2025-02-10
该接口用于查询所有实例的详细信息。

注意事项：不同查询字段之间是and关系，同一查询字段传入的多个值之间是or关系。

请求结构

Plain Text复制
GET /v{version}/instance?marker={marker}&maxKeys={maxKeys}&internalIp={internalIp}&dedicatedHostId={dedicatedHostId}&zoneName={zoneName}&autoRenew={autoRenew} HTTP/1.1
Host: bcc.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必需
参数位置
描述
version	String	是	URL参数	API版本号
marker	String	否	Query参数	批量获取列表的查询的起始位置，是一个由系统生成的字符串
maxKeys	int	否	Query参数	每页包含的最大数量，最大数量通常不超过1000，缺省值为1000
internalIp	String	否	Query参数	内网IP
dedicatedHostId	String	否	Query参数	专属服务器ID
zoneName	String	否	Query参数	可用区信息
instanceIds	String	否	Query参数	多个实例ID，英文逗号分割，最多支持100个
volumeIds	String	否	Query参数	多个磁盘ID，英文逗号分割，最多支持100个
instanceNames	String	否	Query参数	多个实例名称，英文逗号分割，精确搜索。最多支持100个
fuzzyInstanceName	String	否	Query参数	实例的名称，支持关键字模糊查询。与instanceNames参数只能2选1，不能同时传值，否则报错。
deploySetIds	String	否	Query参数	多个部署集ID，英文逗号分割，最多支持100个
securityGroupIds	String	否	Query参数	多个安全组ID，英文逗号分割，最多支持100个
paymentTiming	String	否	Query参数	支付方式（Prepaid / Postpaid）
status	String	否	Query参数	实例状态（Recycled / Running / Stopped / Stopping / Starting）
tags	String	否	Query参数	多个标签，逗号分割，格式：tagKey:tagValue 或 tagKey
vpcId	String	否	Query参数	vpcId，只能与privateIps查询参数组合使用
privateIps	String	否	Query参数	多个内网IP，英文逗号分隔，最多支持100个，必须和vpcId组合使用
ehcClusterId	String	否	Query参数	ehc集群id
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
描述
marker	String	标记查询的起始位置
isTruncated	boolean	true表示后面还有数据，false表示已经是最后一页
nextMarker	String	获取下一页所需要传递的marker值。当isTruncated为false时，该域不出现
maxKeys	int	每页包含的最大数量
instances	List<InstanceModel>	实例信息，由 InstanceModel 组成的集合
错误码

错误码
错误描述
HTTP状态码
中文解释
BadRequest	zone is invalid.	400	无效的可用区
NoSuchObject	subnet not exists.	404	子网不存在
请求示例

Plain Text复制
GET /v2/instance?vpcId=vpc-vv3xw6d9970b&privateIps=192.168.48.3 HTTP/1.1
Host: bcc.bj.baidubce.com
ContentType: application/json
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2015-08-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
HTTP/1.1 200 OK
x-bce-request-id: 1214cca7-4ad5-451d-9215-71cb844c0a50
Date: Wed, 03 Dec 2014 06:42:19 GMT
Content-Type: application/json;charset=UTF-8
Server: BWS

{
    "marker": "",
    "isTruncated": false,
    "maxKeys": 1000,
    "instances": [
        {
            "id": "i-zadG8d4l",
            "name": "instance-696snyc6",
            "roleName": "",
            "hostname": "instance-696snyc6",
            "instanceType": "N6",
            "spec": "bcc.g5.c1m4",
            "status": "Running",
            "desc": "",
            "createdFrom": "customPurchase",
            "paymentTiming": "Prepaid",
            "createTime": "2022-10-11T06:11:42Z",
            "expireTime": "2023-01-11T06:11:42Z",
            "internalIp": "192.168.48.3",
            "publicIp": "",
            "cpuCount": 1,
            "isomerismCard": "",
            "cardCount": "0",
            "npuVideoMemory": "",
            "memoryCapacityInGB": 4,
            "localDiskSizeInGB": 0,
            "imageId": "m-zlaNc3qH",
            "placementPolicy": "unknown",
            "subnetId": "sbn-2escuever5fi",
            "vpcId": "vpc-vv3xw6d9970b",
            "zoneName": "cn-bj-a",
            "dedicatedHostId": "",
            "deletionProtection": 0,
            "deploysetList": [],
            "autoRenew": true,
            "ipv6": "",
            "resGroupInfos":[
                {
                    "groupId":"RESG-jec9gimkKaY",
                    "groupName":"test2"
                }
            ],
            "nicInfo": {
                "eniId": "eni-ramtd68yeyiq",
                "eniUuid": "8ed449ff-b2ee-4491-b117-35fb731c4370",
                "name": "eth0",
                "type": "primary",
                "subnetId": "sbn-2escuever5fi",
                "subnetType": "BCC",
                "az": "zoneA",
                "description": "",
                "deviceId": "608666b9-7156-4f47-8445-9c5497282573",
                "status": "inuse",
                "macAddress": "fa:f6:00:01:7e:ef",
                "vpcId": "vpc-vv3xw6d9970b",
                "createdTime": "Tue Oct 11 14:11:44 UTC 2022",
                "eniNum": 1,
                "eriNum": 0,
                "eriInfos": [],
                "ips": [
                    {
                        "privateIp": "192.168.48.3",
                        "eip": "null",
                        "primary": "true",
                        "eipId": "",
                        "eipAllocationId": "",
                        "eipSize": "0",
                        "eipStatus": "",
                        "eipGroupId": "",
                        "eipType": "null"
                    }
                ],
                "securityGroups": []
            },
            "eniNum": "1",
            "tags": [
                {
                    "tagKey": "test2",
                    "tagValue": "bcc"
                }
            ],
            "networkCapacityInMbps": 0
        }
    ]
}


查询指定实例详情
更新时间：2024-08-05
该接口用于查询指定实例的详细信息。

请求结构

Plain Text复制
GET /v{version}/instance/{instanceId} HTTP/1.1
Host: bcc.bj.baidubce.com
Authorization: authorization string
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必需
参数位置
描述
version	String	是	URL参数	API版本号
instanceId	String	是	URL参数	待查询的实例ID
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
描述
instance	InstanceModel	返回的实例详情
请求示例

Plain Text复制
GET /v2/instance/i-CFQRKlT2 HTTP/1.1
Host: bcc.bj.baidubce.com
ContentType: application/json
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2015-08-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
返回示例

Plain Text复制
```
HTTP/1.1 200 OK
x-bce-request-id: 1214cca7-4ad5-451d-9215-71cb844c0a50
Date: Wed, 03 Dec 2014 06:42:19 GMT
Content-Type: application/json;charset=UTF-8
Server: BWS

   {
      "instance": {
        "id": "i-JmwRSUbR",
        "name": "instance-4nbckz0b",
        "roleName": "",
        "hostname": "instance-4nbckz0b",
        "instanceType": "N5",
        "spec": "bcc.g4.c2m8",
        "status": "Running",
        "repairStatus": "normal",
        "desc": "",
        "createdFrom": "",
        "paymentTiming": "Postpaid",
        "createTime": "2023-06-13T08:07:52Z",
        "internalIp": "172.16.16.15",
        "publicIp": "",
        "cpuCount": 2,
        "isomerismCard": "",
        "cardCount": "0",
        "npuVideoMemory": "",
        "memoryCapacityInGB": 8,
        "localDiskSizeInGB": 0,
        "imageId": "m-Z1TCx0Zv",
        "imageName": "slurm-good3-0531",
        "imageType": "custom",
        "placementPolicy": "default",
        "subnetId": "sbn-b7ekx6uj6k6m",
        "vpcId": "vpc-41avheyaawqc",
        "hostId": "",
        "switchId": "",
        "rackId": "",
        "deploysetId": "",
        "zoneName": "cn-bd-b",
        "dedicatedHostId": "",
        "osVersion": "20.04 LTS",
        "osArch": "amd64 (64bit)",
        "osName": "Ubuntu",
        "hosteyeType": "open",
        "deploysetList": [],
        "resGroupInfos":[
                {
                    "groupId":"RESG-jec9gimkKaY",
                    "groupName":"test2"
                }
            ],
        "nicInfo": {
          "eniId": "eni-4scnfvrstj72",
          "eniUuid": "95da812f-f27f-4456-aad9-e27cf13d3e61",
          "name": "eth0",
          "type": "primary",
          "subnetId": "sbn-b7ekx6uj6k6m",
          "subnetType": "BCC",
          "az": "zoneB",
          "description": "",
          "deviceId": "3ac2af07-c13c-4bfd-ab00-a19706033b4a",
          "status": "inuse",
          "macAddress": "fa:26:00:0e:38:26",
          "vpcId": "vpc-41avheyaawqc",
          "createdTime": "Tue Jun 13 16:07:52 UTC 2023",
          "eniNum": 0,
          "eriNum": 0,
          "eriInfos": [],
          "ips": [
            {
              "privateIp": "172.16.16.15",
              "eip": "null",
              "primary": "true",
              "eipId": "",
              "eipAllocationId": "",
              "eipSize": "0",
              "eipStatus": "",
              "eipGroupId": "",
              "eipType": "null"
            }
          ],
          "securityGroups": [
            "g-wxsaduu9uajq"
          ],
          "enterpriseSecurityGroups": []
        },
        "deletionProtection": 0,
        "ipv6": "",
        "tags": [
          {
            "tagKey": "nodeType",
            "tagValue": "compute"
          }
        ],
        "volumes": [
          {
            "isSystemVolume": true,
            "diskSizeInGB": 40,
            "volumeId": "v-ClTVjiB4"
          }
        ],
        "networkCapacityInMbps": 0
      }
    }
```

查询多个实例详情
更新时间：2024-07-02
根据多个实例ID来查询多个实例详情。

请求结构

HTML复制
POST /v{version}/instance/listByInstanceId HTTP/1.1
Host: bcc.bj.baidubce.com
Authorization: authorization string
{
		"instanceIds": ["instanceId",""]
}
请求头域

除公共头域外，无其它特殊头域。

请求参数

参数名称
类型
是否必需
参数位置
描述
version	String	是	URL参数	API版本号
instanceIds	Array	是	RequestBody参数	实例id数组
marker	String	否	Query参数	批量获取列表的查询的起始位置，是一个由系统生成的字符串
maxKeys	int	否	Query参数	每页包含的最大数量，最大数量通常不超过1000，缺省值为1000。
返回头域

除公共头域，无其它特殊头域。

返回参数

参数名称
类型
描述
marker	String	标记查询的起始位置
isTruncated	boolean	true表示后面还有数据，false表示已经是最后一页
nextMarker	String	获取下一页所需要传递的marker值。当isTruncated为false时，该域不出现
maxKeys	int	每页包含的最大数量
instances	List<InstanceModel>	实例信息，由 InstanceModel 组成的集合
请求示例

HTML复制
POST /v2/instance/listByInstanceId
Host: bcc.bj.baidubce.com
ContentType: application/json
Authorization: bce-auth-v1/f81d3b34e48048fbb2634dc7882d7e21/2015-08-11T04:17:29Z/3600/host/74c506f68c65e26c633bfa104c863fffac5190fdec1ec24b7c03eb5d67d2e1de
{
    "instanceIds":["i-5polAZSW","i-q490RD6t"]
}
返回示例

HTML复制
HTTP/1.1 200 OK
x-bce-request-id: 1214cca7-4ad5-451d-9215-71cb844c0a50
Date: Wed, 03 Dec 2014 06:42:19 GMT
Content-Type: application/json;charset=UTF-8
Server: BWS
{
	"marker": "",
	"isTruncated": false,
	"maxKeys": 1000,
	"instances": [{
		"id": "i-cZbnhO0B",
		"serialNumber": "1060b348-b9e4-4940-baa6-fd9f300fc566",
		"hostId": "h-gHBSWl6i2Cq5rIynq2ngw",
		"rackId": "rk-10iVdnFTv5xYMmArVurhw",
		"switchId": "sw-Jew0Mc0xnIjBz26wFLT4RA",
		"deploysetId": "dset-qrE9FWAR",
		"deploysetList": [{
			"deploysetId": "dset-qrE9FWAR",
			"name": "name",
			"concurrency": 1,
			"strategy": "HOST_HA"
		}],
		"name": "instance-r6337ue1-1",
		"hostname": "instance-r6337ue1-1",
		"instanceType": "E1",
		"status": "Running",
		"desc": "",
		"createdFrom": "customPurchase",
		"paymentTiming": "Postpaid",
		"createTime": "2024-06-26T11:42:01Z",
		"internalIp": "192.168.64.65",
		"publicIp": "",
		"cpuCount": 2,
		"isomerismCard": "",
		"cardCount": "0",
		"npuVideoMemory": "",
		"memoryCapacityInGB": 2,
		"localDiskSizeInGB": 0,
		"imageId": "m-H2E8PurP",
		"placementPolicy": "unknown",
		"subnetId": "sbn-yfxhv6b0sxy4",
		"vpcId": "vpc-nys8a7qhzdrs",
		"zoneName": "cn-bj-d",
		"repairStatus": "normal",
		"dedicatedHostId": "",
		"ipv6": "240c:4081:8005:ca01::14",
		"eniQuota": 2,
		"eriQuota": 0,
		"serviceComponents": {
			"hasAlive": "notSupport"
		},
		"nicInfo": {
			"eniId": "eni-kgm8hqvsp6a3",
			"eniUuid": "96f54c86-15f6-4d2b-b63b-1a94c6dfd194",
			"name": "eth0",
			"type": "primary",
			"subnetId": "058855bc-fbcb-4003-b5c4-18f19d47e68b",
			"subnetType": "BCC",
			"az": "zoneD",
			"description": "",
			"deviceId": "1060b348-b9e4-4940-baa6-fd9f300fc566",
			"status": "inuse",
			"macAddress": "fa:20:20:33:e8:8f",
			"vpcId": "3c63adcf-2b76-4a3b-82cf-04b8e36051df",
			"createdTime": "Wed Jun 26 19:42:02 UTC 2024",
			"eniNum": 0,
			"ips": [{
				"privateIp": "192.168.64.65",
				"eip": "null",
				"primary": "true",
				"eipId": "",
				"eipAllocationId": "",
				"eipSize": "0",
				"eipStatus": "",
				"eipGroupId": "",
				"eipType": "null"
			}],
			"ipv6s": [{
				"privateIp": "240c:4081:8005:ca01::14",
				"eip": "null",
				"primary": "false",
				"eipId": "",
				"eipAllocationId": "",
				"eipSize": "0",
				"eipStatus": "",
				"eipGroupId": "",
				"eipType": "null"
			}],
			"securityGroups": [
				"g-37bb45gkyuat"
			]
		},
		"eniNum": "0",
		"tags": [{
			"tagKey": "默认项目",
			"tagValue": ""
		}],
		"networkCapacityInMbps": 0
	}]
}

附录
更新时间：2026-03-04
Model对象定义
InstanceModel
参数名称
类型
描述
id	String	实例ID，符合BCE规范，是一个定长字符串，且只允许包含大小写字母、数字、连字号（-）和下划线(_)。
name	String	实例名称,支持大小写字母、数字、中文以及-_ /.特殊字符，必须以字母开头，长度1-65。
hostname	String	实例主机名,仅支持小写字母、数字以及- . 特殊字符，必须以字母开头，不可连续使用特殊符号，不支持特殊符号开头或结尾，长度2-64。
instanceType	InstanceType	实例类型，具体可选类型参见InstanceType，DCC（专属服务器）该字段为空
status	InstanceStatus	实例状态
chargeStatus	String	计费状态，包含 IS_CHARGING（计费中），STOPPED_NOT_CHARGING（关机不计费），REBOOTING_NOT_CHARGING（开机中，未开始计费）。
repairStatus	String	实例维修状态，包含normal（正常），wait_authorize（待授权维修）， wait_repair（待发单维修），repairing（维修中）四种状态 。
desc	String	实例描述信息
paymentTiming	String	付费方式，付费方式，包括Postpaid(按量付费)，Prepaid(包年包月付费)两种。
createTime	String	创建时间
expireTime	String	过期时间
internalIp	String	内网IP
publicIp	String	外网IP
spec	String	规格
cpuCount	int	CPU(Core)个数
gpuCard	String	实例所携带的GPU卡信息，具体信息参照GpuType
fpgaCard	String	实例所携带的FPGA卡信息，具体信息参照FpgaType
cardCount	int	实例所携带的GPU卡或FPGA卡或异构卡数量，仅在gpuCard或fpgaCard或isomerismCard字段不为空时返回该字段
memoryCapacityInGB	int	内存容量，单位为GB
npuVideoMemory	int	npu显存大小
localDiskSizeInGB	int	本地磁盘大小（不含系统盘，系统盘为免费赠送），单位为GB
imageId	String	镜像ID
imageName	String	镜像名称
imageType	String	镜像类型
serviceComponents	Map<String, String>	服务组件，Map<组件名称,组件状态>
networkCapacityInMbps	int	公网带宽，单位为Mb
placementPolicy	String	实例置放策略，取值default、dedicatedHost。
zoneName	String	可用区信息
subnetId	String	子网ID
vpcId	String	VPC ID
autoRenew	Boolean	是否自动续费，是：true，否：false
enableJumboFrame	Boolean	是否开启Jumbo帧，开启：true，关闭：false
keypairId	String	密钥对ID
keypairName	String	密钥对名称
dedicatedHostId	String	专属服务器ID
ipv6	String	ipv6地址
tags	List<Tag>	标签信息
deploysetId	String	部署集ID
deploysetList	List<DeploySetModel>	部署集信息列表
osVersion	String	操作系统版本
osArch	String	操作系统架构
osName	String	操作系统名称
hosteyeType	String	hosteye版本，enterprise企业版，open基础版，为空或无该字段表示不绑定hosteye
nicInfo	NicInfo	网卡信息，具体参数参见 NicInfo
deletionProtection	int	是否开启删除保护，1开启，0没开
volumes	List<VolumeModel>	磁盘信息，具体参数参见VolumeModel
isEipAutoRelatedDelete	Boolean	实例绑定的EIP是否随抢占实例关联自动释放，是：true，否：false
ehcClusterId	String	实例所在ehc集群id
NicInfo
参数名称
类型
描述
eniId	String	网卡ID
eniUuid	String	网卡长ID
name	String	网卡名称
type	String	网卡类型，primary为主网卡
subnetId	String	子网ID
subnetType	String	子网类型
az	String	可用区信息
description	string	描述
deviceId	string	虚机长ID
status	string	网卡状态
macAddress	string	物理地址
vpcId	string	VPC ID
createdTime	string	创建时间
eniNum	int	网卡数量
eriNum	int	rdma套餐的eri网卡数量
eriInfos	EriInfo	eri网卡信息
ips	List<IpInfo>	辅助IP和主IP信息
ipv6s	List<IpInfo>	ipv6信息
securityGroups	List	安全组短ID列表（主网卡+弹性网卡的安全组）
enterpriseSecurityGroups	List	企业安全组短ID列表（主网卡+弹性网卡的企业安全组）
IpInfo
参数名称
类型
描述
privateIp	String	内网IP地址
eip	String	公网IP地址
primary	String	是否为主IP
eipId	String	绑定的eip 长ID
eipAllocationId	String	eip 短ID
eipSize	String	eip带宽峰值
eipStatus	String	eip状态
eipGroupId	String	共享带宽组ID
eipType	String	eip类型，shared表示共享带宽，normal表示普通eip
VolumeModel
参数名称
类型
描述
id	String	磁盘ID（磁盘详情、磁盘列表接口返回）
productCategory	String	挂载的实例服务类别，可选值包含BCC/HPAS（磁盘详情、磁盘列表接口返回）
name	String	磁盘名称,支持大小写字母、数字、中文以及-_ /.特殊字符，必须以字母开头，长度1-65。（磁盘详情、磁盘列表接口返回）
diskSizeInGB	int	磁盘大小，单位是GB（实例详情、磁盘详情、磁盘列表接口返回）
paymentTiming	String	付费方式，付费方式，包括Postpaid(按量付费)，Prepaid(包年包月)两种。（磁盘列表、磁盘详情接口返回）
createTime	String	创建日期，符合BCE日期规范（磁盘列表、磁盘详情接口返回）
expireTime	String	过期时间（磁盘列表、磁盘详情接口返回）
status	VolumeStatus	磁盘状态 （磁盘列表、磁盘详情接口返回）
type	VolumeType	磁盘类型 （磁盘列表、磁盘详情接口返回）
storageType	StorageType	CDS磁盘存储类型，包括SSD_Enhanced (增强型SSD)，cloud_hp1（通用型SSD），hp1 (高性能云磁盘)和hdd (通用型HDD) 共四种磁盘类型，默认 hp1。（磁盘列表、磁盘详情接口返回）
description	string	描述信息（磁盘列表接口返回）
desc	String	描述信息 （磁盘详情接口返回）
attachments	List<VolumeAttachmentModel>	挂载设备信息列表，磁盘未挂载时该值为空。 （磁盘列表、磁盘详情接口返回）
zoneName	String	可用区信息 （磁盘列表、磁盘详情接口返回）
regionId	String	所在region（磁盘详情接口返回）
snapshotNum	String	磁盘当前具有的快照数量（磁盘详情接口返回）
sourceSnapshotId	String	创建磁盘所用的快照id（磁盘详情接口返回）
autoSnapshotPolicy	AutoSnapshotPolicyModel	磁盘当前配置的快照策略（磁盘详情接口返回）
tags	List<TagModel>	磁盘当前配置的标签（磁盘详情接口返回）
resGroupInfos	List<GroupInfo>	磁盘当前绑定的资源组（磁盘详情接口返回）
encrypted	boolean	是否加密 （磁盘列表、磁盘详情接口返回）
enableAutoRenew	boolean	是否自动续费（磁盘列表、磁盘详情接口返回）
autoRenewTime	int	自动续费时间（磁盘列表、磁盘详情接口返回）
isSystemVolume	boolean	是否为系统盘（实例详情、磁盘列表、磁盘详情接口返回）
clusterId	string	CDS专属集群ID（磁盘列表、磁盘详情接口返回）
volumeId	string	磁盘ID（实例详情接口返回）
cdsExtraIo	int	额外性能（磁盘详情、磁盘列表接口返回）
deleteWithInstance	boolean	磁盘随实例删除，仅后付费类型的数据盘返回
deleteAutoSnapshot	boolean	自动快照随磁盘删除，任何类型的磁盘都会返回
diskCategory	string	磁盘类别， Ephemeral：弹性临时盘， Standard：非弹性临时盘
GroupInfo
参数名称
类型
描述
groupId	String	资源组id
groupName	String	资源组名称
VolumeClusterModel
参数名称
类型
描述
clusterId	String	专属集群ID
clusterName	String	专属集群名称,支持大小写字母、数字、中文以及-_ /.特殊字符，必须以字母开头，长度1-65
createdTime	String	创建日期，符合BCE日期规范
expiredTime	String	过期时间，符合BCE日期规范。
status	String	专属集群状态
logicalZone	String	专属集群类型
productType	String	专属集群付费类型
clusterType	String	专属集群类型
totalCapacity	int	专属集群总容量
usedCapacity	int	专属集群已使用容量
availableCapacity	int	专属集群可用容量
expandingCapacity	int	专属集群扩展容量
createdVolumeNum	int	由专属集群创建的CDS数量
affiliatedCDSNumber	List	由专属集群创建的CDS列表
enableAutoRenew	boolean	是否开启自动付费
DiskZoneResources
参数名称
类型
描述
zoneName	String	zone信息，zoneName命名规范是“国家-region-可用区序列"，小写，例如北京可用区A为"cn-bj-a"。
diskInfos	List<DiskInfo>	可用区可创建的磁盘信息，具体参数参见DiskInfo
DiskInfo
参数名称
类型
描述
storageType	String	磁盘存储类别
maxDiskSize	int	最大可创建磁盘容量
minDiskSize	int	最小创建磁盘容量
EniInfo
参数名称
类型
描述
eniId	String	网卡ID
name	String	网卡名称
vpcId	String	VPC ID
subnetId	String	子网ID
zoneName	String	区域
descritption	String	描述
createdTime	String	创建时间
macAddress	String	物理地址
status	String	状态
securityGroupIds	List	绑定的安全组列表
privateIpSet	List<IpAddress>	IP地址信息，具体参数参见 IpAddress
IpAddress
参数名称
类型
描述
primary	boolean	是否为主IP
publicIpAddress	String	公网IP
privateIpAddress	String	内网IP
ipv6Address	String	IPV6地址
EphemeralDisk
参数名称
类型
描述
storageType	StorageType	磁盘存储类别
sizeInGB	int	磁盘总容量
freeSizeInGB	int	可用容量，GB
ZoneModel
参数名称
类型
描述
zoneName	String	可用区信息
TagModel
参数名称
类型
描述
tagKey	String	标签键
tagValue	String	标签值
ResourceBo
参数名称
类型
描述
id	String	实例ID
serialNumber	String	实例长ID
name	String	实例名称
recycleTime	String	进入回收站的时间
deleteTime	String	从回收站删除的时间
paymentTiming	String	付费类型 prepay/postpay
serviceName	String	资源名称，这里为"云服务器"
serviceType	String	资源类型，这里为"BCC"
configItem	ConfigItem	实例配置信息，具体信息参照 ConfigItem
configItems	List	实例配置列表
RegionModel
参数名称
类型
描述
regionId	String	地域ID，例：bj
regionName	String	地域名称，例：华北-北京
regionEndpoint	String	地域对应的接入地址（Endpoint）
ConfigItem
参数名称
类型
描述
cpu	int	cpu个数
memory	int	内存大小
type	String	实例类型，具体可选类型参见InstanceType
specId	String	实例规格类型
spec	String	实例规格
zoneName	String	可用区名称
CreateCdsModel
参数名称
类型
是否必需
描述
cdsSizeInGB	int	是	CDS磁盘容量，必须为大于0的整数，单位为GB，大小为0~5120G
storageType	StorageType	否	CDS磁盘存储类型，默认是hp1(高性能云磁盘)。
snapshotId	String	否	快照ID，当通过快照创建磁盘时，此属性有效，不能小于快照大小
deleteWithInstance	boolean	否	磁盘随实例删除，计费方式为按量后付时生效，初始值为false，V2 API需要在释放实例时指定cdsAttributeActive参数为true才可生效
encryptKey	String	否	加密密钥
VolumeAttachmentModel
参数名称
类型
描述
volumeId	String	磁盘ID
instanceId	String	实例ID
device	String	挂载设备路径（该参数即将停止使用，为提高代码的兼容性，建议您尽量不要使用该参数）
serial	String	磁盘序列号
SnapshotModel
参数名称
类型
描述
id	String	快照ID
name	String	快照名称,支持大小写字母、数字、中文以及-_ /.特殊字符，必须以字母开头，长度1-65。
sizeInGB	int	快照大小，单位是GB
createTime	String	快照创建时间，符合BCE规范的日期格式
status	SnapshotStatus	快照状态
createMethod	String	快照创建方式，包括手动创建，计划创建
volumeId	String	磁盘ID或实例ID，为空表示相关磁盘已释放
desc	String	快照描述信息
expireTime	String	快照到期时间，符合BCE规范的日期格式（list返回的简化版model无此参数）
package	boolean	是否为大镜像，默认为false
templateId	String	自定义镜像id
insnapId	String	实例快照id
encrypted	boolean	是否加密过
tags	List<Tag>	快照绑定的标签列表
ImageModel
参数名称
类型
描述
id	String	镜像ID
name	String	镜像名称,支持大小写字母、数字、中文以及-_ /.特殊字符，必须以字母开头，长度1-65。
type	ImageType	镜像类型
osType	String	操作系统类型
osVersion	String	操作系统版本
osArch	String	操作系统位数
osName	String	操作系统名称
osBuild	String	镜像操作系统的构建时间
osLang	String	操作系统语言（CHS中文版，ENG英文版）
createTime	String	镜像的创建时间，符合BCE规范的日期格式
status	ImageStatus	镜像状态
desc	String	镜像描述信息
specialVersion	String	操作系统特殊版本信息，financial_safty代表金融加固版本
diskSize	int	已废弃
minDiskGb	int	所需磁盘最小容量
ephemeralSize	int	已废弃
shareToUserNumLimit	int	可共享的用户数量限制（镜像列表接口不支持此字段）
sharedToUserNum	int	已共享的用户数量（镜像列表接口不支持此字段）
package	boolean	是否是大镜像，默认为false
encrypted	boolean	是否为加密镜像
snapshot	List<SnapshotModel>	作为一个大镜像所附带的数据盘快照
SecurityGroupModel
参数名称
类型
描述
id	String	安全组ID
name	String	名称,支持大小写字母、数字、中文以及-_ /.特殊字符，必须以字母开头，长度1-65。
desc	String	描述
vpcId	String	私有网络VPC ID
createdTime	String	安全组创建时间
sgVersion	long	安全组版本号
rules	List<SecurityGroupRuleModel>	安全组规则
tags	List<Tag>	安全组绑定的标签列表
SecurityGroupRuleModel
参数名称
类型
描述
是否必须
remark	String	备注	否
direction	String	入站/出站，取值ingress或egress。	是
ethertype	String	网络类型，取值IPv4或IPv6。值为空时表示默认取值IPv4。	否
portRange	String	端口范围，可以指定80等单个端口，值为空时默认取值1-65535。	否
protocol	String	协议类型，tcp、udp或icmp，值为空时默认取值all。	否
sourceGroupId	String	源安全组ID	否
sourceIp	String	源IP地址，与sourceGroupId不能同时设定值。	否
destGroupId	String	目的安全组ID	否
destIp	String	目的IP地址，与destGroupId不能同时设定值。	否
securityGroupId	String	安全组ID	否
securityGroupRuleId	String	安全组规则ID	否
createdTime	String	安全组规则创建时间	否
updatedTime	String	安全组规则修改时间	否
SnapchainModel
参数名称
类型
描述
status	String	快照链状态 可取值active,expired,clear
chainSize	String	快照链容量,单位GB
chainId	String	快照链id
instanceId	String	虚机id
userId	String	用户id
volumeId	String	磁盘id
volumeSize	int	磁盘大小,单位GB
manualSnapCount	int	手动快照个数
autoSnapCount	int	自动快照个数
createTime	String	创建时间
ZoneInstanceType
参数名称
类型
描述
zoneName	String	zone信息,zoneName命名规范是“国家-region-可用区序列"，小写，例如北京可用区A为"cn-bj-a"。
instanceTypes	List<String>	可用机型
ZoneResource
参数名称
类型
描述
zoneName	String	可用区名称
bccResources	List<BccBidResources>	bcc资源
BccBidResources
参数名称
类型
描述
instanceType	String	实例类型
flavors	List<BccBidFlavors>	套餐列表，当instanceType对应的竞价实例的套餐售罄时flavors返回为空。
BccBidFlavors
参数名称
类型
描述
specId	String	实例规格类型
cpuCount	int	cpu核数
memoryCapacityInGB	int	内存大小
productType	ProductType	产品类型
spec	String	实例规格
InstanceTypeModel
参数名称
类型
描述
type	String	规格分类
name	String	规范代码
cpuCount	int	CPU（Core）个数
memorySizeInGB	int	内存（GB）
localDiskSizeInGB	int	本地磁盘（GB）
KeypairModel
参数名称
类型
描述
keypairId	String	密钥对id
name	String	密钥对名称
description	String	密钥对描述
createdTime	Datetime	密钥对创建时间
publicKey	String	公钥内容
privateKey	String	私钥内容
instanceCount	Integer	密钥对绑定的虚机数目
regionId	String	密钥对所在的地域id
fingerPrint	String	公钥指纹
OsModel
参数名称
类型
描述
instanceId	String	实例ID
osArch	String	操作系统位数
osName	String	操作系统名称
osVersion	String	操作系统版本
osType	String	操作系统类型
osLang	String	操作系统语言（CHS中文版，ENG英文版）
specialVersion	String	操作系统特殊版本信息，financial_safty代表金融加固版本
SharedUser
参数名称
类型
描述
account	String	共享的用户名
accountId	String	共享的用户ID
ucAccount	String	uc账号
AutoSnapshotPolicyModel
参数名称
类型
描述
id	String	自动快照策略ID
name	String	自动快照策略名称,支持大小写字母、数字、中文以及-_ /.特殊字符，必须以字母开头，长度1-65。
timePoints	List<int>	指定自动快照的创建时间点。最小单位为小时，从 00:00~23:00 共 24 个时间点可选，参数为 0~23 的数字，如：1 代表在 01:00 时间点。可以选定多个时间点。 传递参数为一个带有格式的 Json Array：[0, 1, … 23]，最多 24 个时间点，用半角逗号字符隔开。
repeatWeekdays	List<int>	指定自动快照的重复日期。选定周一到周日中需要创建快照的日期，参数为0~6 的数字，如：0 表示周一。允许选择多个日期。 传递参数为一个带有格式的 Json Array：[ 0，1…6]。
status	String	快照状态，有active(运行)、deleted（删除）、paused（暂停）三种状态
retentionDays	int	指定自动快照的保留时间，单位为天。 -1：永久保存 1~65536：指定保存天数。
createdTime	String	自动快照策略的创建时间，符合BCE规范的日期格式 （自该字段起，及之后字段，在volume的接口中没有返回）
updatedTime	String	自动快照策略的最近更新时间，符合BCE规范的日期格式
deletedTime	String	自动快照策略的删除时间，符合BCE规范的日期格式
lastExecuteTime	String	自动快照策略的最后执行时间，符合BCE规范的日期格式
volumeCount	int	关联磁盘数量
InstancePassRoleModel
参数名称
类型
描述
instanceId	String	实例ID
InstancePassRoleFailModel
参数名称
类型
描述
instanceId	String	实例ID
failMessage	String	失败信息
InstanceRoleAssociationModel
参数名称
类型
描述
instanceId	String	实例ID
InstanceRoleModel
参数名称
类型
描述
roleName	String	角色名称
ZoneResourceDetailSpec
参数名称
类型
描述
zoneName	String	可用区
bccResources	BccResources	BCC实例资源信息
ebcResources	BbcResources	EBC实例资源信息
BccResources
参数名称
类型
描述
flavorGroups	List<BccFlavorGroup>	实例套餐规格信息
BbcResources
参数名称
类型
描述
flavorGroups	List<BbcFlavorGroup>	实例套餐规格信息
FileSystemModel
参数名称
类型
描述
fsId	String	cfs文件系统ID
mountAds	String	挂载目标的地址
path	String	挂载目录
protocol	String	cfs文件系统的协议类型，可选值为：nfs，smb
BccFlavorGroup
参数名称
类型
描述
groupId	String	实例套餐规格族
flavors	List<BccFlavor>	实例套餐规格
BbcFlavorGroup
参数名称
类型
描述
groupId	String	实例套餐规格族
flavors	List<BbcFlavor>	实例套餐规格
BccFlavor
参数名称
类型
描述
cpuCount	int	cpu数量
memoryCapacityInGB	int	内存容量（单位：GB）
ephemeralDiskInGb	int	本地数据盘容量（单位：GB）
ephemeralDiskCount	int	本地数据盘数量
ephemeralDiskType	String	本地数据盘类型
gpuCardType	String	gpu卡类型
gpuCardCount	int	gpu卡数量
fpgaCardType	String	fpga卡类型
fpgaCardCount	int	fpga卡数量
productType	String	支持计费类型（PrePaid：包年包月；PostPaid：按量付费；both：包年包月/按量付费）
spec	String	实例套餐规格
specId	String	实例套餐规格类型
enableJumboFrame	Boolean	实例套餐是否支持开启Jumbo帧，开启:true，关闭:false
cpuModel	String	处理器型号
cpuGHz	String	处理器主频
networkBandwidth	String	内网带宽(Gbps)
networkPackage	String	网络收发包
netEthQueueCount	String	套餐网卡队列数
netEthMaxQueueCount	String	套餐网卡最大支持的队列数
eniQuota	int	ENI最大数量（配额）
eriQuota	int	ERI最大数量（配额）
rdmaType	String	rdma类型，RoCE或IB
rdmaNetCardCount	int	rdma网卡数量
rdmaNetBandwidth	int	rdma网卡带宽(Gbps)
systemDiskType	StorageType	套餐支持的系统盘磁盘类型
dataDiskType	StorageType	套餐支持的数据盘磁盘类型
nicIpv4Quota	int	单网卡IPv4地址数量（配额）
nicIpv6Quota	int	单网卡IPv6地址数量（配额）
volumeCount	int	CDS数量
BbcFlavor
参数名称
类型
描述
cpuCount	int	cpu数量
memoryCapacityInGB	int	内存容量（单位：GB）
ephemeralDiskCount	int	本地数据盘数量
ephemeralDiskType	String	本地数据盘类型
gpuCardType	String	gpu卡类型
gpuCardCount	int	gpu卡数量
fpgaCardType	String	fpga卡类型
fpgaCardCount	int	fpga卡数量
productType	String	支持计费类型（PrePaid：包年包月；PostPaid：按量付费；both：包年包月/按量付费）
spec	String	实例套餐规格
specId	String	实例套餐规格类型
enableJumboFrame	Boolean	实例套餐是否支持开启Jumbo帧，开启:true，关闭:false
cpuModel	String	处理器型号
cpuGHz	String	处理器主频
networkBandwidth	String	内网带宽(Gbps)
networkPackage	String	网络收发包
netEthQueueCount	String	套餐网卡队列数
netEthMaxQueueCount	String	套餐网卡最大支持的队列数
eniQuota	int	ENI最大数量（配额）
eriQuota	int	ERI最大数量（配额）
rdmaType	String	rdma类型，RoCE或IB
rdmaNetCardCount	int	rdma网卡数量
rdmaNetBandwidth	int	rdma网卡带宽(Gbps)
systemDiskType	StorageType	套餐支持的系统盘磁盘类型
dataDiskType	StorageType	套餐支持的数据盘磁盘类型
nicIpv4Quota	int	单网卡IPv4地址数量（配额）
nicIpv6Quota	int	单网卡IPv6地址数量（配额）
volumeCount	int	CDS数量
SpecIdPrices
参数名称
类型
描述
specId	String	实例规格类型
specPrices	List<SpecPrices>	实例套餐规格信息
SpecPrices
参数名称
类型
描述
spec	String	实例套餐规格
status	String	实例套餐规格状态
specPrice	double	实例套餐规格对应价格
tradePrice	double	实例最终价，即优惠后订单实付价格
AsGroup
参数名称
类型
描述
groupId	String	伸缩组ID，符合BCE规范，是一个定长字符串，且只允许包含大小写字母、数字、连字号（-）和下划线（_)。
groupName	String	伸缩组名称,支持大小写字母、数字、中文以及-_ /.特殊字符，必须以字母开头，长度1-65。
region	String	伸缩组所在地域
status	AsGroupStatus	伸缩组状态
vpcId	String	私有网络VpcId
nodeNum	int	伸缩组下节点数量
createTime	String	创建时间
zoneInfo	ZoneInfo	可用区及子网信息
groupConfig	GroupConfig	伸缩组规格
blbId	String	负载均衡Id
ZoneInfo
参数名称
类型
描述
zone	String	可用区
subnetId	String	子网ID
GroupConfig
参数名称
类型
描述
minNodeNum	int	最小节点数量
maxNodeNum	int	最大节点数量
cooldownInSec	int	冷却时间（单位：秒）
VpcInfo
参数名称
类型
描述
vpcId	String	私有网络VpcId
vpcName	String	私有网络VPC名称
NodeModel
参数名称
类型
描述
instanceId	String	实例ID
instanceName	String	实例名称
floatingIp	String	浮动IP
internalIp	String	内网IP
status	String	节点状态
payment	String	付费方式
cpuCount	int	cpu数量
memoryCapacityInGB	int	内存大小
instanceType	String	实例类型
sysDiskInGB	int	系统盘大小
subnetType	String	子网类型
isProtected	boolean	是否受保护节点
createTime	String	创建时间
nodeType	String	节点类型
eip	AsEipModel	eip信息
AsEipModel
参数名称
类型
描述
bandwidthInMbps	int	最大带宽
address	String	公网IP
eipStatus	String	EIP状态
eipAllocationId	String	弹性公网IP-实例ID
DeploySetModel
参数名称
类型
描述
deploysetId	String	部署集id
name	String	部署集名称
desc	String	部署集描述
concurrency	int	部署集并发数
strategy	String	部署集策略，HOST_HA：宿主机；RACK_HA：机架；TOR_HA：交换机；POD_RQ：集群
azIntstanceStatisList	List<AzIntstanceStatisDetail>	可用区实例数量统计列表
AzIntstanceStatisDetail
参数名称
类型
描述
zoneName	String	可用区名称
instanceCount	String	部署集关联的实例数量
bccInstanceCnt	String	部署集关联的BCC实例数量
bbcInstanceCnt	String	部署集关联的BBC实例数量
instanceTotal	int	当前部署集strategy类型下指定可用区配额
instanceIds	List	部署集关联的实例列表，查询部署集详情返回，查询部署集列表不返回
bccInstanceIds	List	部署集关联的BCC实例ID列表，查询部署集详情返回，查询部署集列表不返回
bbcInstanceIds	List	部署集关联的BBC实例数量，查询部署集详情返回，查询部署集列表不返回
PrepayConfig
参数名称
类型
描述
instanceId	String	实例ID
duration	int	购买时长（单位：月）
cdsList	List	（该参数已废弃，bcc挂载的按量付费CDS数据盘必须一起转包年包月） 变更关联的数据盘列表，默认为空，all表示关联的全部数据盘（例"cdsList":["all"]，若仅变更部分关联数据盘，传具体的数据盘id）
autoRenew	boolean	实例到期后是否自动续费，取值：true：自动续费，false：不自动续费，默认值：false。
autoRenewPeriod	int	每次自动续费的时长（单位：月）。取值范围：1，2，3，4，5，6，7，8，9，12，24，36，默认值：1。仅当autoRenew取值为true，该参数有效。
autoPay	boolean	是否自动支付，默认true，表示自动支付
PostpayConfig
参数名称
类型
描述
instanceId	String	实例ID
cdsList	List	（该参数已废弃，bcc挂载的包年包月CDS数据盘必须一起转按量付费）变更关联的数据盘列表，默认为空，all表示关联的全部数据盘（例"cdsList":["all"]，若仅变更部分关联数据盘，传具体的数据盘id）。
effectiveType	String	生效方式，可选参数：AtOnce（立即转按量付费）、AfterExpiration（到期后转按量付费）。不传默认为到期后按量付费。批量操作该参数必须保持一致。
InstanceDeleteResultModel
参数名称
类型
描述
instanceId	String	实例id
eip	String	eip
insnapIds	List	实例快照id列表
snapshotIds	List	快照id列表
volumeIds	List	磁盘id列表
ModifyReservedInstanceModel
参数名称
类型
描述
reservedInstanceId	String	要调整的预留实例券id
zoneName	String	要调整的目标可用区，例如：cn-bj-b。不支持同时修改reservedInstanceName
reservedInstanceName	String	要调整的实例券名称；规则：支持大小写字母、数字、中文以及-_ /.特殊字符，必须以中文或字母开头，长度1-65，可重复；客户未命名的情况下自动命名：reservedInstance-${随机生成}，同样遵循以上命名规则。不支持同时修改zoneName
ehcClusterId	String	变更roce预留实例券时可选参数，若为空则使用默认EHC集群
ModifyReservedInstanceResultModel
参数名称
类型
描述
reservedInstanceId	String	预留实例券的id
orderId	String	预留实例券变更的订单号reservedInstanceName
类型编码定义
VolumeType
编码
描述
System	系统盘
Ephemeral	本地磁盘
Cds	CDS云磁盘
StorageType
编码
描述
可创建数据盘
可创建系统盘
enhanced_ssd_pl1 或 SSD_Enhanced	增强型SSD_PL1	是	是
enhanced_ssd_pl2	增强型SSD_PL2	是	是
enhanced_ssd_pl3	增强型SSD_PL3	是	是
cloud_hp1 或 premium_ssd	通用型SSD	是	是
hp1 或 ssd	高性能云磁盘	是	是
hdd	通用型HDD (该类型已在逐步下线中)	是	否
elastic_ephemeral_disk	弹性临时盘普通型	是	否
local	本地盘	否	否
sata	上一代云磁盘，创建DCC子实例专用	-	-
local_ssd	数据存储于本地SSD盘，延时较低，IO和吞吐能力较好，适用于中大型关系型数据库业务	-	-
local_hdd 或 std1	本地HDD磁盘，适合大规模数据存储的场景	-	-
local_nvme 或 nvme	本地NVME磁盘,数据存储于本地NVME SSD盘，超高性能，适用于时延敏感型业务	-	-
ImageType
编码
描述
All	所有镜像
System	bcc系统镜像/公共镜像(不包括ebc)
Custom	bcc自定义镜像(不包括ebc)
Integration	服务集成镜像
Sharing	共享镜像
BbcSystem	bbc系统镜像，ebc系统镜像
BbcCustom	bbc自定义镜像，ebc自定义镜像
GpuBccSystem	bcc GPU公共镜像
GpuBccCustom	bcc GPU自定义镜像
GpuBbcSystem	bbc GPU公共镜像
GpuBbcCustom	bbc GPU自定义镜像
EbcTotal	ebc所有镜像
EbcSystem	ebc系统镜像
EbcCustom	ebc自定义镜像
FpgaBccSystem	FPGA专用公共镜像
FpgaBccCustom	FPGA自定义镜像
GpuType
编码
描述
V100-32	NVIDIA Tesla V100-32G
V100-16	NVIDIA Tesla V100-16G
P40	NVIDIA Tesla P40
P4	NVIDIA Tesla P4
K40	NVIDIA Tesla K40
DLCard	NVIDIA 深度学习开发卡
FpgaType
编码
描述
KU115	xilinx ku115
InternetChargeType
编码
描述
BANDWIDTH_PREPAID	包年包月按带宽结算
TRAFFIC_POSTPAID_BY_HOUR	流量按小时后付费
BANDWIDTH_POSTPAID_BY_HOUR	带宽按小时后付费
BidModel
编码
描述
market	按照市场价出价
custom	自定义出价
DeployStrategy
编码
描述
HOST_HA	宿主机隔离
RACK_HA	机架隔离
TOR_HA	交换机隔离
SystemImageModel
﻿
参数名称
类型
imageId	String	镜像ID
imageName	String	镜像名称
osType	String	操作系统类型
osVersion	String	操作系统版本
osArch	String	操作系统位数
osName	String	操作系统名称
osLang	String	操作系统语言（CHS中文版，ENG英文版）
minSizeInGiB	String	支持系统盘最小容量（单位：GB）
状态编码定义
ProductType
编码
描述
Prepaid	包年包月（预付费）
Postpaid	按量付费（后付费）
InstanceStatus
编码
描述
Starting	启动中
Running	运行中
Stopping	停止中
Stopped	已停止
Recycled	处于回收站中
Deleted	已释放，该状态为内部状态，API无法查询
Scaling	扩展中
Expired	已过期或欠费
Error	错误
SnapshotProcessing	快照操作中
ImageProcessing	镜像操作中
Recharging	续费中
VolumeResizing	磁盘扩容中
BillingChanging	计费变更中
ChangeSubnet	子网变更中
ChangeVpc	VPC变更中
AttachingPort	挂载弹性网卡中
DetachingPort	卸载弹性网卡中
Moving	迁移中，实例操作变更可用区/跨AZ迁移时的状态
VolumeStatus
编码
描述
Creating	创建中。卷创建是异步操作，Creating表示系统已收到创建请求，并分配相应卷ID，但尚未创建完成
Available	待挂载。卷已创建完成，状态正常，且未attach到任何虚拟机实例
Attaching	挂载中。卷attach是异步操作，该状态表示正在进行attach操作
NotAvailable	临时不可用状态
InUse	使用中
Detaching	卸载中。卷detach是异步操作，该状态表示正在进行detach操作
Deleting	删除中
Deleted	已删除，该状态为内部状态，API无法查询
Scaling	扩展中
Expired	已过期或欠费
Error	错误
SnapshotProcessing	快照操作中
ImageProcessing	镜像操作中
Recharging	续费中
RemoteCopyRequest
编码
类型
描述
name	String	快照名称
destRegion	String	待复制快照的目标区域
RemoteCopySnapshot
编码
类型
描述
region	String	目标区域
snapshotId	String	成功复制到目标区域快照的快照ID
SnapshotStatus
编码
描述
Creating	创建中
CreatedFailed	创建失败
Available	可用
NotAvailable	不可用
ImageStatus
编码
描述
Creating	创建中
CreatedFailed	创建失败
Available	可用
NotAvailable	不可用
Error	错误
RelatedRenewFlag
编码
描述
CDS	只对BCC实例关联的包年包月（预付费）CDS进行续费
EIP	只对BCC实例关联的包年包月（预付费）EIP进行续费
MKT	只对BCC实例关联的包年包月（预付费）MKT进行续费
CDS_EIP	只对BCC实例关联的包年包月（预付费）CDS、EIP进行续费
CDS_MKT	只对BCC实例关联的包年包月（预付费）CDS、MKT进行续费
EIP_MKT	只对BCC实例关联的包年包月（预付费）EIP、MKT进行续费
CDS_EIP_MKT	只对BCC实例关联的包年包月（预付费）CDS、EIP、MKT进行续费
AsGroupStatus
编码
描述
CREATING	创建中
RUNNING	运行中
SCALING_UP	扩容中
SCALING_DOWN	缩容中
ATTACHING_NODE	移入节点中
DETACHING_NODE	移出节点中
DELETING	删除中
BINDING_BLB	绑定blb中
UNBINDING_BLB	解绑blb中
COOLDOWN	冷却中
PAUSE	挂起中
DELETED	已删除
区域机型以及可选配置
InstanceType
编码
描述
新机型名称
N1	普通型BCC实例	通用型g1、计算型c1、密集计算型ic1、内存型m1
N2	普通型ⅡBCC实例	通用型g2、计算型c2、密集计算型ic2、内存型m2
N3	普通型ⅢBCC实例	通用型g3、计算型c3、密集计算型ic3、内存型m3
N4	网络增强型BCC实例	通用网络增强型g3ne、计算网络增强型c3ne、内存网络增强型m3ne
N5	普通型ⅣBCC实例	通用型g4、密集计算型ic4、计算型c4、内存型m4
N6	普通型V BCC实例	通用型g5、密集计算型ic5、计算型c5、内存型m5
C1	计算优化型实例	高主频计算型hcc1、高主频通用型hcg1
C2	计算优化Ⅱ型实例	高主频计算型hcc2、高主频通用型hcg2
S1	存储优化型实例	本地SSD型l1
G1	GPU型实例	---
F1	FPGA型实例	---
GpuType
编码
描述
V100-32	NVIDIA Tesla V100-32G
V100-16	NVIDIA Tesla V100-16G
P40	NVIDIA Tesla P40
P4	NVIDIA Tesla P4
K40	NVIDIA Tesla K40
DLCard	NVIDIA 深度学习开发卡
区域可支持实例类型（随产品规划而变化，请以控制台购买页为准）
区域
支持创建实例类型
北京(bj)	普通型BCC(N1)，可选配置参考普通型BCC(N1)可选规格配置
普通型ⅡBCC(N2)，可选配置参考普通型ⅡBCC(N2)可选规格配置
普通型ⅢBCC(N3)，可选配置参考普通型ⅢBCC(N3)可选规格配置
计算优化型实例(C1)，可选配置参考计算优化型实例(C1)可选规格配置
存储优化型实例(S1)，可选配置参考存储优化型实例(S1)可选规格配置
GPU型实例(G1)，可选配置参考GPU型实例(G1)可选规格配置
FPGA型实例(F1)，可选配置参考FPGA型实例(F1)可选规格配置
广州(gz)	普通型BCC(N1)，可选配置参考普通型BCC(N1)可选规格配置
普通型ⅡBCC(N2)，可选配置参考普通型ⅡBCC(N2)可选规格配置
普通型ⅢBCC(N3)，可选配置参考普通型ⅢBCC(N3)可选规格配置
计算优化型实例(C1)，可选配置参考计算优化型实例(C1)可选规格配置
存储优化型实例(S1)，可选配置参考存储优化型实例(S1)可选规格配置
GPU型实例(G1)，可选配置参考GPU型实例(G1)可选规格配置
苏州(su)	普通型ⅡBCC(N2)，可选配置参考普通型ⅡBCC(N2)可选规格配置
普通型ⅢBCC(N3)，可选配置参考普通型ⅢBCC(N3)可选规格配置
计算优化型实例(C1)，可选配置参考计算优化型实例(C1)可选规格配置
存储优化型实例(S1)，可选配置参考存储优化型实例(S1)可选规格配置
GPU型实例(G1)，可选配置参考GPU型实例(G1)可选规格配置
普通型BCC可选规格配置
包年包月（预付费）可选规格配置(CPU核数, 内存GB)
按量付费（后付费）可选规格配置(CPU核数, 内存GB)
[1, 1], [1, 2], [1, 4], [1, 8],
[2, 2], [2, 4], [2, 8], [2, 12], [2, 16],
[4, 4], [4, 8], [4, 12], [4, 16], [4, 32],
[8, 8], [8, 12], [8, 16], [8, 24], [8, 32], [8, 64],
[12, 12], [12, 16], [12, 24], [12, 32], [12, 48], [12, 64],
[16, 16], [16, 24], [16, 32], [16, 48], [16, 64]	同包年包月（预付费）可选规格配置(CPU核数, 内存GB)
普通型BCCⅡ可选规格配置
包年包月（预付费）可选规格配置(CPU核数, 内存GB)
按量付费（后付费）可选规格配置(CPU核数, 内存GB)
[1, 1], [1, 2], [1, 4], [1, 8],
[2, 2], [2, 4], [2, 8], [2, 12], [2, 16],
[4, 4], [4, 8], [4, 12], [4, 16], [4, 32],
[8, 8], [8, 12], [8, 16], [8, 24], [8, 32], [8, 64],
[12, 12], [12, 16], [12, 24], [12, 32], [12, 48], [12, 64],
[16, 16], [16, 24], [16, 32], [16, 48], [16, 64], [16, 128],
[32, 64], [32, 128],
[48, 96], [48, 128], [48, 192]	[1, 1], [1, 2], [1, 4], [1, 8],
[2, 2], [2, 4], [2, 8], [2, 12], [2, 16],
[4, 4], [4, 8], [4, 12], [4, 16], [4, 32],
[8, 8], [8, 12], [8, 16], [8, 24], [8, 32], [8, 64],
[12, 12], [12, 16], [12, 24], [12, 32], [12, 48], [12, 64],
[16, 16], [16, 24], [16, 32], [16, 48], [16, 64], [16, 128]
###普通型BCCⅢ可选规格配置

包年包月（预付费）可选规格配置(CPU核数, 内存GB)
按量付费（后付费）可选规格配置(CPU核数, 内存GB)
[1, 1], [1, 2], [1, 4], [1, 8],
[2, 2], [2, 4], [2, 8], [2, 12], [2, 16],
[4, 4], [4, 8], [4, 12], [4, 16], [4, 32],
[8, 8], [8, 12], [8, 16], [8, 24], [8, 32], [8, 64],
[12, 12], [12, 16], [12, 24], [12, 32], [12, 48], [12, 64],
[16, 16], [16, 24], [16, 32], [16, 48], [16, 64], [16, 128],
[24, 48], [24, 96], [24, 128],
[32, 64], [32, 128], [32, 256],
[48, 96], [48, 128], [48, 192], [48, 256],
[64, 128], [64, 256],
[96, 256]	同包年包月（预付费）可选规格配置(CPU核数, 内存GB)
计算优化型实例可选规格配置
包年包月（预付费）可选规格配置(CPU核数, 内存GB)
按量付费（后付费）可选规格配置(CPU核数, 内存GB)
[4, 8], [4, 16], [4, 32],
[8, 16], [8, 32],
[16, 32], [16, 64],
[24, 96]	同包年包月（预付费）可选规格配置(CPU核数, 内存GB)
存储优化型实例可选规格配置
预付费可选规格配置(CPU核数, 内存GB)
后付费可选规格配置(CPU核数, 内存GB)
[1, 1], [1, 2], [1, 4], [1, 8],
[2, 2], [2, 4], [2, 8], [2, 12], [2, 16],
[4, 4], [4, 8], [4, 12], [4, 16], [4, 32],
[8, 8], [8, 12], [8, 16], [8, 24], [8, 32], [8, 64],
[12, 12], [12, 16], [12, 24], [12, 32], [12, 48], [12, 64],
[16, 16], [16, 24], [16, 32], [16, 48], [16, 64]	同预付费可选规格配置(CPU核数, 内存GB)
GPU型BCC可选规格配置
预付费可选规格配置(GPU卡类型,GPU卡数量,CPU核数, 内存GB,本地磁盘大小GB)
后付费可选规格配置(GPU卡类型,GPU卡数量,CPU核数, 内存GB,本地磁盘大小GB)
[P4,1,12,40,450],[P4,2,24,80,900],[P4,4,48,160,1800],
[P40,1,12,40,450],[P40,2,24,80,900],[P40,4,48,160,1800],
[K40,1,6,40,450],[K40,2,12,80,400],[K40,4,24,160,800],
[DLCard,1,6,40,450],[DLCard,2,12,80,400],[DLCard,4,24,160,800]	同预付费可选规格配置(GPU卡类型,GPU卡数量,CPU核数, 内存GB,本地磁盘大小GB)
FPGA型BCC可选规格配置
预付费可选规格配置(FPGA卡类型,FPGA卡数量,CPU核数, 内存GB,本地磁盘大小GB)
后付费可选规格配置(FPGA卡类型,FPGA卡数量,CPU核数, 内存GB,本地磁盘大小GB)
[KU115,1,16,64,450]	同预付费可选规格配置(FPGA卡类型,FPGA数量,CPU核数, 内存GB,本地磁盘大小GB)
实例套餐规格定义（已废弃，不建议使用）
规格分类
规格代码
CPU(Core)
内存（GB)
Tiny	bcc.t1.tiny	1	1
General	bcc.g1.tiny	1	2
General	bcc.g2.tiny	1	4
General	bcc.g3.tiny	1	8
General	bcc.g1.small	2	2
General	bcc.g2.small	2	4
General	bcc.g3.small	2	8
General	bcc.g4.small	2	12
General	bcc.g1.medium	4	4
General	bcc.g2.medium	4	8
Memory	bcc.m1.medium	4	12
Memory	bcc.m2.medium	4	16
Memory	bcc.m1.large	8	16
Memory	bcc.m2.large	8	24
Memory	bcc.m3.large	8	32
cpu	bcc.c1.large	8	8
cpu	bcc.c2.large	8	12
cpu	bcc.c1.xlarge	12	12
cpu	bcc.c2.xlarge	12	16
cpu	bcc.c3.xlarge	12	24
cpu	bcc.c4.xlarge	12	32
cpu	bcc.c5.xlarge	12	48
cpu	bcc.c1.2xlarge	16	16
cpu	bcc.c2.2xlarge	16	24
cpu	bcc.c3.2xlarge	16	32
cpu	bcc.c4.2xlarge	16	48
cpu	bcc.c5.2xlarge	16	64
订单信息定义
Billing
状态
类型
描述
paymentTiming	String	付费方式，包括预支付（Prepaid）、后支付（Postpaid）和抢占实例（bidding）
reservation	Reservation	保留信息，支付方式为后支付时不需要设置，预支付时必须设置
Reservation
状态
类型
描述
reservationLength	int	时长，[1,2,3,4,5,6,7,8,9,12,24,36]
reservationTimeUnit	String	时间单位，Month，当前仅支持按月
TransferInRecord
状态
类型
描述
transferRecordId	String	券转移记录id
grantorUserId	String	转让人账号(脱敏处理)
status	String	券转移记录状态
reservedInstanceInfo	ReservedInstanceInfo	预留实例券详情
applicationTime	String	券转移发起时间
expireTime	String	券转移过期时间
endTime	String	券转移结束时间
TransferOutRecord
状态
类型
描述
transferRecordId	String	券转移记录id
recipientUserId	String	接收人账号(脱敏处理)
status	String	券转移记录状态
reservedInstanceInfo	ReservedInstanceInfo	预留实例券详情
applicationTime	String	券转移发起时间
expireTime	String	券转移过期时间
endTime	String	券转移结束时间
ReservedInstanceInfo
状态
类型
描述
reservedInstanceId	String	预留实例券id
reservedInstanceUuId	String	预留实例券长id
reservedInstanceName	String	预留实例券名称
scope	String	预留实例券生效范围
zoneName	String	预留实例券可用区
spec	String	预留实例券实例规格
reservedType	String	预留实例券类型
offeringType	String	预留实例券付费方式
osType	String	预留实例券镜像类型
reservedInstanceStatus	String	预留实例券状态
instanceCount	int	预留实例券实例数量
instanceId	String	抵扣实例ID
instanceName	String	抵扣实例名称
effectiveTime	String	预留实例券生效时间
expireTime	String	预留实例券过期时间
autoRenew	String	预留实例券是否开启自动续费
renewTimeUnit	String	预留实例券自动续费单位
renewTime	String	预留实例券续费时长
nextRenewTime	String	预留实例券下次自动续费时间
ehcClusterId	String	预留实例券所在ehc集群id
TaskModel
状态
类型
描述
taskId	String	任务ID，符合BCE规范，是一个定长字符串，且只允许包含大小写字母、数字、连字号（-）和下划线（_）。
instanceId	String	实例ID
internalIp	String	实例内网IP
status	String	任务状态
errResult	String	故障描述
createTime	String	创建时间
enableHotplug	Boolean	是否支持热维修，true表示支持，空表示不支持
isSystemDiskRecoverable	Boolean	系统盘数据是否可修复，true表示可修复，空表示不可修复
relocationTime	int	冷迁预估时长，空表示无此信息
retainDataDisk	Boolean	是否保留数据盘数据，true表示保留，空表示不保留
errStartTime	String	故障发生时间
newTaskTime	String	创建维修任务时间
authorizeTaskTime	String	授权维修任务时间
unAuthorizeTaskTime	String	未授权维修任务时间
simCompletionTime	String	维修人员维修完成时间
checkTaskTime	String	验收维修任务时间
firstConfirmedTime	String	首次验收维修任务或验收未完成时间
ClosedTaskModel
状态
类型
描述
taskId	String	任务ID，符合BCE规范，是一个定长字符串，且只允许包含大小写字母、数字、连字号（-）和下划线（_）。
instanceId	String	实例ID
internalIp	String	实例内网IP
errResult	String	故障描述
startTime	String	任务开始时间
endTime	String	任务结束时间
errStartTime	String	故障发生时间
newTaskTime	String	创建维修任务时间
authorizeTaskTime	String	授权维修任务时间
unAuthorizeTaskTime	String	未授权维修任务时间
simCompletionTime	String	维修人员维修完成时间
checkTaskTime	String	验收维修任务时间
firstConfirmedTime	String	首次验收维修任务或验收未完成时间
RepairTaskDetail
状态
类型
描述
taskId	String	任务ID，符合BCE规范，是一个定长字符串，且只允许包含大小写字母、数字、连字号（-）和下划线（_）。
instanceId	String	实例ID
instanceName	String	实例名称
errResult	String	故障描述
status	String	任务状态
serverStatus	String	实例状态
region	String	实例所在region
internalIp	String	实例内网ip
floatingIp	String	实例floating ip
errStartTime	String	故障发生时间
newTaskTime	String	创建维修任务时间
authorizeTaskTime	String	授权维修任务时间
unAuthorizeTaskTime	String	未授权维修任务时间
simCompletionTime	String	维修人员维修完成时间
checkTaskTime	String	验收维修任务时间
firstConfirmedTime	String	首次验收维修任务或验收未完成时间
OperationRecord
状态
类型
描述
name	String	操作名
operator	String	操作人
operateTime	String	操作时间
RuleModel
状态
类型
描述
ruleId	String	操作名
ruleName	String	操作人
tagCount	int	关联的标签数量
limit	int	预授权上限
status	String	规则状态，enabled/disabled
RuleDetail
状态
类型
描述
ruleId	String	操作名
ruleName	String	操作人
tagCount	int	关联的标签数量
limit	int	预授权上限
status	String	规则状态，enabled/disabled
tags	List<Tag>	关联标签列表
CdsCustomPeriod
状态
类型
描述
volumeId	String	磁盘ID（磁盘详情、磁盘列表接口返回）
period	int	续费时长，单位为月，范围为【1，60】。需保证续费后磁盘的到期时间等于或晚于BCC到期时间，否则续费失败。
SnapshotShareModel
状态
类型
描述
sourceSnapshotId	String	源快照ID
sourceSnapshotUuid	String	源快照uuid
snapshotId	String	共享快照ID
sourceAccountId	String	共享方用户ID
accountId	String	接收方用户ID
snapshotType	String	快照类型
name	String	共享快照名称
sizeInGB	Long	快照大小
shareTime	LocalDateTime	快照共享时间
desc	String	共享快照描述
shareStatus	String	共享状态
encryptKey	String	加密的密钥对
isSourceDeleted	Boolean	源快照是否已被删除
TaskDetail
参数名称
类型
描述
taskId	String	任务ID
taskAction	String	任务类型
taskStatus	String	任务状态：
Processing 处理中
Finished 已完成
Failed 处理失败
createdTime	String	创建时间
finishedTime	String	完成时间
totalCount	Integer	总数
successCount	Integer	成功数量
failedCount	Integer	失败数量
operationProgressSet	List<OperationProgressSet>	操作列表，任务列表接口无此信息

OperationProgressSet
参数名称
类型
描述
resourceId	String	资源ID
operationStatus	String	操作状态
code	String	响应码
errorMessage	String	错误信息

OperationRecordResponse
参数名称
类型
描述
name	String	操作名
operator	String	操作人
operateTime	String	操作时间，符合BCE规范的日期格式

IssueResponse
参数名称
类型
描述
issueName	String	故障名称
issueEffect	String	故障影响
issueDescription	String	故障描述
issueOccurTime	String	故障发生时间，符合BCE规范的日期格式

IssueDiskInfoResponse
参数名称
类型
描述
issueDiskSn	String	故障磁盘sn

UnplannedEventResponse
参数名称
类型
描述
serverEventId	String	事件id
serverEventType	String	事件类型，支持类型：InstanceRepairBySystemFailureEvent，InstanceRepairOrFastRepairBySystemFailureEvent，LocalDiskInstanceRepairBySystemFailureEvent，LocalDiskInstanceRepairOrFastRepairBySystemFailureEvent
serverEventStatus	String	事件状态，支持状态：Inquiring，Processing，Executing，Executed，Abnormal，Closed
instanceId	String	故障实例ID
productCategory	String	故障实例产品类型
instanceSpec	String	故障实例规格
instanceName	String	故障实例名
privateIp	String	故障实例的内网IP。
tags	List<TagModel>	故障实例的标签信息
serverEventCreatedTime	String	创建时间，符合BCE规范的日期格式，例如：2025-02-13T00:00:00Z
serverEventEndedTime	String	事件结束时间，符合BCE规范的日期格式，例如：2025-02-13T00:00:00Z
maintenanceOptions	List<String>	该事件支持的运维操作，可能支持的类型：Repair、Reboot
supportMaintenanceOptions	List<String>	用户可授权的运维操作（多事件场景下会过滤掉当前事件支持但是优先级低的情况，比如该事件是Reboot，另一事件为Repair，此时展示为空），可能支持的类型：Repair、Reboot
authorizedMaintenanceOperation	String	该事件已授权的维修方式，与授权时使用的方式一致
associatedPlannedMaintenanceServerEventIds	List<String>	多事件情况下该实例关联计划内运维事件ID列表
associatedUnplannedMaintenanceServerEventIds	List<String>	多事件情况下该实例关联非预期运维事件ID列表
executeTime	String	事件执行时间，符合BCE规范的日期格式，例如：2025-02-13T00:00:00Z
serverEventLogs	List<OperationRecordResponse>	操作日志，包括用户授权、运维、验收等操作记录。
failures	List<IssueResponse>	故障事项
issueDiskInfos	List<IssueDiskInfoResponse>	故障磁盘信息

PlannedEventResponse
参数名称
类型
描述
serverEventId	String	事件id
serverEventType	String	事件类型，支持类型：InstanceRepairBySystemFailureEvent，InstanceRepairOrFastRepairBySystemFailureEvent，LocalDiskInstanceRepairBySystemFailureEvent，LocalDiskInstanceRepairOrFastRepairBySystemFailureEvent
serverEventStatus	String	事件状态，支持状态：Inquiring，Processing，Executing，Executed，Abnormal，Closed
instanceId	String	故障实例ID
productCategory	String	故障实例产品类型
instanceSpec	String	故障实例规格
instanceName	String	故障实例名
privateIp	String	故障实例的内网IP。
tags	List<TagModel>	故障实例的标签信息
serverEventCreatedTime	String	创建时间，符合BCE规范的日期格式，例如：2025-02-13T00:00:00Z
serverEventEndedTime	String	事件结束时间，符合BCE规范的日期格式，例如：2025-02-13T00:00:00Z
maintenanceOptions	List<String>	该事件支持的运维操作，可能支持的类型：Repair、Reboot
supportMaintenanceOptions	List<String>	用户可授权的运维操作（多事件场景下会过滤掉当前事件支持但是优先级低的情况，比如该事件是Reboot，另一事件为Repair，此时展示为空），可能支持的类型：Repair、Reboot
authorizedMaintenanceOperation	String	该事件已授权的维修方式，与授权时使用的方式一致
associatedPlannedMaintenanceServerEventIds	List<String>	多事件情况下该实例关联计划内运维事件ID列表
associatedUnplannedMaintenanceServerEventIds	List<String>	多事件情况下该实例关联非预期运维事件ID列表
executeTime	String	事件执行时间，符合BCE规范的日期格式，例如：2025-02-13T00:00:00Z
serverEventLogs	List<OperationRecordResponse>	操作日志，包括用户授权、运维、验收等操作记录。
risks	List<IssueResponse>	风险事项

InstUserOpAuthorizeRuleResponse
参数名称
类型
描述
ruleId	String	规则ID
ruleName	String	规则名称
serverEventCategory	String	预授权事件分类（UnplannedMaintenanceEvent / PlannedMaintenanceEvent）
status	String	规则状态（ DISABLED / ENABLED）
authorizeMaintenanceOperations	List<String>	授权方法（TamAuthorize / Repair / Reboot）
createTime	String	创建时间，符合BCE规范的日期格式