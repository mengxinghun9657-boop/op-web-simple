#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BCM 指标 / 事件报警回调接收服务
"""

from flask import Flask, request, jsonify
import hashlib
import json
import time
from datetime import datetime

app = Flask(__name__)

# 允许的时间偏移（秒）
MAX_TIME_SKEW = 600  # 10 分钟


def md5_hex(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def verify_signature(alert_id, task_ts, signature) -> bool:
    """
    官方校验规则：
    MD5(alertId + taskTimestamp) == signature
    """
    expected = md5_hex(f"{alert_id}{task_ts}")
    return expected == signature


def verify_timestamp(task_ts: int) -> bool:
    """防重放 / 过期校验"""
    now = int(time.time())
    return abs(now - task_ts) <= MAX_TIME_SKEW


@app.route("/bcm/callback", methods=["POST"])
def bcm_callback():
    raw = request.get_data(as_text=True)

    print(f"\n{'='*60}")
    print(f"[{datetime.now()}] 📥 BCM 回调")
    print(f"{'='*60}")

    try:
        data = json.loads(raw)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception:
        print("❌ 非法 JSON")
        return jsonify({"success": False, "error": "invalid json"}), 400

    # 公共字段
    signature = data.get("signature")
    task_ts = data.get("taskTimestamp")

    if not signature or not task_ts:
        return jsonify({"success": False, "error": "missing signature or taskTimestamp"}), 400

    if not verify_timestamp(int(task_ts)):
        return jsonify({"success": False, "error": "expired request"}), 403

    # 指标报警有 alertId，事件报警没有（文档就是这么不一致）
    alert_id = data.get("alertId", "")

    if alert_id:
        if not verify_signature(alert_id, task_ts, signature):
            return jsonify({"success": False, "error": "signature mismatch"}), 403
    else:
        print("⚠️ 事件报警：无 alertId，跳过签名校验")

    handle_alarm(data)
    return jsonify({"success": True})


def handle_alarm(data: dict):
    """
    统一处理报警
    """
    policy_type = data.get("policyType", "Event")
    alarm_name = data.get("alarmName")
    status = data.get("alarmStatus", "N/A")

    print("\n🚨 报警解析结果")
    print(f"类型: {policy_type}")
    print(f"策略: {alarm_name}")
    print(f"状态: {status}")

    if policy_type == "Metric":
        print(f"对象: {data.get('monitoringObject')}")
        print(f"等级: {data.get('alarmLevel')}")
        print(f"条件: {data.get('formula')}")
        print(f"当前值: {data.get('currentValue')}")
    else:
        print(f"事件内容: {data.get('alertContent')}")

    print("✅ 报警处理完成\n")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "bcm-callback",
        "time": datetime.now().isoformat()
    })


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║              BCM 报警回调服务                               ║
╚════════════════════════════════════════════════════════════╝

📍 回调地址:
  POST http://<ip>:8100/bcm/callback

📍 健康检查:
  GET  http://<ip>:8100/health
""")

    app.run(host="0.0.0.0", port=8100, debug=True)