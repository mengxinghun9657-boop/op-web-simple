#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 下载配置：在此填写你的 Cookie 与区域；已内置所有集群ID

# 将下面的字符串替换为你的完整 Cookie（含所有键值对）
COOKIES = "BAIDUID=6B221795D6B905FCB0BAAC08B0A7C9C4:FG=1; UUAP_TRACE_TOKEN=0f0f2e0352ab529493cddcfe137289d6; BDUSS=m54eGotaXMtRnJscHV3UEZTNzVHQU4zTjFHRkNQMUFLY1FjY1VJR2FQQ284dzlwRVFBQUFBJCQAAAAAAAAAAAEAAADFEctyzdvRvdG9tPLLwMTjAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAKhm6GioZuhoc; BDUSS_BFESS=m54eGotaXMtRnJscHV3UEZTNzVHQU4zTjFHRkNQMUFLY1FjY1VJR2FQQ284dzlwRVFBQUFBJCQAAAAAAAAAAAEAAADFEctyzdvRvdG9tPLLwMTjAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAKhm6GioZuhoc; Hm_lvt_d44eafc4ef208343b60ab82098de5a9c=1760061235; BIDUPSID=6B221795D6B905FCB0BAAC08B0A7C9C4; PSTM=1760326810; Hm_up_28a17f66627d87f1d046eae152a1c93d=%7B%22uid_%22%3A%7B%22value%22%3A%22f008db4751894afe9b851e32a2068335%22%2C%22scope%22%3A1%7D%7D; MAWEBCUID=web_ePxqfcdDBTiTvbGYxFQrxfvMPOlvGwbybekrMFewfYNcuZaBVd; BAIDUID_BFESS=6B221795D6B905FCB0BAAC08B0A7C9C4:FG=1; __bid_n=1989724ea9513289d336db; UUAP_P_TOKEN=PT-1197938365971841025-b95db44c58b3e81e00d2627f76e6d3b51e488c4f96dbfd56cf8e404881e35e43-uuapenc; SECURE_UUAP_P_TOKEN=PT-1197938365971841025-Lp63T79cdwIJm0kZpMWT-uuap; BAIDU_CLOUD_TRACK_PATH=https%3A%2F%2Fcloud.baidu.com%2Fdoc%2FAPI%2Findex.html; H_WISE_SIDS_BFESS=63143_65894_65361_65986_66106_66142_66189_66227_66203_66246_66307_66354_66328_66347_66291_66260_66393_66395_66443_66461_66482_66515_66529_66558_66586_66582_66592_66521; SECURE_ZT_EXTRA_INFO=gfp5pKQPWvJynPx3_Sk4cT6OgJyPRZ0--TWg7eyKnMzKESvnV1kpiFwIxOM_B9wnu8lPdqmVyBywhqrPEDkNtANSGseRW4hy1UXL3Zhw5I-IDI2x9ywOp4y362w7m5Dy; ZT_EXTRA_INFO=gfp5pKQPWvJynPx3_Sk4cT6OgJyPRZ0--TWg7eyKnMzKESvnV1kpiFwIxOM_B9wnu8lPdqmVyBywhqrPEDkNtANSGseRW4hy1UXL3Zhw5I-IDI2x9ywOp4y362w7m5Dy; Hm_lvt_1d218938b987e1cd56daa5e45102d928=1762221085,1762482470,1762930347,1764123497; Hm_lvt_20ba3a41aeedac500c94bdef787f57e6=1761706059,1763630339,1764124637; ZFY=b8lsPH5HL6fdn8hCdqFMvcsFI6uc2Vw8ofqG:As9ea3A:C; jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhZG1pbiI6ZmFsc2UsImF1ZCI6Im5vYWhFRS1jbGllbnQiLCJleHAiOjE3NjQ1MjAzNzY5NDYsImlhdCI6MTc2NDUxOTc3Njk0NiwiaXNzIjoibm9haEVFIiwicmVmcmVzaCI6MTc2NzExMTc3Njk0Niwicm9sZUlkTGlzdCI6W10sInN1YiI6InZfemhhbmd4aW5ncGVpIiwidG9rZW5Vc2VyIjpmYWxzZSwidXNlckFsaWFzIjoi5byg5pif5Z-5IiwidXNlcklkIjo0NjkxNDM0LCJ1c2VyTmFtZSI6InZfemhhbmd4aW5ncGVpIiwidXNlclR5cGUiOjB9.cHo_3bq_3vYvs_zbYH8ih5k3tbk0tBZHgsebwHpb964; Hm_lvt_28a17f66627d87f1d046eae152a1c93d=1762779838,1762825956,1764123481,1764555100; HMACCOUNT=66DA3CE632A58573; ppfuid=FOCoIC3q5fKa8fgJnwzbE0LGziLN3VHbX8wfShDP6RCsfXQp/69CStRUAcn/QmhIlFDxPrAc/s5tJmCocrihdwitHd04Lvs3Nfz26Zt2holplnIKVacidp8Sue4dMTyfg65BJnOFhn1HthtSiwtygiD7piS4vjG/W9dLb1VAdqNi1Ip/WIBaxFs0gxk7zc+0O0V6uxgO+hV7+7wZFfXG0MSpuMmh7GsZ4C7fF/kTgmt3jpj+McMorhe+Cj/9lStSBwMLYHXX6sSySAfDc47AfQqYgheSYkz7BDnJkD5v5D41v2iwj13daM+9aWJ5GJCQu/SUbF5jV5AUyz/jBiIgKVObaDCHgWJZH3ZrTGYHmi7XJB9z3y2o8Kqxep5XBCsugNOW5C73e/g54kuY4PKIS71ZI76Ek4aqBDEnUMj+O8679rCuwgzS80wwjQEaGzjcnvNXIEW2pwj4BXINSNFrPK50zl9AzLO29cv5RG/TJ9GIGhYqrYfhHGZqJNx2uWmglAIQEZY21OyYDgpfKN3zxRn6ONqHK83MkBENWBMWSAwea/+1VSNUTGfIG+NKu2s+g28sOzjnLUnUE9KukMAMTPZYfT79sbFYuntY0Ry6GX3OsRAJVdXPXKlPRQiighN2h3utZNfUsAGL2WWa3tubT9td9rGfOenGkLOGCRladXTg1IKPDQ9z3/DiqHtAIbmyu3emEg6nEYu6lQuvYr6/UJpAq7e+CnVRC2DzwICP6cu9A5mNm34ZPuoRV+zY3FkheurvlHUUQ38bi4/cGs6Q7GAQH6fhEN4ctu60khKCAre+XZJPkiRNLrjgnbFCE5chdRGSluqM4FuAgHCvdnqfGnnbe3vsHq3LuF7pombT65cVprejPaivGVaWugm+VA1kVl5OE/aBXOg67P9UlCyJKVyutwgoMp5Aa/ZkjblrEvPdXZFhAgvw25kAwV0TwSXShFiLc69i+L04YAPBbGyf0a8/4gXL7D1yhOWYXNZvRaSNIhIuBVe4+Jop0oczpupZGEQw3OLo5dsSUeQDd6vDni1evF/M7yvmL+FUAwPmWZFbvNq69O2z3wBW+ogxJUDy9IDhObhno4D7MBZG4B+pNlhGWn0jikQ5zzmAASlnix3V2XtmwNAzvtRZUfKm/j5ohXGVaLqOQwr5UIY0Yb6SLY1Idv8jX8h4522dQP4UUSOwRVQ7btSmic48edZ0zdfs3/Nuh02ISWqx07kkZMfmdnyOb+SUndpETWRO7Om0KwOcjCN9Un1A4MQ67HepT7VF; bce-org-delegate=false; bce_mfa_type=PHONE%2CTOTP; bce-login-accountid=f008db4751894afe9b851e32a2068335; bce-org-master-id=0878bc4c70a949c0a235ab33ad9a38d2; bce-login-display-name=Baidu_TAM_Service; bce-login-domain-account=zhisuan-changan; bce-org-assign-type=CREATED; bce-org-id=c357ef63d0624d5fbeb2b2d72c9973d9; bce-auth-type=BCEPASS; bce-sessionid=0002463b1e7fb6e439fb40cac4b449d3586; bce-long-term-sessionid=0000da90db7781a42d39afbf90fe865b59b; bce-sessionid=0002463b1e7fb6e439fb40cac4b449d3586; bce-ctl-client-cookies=BAIDUID; bce-ctl-client-parameters=brt; bce-ctl-client-headers=\"\"; bce-user-info=\"2025-12-01T10:11:46Z|75f5ecdef58cae43091f6056023d8755\"; bce-userbind-source=PASSPORT%3BUUAP; bce-login-type=BCEPASS; bce-session=681700d37468494182cc52e535b9f6c586bfb9b31e8942599ab80d175a84dc4c|cc2d852aef657d0c451be0ff6a2777ac; bce-ctl-sessionmfa-cookie=bce-session; bce-login-userid=681700d37468494182cc52e535b9f6c5; bce-locale=zh-cn; bce-fe-load-type=self; x-bce-login-redirect-url-console=https://console.bce.baidu.com/cce/#/cce/cluster/list; Smartterm-Id=6B221795D6B905FCB0BAAC08B0A7C9C4; BDRCVFR[S4-dAuiWMmn]=I67x6TjHwwYf0; delPer=0; jsdk-uuid=15a6ebae-cf37-4b22-b08b-ce74d06b186d; jsdk-user=vXPAViC1z1pGzwPoGjHkpg==; Locale=zh-CN; Timezone=UTC+8:00; Hm_lvt_7b94f7a780143fa5acbde2d8404b5293=1763362085,1764582735; RT=\"z=1&dm=baidu.com&si=f044607f-bd5c-494d-9e6c-637e7bed5573&ss=mio901n5&sl=1&tt=1j0&bcn=https%3A%2F%2Ffclog.baidu.com%2Flog%2Fweirwood%3Ftype%3Dperf&ld=2ay&ul=3n5o&hd=3nie\"; Hm_lpvt_7b94f7a780143fa5acbde2d8404b5293=1764742464; noah_magic_user_name=v_zhangxingpei; USER_NOAH=v_zhangxingpei; NOAH_VERSION=1; EXPIRE_NOAH=1765353320; SIG_NOAH=e81e0b19d9f067b3ee85cd59bf135db7; BA_HECTOR=a4a0ah8ka4252g040kal81a58l2kag1kj1rnf25; BDORZ=B490B5EBF6F3CD402E515D22BCDA1598; H_PS_PSSID=63143_66106_66189_66227_66246_66291_66260_66393_66515_66529_66558_66586_66582_66592_66613_66648_66664_66700_66683_66745_66776_66782_66793_66747_66803_66802; PSINO=2; H_WISE_SIDS=63143_66106_66189_66227_66246_66291_66260_66393_66515_66529_66558_66586_66582_66592_66613_66648_66664_66700_66683_66745_66776_66782_66793_66747_66803_66802; BCE_MONITOR_TRACK_SESSION_ID=176482899439260d7; __bce-console-referrer__=; Hm_lpvt_28a17f66627d87f1d046eae152a1c93d=1764830425; JSESSIONID=615FDD814F9DAA26CF4212328CC4B2F7; ab_sr=1.0.1_ODUzMzE1OGEzZGQ3ZjU4ZDgxZDQ4NjJhODRkNzk3YmM2MzI3YzI3ODQ5YjFjMDAxMjlkZmE4YmQ5MzBiODNlMjU2MzZmOTRkZTAzODA2MTZjZTI3Zjk1NGFkZjIxZWZjMjQ0ZDFiN2MxNmQzYWU4YWUzZDNkMmZlNmZiZjQ2NTJhN2Q0ZmNlNDdlY2NkOTUxMGIxNjc1OWFiMzM2ZjRiYQ=="
# 区域：按你的实际区域填写，例如 "bj", "cd", "gz" 等
REGION = "cd"

# 支持多集群：run.py 会读取 CLUSTER_IDS（列表或逗号分隔字符串）或单个 CLUSTER_ID
CLUSTER_IDS = [
    "cce-266b50jq",
    "cce-3nusu9su",
    "cce-9m1ht29q",
    "cce-elwhlymq",
    "cce-48c915gn",
    "cce-ld2ckre2",
    "cce-216ima4l",
    "cce-2ys5dxch",
    "cce-75n0j16r",
    "cce-hcbs74xg",
    "cce-xrg955qz",
    "cce-pog0r4mg",
    "cce-gzk0qlzk",
    "cce-p6w3c5z8",
    "cce-uk1zi507",
    "cce-k5sn275j",
    "cce-4nmy1x1s",
]

# 单集群可选：若只需一个集群，可填写此字段
# CLUSTER_ID = "cce-266b50jq"

# ===== 数据库配置 =====
# MySQL数据库连接信息（用于自动入库功能）
DB_CONFIG = {
    'host': 'localhost',           # 数据库主机地址
    'port': 8306,                  # 数据库端口
    'user': 'root',                # 数据库用户名
    'password': 'DF210354ws!',                # 数据库密码
    'database': 'mydb',            # 数据库名
    'bcc_table': 'bce_bcc_instances',   # BCC实例表名
    'cce_table': 'bce_cce_nodes'        # CCE节点表名
}

# ===== 容器数据库配置（同步目标） =====
# 宿主机通过 3307 端口访问容器内 MySQL，采集完成后自动同步
CONTAINER_DB_CONFIG = {
    'host': 'localhost',
    'port': 3307,                        # docker-compose 映射的端口
    'user': 'cluster_user',
    'password': 'Zhang~~1',              # 与 .env 中 MYSQL_PASSWORD 一致
    'database': 'cluster_management',
    'bcc_table': 'bce_bcc_instances',
    'cce_table': 'bce_cce_nodes'
}
