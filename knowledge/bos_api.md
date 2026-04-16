ListBuckets
更新时间：2022-11-01
接口描述
本接口列举了请求者拥有的所有bucket。

请求（Request）
请求语法
Plain Text复制
GET / HTTP/1.1
Host: bj.bcebos.com
Date: <Date>
Authorization: <AuthorizationString>
请求头域
无特殊参数

请求参数
无特殊参数

响应（Response）
响应头域
无特殊Header参数响应

响应元素
名称
类型
描述
owner	Object	Bucket owner（拥有者）信息
+id	String	Bucket owner的用户id
+displayName	String	Bucket owner的名称
buckets	Array	存放多个bucket信息的容器
+bucket	Object	存放一个bucket信息的容器
+name	String	Bucket名称
+location	String	Bucket所在区域
+creationDate	Date	Bucket创建时间
+enableMultiAz	Boolean	Bucket数据是否多AZ分布，非多AZ bucket不返回该属性
注意: 如果请求中没有用户验证信息（即匿名访问），返回403 Forbidden，错误信息：AccessDenied。

示例
JSON请求示例
说明：一次请求最多返回100个bucket的信息。

JSON复制
GET / HTTP/1.1
Host: bj.bcebos.com
Date: Wed, 06 Apr 2016 06:34:40 GMT
Authorization: AuthorizationString
JSON请求响应示例
JSON复制
{
    "owner":{
        "id":"10eb6f5ff6ff4605bf044313e8f3ffa5",
        "displayName":"BosUser"
    },
    "buckets":[
        {
            "name":"bucket1",
            "location":"bj",
            "creationDate":"2016-04-05T10:20:35Z",
            "enableMultiAz":true
        },
        {
            "name":"bucket2",
            "location":"bj",
            "creationDate":"2016-04-05T16:41:58Z"
        }
    ]
}
说明： JSON请求响应项的命名规则是首字母小写的驼峰格式。

