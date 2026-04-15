# Changelog

All notable changes to nastool will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [6.0.0-hwjet] - 2026-04-15

### Added 鈥?hw-jet v6.0 鏄囪吘 + Jetson 鍙屽钩鍙拌瘖鏂?馃殌

**浜у搧瀹氫綅**锛氬崕涓烘槆鑵?+ NVIDIA Jetson 鍙屽钩鍙?AI 杈圭紭璁惧璇婃柇涓撲笟鐗?
**鏀寔璁惧**锛?- 鏄囪吘 4 绫?10 娆撅細Atlas 200绯?300绯?500绯?A2 Lite绯?- Jetson 6 绫?10 娆撅細Orin AGX/NX/Nano, AGX Xavier, Xavier NX, Nano/TX2

**鏍稿績妯″潡**锛?
| 妯″潡 | 鏂囦欢 | 璇存槑 |
|------|------|------|
| CLI鍏ュ彛 | `adapters/hw_jet.py` | 缁熶竴鍛戒护琛屽叆鍙ｏ紙--device/--mock/--json/--output锛墊
| 鍩虹鎶借薄 | `adapters/base.py` | BaseAdapter + ErrorCode + AdapterError |
| 鎺ㄧ悊鍩哄噯 | `adapters/benchmark.py` | ONNX/TensorRT/ACL/MindSpore/Heuristic |
| 鎶ュ憡鐢熸垚 | `adapters/reporter.py` | HTML/JSON/Markdown 澶氭牸寮忔姤鍛?|
| 鏃ュ織绯荤粺 | `adapters/logger.py` | 褰╄壊鎺у埗鍙?+ JSON 鏂囦欢鏃ュ織 |
| 鏄囪吘閫傞厤 | `adapters/ascend/` | AscendAdapter + NPU璇︽儏瑙ｆ瀽 |
| Jetson閫傞厤 | `adapters/jetson/` | JetsonAdapter + 鍔熻€?椋庢墖/JetPack鏄犲皠 |

**Jetson 涓撻」鍔熻兘**锛?- `jetson/power.py`锛歯vpmodel 鍔熻€楁ā寮忕鐞?- `jetson/fan.py`锛氶鎵?PWM 鐘舵€佺洃鎺?- `jetson/jetpack.py`锛欽etPack鈫扖UDA/TensorRT 鐗堟湰鏄犲皠琛?
**鏄囪吘涓撻」鍔熻兘**锛?- `ascend/npu.py`锛歯pu-smi 璇︾粏瑙ｆ瀽锛堝埄鐢ㄧ巼/娓╁害/鍔熺巼/鍐呭瓨/鍋ュ悍鐘舵€侊級
- 鑺墖鍨嬪彿鏄犲皠锛圓scend 310/910/910B 绛夛級

**娴嬭瘯瑕嗙洊**锛?- 鍗曞厓娴嬭瘯锛?1 鐢ㄤ緥
- 闆嗘垚娴嬭瘯锛?7 鐢ㄤ緥
- 鎬昏锛?*38 passed**

### Usage

```bash
# 鑷姩妫€娴嬭澶?python -m adapters.hw_jet

# 寮哄埗鎸囧畾骞冲彴
python -m adapters.hw_jet --device ascend
python -m adapters.hw_jet --device jetson

# Mock 娴嬭瘯
python -m adapters.hw_jet --mock atlas_200i_a2
python -m adapters.hw_jet --mock nvidia_jetson_agx_orin_64gb --json

# 瀹屾暣璇婃柇 + 鎶ュ憡
python -m adapters.hw_jet --full --benchmark --output report.html
```

### Stats

- 鏂板鏂囦欢锛?2 涓?- 鏂板浠ｇ爜锛殈5000 琛?- 鏀寔璁惧锛?0 娆?- 寮€鍙戝懆鏈燂細15 澶?
---

## [5.0.4] - 2026-04-15

### Added 鈥?鏅鸿兘淇鎺ㄨ崘绯荤粺 馃敡

**鏂板 `fixes/fix_recommendations.py`**锛?,237 B锛夛細
- 妫€娴嬧啋淇鏄犲皠琛細涓€涓?check 鍙搴斿涓?fix 寤鸿
- 鍙帹鑽愪笉鑷姩鎵ц锛屼繚鐣?fix 鑷韩鐨?`is_applicable()` 浜屾楠岃瘉
- 鎸夌被鍒垎缁勬樉绀猴細瀹夊叏绫?/ 瀛樺偍绫?/ Docker 绫?/ 闇€浜哄伐澶勭悊

**鏂板 `fixes/interactive_fix.py`**锛?,962 B锛夛細
- 浜や簰寮忎慨澶?UI锛氱紪鍙烽€夋嫨銆佹壒閲忔墽琛屻€佺姸鎬佽拷韪?- 鏅鸿兘鎽樿锛氭樉绀恒€孨椤瑰彲淇 / M椤归渶浜哄伐銆?- 鏀寔杈撳叆缂栧彿鍒楄〃锛堝 `[1,2,5]`锛?
**淇敼 `arm_diagnose.py`**锛?- `--fix` 妯″紡浠庣洿鎺ユ墽琛屾敼涓哄厛鎺ㄨ崘銆佸悗閫夋嫨
- `--fix --auto` 淇濇寔鍘熸湁鑷姩鎵ц琛屼负

### Fixed

| Bug | 鍘熷洜 | 淇 |
|-----|------|------|
| `--fix` 浠ｇ爜鍧楁浛鎹㈠け璐?| CRLF 缂栫爜 + PowerShell 瑙ｆ瀽 | Python 鑴氭湰鐩存帴鏇挎崲 |
| `CheckSeverity` 姣旇緝閫昏緫閿欒 | `.value` 杩斿洖瀛楃涓查潪鏁存暟 | 鐢?enum 鏈韩姣旇緝 |
| `BMAG` 棰滆壊鍙橀噺鏈畾涔?| 鎷煎啓閿欒 | 淇甯搁噺鍚?|
| `os.geteuid()` Windows 宕╂簝 | Unix 鐗规湁 API | 娣诲姞 `os.name == 'nt'` 鍒嗘敮 |

### Stats

- Python 鏂囦欢锛?23
- 鎬昏鏁帮細40,087
- 妫€娴嬮」锛?6锛?4 USB锛?- 淇妯″潡锛?8

---

## [5.0.3] - 2026-04-15

### Added 鈥?USB 杩炴帴妫€娴嬫ā鍧?馃攲

鏂板 `checks/usb/` 鐩綍锛? 椤规娴嬶級锛?
| check_id | 妫€娴嬪唴瀹?| Severity | 璇存槑 |
|----------|---------|----------|------|
| `usb_devices` | USB 璁惧鍒楄〃 | INFO | `lsusb` 瑙ｆ瀽锛屾渶澶?4 鏉℃埅鏂?|
| `usb_storage_mount` | USB 瀛樺偍鎸傝浇 | WARNING | `/dev/sd*` 鍒嗗尯 + mount 鐘舵€?|
| `usb_permissions` | USB 璁惧鏉冮檺 | WARNING | `dmesg` + `udevadm` 鏉冮檺閿欒 |
| `usb_power` | USB 绔彛渚涚數 | WARNING | 浣庡帇鍛婅 + 渚涚數淇℃伅 |

**鏋舵瀯鏀瑰姩**锛?- `checks/base.py` 鈥?鏂板 `CheckCategory.USB` 鏋氫妇
- `checks/usb/__init__.py` 鈥?4 涓娴嬬被娉ㄥ唽
- `checks/__init__.py` 鈥?娉ㄥ唽 USB 妫€娴?- `utils/terminology.py` 鈥?USB 4 椤规湳璇炕璇?- `utils/health_scorer.py` 鈥?USB 4 椤规潈閲?- `data/mock_results.py` 鈥?USB 4 椤?mock 鏁版嵁

**楠岃瘉**锛?6椤规€诲垎 97/100锛孶SB 杩炴帴 100 鍒?鉁?
---

## [5.0.2] - 2026-04-14

### Added 鈥?鍋ュ悍璇勫垎绯荤粺 v2 馃専

**璇勫垎寮曟搸 `utils/health_scorer.py`**锛?0,222 B锛夛細
- 涓夊眰鏉冮噸浣撶郴锛歝ritical=3x / important=2x / standard=1x / info=0x
- 7绫荤嫭绔嬭瘎鍒嗭細瀛樺偍/绯荤粺/缃戠粶/AI/瀹夊叏/NAS/USB
- 鍔犳潈缁煎悎鍒?+ 6绾ц瘎鍒嗗埗锛圓+/A/A-/B+/B/C/D/F锛?- 鍒嗘暟鍙樺寲杩借釜锛堚啈鈫擄級

**鍋ュ悍浠〃鐩?`reporters/health_dashboard.py`**锛?,831 B锛夛細
- 褰╄壊澶у瓧浣撹瘎鍒嗘樉绀?- ASCII 杩涘害鏉★紙64瀛楃瀹藉害锛?- 7绫诲垎绫昏瘎鍒嗘潯锛堢嫭绔嬮鑹诧級
- 绱ф€ヤ簨椤瑰垪琛?+ 淇寤鸿
- `compact=True` 涓€琛岀揣鍑戣緭鍑烘ā寮?
**鏈缈昏瘧灞?`utils/terminology.py`**锛?6,607 B锛夛細
- 90涓娴嬮」宸ョ▼甯堚啋閫氫織璇█缈昏瘧
- 7澶х被鍒腑鏂囨爣绛?- 涓ラ噸绋嬪害 / 椋庨櫓绛夌骇缈昏瘧
- `translate_result()` / `generate_suggestions()`

**鏅€氫汉鍙嬪ソ鎶ュ憡鍣?`reporters/friendly_reporter.py`**锛?3,187 B锛夛細
- 褰╄壊鍋ュ悍浠〃鐩?+ 6绫诲垎绫昏瘎鍒嗗窘绔?- 绱ф€ュ缓璁尯锛堥檺鏄?5 鏉★級
- 姣忔潯寤鸿鍚細闂鎻忚堪 + 閲嶈鎬?+ 鎿嶄綔姝ラ + 椋庨櫓 + 棰勬湡鏁堟灉

### Added 鈥?妫€娴嬮」鎵╁锛?0鈫?6椤癸級馃敟

**瀛樺偍 脳5**锛歋MART 纭洏鍋ュ悍銆丠DD/SSD 娓╁害銆丷AID 鐘舵€併€丏ocker 闀滃儚銆佸瓨鍌ㄨ秼鍔?**绯荤粺 脳3**锛欳PU 娓╁害銆佺郴缁熻繍琛屾椂闂淬€丏ocker 瀹瑰櫒
**缃戠粶 脳2**锛氱綉鍗￠€熺巼銆丏NS 瑕嗙洊
**瀹夊叏 脳2**锛歋SH 鐧诲綍澶辫触妫€娴嬨€丼SL 璇佷功鏈夋晥鏈?**NAS 脳6**锛欴SM/QTS 鐗堟湰銆佺敤鎴风粺璁°€佸叡浜潈闄愩€乁PS銆佹棩蹇楃鐩樸€佸畾鏃朵换鍔″啿绐?
---

## [5.0.1] - 2026-04-14

### Added 鈥?淇鑳藉姏鎵╁锛?鈫?5绉嶏級馃敡

**瀹夊叏绫?脳4**锛歞isable_root_login銆乪nable_fail2ban銆乪nforce_password_policy銆乺enew_ssl_cert
**瀛樺偍绫?脳4**锛歝leanup_logs銆乧leanup_docker_images銆乧leanup_tmp_space銆乧onfig_raid_recovery
**绯荤粺绫?脳1**锛歴etup_logrotate
**NAS 绫?脳1**锛歝onfig_ups_shutdown

### Added 鈥?璁惧瑕嗙洊鎵╁锛?8鈫?1娆撅級馃帀

鏂板 13 娆捐澶囬厤缃細QNAP 5娆俱€丄sustor 3娆俱€乀erraMaster 2娆俱€丷aspberry Pi 4銆丱rangePi 5 Plus銆丷ock ITX

---

## [5.0.0] - 2026-04-14

### Changed 鈥?鏋舵瀯鍗囩骇

浠?v3.0.7 鐩存帴璺冨崌鑷?v5.0.0锛屽紩鍏?`checks/` 妯″潡鍖栨娴嬫灦鏋勶紝鍙栦唬鏃?`core/_health.py` 鍗曚綋妯″紡銆?
**妫€娴嬮」浠?28 鎵╁睍鍒?80+**锛屾柊澧?NAS銆佸瓨鍌ㄣ€佸畨鍏ㄤ笁澶х被妫€娴嬨€?
---

### Added 鈥?P1-A 鍋ュ悍璇勫垎绯荤粺锛?-100 鍒嗙骇鏄剧ず锛夝煍?
**2026-04-14**: v4.0.2 P1-A 瀹屾垚

**鏂板璇勫垎寮曟搸** `utils/health_scorer.py`锛?0222瀛楄妭锛夛細
- 涓夊眰鏉冮噸浣撶郴锛歝ritical=3x / important=2x / standard=1x / info=0x
- 鍒嗙被鐙珛璇勫垎锛氬瓨鍌?绯荤粺/缃戠粶/AI/瀹夊叏/NAS 鍚勬湁鐙珛鍒嗘暟
- 鍔犳潈缁煎悎鍒嗭細`weighted_sum / total_weight`
- 6绾ц瘎鍒嗗埗锛欰+/A/A-/B+/B/C/D/F
- 鐩告瘮涓婃鍒嗘暟鍙樺寲杩借釜锛堚啈鈫擄級
- 绱ф€ヤ簨椤规敹闆嗭紙critical_items / warnings_items锛?- 鏀寔 `calculate_health_score(results, previous_score)` 涓€琛岃皟鐢?
**鏂板鍋ュ悍浠〃鐩?* `reporters/health_dashboard.py`锛?831瀛楄妭锛夛細
- 褰╄壊澶у瓧浣撹瘎鍒嗘樉绀猴紙馃専馃専/鉁?鈿狅笍/馃敶 鍥涜壊锛?- ASCII 杩涘害鏉★紙64瀛楃瀹藉害锛?- 6 绫诲垎绫昏瘎鍒嗘潯锛堟瘡绫荤嫭绔嬮鑹诧級
- 绱ф€ヤ簨椤瑰垪琛紙甯︿慨澶嶅缓璁級
- 淇寤鸿锛堟牴鎹?critical/warnings 鏁伴噺锛?- `compact=True` 涓€琛岀揣鍑戣緭鍑烘ā寮?
**闆嗘垚鏇存柊**锛?- `checks/base.py` 鈥?`CheckSummary.get_health_report()` 鏂版柟娉曪紙鍚戝悗鍏煎鏃?`calculate_score`锛?- `arm_diagnose.py` 鈥?涓绘祦绋嬮泦鎴?`HealthDashboard`锛屾浛鎹㈡棫 `SummaryReporter.calculate_score` 閾捐矾
- `reporters/__init__.py` 鈥?鏂板 `HealthDashboard` 瀵煎嚭
- `utils/__init__.py` 鈥?鏂板 `HealthScorer/HealthReport/calculate_health_score/score_color/WEIGHTS` 瀵煎嚭

**璇勫垎鏁堟灉绀轰緥**锛?```
    馃専 Excellent
    92 /100   Grade: A
    [鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻戔枒鈻戔枒鈻戔枒鈻戔枒鈻戔枒鈻戔枒鈻戔枒鈻戔枒鈻戔枒鈻戔枒鈻戔枒鈻戔枒鈻慮
      鉁?28 閫氳繃  鈿狅笍 4 璀﹀憡  鉂?1 涓ラ噸  鈩癸笍 0 淇℃伅

  馃搳鍒嗙被璇勫垎
    瀛樺偍     [鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻戔枒鈻戔枒鈻慮  85/100
    绯荤粺     [鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅]  100/100
    缃戠粶     [鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枒鈻戔枒]   90/100
    瀹夊叏     [鈻堚枅鈻堚枅鈻堚枅鈻戔枒鈻戔枒鈻戔枒鈻戔枒鈻戔枒鈻戔枒]   50/100  鉂?
    AI       [鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枒鈻戔枒]   90/100
    NAS      [鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻戔枒]   95/100
```

---

### Added 鈥?P1-B 淇鑳藉姏澶ф墿瀹癸紙5 鈫?15 绉嶏級馃敡

**2026-04-14**: v4.0.2 P1-B 瀹屾垚锛?0 涓柊 fix

**瀹夊叏绫伙紙4涓級**锛?- `disable_root_login` 鈥?绂佺敤 SSH root 鐧诲綍锛圥ermitRootLogin no锛?- `enable_fail2ban` 鈥?瀹夎骞堕厤缃?fail2ban SSH 闃叉姢锛堣嚜鍔ㄥ皝绂佹毚鍔涚牬瑙ｏ級
- `enforce_password_policy` 鈥?閿佸畾寮卞瘑鐮佺敤鎴疯处鍙?- `renew_ssl_cert` 鈥?缁湡鍗冲皢杩囨湡 SSL 璇佷功锛堢敓鎴?365 澶╀复鏃惰瘉涔︼級

**瀛樺偍绫伙紙4涓級**锛?- `cleanup_logs` 鈥?娓呯悊 30 澶╀互涓?.gz 鏃ュ織鏂囦欢
- `cleanup_docker_images` 鈥?娓呯悊 Docker dangling 闀滃儚锛坄docker image prune`锛?- `cleanup_tmp_space` 鈥?娓呯悊 /tmp 鍜?/var/tmp 瓒呰繃 7 澶╃殑涓存椂鏂囦欢
- `config_raid_recovery` 鈥?RAID 闄嶇骇鎭㈠寮曞锛堟彁渚涘畨鍏ㄦ搷浣滄寚寮曪紝闈炶嚜鍔ㄦ墽琛岋級

**绯荤粺绫伙紙1涓級**锛?- `setup_logrotate` 鈥?閰嶇疆 logrotate锛岄槻姝㈡棩蹇楁棤闄愬闀?
**NAS 绫伙紙1涓級**锛?- `config_ups_shutdown` 鈥?瀹夎骞堕厤缃?NUT锛屽疄鐜?UPS 鏂數鑷姩鍏虫満

**淇鑳藉姏瀵规瘮**锛?
| 鐗堟湰 | Fix 鏁伴噺 | 瑕嗙洊绫诲埆 |
|------|----------|---------|
| v4.0.1 | 5 绉?| 绯荤粺/缃戠粶/瀛樺偍/AI |
| v4.0.2 | 15 绉?| 绯荤粺/缃戠粶/瀛樺偍/AI/瀹夊叏/NAS |

**鏋舵瀯鏀瑰姩**锛?- `fixes/security/__init__.py` 鈥?鏂板缓锛屽鍑?4 涓畨鍏?fix
- `fixes/nas/__init__.py` 鈥?鏂板缓锛屽鍑?1 涓?NAS fix
- `fixes/__init__.py` 鈥?閲嶅啓锛?5 涓?fix 鍏ㄩ儴娉ㄥ唽

---

### Added 鈥?P2 鏅€氫汉瑙嗚浼樺寲 馃尡

**2026-04-14**: v4.0.2 P2 瀹屾垚

**鏈缈昏瘧灞?* `utils/terminology.py`锛?6607瀛楄妭锛夛細
- 33 涓娴嬮」鏈缈昏瘧锛堝伐绋嬪笀鏈 鈫?閫氫織璇█锛?- 6 澶х被鍒腑鏂囨爣绛撅紙馃捑鏁版嵁瀛樺偍 / 馃枼锔忕郴缁熻繍琛?/ 馃寪缃戠粶杩炴帴 / 馃AI鍔犻€?/ 馃敀瀹夊叏闃叉姢 / 馃梽锔廚AS绯荤粺锛?- 涓ラ噸绋嬪害缈昏瘧锛圕RITICAL 鈫?馃敶涓ラ噸锛屽繀椤荤珛鍗冲鐞嗭級
- 椋庨櫓绛夌骇缈昏瘧锛坙ow/medium/high 鈫?鈿綆椋庨櫓/馃煛涓闄?馃敶楂橀闄╋級
- `translate_result()` 鈥?鍗曚釜妫€娴嬬粨鏋滅殑閫氫織缈昏瘧
- `translate_category()` 鈥?绫诲埆閫氫織鍚嶇О
- `generate_suggestions()` 鈥?鑷姩鐢熸垚"鍘熷洜+鎿嶄綔+鏁堟灉"寤鸿鍒楄〃

**鏅€氫汉鍙嬪ソ鎶ュ憡鍣?* `reporters/friendly_reporter.py`锛?3187瀛楄妭锛夛細
- 褰╄壊鍋ュ悍浠〃鐩橈紙璇勫垎+绛夌骇+Grade 瀛楁瘝锛?- 6 绫诲垎绫昏瘎鍒嗗窘绔狅紙鐙珛棰滆壊+杩涘害鏉★級
- 绱ф€ュ缓璁尯锛堝彧鐪?CRITICAL/WARNING锛岄檺鏄?5 鏉★級
- 姣忔潯寤鸿鍚細闂鎻忚堪 + 閲嶈鎬?+ 鎿嶄綔姝ラ + 鎿嶄綔椋庨櫓 + 棰勬湡鏁堟灉
- 妫€鏌ラ」鍒楄〃锛堥棶棰橀」鈫掓甯搁」锛岄鑹插尯鍒嗭級
- `build_compact_text()` 鈥?缁堢绱у噾鏂囧瓧鎽樿
- 鎵撳嵃鍙嬪ソ锛園media print 浼樺寲锛?
**瀵煎嚭澧炲己**锛?- `utils/__init__.py` 鈥?鏂板 terminology 妯″潡瀵煎嚭
- `reporters/__init__.py` 鈥?鏂板 FriendlyReporter 瀵煎嚭

---

### Added 鈥?璁惧瑕嗙洊鎵╁ 馃帀

**2026-04-14**: v4.0.2 璁惧瑕嗙洊浠?38 娆惧鑷?**51 娆?*

**鏂板閰嶇疆鏂囦欢** `profiles/new_devices.yaml`锛?5846 瀛楄妭锛?3 娆炬柊璁惧锛夛細

| 鍝佺墝 | 鍨嬪彿 | 鏋舵瀯 | AI 绫诲瀷 |
|------|------|------|---------|
| 濞佽仈閫?QNAP锛?娆撅級 | TS-264 / TS-464 / TS-673A / TS-873A / TS-h2490FU | x86_64 | GPU/CPU |
| 鍗庣 Asustor锛?娆撅級 | Drivestor Pro AS7110T / Lockstor AS6508T / Nimbia AS3302T | x86_64/arm64 | CPU |
| 閾佸▉椹?TerraMaster锛?娆撅級 | F4-423 / F5-422 | x86_64 | CPU |
| 鏍戣帗娲撅紙1娆撅級 | Raspberry Pi 4 Model B | arm64 | CPU |
| OrangePi锛?娆撅級 | OrangePi 5 Plus | arm64 | NPU (RKNN) |
| Radxa锛?娆撅級 | ROCK 5 ITX | arm64 | NPU (RKNN) |

**loader.py 閲嶆瀯**锛?- 淇 detect_device 鎹熷潖鍧?- 鏂板 `_detect_qnap()` 鈥?/etc/nas.conf + hostname 妫€娴嬪▉鑱旈€?- 鏂板 `_detect_terramaster()` 鈥?hostname 妫€娴嬮搧濞侀┈
- 鏇存柊 `_detect_rk3588()` 鈥?鏀寔 OrangePi 5 Plus / Radxa ROCK 5 ITX
- 缁熶竴 meta_keys 杩囨护闆嗭紙鏂板 `total_new_devices`锛?
**璁惧鎬昏鐩?*锛?1 娆撅紙缇ゆ櫀 13 + Jetson 9 + SOPHON 12 + RK3588 6 + QNAP 5 + 鍗庣 3 + 閾佸▉椹?2 + 鍏朵粬 1锛?
---

