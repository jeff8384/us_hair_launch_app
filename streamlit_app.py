"""Streamlit app entry point for US Hair Launch — Streamlit Cloud deployment."""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="US Hair Launch",
    page_icon="💇",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session-state defaults
# ---------------------------------------------------------------------------
if "gemini_api_key" not in st.session_state:
    st.session_state["gemini_api_key"] = ""


# ---------------------------------------------------------------------------
# Helper: lazy import of pipeline (avoids import errors at module level when
# optional deps are not installed)
# ---------------------------------------------------------------------------
def _run_pipeline(uploaded_files: list, api_key: str):
    """Save uploaded files to a temp dir, run the pipeline, return result + md."""
    from us_hair_launch.pipeline import run_pipeline

    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out, tempfile.TemporaryDirectory() as tmp_exp, tempfile.TemporaryDirectory() as tmp_sch:
        # Save uploaded files
        for uploaded_file in uploaded_files:
            dest = Path(tmp_in) / uploaded_file.name
            dest.write_bytes(uploaded_file.read())

        result = run_pipeline(
            input_dir=tmp_in,
            output_dir=tmp_out,
            exports_dir=tmp_exp,
            schema_dir=tmp_sch,
            ai_backend="gemini",
            ai_api_key=api_key,
        )

        md_path = Path(tmp_exp) / "pdp_copy_drafts.md"
        md_text = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
        return result, md_text


# ---------------------------------------------------------------------------
# Screen 1: API Key input
# ---------------------------------------------------------------------------
def _page_api_key() -> None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🔑 Google AI Studio API Key")
        st.markdown(
            "이 앱은 **Google Gemini API**를 사용합니다.  \n"
            "[Google AI Studio](https://aistudio.google.com/app/apikey)에서 무료 API Key를 발급받으세요."
        )
        st.divider()
        with st.form("api_key_form"):
            key_input = st.text_input(
                "API Key",
                type="password",
                placeholder="AIza...",
                help="입력한 Key는 현재 세션 메모리에만 저장되며 서버에 기록되지 않습니다.",
            )
            submitted = st.form_submit_button("시작하기 →", use_container_width=True)

        if submitted:
            key = key_input.strip()
            if not key:
                st.error("API Key를 입력해주세요.")
            elif not key.startswith("AI"):
                st.warning("Google AI Studio API Key는 'AI'로 시작합니다. 확인해주세요.")
                st.session_state["gemini_api_key"] = key
                st.rerun()
            else:
                st.session_state["gemini_api_key"] = key
                st.rerun()


# ---------------------------------------------------------------------------
# Screen 2: Main app
# ---------------------------------------------------------------------------
def _page_main() -> None:
    api_key: str = st.session_state["gemini_api_key"]

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ 설정")
        st.success("✅ Gemini API Key 설정됨")
        if st.button("🔄 API Key 재설정"):
            st.session_state["gemini_api_key"] = ""
            st.rerun()
        st.divider()
        st.markdown(
            "**모델:** `gemini-2.0-flash`  \n"
            "**AI 백엔드:** Google Gemini"
        )

    st.title("💇 US Hair Launch App")
    st.markdown("경쟁사 헤어케어 데이터를 분석하여 PDP 카피 초안을 생성합니다.")
    st.divider()

    # File upload
    st.subheader("📁 데이터 파일 업로드")
    st.markdown(
        "Sephora / Ulta 경쟁사 데이터 파일을 업로드하세요. (`.csv` 또는 `.xlsx`)"
    )
    uploaded_files = st.file_uploader(
        "파일 선택",
        type=["csv", "xlsx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if not uploaded_files:
        st.info("📂 파일을 업로드하면 파이프라인을 실행할 수 있습니다.")
        return

    st.success(f"{len(uploaded_files)}개 파일 업로드됨: {', '.join(f.name for f in uploaded_files)}")

    st.divider()
    st.subheader("🚀 파이프라인 실행")

    if st.button("파이프라인 실행 (Gemini AI)", type="primary", use_container_width=True):
        with st.spinner("Gemini AI로 분석 중... 잠시 기다려주세요."):
            try:
                result, md_text = _run_pipeline(uploaded_files, api_key)
            except Exception as exc:
                st.error(f"❌ 파이프라인 실행 중 오류 발생:\n\n`{exc}`")
                return

        st.success("✅ 파이프라인 완료!")

        # Summary metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("정규화된 레코드", result.normalized_count)
        col2.metric("추출된 클레임", result.claims_count)
        col3.metric("소매점", ", ".join(result.retailers) if result.retailers else "—")

        if result.diagnostics:
            with st.expander("⚠️ 진단 메시지"):
                for msg in result.diagnostics:
                    st.warning(msg)

        st.divider()
        st.subheader("📄 PDP 카피 초안 (Markdown)")

        if md_text:
            st.markdown(md_text)
            st.download_button(
                label="⬇️ Markdown 다운로드",
                data=md_text.encode("utf-8"),
                file_name="pdp_copy_drafts.md",
                mime="text/markdown",
                use_container_width=True,
            )
        else:
            st.warning("마크다운 출력이 생성되지 않았습니다.")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
def main() -> None:
    if not st.session_state["gemini_api_key"]:
        _page_api_key()
    else:
        _page_main()


if __name__ == "__main__":
    main()
else:
    # Streamlit runs module at top level; call main() unconditionally.
    main()
