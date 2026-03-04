#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试如流回调机制

用法：
1. 在厂内服务器上运行此脚本: python3 test_ruliu_callback.py
2. 脚本会在 8100 端口启动 HTTP 服务
3. 在如流后台配置回调地址: http://10.175.96.168:8100/ruliu/callback
4. 在如流群组发送消息测试（@机器人或使用/命令）
"""

from flask import Flask, request, jsonify
import hashlib
import json
from datetime import datetime
import base64
from Crypto.Cipher import AES
import os

app = Flask(__name__)

# 如流配置
RULIU_TOKEN = os.getenv("RULIU_TOKEN", "T2yJvnNier")
RULIU_ENCODING_AES_KEY = os.getenv("RULIU_ENCODING_AES_KEY", "VrBuaSxT9P5Z6bfdHneKv0")
RULIU_GROUP_ID = 12203583


def verify_signature(signature, timestamp, rn, token):
    """验证如流签名"""
    params = sorted([token, timestamp, rn])
    sign_str = ''.join(params)
    sha1 = hashlib.sha1(sign_str.encode('utf-8')).hexdigest()
    
    print(f"🔍 签名验证: {sha1 == signature}")
    return sha1 == signature


def decrypt_message(encrypted_msg, encoding_aes_key):
    """
    解密如流消息
    
    参考如流官方文档：
    - 加密算法：AES-128
    - 加密模式：ECB（不需要 IV）
    - 填充方式：PKCS5（PKCS7兼容）
    - 编码方式：Base64URLSafe
    - AESKey = Base64_Decode(EncodingAESKey + "==")
    """
    try:
        if isinstance(encrypted_msg, bytes):
            encrypted_msg = encrypted_msg.decode('utf-8')
        
        print(f"🔐 解密调试:")
        print(f"   EncodingAESKey: {encoding_aes_key} (长度: {len(encoding_aes_key)})")
        
        # Base64URLSafe 解码
        encrypted_msg_standard = encrypted_msg.replace('-', '+').replace('_', '/')
        missing_padding = len(encrypted_msg_standard) % 4
        if missing_padding:
            encrypted_msg_standard += '=' * (4 - missing_padding)
        
        cipher_text = base64.b64decode(encrypted_msg_standard)
        print(f"   密文长度: {len(cipher_text)} 字节")
        
        # 生成 AESKey：EncodingAESKey + "=="
        aes_key = base64.b64decode(encoding_aes_key + "==")
        print(f"   AES密钥长度: {len(aes_key)} 字节")
        
        # AES-128-ECB 解密
        cipher = AES.new(aes_key, AES.MODE_ECB)
        decrypted = cipher.decrypt(cipher_text)
        
        # 去除PKCS7补位
        pad = decrypted[-1]
        if isinstance(pad, str):
            pad = ord(pad)
        decrypted = decrypted[:-pad]
        print(f"   解密后长度: {len(decrypted)} 字节")
        
        # 解码为 UTF-8
        content = decrypted.decode('utf-8')
        print(f"   ✅✅✅ 解密成功！消息长度: {len(content)} 字符\n")
        
        return content
    except Exception as e:
        print(f"❌ 解密失败: {e}\n")
        import traceback
        traceback.print_exc()
        return None


@app.route('/ruliu/callback', methods=['GET', 'POST'])
def ruliu_callback():
    """如流回调接口"""
    
    # URL 验证
    signature = request.args.get('signature', '') or request.form.get('signature', '')
    timestamp = request.args.get('timestamp', '') or request.form.get('timestamp', '')
    rn = request.args.get('rn', '') or request.form.get('rn', '')
    echostr = request.args.get('echostr', '') or request.form.get('echostr', '')
    
    if signature and timestamp and rn and echostr:
        print(f"\n{'='*60}")
        print(f"[{datetime.now()}] 📥 URL 验证请求")
        print(f"{'='*60}")
        verify_signature(signature, timestamp, rn, RULIU_TOKEN)
        print("✅ 返回 echostr\n")
        return echostr
    
    # 接收消息
    if request.method == 'POST':
        try:
            raw_data = request.get_data()
            
            print(f"\n{'='*60}")
            print(f"[{datetime.now()}] 📨 收到如流消息")
            print(f"{'='*60}")
            print(f"  Content-Length: {len(raw_data)} 字节\n")
            
            # 尝试直接解析 JSON
            try:
                data = json.loads(raw_data)
                print("📋 未加密消息:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                parse_message(data)
            except json.JSONDecodeError:
                # 解密消息
                decrypted_content = decrypt_message(raw_data, RULIU_ENCODING_AES_KEY)
                if decrypted_content:
                    data = json.loads(decrypted_content)
                    print("📋 解密后的消息:")
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                    print()
                    parse_message(data)
            
            return jsonify({"success": True})
            
        except Exception as e:
            print(f"\n❌ 处理消息失败: {e}\n")
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500


def parse_message(data):
    """解析消息内容"""
    if 'message' not in data:
        return
    
    message = data['message']
    header = message.get('header', {})
    body = message.get('body', [])
    
    print(f"👤 发送者: {header.get('fromuserid', 'N/A')}")
    print(f"📍 群组ID: {data.get('groupid', 'N/A')}")
    print(f"🕐 时间: {data.get('time', 'N/A')}\n")
    
    # 解析消息内容
    text_content = []
    for item in body:
        item_type = item.get('type', '')
        if item_type == 'TEXT':
            text_content.append(item.get('content', ''))
        elif item_type == 'command':
            print(f"🔧 命令: /{item.get('commandname', '')}")
        elif item_type == 'AT':
            print(f"👥 @: {item.get('name', '')}")
    
    if text_content:
        full_text = ''.join(text_content)
        print(f"📝 完整消息: {full_text}\n")


@app.route('/test', methods=['GET'])
def test():
    """测试接口"""
    return jsonify({
        "status": "ok",
        "message": "如流回调测试服务运行中",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "group_id": RULIU_GROUP_ID,
            "token_configured": bool(RULIU_TOKEN),
            "aes_key_configured": bool(RULIU_ENCODING_AES_KEY)
        }
    })


@app.route('/send_test_alert', methods=['POST'])
def send_test_alert():
    """发送测试告警到如流群组"""
    try:
        import requests
        
        webhook_url = "http://apiin.im.baidu.com/api/msg/groupmsgsend?access_token=df122a943f99d7fb465557ed02ae4b070"
        
        test_message = f"""🧪 如流回调测试 [{datetime.now().strftime('%H:%M:%S')}]

请回复此消息或 @机器人测试回调功能"""
        
        payload = {
            "message": {
                "header": {"toid": [RULIU_GROUP_ID]},
                "body": [{"type": "TEXT", "content": test_message}]
            }
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return jsonify({"success": True, "message": "测试消息已发送"})
        else:
            return jsonify({"success": False, "error": f"HTTP {response.status_code}"}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    print("""
╔════════════════════════════════════════════════════════════╗
║          如流回调测试服务 (厂内服务器版)                      ║
╚════════════════════════════════════════════════════════════╝

📋 配置信息:
  - 服务器: 10.175.96.168
  - 端口: 8100
  - 群组ID: 12203583
  - Token: T2yJvnNier
  - EncodingAESKey: VrBuaSxT9P5Z6bfdHneKv0
  
🔗 接口地址:
  - 测试: http://10.175.96.168:8100/test
  - 回调: http://10.175.96.168:8100/ruliu/callback
  - 发送测试消息: curl -X POST http://10.175.96.168:8100/send_test_alert

📝 使用步骤:
  1. 运行: python3 test_ruliu_callback.py
  2. 配置如流回调地址（已配置）
  3. 在群组中 @机器人 测试

""")
    
    app.run(host='0.0.0.0', port=8100, debug=True)