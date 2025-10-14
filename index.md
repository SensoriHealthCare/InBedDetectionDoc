# 在床检测模块 · 测试环境

> 本环境仅用于验证模块输出，后续上线方案可能替换组件。

---

## 1. 测试环境包含

- 云服务器（52.184.82.194）：
  - [设备配置页](http://52.184.82.194:8880/)，更新配置后设备会**自动更新配置**，无需手动重启设备。
  - EMQX（MQTT Broker, Port 1883)
  - ingestor：订阅并写库（测试期）
  - MongoDB & [mongo-express](http://52.184.82.194:8081/db/cfgdb/)（账号：`admin`，密码: `Sensori123#@!`）：仅作观察，不是必须
- 硬件设备
  ![image-20251014135056170](C:\Users\win10\AppData\Roaming\Typora\typora-user-images\image-20251014135056170.png)
  - 检测模块（设备号: `1742883471`）, 默认配套路由器，也可以手动配置其他路由器（SSID：`Sensoritest`，Password:`12345678`），**WiFi模式选择2.4G**。
  - 电源接口：Type-c类型，要求**输入5v**（建议独立电源供电，不要使用电脑USB口），供电正常后`电源指示灯`会常亮。**通电后设备自动运行**。
  - 复位键：**按下并松开后**系统重启。

> 当前允许匿名连接（测试方便）；生产请重配账号。

---

## 2. 启动 / 停止

连接云服务器，进入项目根目录后，执行如下命令（**当前已经启动**）

```bash
docker compose up -d --build
```

停止服务，执行如下命令
```bash
docker compose down
```
---

## 3. 模块的输出（主题与报文）

- 主题：`/sensori/{node_id}/current_sta`  （例如` /sensori/1742883471/current_sta`）
- 报文（JSON）：
  - `Device`：设备号，字符串格式；
  - `Status`：状态结果，整型。
    - `0`，无人；
    - `1`，有人，处于静止状态；
    - `2`， 有人，处于运动状态。
  - `HR`：心率，浮点型，单位为`次/分钟`
  - `BR`：呼吸频率，浮点型，单位为`次/分钟`
```json
{"Device":"1742883471","Status":0,"HR":141.000000,"BR":19.000000}
```

---

## 4. 如何获取消息（任选其一）

> 这里以`52.184.82.194`服务器，设备号`1742883471`为例
---

### A. 客户端软件（[MQTTX](https://mqttx.app/zh/downloads)）
- 连接52.184.82.194:1883（匿名）
  ![image-20251014130920340](C:\Users\win10\AppData\Roaming\Typora\typora-user-images\image-20251014130920340.png)
- 订阅 `/sensori/1742883471/current_sta`主题
  ![image-20251014131022295](C:\Users\win10\AppData\Roaming\Typora\typora-user-images\image-20251014131022295.png)

### B. 命令行（mosquitto_sub）
```bash
mosquitto_sub -h 52.184.82.194 -p 1883 -t "/sensori/1742883471/current_sta" -v
```

![image-20251014131457475](C:\Users\win10\AppData\Roaming\Typora\typora-user-images\image-20251014131457475.png)

### C. Python 订阅脚本

`mqtt_subscriber_quick.py`

``` python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mqtt_subscriber_quick.py
Minimal MQTT subscriber: connect to EMQX, subscribe topic(s), print messages, optionally save to CSV.

Usage:
  pip install paho-mqtt
  python mqtt_subscriber_quick.py --host localhost --port 1883 --topic "/sensori/+/current_sta" --csv out.csv
"""
import argparse
import csv
import json
import sys
import time
from typing import Optional

import paho.mqtt.client as mqtt


def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected rc={rc}")
    if rc != 0:
        print("[MQTT] Connection failed. Check host/port/auth.")
    topic = userdata.get("topic")
    if topic:
        client.subscribe(topic, qos=0)
        print(f"[MQTT] Subscribed: {topic}")


def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8", errors="ignore")
    print(f"[{time.strftime('%H:%M:%S')}] {msg.topic} -> {payload}")
    writer = userdata.get("writer")
    if writer:
        try:
            data = json.loads(payload)
        except Exception:
            data = {"raw": payload}
        data["__topic__"] = msg.topic
        data["__ts__"] = int(time.time() * 1000)
        writer.writerow(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--topic", default="/sensori/+/current_sta", help="Wildcard supported, e.g. /sensori/+/current_sta or /sensori/#")
    ap.add_argument("--csv", default=None, help="Optional: save to CSV file")
    args = ap.parse_args()

    userdata = {"topic": args.topic, "writer": None}
    if args.csv:
        f = open(args.csv, "a", newline="", encoding="utf-8")
        fieldnames = ["__ts__", "__topic__", "node_id", "ts", "in_bed", "confidence", "raw"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if f.tell() == 0:
            writer.writeheader()
        userdata["writer"] = writer
        print(f"[CSV] Append to {args.csv}")

    cli = mqtt.Client(client_id=f"sub-{int(time.time())}", userdata=userdata)
    cli.on_connect = on_connect
    cli.on_message = on_message

    try:
        cli.connect(args.host, args.port, keepalive=30)
    except Exception as e:
        print(f"[MQTT] Connect failed: {e}")
        sys.exit(2)

    try:
        cli.loop_forever()
    except KeyboardInterrupt:
        print("\n[MQTT] Bye!")


if __name__ == "__main__":
    main()

```



```bash
python -m pip install -U paho-mqtt
python mqtt_subscriber_quick.py --host 52.184.82.194 --port 1883 --topic "/sensori/1742883471/current_sta"
```

![image-20251014132220667](C:\Users\win10\AppData\Roaming\Typora\typora-user-images\image-20251014132220667.png)

### D. 直接登录[mongo-express](http://52.184.82.194:8081/db/cfgdb/)查看

![image-20251014131744186](C:\Users\win10\AppData\Roaming\Typora\typora-user-images\image-20251014131744186.png)

---

## 5. 常见问题
- 设备无响应: 未连接上WiFi，请重启设备（插拔电源或按复位按键）
- 连接失败：确认端口未被占用或已启动。
- 订阅不到：检查通配符与主题拼写；确认模块已在发布。
- 历史数据：若启用 ingestor+Mongo，可从 DB 查；否则请在线订阅获取。

---

## 6. 安全提示（仅测试）
- 目前为测试环境，启用匿名与默认口令；上线前请关闭匿名、启用账号，并更换密码。
