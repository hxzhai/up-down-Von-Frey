import streamlit as st
import pandas as pd
import numpy as np

# ----------------------------
# 页面设置
# ----------------------------
st.set_page_config(page_title="50% 缩足阈值计算", layout="wide")
st.info("👉 请点击左上角的 ‘>>’ 图标展开侧边栏，填写参数后开始计算。")
st.title("🐭 Von Frey 50% 缩足阈值计算工具")

# ----------------------------
# 读取数据
# ----------------------------
try:
    code_df = pd.read_csv("编号表.txt", sep="\t")
    k_df = pd.read_csv("k值表.txt", sep="\t", dtype={"测量结果": str})
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

# ✅ 使用 log10(克重) 编号计算 δ
log_codes = np.log10(sub_df["克数"].values)
delta_log = (max(log_codes) - min(log_codes)) / (len(log_codes) - 1)

with st.expander("📘 查看 log10(克重) 编号与 δ", expanded=False):
    st.markdown("**所选刺激丝克重（单位：g）**")
    st.write(sub_df["克数"].tolist())
    st.markdown("**log10(克重) 编号**")
    st.write([round(v, 4) for v in log_codes])
    st.markdown(
        f"📐 δ = (最大 log10 克重编号 - 最小编号) / (n - 1) = "
        f"{round(max(log_codes), 4)} - {round(min(log_codes), 4)} / ({len(log_codes) - 1}) = "
        f"`{round(delta_log, 4)}`"
    )

# ----------------------------
# 主计算逻辑
# ----------------------------
if start:
    st.subheader("📌 计算结果")

    # 清洗 K 值表
    k_df["测量结果"] = k_df["测量结果"].astype(str).str.replace(r"[\s\r\n\t]", "", regex=True)
    k_df["k值"] = pd.to_numeric(k_df["k值"], errors="coerce")

    seq_list = [line.strip() for line in seq_input.strip().splitlines() if line.strip()]
    results = []

    for seq in seq_list:
        seq_clean = ''.join(ch for ch in seq if ch in ['0', '1'])

        # 记录路径，找出最后一次测量的刺激丝（倒数第2个）
        cur_order = median_order
        path = [cur_order]
        for ch in seq_clean:
            if ch == "0":
                cur_order += 1
            elif ch == "1":
                cur_order -= 1
            cur_order = max(min_order, min(max_order, cur_order))
            path.append(cur_order)

        if len(path) < 2:
            results.append({"反应序列": seq_clean, "错误": "序列太短，无法计算"})
            continue
        last_order = path[-2]

        row = code_df[code_df["序号"] == last_order]
        if row.empty:
            results.append({"反应序列": seq_clean, "错误": "找不到对应序号"})
            continue

        final_weight = row["克数"].values[0]
        xf_log = np.log10(final_weight)  # ✅ 用 log10(克重) 作为编号

        if not k_df["测量结果"].isin([seq_clean]).any():
            results.append({"反应序列": seq_clean, "错误": "k 值表中未找到该序列"})
            continue

        try:
            k_val = float(k_df.loc[k_df["测量结果"] == seq_clean, "k值"].values[0])
        except:
            results.append({"反应序列": seq_clean, "错误": "k 值无法转换为数值"})
            continue

        threshold_log = xf_log + k_val * delta_log
        threshold_g = 10 ** threshold_log / 10000

        results.append({
            "反应序列": seq_clean,
            "最后刺激丝克重": final_weight,
            "Xf = log10(克重)": round(xf_log, 4),
            "k 值": k_val,
            "δ": round(delta_log, 4),
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
