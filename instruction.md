# 光伏组串遮挡审计

光伏电站的运维班要把逆变器导出的组串扫描和汇流箱曲线整理成当班审计单。现场反馈，遮挡发生在双面组件的背板侧时，审计单会把受影响的组件组判错；多段遮挡时，辐照度分层和最大功率点也常与复测结果对不上。

## 运行方式

程序入口是 `/app/main.py`，用法为：

```bash
python3 /app/main.py <输入文件>
```

输入是 UTF-8 编码的 JSON，通过 `kind` 区分三种计算。程序只向标准输出写一个 JSON 对象，不写其他内容。未知计算类型或参数个数不对时，退出码为 2。

三种计算共用以下电池参数口径。参考条件是 1000 W/m²、25 °C：

- `isc_stc_a`、`voc_stc_v`：单片的短路电流和开路电压。
- `alpha_isc_pct_per_c`、`beta_voc_pct_per_c`：按 %/°C 给出的温度系数。
- `ideality_factor`：单片二极管理想因子。
- `series_ohm`：单片串联电阻。
- `bifaciality_factor`：背板辐照度折算到正面的系数。

电池温度为 `temperature_c`，单位为 °C。热电压使用绝对温度，单玻组件的背板辐照度取 0。每组数据中的 `cells` 是该旁路区串联的电池片数，`bypass_forward_v` 是旁路二极管导通时的组端压降大小。

## 1. 旁路状态

`kind` 为 `bypass` 时，输入另外给出组串电流 `current_a` 和各区正、背面辐照度：

```json
{
  "kind": "bypass",
  "temperature_c": 52.0,
  "current_a": 8.2,
  "cell": {
    "isc_stc_a": 9.55,
    "voc_stc_v": 0.688,
    "alpha_isc_pct_per_c": 0.048,
    "beta_voc_pct_per_c": -0.272,
    "ideality_factor": 1.12,
    "series_ohm": 0.0028,
    "bifaciality_factor": 0.70
  },
  "bypass_forward_v": 0.66,
  "sections": [
    {
      "id": "A1",
      "cells": 20,
      "front_irradiance_w_m2": 800.0,
      "rear_irradiance_w_m2": 130.0
    }
  ]
}
```

旁路状态按当前电流与各区有效辐照度计算。区端电压低于 `-bypass_forward_v`，或当前电流达到该区的光生电流时，旁路二极管导通。输出只含一个字段：

```json
{"bypassed_section_ids": ["A2", "A3"]}
```

编号保持输入顺序。

## 2. 辐照度分层

`kind` 为 `irradiance` 时，输入给出同一组串的电流扫描。`sweep` 按电流从小到大排列，电压是整串电压：

```json
{
  "kind": "irradiance",
  "temperature_c": 46.0,
  "cell": {
    "isc_stc_a": 9.42,
    "voc_stc_v": 0.691,
    "alpha_isc_pct_per_c": 0.052,
    "beta_voc_pct_per_c": -0.265,
    "ideality_factor": 1.18,
    "series_ohm": 0.0031,
    "bifaciality_factor": 0.72
  },
  "bypass_forward_v": 0.64,
  "reference_irradiance_w_m2": 861,
  "sections": [
    {"id": "S01", "cells": 20}
  ],
  "sweep": [
    {"current_a": 0.0, "voltage_v": 251.37},
    {"current_a": 0.02, "voltage_v": 251.36}
  ]
}
```

各区的电池片数相同。扫描来自同一套单二极管与旁路模型，电压保留 5 位小数。各区有效辐照度按升序输出为整数，单位 W/m²，每区一个值：

```json
{"irradiance_levels_w_m2": [310, 325, 340, 640, 655, 670, 970, 985, 1000]}
```

## 3. 全局最大功率点

`kind` 为 `mpp` 时，输入是一个或多个并联组串的实测折线。每条 `curve` 按电压从小到大排列，相邻扫描点之间电流按直线变化：

```json
{
  "kind": "mpp",
  "strings": [
    {
      "id": "A",
      "curve": [
        {"voltage_v": 0.0, "current_a": 8.2},
        {"voltage_v": 20.0, "current_a": 7.9},
        {"voltage_v": 46.0, "current_a": 6.0}
      ]
    }
  ]
}
```

多条组串并联时必须使用同一个工作电压。组合曲线的全局最大功率点可能落在两个扫描点之间。输出为：

```json
{
  "voltage_v": 61.571,
  "current_a": 4.789,
  "power_w": 294.859,
  "string_currents_a": {"A": 4.789}
}
```

`voltage_v`、`current_a`、`power_w` 和每条组串的电流都保留 3 位小数。结果相同计算重复执行时保持一致。

## 约束

- 只使用 Python 标准库，不访问网络。
- 不依赖输入文件中的示例数值，隐藏输入会更换温度、辐照度、组串数量和折线点数。
- 输入中的数组顺序有意义；辐照度分层结果除外，该结果固定按升序输出。
