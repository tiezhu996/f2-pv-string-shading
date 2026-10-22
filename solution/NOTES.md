# 参考解说明

## 三个难点

| 编号 | 错误认知 | 正确知识 | 对应测试（tests/scoring.json） |
|---|---|---|---|
| difficulty_1 | 只按正面辐照度判断组端状态 | 双面组件的有效辐照度包含背板贡献；温度修正后的光生电流决定旁路边界 | test_bifacial_gain_changes_bypass_state、test_temperature_corrected_current_at_knee、test_hot_module_boundary_uses_isc_coefficient |
| difficulty_2 | 把参考辐照度当成每个旁路区的辐照度 | 整串 V-I 曲线是各区伏安特性之和，需要从曲线膝点反演各区辐照度 | test_three_irradiance_levels_are_recovered、test_close_levels_near_bypass_knees_are_resolved、test_alternating_dark_and_bright_levels_are_recovered |
| difficulty_3 | 只在输入折线的采样点比较功率，并忽略逆变器限流 | 并联后各段电流随电压线性变化，功率在段内是二次函数；可行域还受电流上限约束 | test_single_curve_interior_maximum、test_parallel_misaligned_curves_share_one_voltage、test_interior_vertex_beats_all_scan_points |

## 参考解文件

- `solution/app/pv_physics.py`：单二极管、温度修正、双面有效辐照度和旁路判定。
- `solution/app/irradiance.py`：从扫描曲线差分定位膝点，再按曲线残差细化各层辐照度。
- `solution/app/mpp.py`：合并并联曲线的电压断点，并在每段求二次功率极值。
- `solution/app/main.py`：三种计算的入口和输出格式。
- `solve.sh`：安装完整实现，并支持 `HTB_SKIP` 将单个难点退回原写法。

## 关键步骤

1. 按 `Isc(T) = Isc25 * (1 + alpha%/100 * (T - 25))` 与 `Voc(T) = Voc25 * (1 + beta%/100 * (T - 25))` 得到电池温度下的参数。
2. 有效辐照度为 `front + bifaciality * rear`；光生电流与有效辐照度成正比。
3. 单区有效电压低于旁路压降或电流达到光生电流时，区电压钳位到 `-bypass_forward_v`。
4. 整串电压为各区电压之和。扫描曲线膝点对应各区的光生电流，把差分膝点与多组确定性初值送入全曲线残差细化，保留重复层和相邻层。
5. 并联曲线在每个电压断点处各自线性插值并求和。每段的总电流随电压线性变化，对 `P = V*I(V)` 求段内驻点；有 `current_limit_a` 时再加入总电流等于上限的交点，过滤不可行点后取全局最大值。

## 核心公式与独立复算

- 解析推导：`research/derivations.md` 第 1 至 3 节。
- 独立数值复核：`research/verify_pv_audit.py`，按 1 mV 电压网格重算三组 MPP，并读取独立生成器保存的真值。
- 两条路径差异：MPP 最大差异小于 0.001 W；辐照度层级由生成器真值与差分反演两条路径互证。
- 最终容差：辐照度每层 4 W/m²；MPP 电压和电流 0.002，功率 0.015 W。测试输入电压保留 5 位小数，正常插值误差低于上述阈值。

## 权重依据

- gate 测试不计分：入口可运行、错误参数退出码和 JSON 基本格式。
- difficulty_1 合计 0.40：旁路状态直接决定遮挡区判定，是现场审计的主结果。
- difficulty_2 合计 0.30：辐照度分层是下一步运维派工的依据。
- difficulty_3 合计 0.30：全局 MPP 决定逆变器工作点校核。

## 数据来源

- 真实数据：本题未使用生产数据。
- 生成数据：`research/pv_reference.py` 按输入中公开的单二极管关系生成，固定参数和案例写在脚本中，无随机过程。复现命令为 `python3 research/pv_reference.py`。
- 生成说明不在 `environment/` 内。

## 答案隔离

- [x] 镜像内没有 `tests/`、`solution/`、`.git/`、缓存和备份
- [x] 注释、文件名、变量名、数据元信息没有答案提示
- [x] Dockerfile 没有先复制正确版本再改坏
