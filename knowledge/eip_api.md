查询EIP列表
更新时间：2026-03-03
可根据多重条件查询EIP列表。
如只需查询单个EIP的详情，只需提供eip参数即可。
如只需查询绑定到指定类型实例上的EIP，提供instanceType参数即可。
如只需查询指定实例上绑定的EIP的详情，提供instanceType及instanceId参数即可。
若不提供查询条件，则默认查询覆盖所有EIP。
返回结果为多重条件交集的查询结果，即提供多重条件的情况下，返回同时满足所有条件的EIP。
以上查询结果支持marker分页，分页大小默认为1000，可通过maxKeys参数指定。
API Explorer
去调试
您可以在 API Explorer 中直接运行该接口，免去您计算签名的困扰。运行成功后，API Explorer 可以自动生成 SDK 代码示例。

请求结构

Plain Text复制
GET /v{version}/eip?ipVersion={ipVersion}&eip={eip}&instanceType={instanceType}&instanceId={instanceId}&status={status}&marker={marker}&maxKeys={maxKeys} HTTP/1.1
Host: eip.bj.baidubce.com
Authorization: authorization string
除公共头域外，无其他特殊头域

请求参数

参数名称
类型
是否必需
参数位置
描述
version	String	是	URL参数	API版本号，当前取值1
ipVersion	String	否	Query参数	要查询的EIP IP类型，包含ipv4和ipv6，默认ipv4。
eip	String	否	Query参数	要查询的EIP，包括IPv4 EIP和IPv6 EIP,如需查询指定IPv6 EIP，需要指定ipVersion为ipv6。
instanceType	String	否	Query参数	绑定实例类型.取值 BCC、BBC、DCC、ENI、BLB、NAT、VPN
instanceId	String	否	Query参数	绑定实例的短ID，若指定了此参数，需同时提供instanceType参数
name	String	否	Query参数	要查询的EIP名称
status	String	否	Query参数	实例状态，仅支持available, binded, paused三种状态的查询
eipIds	List <String>	否	Query参数	EIP短ID，支持单EIP ID或者多EIP ID查询（多个EIP ID用英文逗号隔开）
marker	String	否	Query参数	批量获取列表的查询的起始位置，是一个由系统生成的字符串
maxKeys	int	否	Query参数	每页包含的最大数量，最大数量不超过1000。缺省值为1000
返回状态码

成功返回200，失败返回见错误码

返回头域

除公共头域外，无其他特殊头域

返回参数

参数名称
类型
描述
eipList	List<EipModel>	包含查询结果的列表
marker	string	标记查询的起始位置，若结果列表为空，此项不存在
isTruncated	boolean	true表示后面还有数据，false表示已经是最后一页
nextMarker	String	获取下一页所需要传递的marker值。当isTruncated为false时，该域不出现
maxKeys	int	每页包含的最大数量
请求示例, 查询IPv4 EIP列表

Plain Text复制
GET /v1/eip?instanceType=BCC&maxKeys=2 HTTP/1.1
HOST eip.bj.baidubce.com
Authorization bce-auth-v1/5e5a8adf11ae475ba95f1bd38228b44f/2016-04-10T08:26:52Z/1800/host;x-bce-date/ec3c0069f9abb1e247773a62707224124b2b31b4c171133677f9042969791f02
请求示例, 查询IPv6 EIP列表

Plain Text复制
GET /v1/eip?ipVersion=ipv6&eip=240c:4082:ffff:ff01:0:4:0:12a HTTP/1.1
HOST eip.bj.baidubce.com
Authorization bce-auth-v1/5e5a8adf11ae475ba95f1bd38228b44f/2016-04-10T08:26:52Z/1800/host;x-bce-date/ec3c0069f9abb1e247773a62707224124b2b31b4c171133677f9042969791f02
响应示例, 查询IPv4 EIP列表

Plain Text复制
HTTP/1.1 200 OK
x-bce-request-id: 946002ee-cb4f-4aad-b686-5be55df27f09
Date: Wed, 10 Apr 2016 08:26:52 GMT
Transfer-Encoding: chunked
Content-Type: application/json;charset=UTF-8
Server: BWS

{
    "eipList": [
        {
            "name":"eip-xrllt5M-1",
            "eip": "180.181.3.133",
            "eipId": "ip-xxxxxxxx",
            "status":"binded",
            "instanceType": "BCC",
            "instanceId": "i-IyWRtII7",
            "shareGroupId": "eg-0c31c93a",
            "eipInstanceType": "shared",
            "bandwidthInMbps": 5,
            "paymentTiming":"Prepaid",
            "billingMethod":null,
            "createTime":"2016-03-08T08:13:09Z",
            "expireTime":"2016-04-08T08:13:09Z",
            "region":"bj",
            "routeType":"BGP",
            "tags": [
                {
                    "tagKey": "aa",
                    "tagValue": "bb"
                }
            ],
            "deleteProtect":true
        },
        {
            "name":"eip-scewa1M-1",
            "eip": "180.181.3.134",
            "eipId": "ip-xxxxxxxx",
            "status":"binded",
            "instanceType": "BCC",
            "instanceId": "i-KjdgweC4",
            "shareGroupId": null,
            "eipInstanceType": "normal",
            "bandwidthInMbps": 1,
            "paymentTiming":"Postpaid",
            "billingMethod":"ByTraffic",
            "createTime":"2016-03-08T08:13:09Z",
            "expireTime":null,
            "region":"bj",
            "routeType":"BGP",
            "tags": [
                {
                    "tagKey": "key",
                    "tagValue": "value"
                }
            ],
            "deleteProtect":false
        }
    ],
    "marker":"eip-DCB50385",
    "isTruncated": true,
    "nextMarker": "eip-DCB50387",
    "maxKeys": 2
}
响应示例, 查询IPV6 EIP列表

Plain Text复制
HTTP/1.1 200 OK
x-bce-request-id: 029433e5-3264-4ed0-9cbf-f4b85a468f00
Date: Wed, 10 Apr 2024 01:10:53 GMT
Transfer-Encoding: chunked
Content-Type: application/json;charset=UTF-8
Server: BWS

{
    "marker": "eipv6-4NOa3gC9",
    "isTruncated": false,
    "nextMarker": null,
    "maxKeys": 1000,
    "eipList": [
        {
            "name": "eip_v6_test",
            "eip": "240c:4082:ffff:ff01:0:4:0:12a",
            "eipId": "eipv6-XXX",
            "status": "available",
            "instanceType": null,
            "instanceId": null,
            "routeType": "BGP",
            "bwBandwidthInMbps": 0,
            "domesticBwBandwidthInMbps": 0,
            "clusterId": "c-76a34e7b",
            "bandwidthInMbps": 150,
            "paymentTiming": "Postpaid",
            "billingMethod": "ByBandwidth",
            "exclusiveCluster": false,
            "createTime": "2024-04-10T09:30:25Z",
            "expireTime": null,
            "shareGroupId": "",
            "eipInstanceType": "normal",
            "tags": null,
            "region": "bd",
            "poolType": null
        }
    ]
}
附录1
更新时间：2026-02-11
Model对象定义
EipModel
参数名称
类型
描述
name	String	EIP的名字
eip	String	EIP地址，点分十进制表示
eipId	String	EIP ID
status	eipStatus	EIP状态
eipInstanceType	eipInstanceType	EIP实例类型
instanceType	instanceType	绑定实例类型，若EIP处于未绑定状态，此项值为空
instanceId	String	实例ID，若EIP处于未绑定状态，此项值为空
shareGroupId	String	共享带宽组ID，若为普通EIP，此项值为空
defaultDomesticBandwidth	int	默认跨境加速带宽，仅香港区域有该属性，单位为Mbps
bandwidthInMbps	int	公网带宽，单位为Mbps
bwShortId	String	带宽包ID
bwBandwidthInMbps	int	带宽包带宽，单位为Mbps
domesticBwShortId	String	跨境加速包ID
domesticBwBandwidthInMbps	int	跨境加速包带宽，单位为Mbps
paymentTiming	string	付款时间，预支付（Prepaid）和后支付（Postpaid）
billingMethod	string	计费方式，按流量（ByTraffic）和按带宽（ByBandwidth，只有后付费产品此参数才有值
createTime	string	创建时间
expireTime	string	过期时间，只有预付费产品此参数才有值
region	string	当前EIP所属区域
routeType	string	EIP线路类型
tags	List<TagModel>	绑定的标签集合
deleteProtect	Boolean	是否开启释放保护
nativeGroup	Boolean	标记EIP是否为原生EIP，true：原生EIP，false：非原生EIP。（只有查询共享带宽详情接口该字段才存在。）
originalBandwidth	Integer	eip原始带宽（移入group前的带宽），如果是原生EIP，（只有查询共享带宽详情接口该字段才存在。）
originProductType	String	group 内 EIP 原始计费类型，如果是原生EIP，值为空，（只有查询共享带宽详情接口该字段才存在。）
originSubProductType	String	group 内 EIP 原始计费子类型，如果是原生EIP，值为空。（只有查询共享带宽详情接口该字段才存在。）
RecycleEipModel
参数名称
类型
描述
name	String	EIP名称
eip	String	EIP地址，点分十进制表示
eipId	String	EIP ID
status	eipStatus	EIP状态
routeType	String	EIP线路类型
bandwidthInMbps	int	公网带宽，单位为Mbps
paymentTiming	String	付款时间，预支付（Prepaid）和后支付（Postpaid）
billingMethod	String	计费方式，按流量（ByTraffic）或按带宽（ByBandwidth）等
recycleTime	String	EIP进入回收站时间
scheduledDeleteTime	String	EIP计划删除时间
EipGroupModel
参数名称
类型
描述
name	String	共享带宽名称
status	eipGroupStatus	共享带宽状态
id	String	共享带宽ID
bandwidthInMbps	int	共享带宽带宽值，单位为Mbps
defaultDomesticBandwidth	int	默认跨境加速带宽，仅香港区域有该属性，单位为Mbps
bwShortId	String	带宽包ID
bwBandwidthInMbps	int	带宽包带宽，单位为Mbps
domesticBwShortId	String	跨境加速包ID
domesticBwBandwidthInMbps	int	跨境加速包带宽，单位为Mbps
paymentTiming	string	付款时间，预支付（Prepaid）和后支付（Postpaid）
billingMethod	string	计费方式，按带宽（ByBandwidth），95峰值计费（ByPeak95)，按主流量计费(ByNetrafficMax)
createTime	string	创建时间
expireTime	string	过期时间，只有预付费产品此参数才有值
region	string	共享带宽所属区域
routeType	string	共享带宽线路类型
tags	List<TagModel>	绑定的标签集合
eips	List<EipModel>	共享带宽中的IPv4 EIP信息
eipv6s	List<EipModel>	共享带宽中的IPv6 EIP信息
EipMoveOutModel
参数名称
类型
是否必需
描述
eip	String	是	待移出的EIP IP地址
bandwidthInMbps	int	否	移出后的EIP带宽值，单位为Mbps（只有移出共享带宽原生的EIP需要此参数）
billing	Billing	否	移出后的EIP计费信息，仅支持后付费（只有移出共享带宽原生的EIP需要此参数）
TbspModel
参数名称
类型
描述
name	String	DDoS增强防护包名称
id	String	DDoS增强防护包ID
defenseLineType	String	DDoS增强防护包线路类型
defenseCountQuota	Int	DDoS增强防护包容量
ipList	List<TbspIpModel>	DDoS增强防护包绑定的IP列表
ipTotalCount	Int	DDoS增强防护包绑定的IP数量
autoRenewSwitch	Int	DDoS增强防护包是否开启自动续费，1代表开启
productStatus	String	DDoS增强防护包状态
createTime	String	DDoS增强防护包创建时间
expireTime	String	DDoS增强防护包到期时间
defenseEnable	Int	DDoS增强防护包防护能力，0代表尽力防护
attackingRecordList	List<TbspAttackRecordModel>	DDoS增强防护包攻击记录列表
attackingRecordTotalCount	Int	DDoS增强防护包攻击记录总数
tags	List<TagModel>	绑定的标签集合
TbspIpCleanModel
参数名称
类型
描述
ip	String	DDoS增强防护包防护对象IP地址
eipName	String	DDoS增强防护包防护对象IP名称
eipId	String	DDoS增强防护包防护对象EIP ID
thresholdType	String	DDoS增强防护包IP清洗阈值类型，包含按带宽上限 (bandwidth)、智能阈值 (auto) 和手动设置 (manual)
ipCleanMbps	Int	清洗阈值每秒流量带宽Mbps
ipCleanPps	Int	清洗阈值每秒报文数pps
productStatus	String	DDoS增强防护包状态
turnOffBeginTime	String	关闭防护IP清洗起始时间
turnOnEndTime	String	关闭防护IP清洗终止时间
TbspIpWhitelistModel
参数名称
类型
描述
ip	String	DDoS增强防护包防护对象IP地址
whitelistId	String	DDoS增强防护包IP白名单ID
ipCidr	String	DDoS增强防护包IP白名单网段 (完整IP地址格式或IP网段格式)
TbspAreaBlockingModel
参数名称
类型
描述
ip	String	DDoS增强防护包防护对象IP地址
blockArea	String	DDoS增强防护包防护对象封禁区域，包含大陆地区 (continent) 和海外及港澳台地区 (overseas)
blockBeginTime	String	DDoS增强防护包防护对象区域封禁起始时间
blockEndTime	String	DDoS增强防护包防护对象区域封禁终止时间
blockType	String	DDoS增强防护包防护对象区域封禁类型
TbspProtocolBlockingModel
参数名称
类型
描述
ip	String	DDoS增强防护包防护对象IP地址
protocolPortList	List<TbspProtocolPortModel>	DDoS增强防护包协议封禁端口列表信息
TbspProtocolPortModel
参数名称
类型
描述
type	String	DDoS增强防护包封禁协议类型，包含icmp、tcp和udp
portBegin	Int	DDoS增强防护包协议封禁端口起始值
portEnd	Int	DDoS增强防护包协议封禁端口终止值
TbspIpModel
参数名称
类型
描述
ip	String	DDoS增强防护包绑定防护对象IP地址
status	String	DDoS增强防护包绑定防护对象运行状态
TbspAttackRecordModel
参数名称
类型
描述
ip	String	DDoS增强防护包被攻击的IP地址
startTime	String	攻击开始时间
DdosModel
参数名称
类型
描述
ip	String	公网IP
status	String	基础防护状，包含normal正常、flush清洗中、blackhole封禁中
bindInstanceType	String	公网IP绑定实例类型，若处于未绑定状态，此项值为空
bindInstanceId	String	公网IP绑定实例ID，若处于未绑定状态，此项值为空
ipCleanMbps	Long	清洗阈值每秒流量带宽Mbps
ipCleanPps	Long	清洗阈值每秒报文数pps
thresholdType	String	清洗阈值类型，包含按带宽上限 (bandwidth)、智能阈值 (auto) 和手动设置 (manual)
maximumThreshold	Long	最大防护阈值MB
DdosAttackRecordModel
参数名称
类型
描述
ip	String	公网IP
startTime	String	攻击开始UTC时间
endTime	String	攻击结束UTC时间
attackType	List	攻击类型
attackPeakMbps	Long	攻击峰值每秒流量带宽Mbps
attackPeakPps	Long	攻击峰值每秒报文数pps
attackPeakQps	Long	攻击峰值每秒服务请求数qps
attackStatus	String	攻击状态，包含underway攻击中、ended攻击结束
TagModel
参数名称
类型
描述
tagKey	String	标签的键，可包含大小写字母、数字、中文以及-_ /.特殊字符，长度1-65
tagValue	String	标签的值，可包含大小写字母、数字、中文以及-_ /.特殊字符，长度0-65
类型编码定义
instanceType
类型
描述
BCC	BCC实例类型
BBC	BBC实例类型
DCC	DCC实例类型
ENI	弹性网卡实例类型
BLB	BLB实例类型
VPN	VPN实例类型
NAT	NAT实例类型
eipInstanceType
类型
描述
normal	普通EIP类型
shared	共享带宽中的EIP
状态编码定义
eipStatus
状态
描述
creating	创建中
available	可用
binded	已绑定
binding	绑定中
unbinding	解绑中
updating	更新中
paused	已暂停
unavailable	暂不可用，修复中
eipGroupStatus
状态
描述
available	可用
paused	已暂停
expired	已过期
deleting	删除中
订单信息定义
Billing
状态
类型
描述
paymentTiming	string	付款时间，预支付（Prepaid）和后支付（Postpaid）
billingMethod	string	计费方式，按流量（ByTraffic）、按带宽（ByBandwidth）、按增强95（ByPeak95）（只有共享带宽后付费支持）、按主流量计费(ByNetrafficMax)（只有共享带宽后付费支持）
reservation	Reservation	保留信息，支付方式为后支付时不需要设置，预支付时必须设置
Reservation
状态
类型
描述
reservationLength	int	时长，[1,2,3,4,5,6,7,8,9,12,24,36]
reservationTimeUnit	string	时间单位，month，当前仅支持按月