API权限
* 任何用户都可以调用API，但是调用API所使用的用户名需要有对应空间的权限，否则会报没有空间权限
* 权限需跟空间权限一致，只读权限不可以调用API、新建权限可以新建卡片、编辑权限可以新建以及修改卡片、管理员权限可以调用新建修改查询等API
* 密码是邮箱密码或者是虚拟密码，这边建议是虚拟密码，获取虚拟密码：虚拟密码
* 虚拟账户或者是虚拟邮箱，也需要添加到空间相应的权限组中，虚拟账户密码可以联系iCafe服务号获取。
* 申请虚拟账户：申请专用(虚拟)账户
账号：v_zhangxingpei
密码：VVV7flJkXw%2BiGoWiwgjWDWSjojCBg6wYsC%2F

创建单张卡片的模板：
{
   "username":"",
   "password" : "",
   "issues" : [{
      "title":"测试一下",
      "detail":"<a href='https://www.baidu.com'>链接</a>", 
      "type" : "Bug",
      "fields" : {
         "负责人" : "", 
         "所属计划":"测试/测试1/测试3",
         "流程状态" : "新建", 
         "优先级" : "P1-High"
      },
      "creator" : "v_liuxiang",
      "comment" : "评论" 
   }]
}
*********************

创建卡片的示例代码：
#!/usr/bin/python2.7
# -*- coding: utf-8 -*- 
 
#################
# create icafe card by api
#################
 
import urllib
import urllib2
import json
import time
 
icafe_api="http://icafeapi.baidu-int.com/api/v2"
icafe_debug="http://icafebeta.baidu.com/api/v2"
api_entry=icafe_debug
 
space_id="zptest"
 
def create_issue(title,detail,type="Bug",emailto=["liuwei18@baidu.com",],owner="liuwei18"):
	print " ------------- 1. cretae issue-----------------"
	url = '%s/space/%s/issue/new' % (api_entry,space_id)
	print url
	i_headers = {"Content-Type": "application/json"}
	values = {
	"username":"liuwei18",
	"password" : "",
	"issues" : [
		{
		"title":title,
		"detail":detail,
		"type" : type,
		"fields" : { "负责人" : owner },
		"notifyEmails" : emailto, 
		"creator" : "liuwei18"
		}
		]
	}
	data = json.dumps(values)
	print data
	req = urllib2.Request(url, data, headers=i_headers)
	response = urllib2.urlopen(req)
	the_page = response.read()
	print the_page
	# read response
	response_json = json.loads(the_page)
	if response_json.get("status","") == 200:
		print "Success!!!"
	else:
		print "Fail, details: %s " % response_json.get("message","") 
		exit(1) 
 
 
if __name__=="__main__":
	title="api test only"
	detail="api test only"
	create_issue(title,detail)



**********
获取空间类型下字段
API基本信息
API名称：获取空间类型下字段
API描述：根据空间标识和类型名称获取类型下的字段 （QPS限制：针对单个IP的所有API调用，晚9点~早9点：5秒25次，早9点~晚9点：5秒10次） 使用api的用户需具备空间(只读)及以上权限
调用地址： http://icafeapi.baidu-int.com/api/v2/spaces/{空间标识}/fieldsForCreate
请求方式：GET
返回类型：JSON
注意!/rpc类型接口Content-type为application/json,/rest与/asyn类型接口Content-type为application/x-www-form-urlencoded
请求参数说明：
参数名称
必选
参数类型
参数示例
说明
空间标识
是
string
string
空间标识，可在“空间设置”的“空间信息”中查看。空间标识名大小写敏感。也可在URL中查看，例如：https://console.cloud.baidu-int.com/devops/icafe/space/iCafeTestDemo/queries/query/all，其中/space/后面的iCafeTestDemo就是空间标识。
issueTypeName
是
string
string
类型名称
username
是
string
string
用户名
password
是
string
string
密码，可使用虚拟密码，员工账号登录iCafe后，访问以下链接 https://console.cloud.baidu-int.com/api/icafe/users/virtual 即可获取虚拟密码。非员工，专用账号，专用邮箱虚拟密码联系iCafe服务号获取。
返回字段说明：
返回值字段
字段类型
是否为数组
字段说明
status
int
否
状态码（200-成功）
message
string
否
提示信息
id
long
否
字段id
name
string
否
字段标识
display
string
否
字段展示名称
required
boolean
否
是否必填
type
string
否
字段类型
valueItems
string
是
字段选项值
返回结果：
{
	"result": [{
		"id": null,
		"name": "responsiblePeopleId",
		"display": "负责人",
		"required": false,
		"type": "user_picker",
		"defaultValue": null,
		"valueItems": []
	}, {
		"id": null,
		"name": "detail",
		"display": "内容",
		"required": false,
		"type": "text_area_field",
		"defaultValue": "",
		"valueItems": []
	}, {
		"id": 210,
		"name": null,
		"display": "所属项目",
		"required": false,
		"type": "project_management",
		"defaultValue": null,
		"valueItems": []
	}, {
		"id": 45788,
		"name": null,
		"display": "所属计划",
		"required": false,
		"type": "plan_box",
		"defaultValue": null,
		"valueItems": ["L1/L2-1/L3", "L1", "L1/L2-1", "L1/L2-2"]
	}, {
		"id": 22797,
		"name": null,
		"display": "优先级",
		"required": false,
		"type": "select_list",
		"defaultValue": null,
		"valueItems": ["P0-Highest", "P1-High", "P2-Middle", "P3-Lowest"]
	}, {
		"id": 58971,
		"name": null,
		"display": "Tag",
		"required": false,
		"type": "free_text_field",
		"defaultValue": null,
		"valueItems": []
	}, {
		"id": 199,
		"name": null,
		"display": "OKR",
		"required": false,
		"type": "okr",
		"defaultValue": null,
		"valueItems": []
	}, {
		"id": 205,
		"name": "detail",
		"display": "内容",
		"required": false,
		"type": "rich_text",
		"defaultValue": null,
		"valueItems": []
	}, {
		"id": 3700176,
		"name": null,
		"display": "单选字段",
		"required": false,
		"type": "radio_field",
		"defaultValue": null,
		"valueItems": ["选项1", "选项2", "选项3"]
	}, {
		"id": 3700177,
		"name": null,
		"display": "多选字段",
		"required": false,
		"type": "check_box_field",
		"defaultValue": null,
		"valueItems": ["选项1", "选项2", "选项3"]
	}, {
		"id": 3700178,
		"name": null,
		"display": "树字段",
		"required": false,
		"type": "tree_field",
		"defaultValue": null,
		"valueItems": ["L1", "L1/L2", "L1/L2/L3"]
	}, {
		"id": null,
		"name": "parentId",
		"display": "父卡片编号",
		"required": false,
		"type": "parent_field",
		"defaultValue": null,
		"valueItems": []
	}, {
		"id": null,
		"name": "comment",
		"display": "评论",
		"required": false,
		"type": "comment_field",
		"defaultValue": null,
		"valueItems": []
	}],
	"status": 200,
	"message": "OK."
}
错误代码说明：
错误代码
错误信息
说明
status:100
Username or password is incorrect.
用户名或密码不正确
status:101
Permission denied.
拒绝许可
status:304
The space required does not exist.
请求的空间不存在
status:601
incorrect parameters
不正确的参数
status:902


*********
获取单张卡片的示例代码：
import optparse
import socket
import urllib
import urllib2
 
class HttpService:
    def post(self,url,params,timeout=50):
        return self.__service(url, params,timeout=timeout)
    def get(self,url,timeout=50):
        return self.__service(url,timeout=timeout)
    #timeout 50s
    def __service(self,url,params=None,timeout=50):
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout( timeout )
        try:
            #POST
            if params:
                request = urllib2.Request( url, urllib.urlencode(params) )
            #GET
            else:
                request = urllib2.Request( url )
            request.add_header( 'Accept-Language', 'zh-cn' )
            response = urllib2.urlopen( request )
            content = response.read()
            if response.code==200:
                return content,True
            return content,False
        except Exception,ex:
            return str(ex),False
        finally:
            if 'response' in dir():
                response.close()
            socket.setdefaulttimeout( old_timeout )
if __name__ == '__main__':
    get_data = ''
    get_data += '&u=songkexin01'
    get_data += '&pw=songkexin01'
    get_data += '&showAssociations=false'
 
    print get_data
    http_service = HttpService()
    try:
        content,status = http_service.get("http://icafebeta.baidu.com/api/spaces/mario/cards/34?"+get_data)
        print content
    except:
        print 'time out'
    pass
    