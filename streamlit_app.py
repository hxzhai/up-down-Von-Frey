import streamlit as st
import pandas as pd
import numpy as np

# ----------------------------
# 页面设置
# ----------------------------
st.set_page_config(page_title="50% 缩足阈值计算", layout="wide")
st.info("👉 请点击左上角的 '»»' 图标展开侧边栏，填写参数后开始计算。")
st.title("🐭 Von Frey 50% 缩足阈值计算工具")

# ----------------------------
# 读取数据
# ----------------------------
try:
    code_df = pd.read_csv("编号表.txt", sep="\t")
    k_df = pd.read_csv("k值表.txt", sep="\t", dtype={"测量结果": str})  # 保留前导 0
except Exception as e:
    st.error("❌ 无法读取编号表或 k 值表，请确保文件放在项目根目录。")
    st.stop()

if '克数' not in code_df.columns or '序号' not in code_df.columns:
    st.error("❌ 编号表格式不正确，必须包含 '克数'、'序号' 列。")
    st.stop()

if '测量结果' not in k_df.columns or 'k值' not in k_df.columns:
    st.error("❌ k 值表格式不正确，必须包含 '测量结果'、'k值' 列。")
    st.stop()

# ✅ 替换编号列为 log10(克重 × 10000)
code_df["编号"] = np.log10(code_df["克数"] * 10000)

# ----------------------------
# 用户输入区域 + 说明
# ----------------------------
with st.sidebar.expander("📐 方法原理与操作说明（点击展开）", expanded=False):
    st.markdown("""
### 📐 方法原理简介

本工具依据 **Dixon 提出的 Up-Down 方法**，对一系列 Von Frey 刺激丝的刺激结果进行逻辑回溯，结合实验所用纤维丝的编号间距（δ）与匹配的经验值 k 值，计算 50% 缩足反应的刺激强度阈值。

**计算公式：**  
  50% 缩足阈值（克） = 10 ^ (Xf + k × δ) / 10000

其中：
- **Xf**：最后一次测试纤维丝的对数编号（log₁₀(克重 × 10000)）
- **k**：与反应序列对应的经验系数（由表查得）
- **δ**：刺激丝编号之间的平均间距（log₁₀ 编号差值）

---

### 🧪 Von Frey 操作说明

1. **选择测试用刺激丝：**  
   建议选取 **5～9 根克重连续、编号间距近似均匀** 的 Von Frey 刺激丝作为测试组。

2. **确定起始刺激丝：**  
   测试应从所选刺激丝中 **中间克重的一根** 开始刺激。

3. **记录反应序列（0/1）：**
   - 0 表示阴性反应（无缩足）
   - 1 表示阳性反应（有缩足）
   - 每次根据反应结果选择下一根刺激丝：
     - **阳性 → 更轻的纤维丝**
     - **阴性 → 更重的纤维丝**

4. **终止条件：**  
   首次观察到阴阳转变后，**继续测试 4 次**终止。

5. **输入反应序列：**  
   每行输入一组完整反应序列（如 `000101`），从最中间克重的纤维丝开始记录。

---
如需帮助请联系维护者：zhaihexin1999@163.com
    """)

st.sidebar.header("📅 参数设置")
min_weight = st.sidebar.selectbox("选择最小刺激丝克重", options=code_df["克数"].tolist())
max_weight = st.sidebar.selectbox("选择最大刺激丝克重", options=code_df["克数"].tolist())
seq_input = st.sidebar.text_area("输入反应序列（每行一条）")
start = st.sidebar.button("🚀 开始计算")

# ----------------------------
# 计算准备
# ----------------------------
sub_df = code_df[(code_df["克数"] >= min_weight) & (code_df["克数"] <= max_weight)].copy()

if sub_df.empty:
    st.error("❌ 所选克重范围无匹配，请重新选择。")
    st.stop()

min_order = sub_df["序号"].min()
max_order = sub_df["序号"].max()
n_fibers = max_order - min_order + 1
median_order = (min_order + max_order) // 2

st.markdown(f"✅ 已选 {n_fibers} 根刺激丝，中位序号为：`{median_order}`")

delta = (sub_df["编号"].max() - sub_df["编号"].min()) / (max_order - min_order)

# ----------------------------
# 主计算逻辑
# ----------------------------
if start:
    st.subheader("🔹 计算结果")

    k_df["测量结果"] = k_df["测量结果"].astype(str).str.replace(r"[\s\r\n\t]", "", regex=True)
    k_df["k值"] = pd.to_numeric(k_df["k值"], errors="coerce")

    seq_list = [line.strip() for line in seq_input.strip().splitlines() if line.strip()]
    results = []

    for idx, seq in enumerate(seq_list, start=1):
        seq_clean = ''.join(ch for ch in seq if ch in ['0', '1'])
        restored_seq = seq_clean.replace("0", "O").replace("1", "X")

        cur_order = median_order
        for ch in seq_clean[:-1]:  # ✅ 推断最后刺激丝
            if ch == "0":
                cur_order += 1
            elif ch == "1":
                cur_order -= 1
            cur_order = max(min_order, min(max_order, cur_order))

        row = code_df[code_df["序号"] == cur_order]
        if row.empty:
            results.append({"序号": idx, "反应序列": seq_clean, "错误": "找不到对应序号"})
            continue

        xf = row["编号"].values[0]
        final_weight = row["克数"].values[0]

        if not k_df["测量结果"].isin([seq_clean]).any():
            results.append({"序号": idx, "反应序列": seq_clean, "错误": "k 值表中未找到该序列"})
            continue

        try:
            k_val = float(k_df.loc[k_df["测量结果"] == seq_clean, "k值"].values[0])
        except:
            results.append({"序号": idx, "反应序列": seq_clean, "错误": "k 值无法转换为数值"})
            continue

        threshold_log = xf + k_val * delta
        threshold_g = 10 ** threshold_log / 10000

        results.append({
            "序号": idx,
            "反应序列": seq_clean,
            "序列还原": restored_seq,
            "所选克重范围": f"{min_weight}g - {max_weight}g",
            "最后刺激丝克重": final_weight,
            "Xf": round(xf, 3),
            "k 值": k_val,
            "δ": round(delta, 4),
            "50% 缩足阈值（克）": round(threshold_g, 4)
        })

    df_result = pd.DataFrame(results)
    st.dataframe(df_result, use_container_width=True)

    csv = df_result.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 下载结果为 CSV",
        data=csv,
        file_name="VonFrey_结果.csv",
        mime="text/csv"
    )
