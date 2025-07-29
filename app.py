import streamlit as st
import subprocess
import sys
from pathlib import Path
from PIL import Image
import io

st.title("Sat2Mesh Demo")
buffer = io.StringIO()
sys.stdout = buffer
# Default lat/lon
lat = st.number_input("Latitude", value=22.315, format="%.6f")
lon = st.number_input("Longitude", value=114.173, format="%.6f")
# 初始化 session_state 状态
if "generating" not in st.session_state:
    st.session_state.generating = False
if "generated" not in st.session_state:
    st.session_state.generated = False
# 如果还没点击过按钮
if not st.session_state.generating:
    if st.button("Use Sat2Mesh to Generate Mesh"):
        st.session_state.generating = True
        st.rerun()
print("Running subprocess...")
# 如果点击了按钮，开始生成
if st.session_state.generating and not st.session_state.generated:
    with st.spinner("Generating... This may take 1-5 minutes. It took avg 3min 46s 31ms for me."):
        try:
            result = subprocess.check_output(
                ["python", "mesh_generate.py", "-lat", str(lat), "-lon", str(lon)],
                stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as e:
            pass
            # st.code(e.output.decode(), language="bash")
        try:
            result1 = subprocess.check_output(
                ["python", "gen_view.py"],
                stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as e:
            pass
            # st.code(e.output.decode(), language="bash")
        st.session_state.generated = True
        st.session_state.generating = False

    # Show outputs if they exist
    output_dir = Path("output")
    model_filename = output_dir / f"sat2mesh_output.glb"
    sys.stdout = sys.__stdout__  # 恢复 stdout
    st.text(buffer.getvalue())


    tif_files = list(output_dir.glob("*.tif"))
    png_files = list(output_dir.glob("*.png"))
    if tif_files:
        st.subheader("real sat Images (.tif)")
        cols = st.columns(4)  # 一行 4 列

        for idx, tif_path in enumerate(tif_files):
            with cols[idx % 4]:  # 按列循环
                st.markdown(f"**{tif_path.name}**")
                try:
                    img = Image.open(tif_path)
                    st.image(img, use_container_width=True)
                except Exception:
                    st.warning(f"Cannot preview {tif_path.name}. May not be a displayable image.")

    if png_files:
        st.subheader("gen sat Images (.png)")
        cols = st.columns(4)
        for idx, png_path in enumerate(png_files):
            with cols[idx % 4]:
                st.markdown(f"**{png_path.name}**")
                try:
                    img = Image.open(png_path)
                    st.image(img, use_container_width=True)
                except Exception:
                    st.warning(f"Cannot preview {png_path.name}. May not be a displayable image.")
    if model_filename.exists():
        st.subheader("Generated 3D Model (.glb)")
        st.download_button("Download .glb", model_filename.read_bytes(), file_name=model_filename.name)
