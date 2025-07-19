import streamlit as st
import pandas as pd
import numpy as np

# ----------------------------
# 页面设置
# ----------------------------
st.set_page_config(page_title="50% 缩足阈值计算", layout="wide")
st.title("🐭 Von Frey 50% 缩足阈值计算工具")

# ----------------------------
# 读取数据
# ----------------------------
try:
    code_df = pd.read_csv("编号表.txt", sep="\t")
    k_df = pd.read_csv("k值表.txt", sep="\t", dtype={"测量结果": str})  # 保留前导0
except Exception as e:
    st.error("❌ 无法读取编号表或 k 值表，请确保文件放在项目根目录。")
    st.stop()

# 检查列名
if '克数' not in code_df.columns or '编号' not in code_df.columns or '序号' not in code_df.columns:
    st.error("❌ 编号表格式不正确，必须包含 ‘克数’, ‘编号’, ‘序号’ 列。")
    st.stop()

if '测量结果' not in k_df.columns or 'k值' not in k_df.columns:
    st.error("❌ k 值表格式不正确，必须包含 ‘测量结果’, ‘k值’ 列。")
    st.stop()

# ----------------------------
# 用户输入区域
# ----------------------------
st.sidebar.header("📥 参数设置")

min_weight = st.sidebar.selectbox("选择最小刺激丝克重", options=code_df["克数"].tolist())
max_weight = st.sidebar.selectbox("选择最大刺激丝克重", options=code_df["克数"].tolist())
seq_input = st.sidebar.text_area("输入反应序列（每行一条）", value="0001\n0010\n0101")
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

min_code = sub_df["编号"].min()
max_code = sub_df["编号"].max()

# ✅ 按新逻辑计算 delta（编号最大值 - 最小值）
delta = max_code - min_code
median_order = (min_order + max_order) // 2

st.markdown(f"✅ 已选 {n_fibers} 根刺激丝，中位序号为：`{median_order}`，delta = `最大编号 - 最小编号 = {round(delta, 4)}`")

# ----------------------------
# 主计算逻辑
# ----------------------------
if start:
    st.subheader("📌 计算结果")

    # 清洗 k 值表中测量结果列
    k_df["测量结果"] = (
        k_df["测量结果"]
        .astype(str)
        .str.replace(r"[\s\r\n\t]", "", regex=True)
    )
    k_df["k值"] = pd.to_numeric(k_df["k值"], errors="coerce")

    # 显示所有可用序列
    valid_sequences = sorted(k_df["测量结果"].dropna().unique().tolist())
    st.markdown("### 🧾 当前可用的反应序列（k值表中）")
    st.write(valid_sequences)

    # 处理每一条输入序列
    seq_list = [line.strip() for line in seq_input.strip().splitlines() if line.strip()]
    results = []

    for seq in seq_list:
        # 保留 0 和 1 字符
        seq_clean = ''.join(ch for ch in seq if ch in ['0', '1'])
        st.markdown(f"🧪 匹配中：`{seq_clean}`")

        cur_order = median_order
        for ch in seq_clean:
            if ch == "0":
                cur_order += 1
            elif ch == "1":
                cur_order -= 1
        cur_order = max(min_order, min(max_order, cur_order))  # 防越界

        row = code_df[code_df["序号"] == cur_order]
        if row.empty:
            results.append({"反应序列": seq_clean, "错误": "找不到对应序号"})
            continue

        xf = row["编号"].values[0]
        final_weight = row["克数"].values[0]

        if not k_df["测量结果"].isin([seq_clean]).any():
            results.append({"反应序列": seq_clean, "错误": "k 值表中未找到该序列"})
            continue

        try:
            k_val = float(k_df.loc[k_df["测量结果"] == seq_clean, "k值"].values[0])
        except:
            results.append({"反应序列": seq_clean, "错误": "k 值无法转换为数值"})
            continue

        threshold_log = xf + k_val * delta
        threshold_g = 10 ** threshold_log / 10000

        results.append({
            "反应序列": seq_clean,
            "最后刺激丝克重": final_weight,
            "Xf（编号）": round(xf, 3),
            "k 值": k_val,
            "delta": round(delta, 4),
            "50% 缩足阈值（克）": round(threshold_g, 4)
        })

    df_result = pd.DataFrame(results)
    st.dataframe(df_result, use_container_width=True)

    # 下载按钮
    csv = df_result.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 下载结果为 CSV",
        data=csv,
        file_name="VonFrey_结果.csv",
        mime="text/csv"
    )
