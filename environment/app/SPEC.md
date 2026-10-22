# 组串审计交接单

入口：

```bash
python3 /app/main.py <输入文件>
```

输入是 UTF-8 编码的 JSON，`kind` 取 `bypass`、`irradiance` 或 `mpp`。标准输出只能有一段 JSON，调试信息写 stderr。参数个数不对或 `kind` 不认识时，退出码为 2。

## 电池参数

`isc_stc_a`、`voc_stc_v` 是单片短路电流和开路电压，标定条件为 1000 W/m²、25 °C。`alpha_isc_pct_per_c`、`beta_voc_pct_per_c` 的单位是 %/°C，计算时除以 100。`ideality_factor` 是单片二极管理想因子，`series_ohm` 是单片串联电阻。`bifaciality_factor` 把背板辐照度折算到正面。

电池热电压按 `a_cell = ideality_factor * k * (temperature_c + 273.15) / q` 计算。温度修正后的短路电流记为 `Isc(T)`，开路电压记为 `Voc(T)`；饱和电流取 `I0 = Isc(T) / exp(Voc(T) / a_cell)`。

一个旁路区的有效辐照度为 `front_irradiance_w_m2 + bifaciality_factor * rear_irradiance_w_m2`。光生电流为 `Iph = Isc(T) * G_eff / 1000`。未旁路时区端电压为：

```text
V = cells * a_cell * ln((Iph - I) / I0) - I * cells * series_ohm
```

当 `I >= Iph` 或 `V <= -bypass_forward_v` 时，该区旁路，区端电压取 `-bypass_forward_v`。整串电压为各区电压之和。

## bypass

输入还要有 `current_a`，`sections` 中每项有 `id`、`cells`、`front_irradiance_w_m2`、`rear_irradiance_w_m2`。按上面的区模型判断哪些区旁路。

输出只有一个字段 `bypassed_section_ids`，按输入中的区顺序排列。

## irradiance

输入有 `temperature_c`、`reference_irradiance_w_m2`、`sections` 和 `sweep`。`sweep` 每项包含 `current_a`、`voltage_v`，按电流升序排列；电压保留 5 位小数。各区电池片数相同。

`reference_irradiance_w_m2` 是单块表计的读数，不能直接复制为各区结果。由整串扫描反演各区的有效辐照度。

每区输出一个取整后的 W/m² 数值，放在 `irradiance_levels_w_m2` 中并按升序排列。

## mpp

输入有 `strings`，每项包含 `id` 和 `curve`。`curve` 中每点包含 `voltage_v`、`current_a`，按电压升序排列。相邻点之间电流按直线变化。多条组串并联时使用同一个工作电压，汇流电流为各串在该电压下的电流之和。

全局最大功率点可能在相邻采样点之间。输入可选 `current_limit_a`；总电流不得超过该值。

输出字段：

- `voltage_v`、`current_a`、`power_w`：保留 3 位小数。
- `string_currents_a`：每条组串在该工作电压下的电流，保留 3 位小数。

同一输入重复执行时，结果保持一致。
