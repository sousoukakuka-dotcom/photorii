# =============================
# ImageMagick
# =============================

import streamlit as st
from openai import OpenAI
from moviepy.editor import *
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
import tempfile
import os
import datetime

VIDEO_W = 720
VIDEO_H = 1280

# =============================
# 初期ステップ管理
# =============================
if "step" not in st.session_state:
    st.session_state.step = 1

st.markdown("<h1 style='text-align:center;'>フォトリ</h1>", unsafe_allow_html=True)

# =============================
# 色味調整
# =============================
def color_grade(img_array, emotion):
    img = Image.fromarray(img_array)

    if emotion == "ありがとう":
        img = ImageEnhance.Brightness(img).enhance(1.05)
        img = ImageEnhance.Color(img).enhance(1.1)

    elif emotion == "だいすき":
        img = ImageEnhance.Brightness(img).enhance(1.08)
        img = ImageEnhance.Color(img).enhance(1.15)

    else:
        img = ImageEnhance.Brightness(img).enhance(0.95)
        img = ImageEnhance.Color(img).enhance(0.9)

    return np.array(img)

# =============================
# Ken Burns
# =============================
def apply_kenburns(clip, emotion, duration):
    if emotion == "ありがとう":
        return clip.resize(lambda t: 1 + 0.03*(t/duration))
    elif emotion == "だいすき":
        zoom = clip.resize(lambda t: 1 + 0.025*(t/duration))
        return zoom.set_position(lambda t: ("center", int(5*np.sin(t))))
    else:
        return clip.resize(lambda t: 1.04 - 0.03*(t/duration))

# =============================
# 固定ブリッジ
# =============================
def get_bridges(emotion):
    if emotion == "ありがとう":
        return ["ほんとはね、", "ちゃんと気づいてたよ", "あのときも、", "これからもね"]
    elif emotion == "だいすき":
        return ["ねぇ、", "しってる？", "いちばんね、", "ずっとね、"]
    else:
        return ["いつか、", "でもね、", "すこしずつ、", "それでも、"]

# =============================
# STEP 1
# =============================
if st.session_state.step == 1:

    st.markdown("### 🎁 誰に贈りますか？")

    if st.button("👨 パパへ", use_container_width=True):
        st.session_state.target = "パパへ"
        st.session_state.step = 2

    if st.button("👩 ママへ", use_container_width=True):
        st.session_state.target = "ママへ"
        st.session_state.step = 2

# =============================
# STEP 2
# =============================
elif st.session_state.step == 2:

    st.markdown("### 💛 残したい気持ちは？")

    if st.button("ありがとう", use_container_width=True):
        st.session_state.emotion = "ありがとう"
        st.session_state.step = 3

    if st.button("だいすき", use_container_width=True):
        st.session_state.emotion = "だいすき"
        st.session_state.step = 3

    if st.button("さみしい", use_container_width=True):
        st.session_state.emotion = "さみしい"
        st.session_state.step = 3

    if st.button("← 戻る"):
        st.session_state.step = 1

# =============================
# STEP 3
# =============================
elif st.session_state.step == 3:

    st.markdown("### 📸 写真を最大5枚選んでください")

    images = st.file_uploader("", accept_multiple_files=True)

    if images:
        st.session_state.images = images
        st.session_state.step = 4

    if st.button("← 戻る"):
        st.session_state.step = 2

# =============================
# STEP 4
# =============================
elif st.session_state.step == 4:

    st.markdown("### 🎬 動画を生成します")

    if st.button("✨ 動画をつくる", use_container_width=True):

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

        photo_arrays = []

        for img in st.session_state.images[:5]:
            img_bytes = img.read()
            img_array = np.array(Image.open(tempfile.NamedTemporaryFile(delete=False)))
            img_array = np.array(Image.open(img))
            img_array = color_grade(img_array, st.session_state.emotion)
            photo_arrays.append(img_array)

        # =============================
        # 本文生成
        # =============================
        if st.session_state.target == "パパへ":
            tone = "少し照れくさいけどまっすぐな語り口"
        else:
            tone = "やさしくて甘えがにじむ語り口"

        story_prompt = f"""
        娘から{st.session_state.target}への手紙を{len(photo_arrays)}行。
        {tone}
        感情：{st.session_state.emotion}
        最後は問いかけ。
        改行のみ。
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":story_prompt}],
            temperature=0.9
        )

        lines = response.choices[0].message.content.split("\n")
        lines = [l.strip() for l in lines if l.strip()!=""]

        while len(lines) < len(photo_arrays):
            lines.append("ありがとう。")

        lines = lines[:len(photo_arrays)]

        bridges = get_bridges(st.session_state.emotion)

        clips = []

        for i, img_array in enumerate(photo_arrays):

            duration = 5 if i < len(photo_arrays)-1 else 8

            base = ImageClip(img_array).set_duration(duration)
            fg = apply_kenburns(base, st.session_state.emotion, duration)

            txt = TextClip(
                lines[i],
                font="C:/Windows/Fonts/meiryo.ttc",
                fontsize=42,
                color="white",
                method="caption",
                size=(VIDEO_W-100,None)
            ).set_position(("center", VIDEO_H-240)) \
             .set_start(1.0) \
             .set_duration(duration-1.0) \
             .crossfadein(1.2)

            video = CompositeVideoClip([fg, txt], size=(VIDEO_W,VIDEO_H)).fadeout(1.0)
            clips.append(video)

            if i < len(photo_arrays)-1 and i < len(bridges):
                bridge_bg = ColorClip((VIDEO_W, VIDEO_H), color=(0,0,0)).set_duration(1.8)
                bridge_txt = TextClip(
                    bridges[i],
                    font="C:/Windows/Fonts/meiryo.ttc",
                    fontsize=36,
                    color="white"
                ).set_position("center").set_duration(1.8)
                clips.append(CompositeVideoClip([bridge_bg, bridge_txt]))

        final_video = concatenate_videoclips(clips)

        # ブランド（最後だけ）
        brand = TextClip(
            "フォトリ",
            font="C:/Windows/Fonts/meiryo.ttc",
            fontsize=28,
            color="white"
        ).set_position(("center", VIDEO_H-100)) \
         .set_start(final_video.duration-3) \
         .set_duration(3) \
         .crossfadein(1)

        final_video = CompositeVideoClip([final_video, brand])

        filename = f"photorii_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        final_video.write_videofile(filename, fps=12)

        st.video(filename)
        st.success("完成しました！")

    if st.button("← 戻る"):

        st.session_state.step = 3
