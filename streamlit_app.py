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
    k_df = pd.read_csv("k值表.txt", sep="\t")
except Exception as e:
    st.error("❌ 无法读取编号表或k值表，请确保文件放在项目根目录。")
    st.stop()

if '克数' not in code_df.columns or '编号' not in code_df.columns or '序号' not in code_df.columns:
    st.error("❌ 编号表格式不正确，必须包含‘克数’, ‘编号’, ‘序号’列。")
    st.stop()

if '测量结果' not in k_df.columns or 'k值' not in k_df.columns:
    st.error("❌ k值表格式不正确，必须包含‘测量结果’, ‘k值’列。")
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
# 计算准备：按钮外，提前定义变量
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
delta = (max_code - min_code) / (n_fibers - 1)
median_order = (min_order + max_order) // 2

st.markdown(f"✅ 已选 {n_fibers} 根刺激丝，中位序号为：`{median_order}`，delta = `{round(delta, 4)}`")

# ----------------------------
# 主计算逻辑
# ----------------------------
if start:
    st.subheader("📌 计算结果")

    # 清洗 k 值表数据
    k_df["测量结果"] = (
        k_df["测量结果"]
        .astype(str)
        .str.replace(r"[\s\r\n\t]", "", regex=True)
    )
    k_df["k值"] = pd.to_numeric(k_df["k值"], errors="coerce")

    seq_list = [line.strip() for line in seq_input.strip().splitlines() if line.strip()]
    results = []

    for seq in seq_list:
        # 清洗用户输入
        seq_clean = (
            seq.strip()
            .replace(" ", "")
            .replace("\t", "")
            .replace("\r", "")
            .replace("\n", "")
        )

        cur_order = median_order
        for ch in seq_clean:
            if ch == "0":
                cur_order += 1
            elif ch == "1":
                cur_order -= 1
        cur_order = max(min_order, min(max_order, cur_order))  # 防止越界

        row = code_df[code_df["序号"] == cur_order]
        if row.empty:
            results.append({"反应序列": seq_clean, "错误": "找不到对应序号"})
            continue

        xf = row["编号"].values[0]
        final_weight = row["克数"].values[0]

        # 更鲁棒的匹配方式
        if not k_df["测量结果"].isin([seq_clean]).any():
            results.append({"反应序列": seq_clean, "错误": "k值表中未找到该序列"})
            continue

        try:
            k_val = float(k_df.loc[k_df["测量结果"] == seq_clean, "k值"].values[0])
        except:
            results.append({"反应序列": seq_clean, "错误": "k值无法转换为数值"})
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

    st.dataframe(pd.DataFrame(results), use_container_width=True)
